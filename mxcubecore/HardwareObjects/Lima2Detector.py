import logging
import os
import time
from contextlib import ExitStack
from uuid import uuid1

import gevent
from gevent import subprocess
from lima2.client import Detector
from lima2.client.smx.aggregation import create_virtual_dataset

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.CommandContainer import ConnectionError
from mxcubecore.HardwareObjects.abstract.AbstractDetector import AbstractDetector
from mxcubecore.TaskUtils import task

_logger = logging.getLogger("HWR")

_logger_det = logging.getLogger("lima2.client.detector")
_logger_smx = logging.getLogger("lima2.client.smx")

_logger_det.setLevel(logging.DEBUG)
_logger_smx.setLevel(logging.DEBUG)

# Logger decorator
def logger(fn):
    def inner(*args, **kwargs):
        _logger.debug(f"Entering %s", fn.__name__)
        to_execute = fn(*args, **kwargs)
        _logger.debug(f"Exiting %s", fn.__name__)
        return to_execute

    return inner

def convert_state(state):
    """Convert detector state to MxCube HWR state"""
    # UNKNOWN = 0
    # WARNING = 1
    # BUSY = 2
    # READY = 3
    # FAULT = 4
    # OFF = 5
    if state == Detector.State.IDLE or state == Detector.State.PREPARED:
        s = HardwareObjectState.READY
    elif state == Detector.State.RUNNING:
        s = HardwareObjectState.BUSY
    else:
        s = HardwareObjectState.UNKNOWN
    return s

def create_directory(path, check=True):
    subprocess.run(
        "mkdir --parents {0} && chmod -R 755 {0}".format(path),
        shell=True,
        check=check,
    )


