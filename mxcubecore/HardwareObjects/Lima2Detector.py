import json
import logging
import os
import time
from contextlib import ExitStack
from uuid import uuid1

import gevent
import numpy as np
from gevent import subprocess
from lima2.client import Detector
from lima2.client.smx.aggregation.writer import Writer as SmxAggregationWriter

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.CommandContainer import ConnectionError
from mxcubecore.HardwareObjects.abstract.AbstractDetector import AbstractDetector
from mxcubecore.TaskUtils import task

_logger = logging.getLogger("HWR")

_logger_det = logging.getLogger("lima2.client.detector")
_logger_smx = logging.getLogger("lima2.client.smx")
_logger_smx_aggr = logging.getLogger("lima2.client.smx.aggregation")

_logger_det.setLevel(logging.DEBUG)
_logger_smx.setLevel(logging.DEBUG)
_logger_smx_aggr.setLevel(logging.DEBUG)

lima2_loggers = [_logger_det, _logger_smx, _logger_smx_aggr]

def update_lima2_loggers():
    for tgt_logger in lima2_loggers:
        tgt_logger.setLevel(_logger.getEffectiveLevel())
        for handler in _logger.handlers:
            tgt_logger.addHandler(handler)


# Logger decorator
def logger(fn):
    def inner(*args, **kwargs):
        _logger.debug(f'Entering %s', fn.__name__)
        to_execute = fn(*args, **kwargs)
        _logger.debug(f'Exiting %s', fn.__name__)
        return to_execute

    return inner

