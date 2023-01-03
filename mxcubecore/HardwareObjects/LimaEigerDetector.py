"""LimaEigerDetector Class
Lima Tango Device Server implementation of the Dectris Eiger2 Detector.
"""
import gevent
import time
import os
import math
import logging

from mxcubecore.TaskUtils import task
from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractDetector import AbstractDetector


class LimaEigerDetector(AbstractDetector):
    def __init__(self, name):
        AbstractDetector.__init__(self, name)
        self.binning_mode = 1

    def init(self):
        AbstractDetector.init(self)

        self.header = dict()

        lima_device = self.get_property("lima_device")
        eiger_device = self.get_property("eiger_device")

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
            "last_image_saved",
            "saving_frame_per_file",
            "saving_managed_mode",
        ):
            self.add_channel(
                {"type": "tango", "name": channel_name, "tangoname": lima_device},
                channel_name,
            )

        for channel_name in ("photon_energy",):
            self.add_channel(
                {"type": "tango", "name": channel_name, "tangoname": eiger_device},
                channel_name,
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
        self.add_channel(
            {"type": "tango", "name": "saving_common_header", "tangoname": lima_device},
            "saving_common_header",
        )

        self.get_command_object("prepare_acq").init_device()
        self.get_command_object("prepare_acq").device.set_timeout_millis(5 * 60 * 1000)
        self.get_channel_object("photon_energy").init_device()
        self._emit_status()

    def has_shutterless(self):
        return True

    def wait_ready(self, timeout=30):
        acq_status_chan = self.get_channel_object("acq_status")
        with gevent.Timeout(timeout, RuntimeError("Detector not ready")):
            while acq_status_chan.get_value() != "Ready":
                time.sleep(1)

    def last_image_saved(self):
        # return 0
        return self.get_channel_object("last_image_saved").get_value() + 1

    def get_deadtime(self):
        return float(self.get_property("deadtime"))

    def prepare_acquisition(
        self,
        take_dark,
        start,
        osc_range,
        exptime,
        npass,
        number_of_images,
        comment,
        mesh,
        mesh_num_lines,
    ):
        """
        diffractometer_positions = HWR.beamline.diffractometer.get_positions()
        self.start_angles = list()
        for i in range(number_of_images):
            self.start_angles.append("%0.4f deg." % (start + osc_range * i))
        self.header["file_comments"] = comment
        self.header["N_oscillations"] = number_of_images
        self.header["Oscillation_axis"] = "omega"
        self.header["Chi"] = "0.0000 deg."
        try:
            self.header["Phi"] = "%0.4f deg." % diffractometer_positions.get(
                "kappa_phi", -9999
            )
            self.header["Kappa"] = "%0.4f deg." % diffractometer_positions.get(
                "kappa", -9999
            )
        except Exception:
            self.header["Phi"] = "0.0000 deg."
            self.header["Kappa"] = "0.0000 deg."
        self.header["Alpha"] = "0.0000 deg."
        self.header["Polarization"] = HWR.beamline.collect.bl_config.polarisation
        self.header["Detector_2theta"] = "0.0000 deg."
        self.header["Angle_increment"] = "%0.4f deg." % osc_range
        self.header["Transmission"] = HWR.beamline.transmission.get_value()
        self.header["Flux"] = HWR.beamline.flux.get_value()
        self.header["Detector_Voffset"] = "0.0000 m"
        self.header["Energy_range"] = "(0, 0) eV"
        self.header["Trim_directory:"] = "(nil)"
        self.header["Flat_field:"] = "(nil)"
        self.header["Excluded_pixels:"] = " badpix_mask.tif"
        self.header["N_excluded_pixels:"] = "= 321"
        self.header["Threshold_setting"] = (
            "%d eV" % self.get_channel_object("photon_energy").get_value()
        )
        self.header["Count_cutoff"] = "1048500"
        self.header["Tau"] = "= 0 s"
        self.header["Exposure_period"] = "%f s" % (exptime + self.get_deadtime())
        self.header["Exposure_time"] = "%f s" % exptime
        """

        self.stop()
        self.wait_ready()

        beam_x, beam_y = self.get_beam_position()
        header_info = [
            "beam_center_x=%s" % (beam_x),
            "beam_center_y=%s" % (beam_y),
            "detector_distance=%s"
            % (HWR.beamline.detector.distance.get_value() / 1000.0),
            "omega_start=%0.4f" % start,
            "omega_increment=%0.4f" % osc_range,
            "wavelength=%s" % HWR.beamline.energy.get_wavelength(),
        ]
        # either we set the wavelength, or we set the energy_threshold
        # up to now we were doing both (lost of time)
        # "wavelength=%s" % HWR.beamline.energy.get_wavelength(),
        # self.set_energy_threshold(HWR.beamline.energy.get_value())

        self.get_channel_object("saving_common_header").set_value(header_info)

        if mesh:
            """
            self.get_channel_object("acq_trigger_mode").set_value("EXTERNAL_TRIGGER_SEQUENCES")
            self.get_channel_object("acq_nb_sequences").set_value(mesh_num_lines)
            """
            # self.get_channel_object("acq_trigger_mode").set_value("EXTERNAL_GATE")
            self.get_channel_object("acq_trigger_mode").set_value(
                "EXTERNAL_TRIGGER_MULTI"
            )
        else:
            self.set_channel_value("acq_trigger_mode", "EXTERNAL_TRIGGER")

        self.get_channel_object("saving_frame_per_file").set_value(
            min(100, number_of_images)
        )

        # 'MANUAL', 'AUTO_FRAME', 'AUTO_SEQUENCE
        self.get_channel_object("saving_mode").set_value("AUTO_FRAME")
        logging.info("Acq. nb frames = %d", number_of_images)
        self.get_channel_object("acq_nb_frames").set_value(number_of_images)
        self.get_channel_object("acq_expo_time").set_value(exptime)
        # 'ABORT', 'OVERWRITE', 'APPEND'
        self.get_channel_object("saving_overwrite_policy").set_value("OVERWRITE")
        # 'SOFTWARE', 'HARDWARE'
        self.get_channel_object("saving_managed_mode").set_value("HARDWARE")

    def set_energy_threshold(self, energy):
        minE = self.get_property("minE")
        if energy < minE:
            energy = minE

        working_energy_chan = self.get_channel_object("photon_energy")
        working_energy = working_energy_chan.get_value() / 1000.0
        if math.fabs(working_energy - energy) > 0.1:
            egy = int(energy * 1000.0)
            working_energy_chan.set_value(egy)

    @task
    def set_detector_filenames(self, frame_number, start, filename):
        prefix, suffix = os.path.splitext(os.path.basename(filename))
        prefix = "_".join(prefix.split("_")[:-1]) + "_"
        dirname = os.path.dirname(filename)
        if dirname.startswith(os.path.sep):
            dirname = dirname[len(os.path.sep) :]

        saving_directory = os.path.join(self.get_property("buffer"), dirname)
        self.wait_ready()

        self.get_channel_object("saving_directory").set_value(saving_directory)
        self.get_channel_object("saving_prefix").set_value(
            prefix + "%01d" % frame_number
        )
        self.get_channel_object("saving_suffix").set_value(suffix)
        # self.get_channel_object("saving_next_number").set_value(frame_number)
        # self.get_channel_object("saving_index_format").set_value("%04d")
        self.get_channel_object("saving_format").set_value("HDF5")

    def start_acquisition(self):
        logging.getLogger("user_level_log").info("Preparing acquisition")
        self.get_command_object("prepare_acq")()
        logging.getLogger("user_level_log").info("Detector ready, continuing")
        self.get_command_object("start_acq")()
        self._emit_status()

    def stop_acquisition(self):
        try:
            self.get_command_object("stop_acq")()
        except Exception:
            pass

        time.sleep(1)
        self.get_command_object("reset")()
        self.wait_ready()
        self._emit_status()

    def reset(self):
        self.stop_acquisition()

    @property
    def status(self):
        try:
            acq_status = self.get_channel_value("acq_status")
        except Exception:
            acq_status = "OFFLINE"

        status = {"acq_satus": acq_status.upper()}

        return status

    def _emit_status(self):
        self.emit("statusChanged", self.status)

    def recover_from_failure(self):
        pass