class Lima2Detector(AbstractDetector):
    def __init__(self, name):
        AbstractDetector.__init__(self, name)
        self.header = dict()
        self.start_angles = list()

    def init(self):
        AbstractDetector.init(self)

        lima_ctrl_device = self.get_property("lima_ctrl_device", "")
        # lima_recv_devices = ast.literal_eval(self.get_property("lima_recv_devices", ""))
        lima_recv_devices = self.get_property("lima_recv_devices", "").split(",")

        _logger.info(
            f"Initializing Lima2Detector: {lima_ctrl_device} {lima_recv_devices}"
        )

        if not lima_ctrl_device or not len(lima_recv_devices) >= 1:
            return

        try:
            self.__device = Detector(lima_ctrl_device, *lima_recv_devices)

            self.__acq_params = self.__device.acq_params
            self.__proc_params = self.__device.proc_params

            # Monitor device state
            def on_state_change(state):
                s = convert_state(state)
                _logger.info(f"State changed to {state} / {s}")
                self.update_state(s)
            self.__device.registerStateLogger(on_state_change)

            self.__proc_loop_task = None
        except ConnectionError:
            self.update_state(HardwareObjectState.FAULT)
            _logger.error("Could not connect to detector %s" % lima_device)
            self._emit_status()

    def has_shutterless(self):
        return True

    @logger
    def wait_idle(self, timeout=3500):
        with gevent.Timeout(timeout, RuntimeError("Detector not idle")):
            idle_states = [Detector.State.IDLE, Detector.State.FAULT]
            while self.__device.state not in idle_states:
                print(self.__device.state)
                gevent.sleep(1)

            proc = self.__proc_loop_task
            if proc:
                _logger.debug("waiting for previous processing to finish")
                gevent.wait([proc])

    @logger
    def wait_prepared(self, timeout=3500):
        with gevent.Timeout(timeout, RuntimeError("Detector not prepared")):
            while self.__device.state != Detector.State.PREPARED:
                gevent.sleep(1)

    @logger
    def last_image_saved(self):
        try:
            img = 0  # TODO
            return img
        except Exception:
            return 0

    def get_deadtime(self):
        return float(self.get_property("deadtime"))

    def find_next_pedestal_dir(self, data_root_path, subdir):
        _index = 1
        _indes_str = "%04d" % _index
        fpath = os.path.join(data_root_path, f"{subdir}_{_indes_str}")

        while os.path.exists(fpath):
            _index += 1
            _indes_str = "%04d" % _index
            fpath = os.path.join(data_root_path, f"{subdir}_{_indes_str}")

        return fpath

    def set_detector_filenames(self, data_root_path, prefix):
        create_directory(data_root_path)

    @logger
    def prepare_acquisition(self, number_of_images, exptime, data_root_path, prefix):
        packet_fifo_depth = 20000

        acq_params = {
            "acq": {
                "expo_time": int(exptime * 1e6),
                # "latency_time": 990,
                "nb_frames": number_of_images,
                "trigger_mode": "external",
                "nb_frames_per_trigger": 1,
            },
            "det": {
                "gain_mode": "dynamic",
                "packet_fifo_depth": packet_fifo_depth,
            },
        }

        self.set_detector_filenames(data_root_path, prefix)

        saving_groups = ["raw", "dense", "sparse", "accumulated"]

        # all streams will be saved in dedicated sub dirs except dense
        data_sub_dir = {g: g if g != "dense" else "" for g in saving_groups}

        data_path = {
            g: os.path.join(data_root_path, s) if s else data_root_path
            for g, s in data_sub_dir.items()
        }

        acc_frames = 1000

        max_nb_frames_per_file = dict(
            raw=1000,
            dense=1000,
            sparse=10000,
            accumulated=10,
        )

        nb_recvs = 2
        nb_recv_frames = number_of_images // nb_recvs
        nb_acc_frames = (number_of_images - 1) // acc_frames + 1

        nb_frames = {
            g: nb_acc_frames if g == "accumulated" else nb_recv_frames
            for g in saving_groups
        }

        def calc_frame_per_file(group, n):
            return min(max_nb_frames_per_file[group], n)

        frames_per_file = {
            g: calc_frame_per_file(g, nb_frames[g]) for g in saving_groups
        }

        save_files = dict(
            raw=False,
            dense=True,
            sparse=True,
            accumulated=True,
        )

        dense_comp_with_hw_nx = True
        dense_comp = "zip" if dense_comp_with_hw_nx else "bshuf_lz4"

        compression = dict(
            raw=dense_comp, dense=dense_comp, sparse="none", accumulated="zip"
        )

        saving_streams = ["raw", "dense", "sparse"] + [
            f"accumulation_{a}" for a in ["corrected", "peak"]
        ]

        def get_stream_group(stream):
            is_acc = stream.startswith("accumulation_")
            return "accumulated" if is_acc else stream

        def get_stream_prefix(stream):
            return stream.replace("accumulation", "acc")

        def get_saving(stream):
            group = get_stream_group(stream)
            stream_prefix = get_stream_prefix(stream)
            return dict(
                enabled=save_files[group],
                base_path=data_path[group],
                filename_prefix=f"{prefix}_{stream_prefix}",
                start_number=0,
                nb_frames_per_file=frames_per_file[group],
                file_exists_policy="abort",
                compression=compression[group],
            )

        sub_dirs = [s for g, s in data_sub_dir.items() if s and save_files[g]]
        # the sub directory for aggregated data from all receivers
        sub_dirs.append("aggregated")
        for s in sub_dirs:
            create_directory(os.path.join(data_root_path, s))

        fai_kernels_base = self.get_property("fai_kernels_base", "")
        params_base = self.get_property("params_base", "")
        pedestal_path = os.path.join(data_root_path, "pedestal.h5")

        mask_beam_stop = True
        mask_filename = "mask.h5" if mask_beam_stop else "mask_no_beamstop.h5"

        manage_proc = True

        energy = 11.56  # 9.06

        fai_params = {
            "mask_path": params_base + mask_filename,
            "csr_path": params_base + "csr.h5",
            "radius2d_path": params_base + "r_center.h5",
            "radius1d_path": params_base + "bin_centers.h5",
            "error_model": "azimuthal",
            "dummy": 0.0,
            "delta_dummy": 0.0,
            "normalization_factor": 1.0,
            "cutoff_clip": 5.0,
            "cycle": 5,
            # "empty": -9999.0,
            "noise": 1.0,
            "cutoff_pick": 3.0,
            "acc_nb_frames_reset": 0,
            "acc_nb_frames_xfer": acc_frames,
        }

        def get_dense_out_params(variant_name):
            legacy_photon_adus = 41.401 * energy

            variant_data = {
                "legacy": dict(
                    pixel_type="int32", photon_adus=legacy_photon_adus, photon_bias=0.0
                ),
                "0": dict(pixel_type="int16", photon_adus=16.0, photon_bias=0.0),
                "1": dict(pixel_type="uint16", photon_adus=16.0, photon_bias=32.0),
                "2": dict(pixel_type="uint16", photon_adus=8.0, photon_bias=32.0),
                "3": dict(pixel_type="int16", photon_adus=8.0, photon_bias=0.0),
            }

            variant = variant_data[variant_name]
            photon_adus = variant["photon_adus"]
            return dict(
                dense_intensity_factor=photon_adus,
                dense_intensity_offset=photon_adus * variant["photon_bias"],
                dense_pixel_type="dense_%s" % variant["pixel_type"],
            )

        dense_variant_name = "legacy"
        fai_params.update(get_dense_out_params(dense_variant_name))

        fai_params_fname = os.path.join(params_base, "fai_params.json")
        if os.path.exists(fai_params_fname):
            with open(fai_params_fname, "rt") as f:
                fai_params.update(json.loads(f.read()))

        proc_params = {
            "proc_mode": "fai",
            "fifo": {
                "nb_fifo_frames": packet_fifo_depth,
            },
            "buffers": {
                "nb_peak_counters_buffer": nb_recv_frames,
            },
            "gpu": {
                "device_idx": 0,
                "cl_source_path": fai_kernels_base,
            },
            "jfrau": {
                "gain_path": params_base + "gains.h5",
                "pedestal_path": pedestal_path,
                "photon_energy": energy,
            },
            "fai": fai_params,
        }

        proc_params.update(
            {f"saving_{stream}": get_saving(stream) for stream in saving_streams}
        )

        self.__device.nb_gpus_per_system = 2

        self.__device.acq_params.update(acq_params)
        _logger.debug("acq_params: %s", self.__device.acq_params)
        self.__device.proc_params.update(proc_params)
        _logger.debug("proc_params: %s", self.__device.proc_params)

        uuid = uuid1()
        _logger.info(f"UUID={uuid}")

        self.__device.prepareAcq(uuid)

        # Async version
        # gevent.spawn(self.__device.prepareAcq, uuid).link_value(on_prepared)

        # Manage processing
        if manage_proc:
            self.__proc_loop_task = gevent.spawn(self.proc_loop, uuid)

    @logger
    def start_acquisition(self):
        self.wait_prepared()

        self.__device.startAcq()

    @logger
    def stop_acquisition(self):
        wait_for_idle_timeout = 10
        try:
            self.wait_idle(wait_for_idle_timeout)
        except:
            _logger.warning("detector not idle after %s", wait_for_idle_timeout)
            pass

        try:
            self.__device.stopAcq()
        except Exception:
            if self.__proc_loop_task:
                gevent.kill(self.__proc_loop_task)
            self.__device.resetAcq()
        finally:
            self.wait_idle()

    @logger
    def proc_loop(self, uuid):
        with ExitStack() as stack:
            def cleanup():
                self.__proc_loop_task = None
            stack.callback(cleanup)

            _logger.debug("starting processing loop for %s", uuid)
            proc_cm = self.__device.getProcessing(uuid, erase_on_cleanup=True)
            proc = stack.enter_context(proc_cm)
            stack.callback(_logger.debug, "erasing processing for %s", uuid)

            # main processing loop
            while not proc.is_finished:
                gevent.sleep(1.0)

    @logger
    def reset(self):
        self.__device.resetAcq()

    @property
    def status(self):
        try:
            acq_status = self.__device.state
        except Exception:
            acq_status = "OFFLINE"

        status = {
            "acq_satus": str(acq_status).upper(),
        }

        return status

    def _emit_status(self):
        self.emit("statusChanged", self.status)