def convert_state(state):
    """ Convert detector state to MxCube HWR state """
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
        self.__device = None

    def init(self):
        AbstractDetector.init(self)

        update_lima2_loggers()
        self.image_rejection_settings_file = self.get_property("image_rejection_settings_file")

        lima_ctrl_device = self.get_property("lima_ctrl_device", "")
        #lima_recv_devices = ast.literal_eval(self.get_property("lima_recv_devices", ""))
        lima_recv_devices = self.get_property("lima_recv_devices", "").split(",")

        _logger.info("Initializing Lima2Detector: %s %s", lima_ctrl_device,
                     lima_recv_devices)

        if not lima_ctrl_device or not len(lima_recv_devices) >= 1:
            return

        self.__proc_loop_task = None
        self.__proc_stalled = None
        self.__started = False
        self.__stopped = False

        try:
            self.__device = Detector(lima_ctrl_device, *lima_recv_devices)

            self.__acq_params = self.__device.acq_params
            self.__proc_params = self.__device.proc_params

            # Monitor device state
            def on_state_change(state):
                s = convert_state(state)
                _logger.info("State changed to %s / %s", state, s)
                self.update_state(s)
            self.__device.registerStateLogger(on_state_change)
        except (ConnectionError, AttributeError):
            self.update_state(HardwareObjectState.FAULT)
            _logger.error("Could not connect to detector %s" % lima_ctrl_device)
            self._emit_status()

    def has_shutterless(self):
        return True

    @logger
    def wait_idle(self, timeout=3500):
        with gevent.Timeout(timeout, RuntimeError("Detector not idle")):
            idle_states = [Detector.State.PREPARED, Detector.State.IDLE,
                           Detector.State.FAULT]
            while self.__device.state not in idle_states:
                _logger.debug("State: %s", self.__device.state)
                gevent.sleep(1)
        gevent.sleep(2)
        proc, stalled = self.__proc_loop_task, self.__proc_stalled
        if proc:
            _logger.debug("waiting for processing to finish")
            gevent.wait([proc, stalled])
            if stalled.is_set():
                raise RuntimeError("Processing stalled")

    @logger
    def wait_prepared(self, timeout=3500):
        with gevent.Timeout(timeout, RuntimeError("Detector not prepared")):
            while self.__device.state != Detector.State.PREPARED:
                gevent.sleep(1)

    @logger
    def last_image_saved(self):
        try:
            img = 0 #TODO
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
    def prepare_acquisition(
        self,
        number_of_images,
        exptime,
        data_root_path,
        prefix,
        dense_skip_nohits=False
    ):
        self.__started = False
        self.__stopped = False

        if number_of_images < 1:
            msg = f"Lima2: Invalid number_of_images: {number_of_images}"
            _logger.error(msg)
            raise ValueError(msg)

        update_lima2_loggers()

        dump_params_file_pattern = "lima2_params-%Y-%m-%d-%H%M%S.json"
        file_name = time.strftime(dump_params_file_pattern)
        dump_params_filename = os.path.join(data_root_path, file_name)

        packet_fifo_depth = 20000

        acq_params = {
            "acq": {
                "expo_time": int(exptime * 1e6),
                #"latency_time": 990,
                "nb_frames": number_of_images,
                "trigger_mode": "external",
                "nb_frames_per_trigger": 1,
            },
            "det": {
                "gain_mode": "dynamic",
                "packet_fifo_depth": packet_fifo_depth,
                "auto_comparator_disable": True,
            }
        }

        self.set_detector_filenames(data_root_path, prefix)

        saving_groups = ["raw", "dense", "sparse", "spots", "accumulated"]

        # all streams will be saved in dedicated sub dirs except dense
        data_sub_dir = {
            g: g if g != "dense" else "" for g in saving_groups
        }

        data_path = {
            g: os.path.join(data_root_path, s) if s else data_root_path
            for g, s in data_sub_dir.items()
        }

        acc_frames = 1000

        max_nb_frames_per_file = dict(
            raw=1000,
            dense=1000,
            sparse=1000,
            spots=1000,
            accumulated=1,
        )

        nb_recvs = len(self.__device.recvs)
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
            spots=True,
            accumulated=True,
        )

        dense_comp_with_hw_nx = True
        dense_comp = "zip" if dense_comp_with_hw_nx else "bshuf_lz4"

        compression = dict(
            raw=dense_comp,
            dense=dense_comp,
            sparse="none",
            spots="none",
            accumulated="zip"
        )

        saving_streams = (["raw", "dense", "sparse", "spots"] +
                          [f"accumulation_{a}" for a in ["corrected", "ishit", "nohit"]])

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

        fai_kernels_base = self.get_property("fai_kernels_base", ".")
        params_base = self.get_property("params_base", ".")
        pedestal_path = os.path.join(data_root_path, "pedestal.h5")

        config_beam = None
        config_beam_dict = self.get_property(f"beam", {})
        if config_beam_dict:
            _logger.debug("config_beam_dict=%s", config_beam_dict)
            config_beam = [float(config_beam_dict.get(f"b{i}", "0.0"))
                           for i in "xy"]

        mask_beam_stop = True
        mask_filename = "mask.h5" if mask_beam_stop else "mask_no_beamstop.h5"

        manage_proc = True

        #energy = 11.56
        energy = HWR.beamline.energy.get_value()
        #energy = 12.75
        jungfrau_gain0_ave = 41.401

        def get_param_file(n):
            return os.path.join(params_base, n)

        fai_params = {
            "mask_path": get_param_file(mask_filename),
            "csr_path": get_param_file("csr.h5"),
            "radius2d_path": get_param_file("r_center.h5"),
            "radius1d_path": get_param_file("bin_centers.h5"),
            "error_model": "azimuthal",
            "dummy": 0.0,
            "delta_dummy": 0.0,
            "normalization_factor": 1.0,
            "cutoff_clip": 0,
            "cycle": 3,
            #"empty": -9999.0,
            "noise": 0.5,
            "cutoff_pick": 4.0,
            "patch_size": 5,
            "connected": 7,
            "min_nb_peaks": 20,
            "dense_skip_nohits": dense_skip_nohits,
            "acc_nb_frames_reset": 0,
            "acc_nb_frames_xfer": acc_frames,
        }

        legacy_photon_adus = jungfrau_gain0_ave * energy

        def get_dense_out_params(variant_name):
            variant_data = {
                "i32":   dict(pixel_type="int32",
                              photon_adus=legacy_photon_adus,
                              photon_bias=0.0),
                "i16_1": dict(pixel_type="int16",
                              photon_adus=16.0,
                              photon_bias=0.0),
                "i16_2": dict(pixel_type="int16",
                              photon_adus=8.0,
                              photon_bias=0.0),
                "i16_3": dict(pixel_type="int16",
                              photon_adus=1.0,
                              photon_bias=0.0),
                "u16_1": dict(pixel_type="uint16",
                              photon_adus=16.0,
                              photon_bias=32.0),
                "u16_2": dict(pixel_type="uint16",
                              photon_adus=8.0,
                              photon_bias=32.0),
                "f16":   dict(pixel_type="float16",
                              photon_adus=1.0,
                              photon_bias=0.0),
            }

            variant = variant_data[variant_name]
            photon_adus = variant["photon_adus"]
            return dict(
                dense_intensity_factor=photon_adus,
                dense_intensity_offset=photon_adus * variant["photon_bias"],
                dense_pixel_type="dense_%s" % variant["pixel_type"],
            )

        dense_variant_name = "i32"
        dense_out_params = get_dense_out_params(dense_variant_name)
        fai_params.update(dense_out_params)

        # pf_params_fname = get_param_file("peakfinder_params.json")
        # if os.path.exists(pf_params_fname):
        #     with open(pf_params_fname, "rt") as f:
        #         pf_params = json.load(f)

        fpath = HWR.get_hardware_repository().find_in_repository(
            self.image_rejection_settings_file
        )

        if os.path.exists(fpath):
            _logger.info(f"Reading parameters from {fpath}")
            with open(fpath, "rt") as f:
                pf_params = json.load(f)

            _logger.info(f"Parameters: {pf_params}")

        pixel_size = 75e-6

        _logger.info("peakfinder params: %s", pf_params)
        # the "threshold" parameter will always refer to int32 scale
        radius_max = pf_params.get("radius_max", 0.0) * pixel_size
        fai_user_params = {
            "radius_max": radius_max,
            "cutoff_pick": pf_params["snr"],
            "noise": pf_params["threshold"] / legacy_photon_adus,
            "patch_size": pf_params["patch_size"],
            "connected": pf_params["connected"],
            "min_nb_peaks": pf_params["min_nb_peaks"],
            "dense_skip_nohits": dense_skip_nohits,
            # "dense_skip_nohits": pf_params["discard_no_hits"],
        }
        fai_params.update(fai_user_params)

        proc_params = {
            "proc_mode": "fai",

            "fifo": {
                "nb_fifo_frames": packet_fifo_depth,
            },

            "buffers": {
                "nb_peak_counters_buffer": nb_recv_frames,
            },

            "gpu" :{
                "device_idx": 0,
                "cl_source_path": fai_kernels_base,
            },

            "jfrau" :{
                "gain_path": get_param_file("gains.h5"),
                "pedestal_path": pedestal_path,
                "photon_energy": energy,
            },

            "fai": fai_params,
        }

        _logger.info("FAI PARAMS: %s", fai_params)
        _logger.info("PARAMS: %s", proc_params)

        proc_params.update({
            f"saving_{stream}": get_saving(stream) for stream in saving_streams
        })

        self.__device.nb_gpus_per_system = 2

        self.__device.acq_params.update(acq_params)
        _logger.debug("acq_params: %s", self.__device.acq_params)
        self.__device.proc_params.update(proc_params)
        _logger.debug("proc_params: %s", self.__device.proc_params)

        uuid = uuid1()
        _logger.info(f'UUID={uuid}')

        lima2_params = self.__device.prepareAcq(uuid)
        if dump_params_filename:
            _logger.info("saving lima2 params to %s", dump_params_filename)
            with open(dump_params_filename, "wt") as f:
                json.dump(lima2_params, f, indent=4, sort_keys=True)

        # Async version
        #gevent.spawn(self.__device.prepareAcq, uuid).link_value(on_prepared)

        if self.__stopped:
            return

        # Read calibration data
        calib_params_file = get_param_file("calib_params.txt")
        with open(calib_params_file, "rt") as f:
            calib_params = json.loads(f.read())
        _logger.debug("calib_params: %s", calib_params)

        sample_distance = calib_params["sample_distance"]
        beam_center = calib_params["beam_center"]
        if config_beam and all(config_beam):
            if any([fabs(c - b) > 1 for c, b in zip(config_beam, beam_center)]):
                _logger.warning("config beam (%s) differs from "
                                "beam_center (%s)", config_beam, beam_center)

        # Master file header: metadata
        hc_over_e = 12.398419
        wavelength = hc_over_e / energy
        adus_per_photon = dense_out_params["dense_intensity_factor"]
        bias_adus = dense_out_params["dense_intensity_offset"]
        photon_dynamic_range = [-1.0, 1e4]
        trusted_range = [int(round(p * adus_per_photon + bias_adus))
                         for p in photon_dynamic_range]

        header = {
            "beam": {
                "incident_wavelength": (wavelength, "angstrom")
            },
            "detector_information": {
                "detector_distance": (sample_distance * 1e-3, "m"),
                "detector_name": "jungfrau-4m",
                "x_pixel_size": (pixel_size, "m"),
                "y_pixel_size": (pixel_size, "m"),
                "beam_center_x": (beam_center[0], "pixel"),
                "beam_center_y": (beam_center[1], "pixel"),
                "adus_per_photon": adus_per_photon,
                "underload_value": trusted_range[0],
                "saturation_value": trusted_range[1],
                "trusted_range": trusted_range,
            }
        }

        # Manage processing
        if manage_proc:
            self.__proc_stalled = gevent.event.Event()
            self.__proc_loop_task = gevent.spawn(self.proc_loop, uuid, header)

    @logger
    def start_acquisition(self):
        self.wait_prepared()
        if not self.__stopped:
            self.__device.startAcq()
            self.__started = True

    @logger
    def stop_acquisition(self):
        self.__stopped = True
        wait_for_idle_timeout = 10
        try:
            self.wait_idle(wait_for_idle_timeout)
        except:
            _logger.warning("detector not idle after %s", wait_for_idle_timeout)

        try:
            if self.__started:
                self.__device.stopAcq()
        except Exception:
            if self.__proc_loop_task:
                gevent.kill(self.__proc_loop_task)
            self.__device.resetAcq()
        finally:
            self.wait_idle()

    @logger
    def proc_loop(self, uuid, header={}):
        with ExitStack() as stack:
            def cleanup():
                self.__proc_loop_task = None
                self.__proc_stalled = None
            stack.callback(cleanup)

            _logger.debug("starting processing loop for %s", uuid)
            proc_cm = self.__device.getProcessing(uuid, erase_on_cleanup=True)
            proc = stack.enter_context(proc_cm)
            stack.callback(_logger.debug, "erasing processing for %s", uuid)

            # Aggregation (master file) writer
            det_name = proc.detector.det_name    # or self.name()
            local_2_shared_dir_map = {
                os.path.join('/nobackup/lid29p9jfrau11/shared',
                             'lima2/detectors/psi/data/processing',
                             'jungfrau_4m_01'):
                os.path.join('/data/id29/inhouse/opid291/Jungfrau',
                             'Calibration'),
            }
            writer_args = dict(det_name=det_name,
                               master_subdir="aggregated",
                               header=header,
                               local_2_shared_dir_map=local_2_shared_dir_map)
            stack.enter_context(SmxAggregationWriter(proc, **writer_args))

            def last_saved():
                cnts = proc.progress_counters
                names = ["dense_saved", "sparse_saved", "spots_saved"]
                return max([getattr(cnts, f"nb_frames_{n}") for n in names])

            stalled_timeout = 10
            last_cnt = 0
            last_t = None

            # main processing loop
            while not proc.is_finished:
                if not self.__started and self.__stopped:
                    break

                # Check if processing is stalled
                l = last_saved()
                if l > last_cnt:
                    last_cnt = l
                    last_t = time.time()
                if last_t and time.time() - last_t > stalled_timeout:
                    _logger.debug("lima2 processing stalled")
                    self.__proc_stalled.set()

                gevent.sleep(1.0)

    def get_acquired_frames(self):
        return self.__device.nb_frames_xferred

    @logger
    def reset(self):
        self.__device.resetAcq()

    @property
    def lima2_device(self):
        return self.__device

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
