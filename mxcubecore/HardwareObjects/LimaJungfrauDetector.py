import gevent
import time
import subprocess
import logging
import os

from mxcubecore.CommandContainer import ConnectionError
from mxcubecore.HardwareObjects.abstract.AbstractDetector import AbstractDetector
from mxcubecore.BaseHardwareObjects import HardwareObjectState


class LimaJungfrauDetector(AbstractDetector):
    def __init__(self, name):
        AbstractDetector.__init__(self, name)
        self.header = dict()
        self.start_angles = list()

    def init(self):
        AbstractDetector.init(self)
        lima_device = self.get_property("lima_device", "")

        if not lima_device:
            return

        t = lima_device.split("/")
        t[-2] = "mask"
        mask_device = "/".join(t)

        try:
            for channel_name in (
                "latency_time",
                "State",
                "acq_status",
                "acq_trigger_mode",
                "saving_mode",
                "acq_nb_frames",
                "acq_expo_time",
                "saving_directory",
                "saving_prefix",
                "saving_suffix",
                "saving_next_number",
                "saving_index_format",
                "saving_format",
                "saving_overwrite_policy",
                "saving_header_delimiter",
                "saving_frame_per_file",
                "last_image_saved",
                "image_roi",
            ):
                self.add_channel(
                    {"type": "tango", "name": channel_name, "tangoname": lima_device},
                    channel_name,
                )

            self.add_channel(
                {"type": "tango", "name": "mask_file", "tangoname": mask_device},
                "MaskFile",
            )
            self.add_channel(
                {"type": "tango", "name": "mask_run_level", "tangoname": mask_device},
                "RunLevel",
            )
            self.add_command(
                {"type": "tango", "name": "start_mask", "tangoname": mask_device},
                "Start",
            )
            self.add_command(
                {"type": "tango", "name": "stop_mask", "tangoname": mask_device},
                "Stop",
            )

            self.add_command(
                {"type": "tango", "name": "prepare_acq", "tangoname": lima_device},
                "prepareAcq",
            )
            self.add_command(
                {"type": "tango", "name": "start_acq", "tangoname": lima_device},
                "startAcq",
            )
            self.add_command(
                {"type": "tango", "name": "stop_acq", "tangoname": lima_device},
                "stopAcq",
            )
            self.add_command(
                {"type": "tango", "name": "reset", "tangoname": lima_device}, "reset"
            )
            self.add_command(
                {"type": "tango", "name": "set_image_header", "tangoname": lima_device},
                "SetImageHeader",
            )

            # prepareAcq can block after large data transfers (buffered by GPFS): 2 min timeout
            self.get_command_object("prepare_acq").set_device_timeout(2 * 60 * 1000)
            self._emit_status()

        except ConnectionError:
            self.update_state(HardwareObjectState.FAULT)
            logging.getLogger("HWR").error(
                "Could not connect to detector %s" % lima_device
            )
            self._emit_status()

    def has_shutterless(self):
        return True

    def wait_ready(self, timeout=3500):
        with gevent.Timeout(timeout, RuntimeError("Detector not ready")):
            while self.get_channel_value("acq_status") != "Ready":
                time.sleep(1)

    def last_image_saved(self):
        try:
            img = self.get_channel_object("last_image_saved").get_value() + 1
            return img
        except Exception:
            return 0

    def get_deadtime(self):
        return float(self.get_property("deadtime"))

    def prepare_acquisition(self, number_of_images, exptime, data_root_path, prefix):
        self.set_channel_value("acq_trigger_mode", "EXTERNAL_TRIGGER_MULTI")

        self.set_channel_value("acq_nb_frames", number_of_images)
        self.set_channel_value("acq_expo_time", exptime)
        self.set_channel_value("latency_time", 990e-6)
        self.set_channel_value("saving_frame_per_file", 1000)

        mask_file = self.get_property("mask_file", None)

        if mask_file:
            self.set_channel_value("mask_file", mask_file)

        self.set_channel_value("mask_run_level", 0)

        self.set_detector_filenames(data_root_path, prefix)

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
        subprocess.Popen(
            "mkdir --parents %s" % (data_root_path),
            shell=True,
            stdin=None,
            stdout=None,
            stderr=None,
            close_fds=True,
        ).wait()

        subprocess.Popen(
            "chmod -R 755 %s" % (data_root_path),
            shell=True,
            stdin=None,
            stdout=None,
            stderr=None,
            close_fds=True,
        ).wait()

        self.set_channel_value("saving_mode", "AUTO_FRAME")
        self.set_channel_value("saving_directory", data_root_path)
        self.set_channel_value("saving_prefix", prefix)
        self.set_channel_value("saving_format", "HDF5BS")

    def start_acquisition(self):
        self.wait_ready()
        self.execute_command("stop_acq")
        self.execute_command("start_mask")
        self.execute_command("prepare_acq")
        self.execute_command("start_acq")
        self._emit_status()

    def stop_acquisition(self):
        try:
            self.execute_command("stop_acq")
        except Exception:
            pass
        finally:
            self.wait_ready()
            self.execute_command("reset")
            self.wait_ready()
            self.execute_command("stop_mask")

        self._emit_status()

    def reset(self):
        self.stop_acquisition()

    @property
    def status(self):
        try:
            acq_status = self.get_channel_value("acq_status")
        except Exception:
            acq_status = "OFFLINE"

        status = {
            "acq_satus": acq_status.upper(),
        }

        return status

    def _emit_status(self):
        self.emit("statusChanged", self.status)

    def restart(self) -> None:
        self.reset()
        return None
