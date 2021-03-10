# pylint: skip-file

import time
from mxcubecore.TaskUtils import task
import logging
from PyTango import DeviceProxy
from mxcubecore import HardwareRepository as HWR


class LimaDetectorMockup:
    def init(self, config, collect_obj=None):
        self.config = config
        self.header = dict()

        lima_device = config.get_property("lima_device")
        pilatus_device = config.get_property("pilatus_device")
        if None in (lima_device, pilatus_device):
            return

        for channel_name in (
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
            "last_image_saved",
        ):
            self.add_channel(
                {"type": "tango", "name": channel_name, "tangoname": lima_device},
                channel_name,
            )

        for channel_name in ("fill_mode", "threshold"):
            self.add_channel(
                {"type": "tango", "name": channel_name, "tangoname": pilatus_device},
                channel_name,
            )

        pilatus_tg_device = DeviceProxy(pilatus_device)
        if hasattr(pilatus_tg_device, "working_energy"):
            self.add_channel(
                {
                    "type": "tango",
                    "name": "energy_threshold",
                    "tangoname": pilatus_device,
                },
                "working_energy",
            )
        else:
            self.add_channel(
                {
                    "type": "tango",
                    "name": "energy_threshold",
                    "tangoname": pilatus_device,
                },
                "energy_threshold",
            )

        self.add_command(
            {"type": "tango", "name": "prepare_acq", "tangoname": lima_device},
            "prepareAcq",
        )
        self.add_command(
            {"type": "tango", "name": "start_acq", "tangoname": lima_device}, "startAcq"
        )
        self.add_command(
            {"type": "tango", "name": "stop_acq", "tangoname": lima_device}, "stopAcq"
        )
        self.add_command(
            {"type": "tango", "name": "reset", "tangoname": lima_device}, "reset"
        )
        self.add_command(
            {"type": "tango", "name": "set_image_header", "tangoname": lima_device},
            "SetImageHeader",
        )

    def last_image_saved(self):
        return 2

    def get_deadtime(self):
        return 0.01

    @task
    def prepare_acquisition(
        self,
        take_dark,
        start,
        osc_range,
        exptime,
        npass,
        number_of_images,
        comment,
        energy,
        still,
    ):
        diffractometer_positions = HWR.beamline.diffractometer.get_positions()
        self.start_angles = list()
        for i in range(number_of_images):
            self.start_angles.append("%0.4f deg." % (start + osc_range * i))
        kappa_phi = diffractometer_positions.get("kappa_phi", -9999)
        if kappa_phi is None:
            kappa_phi = -9999
        kappa = diffractometer_positions.get("kappa", -9999)
        if kappa is None:
            kappa = -9999

    def set_energy_threshold(self, energy):
        return

    @task
    def set_detector_filenames(
        self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path
    ):
        return

    @task
    def start_acquisition(self):
        logging.getLogger("HWR").info("Mockup detector starts acquisition")
        return

    def stop(self):
        time.sleep(1)
