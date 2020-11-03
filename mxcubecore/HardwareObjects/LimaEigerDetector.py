import gevent
import time
import os
import math
from HardwareRepository.TaskUtils import task
import logging
from HardwareRepository import HardwareRepository as HWR

from HardwareRepository.HardwareObjects.abstract.AbstractDetector import (
    AbstractDetector
)


class LimaEigerDetector(AbstractDetector):
    def __init__(self, name):
        AbstractDetector.__init__(self, name)
        self.binning_mode = 1

    def init(self):
        AbstractDetector.init(self)

        self.header = dict()

        lima_device = self.getProperty("lima_device")
        eiger_device = self.getProperty("eiger_device")

        for channel_name in (
            "acq_status",
            "acq_trigger_mode",
            "acq_nb_sequences",
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
            {"type": "tango", "name": "set_image_header", "tangoname": lima_device},
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
            while acq_status_chan.getValue() != "Ready":
                time.sleep(1)

    def last_image_saved(self):
        # return 0
        return self.get_channel_object("last_image_saved").getValue() + 1

    def get_deadtime(self):
        return float(self.getProperty("deadtime"))

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
        mesh_num_lines
    ):        
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
            "%d eV" % self.get_channel_object("photon_energy").getValue()
        )
        self.header["Count_cutoff"] = "1048500"
        self.header["Tau"] = "= 0 s"
        self.header["Exposure_period"] = "%f s" % (exptime + self.get_deadtime())
        self.header["Exposure_time"] = "%f s" % exptime

        beam_x, beam_y = HWR.beamline.detector.get_beam_position()
        header_info = [
            "beam_center_x=%s" % (beam_x / 7.5000003562308848e-02),
            "beam_center_y=%s" % (beam_y / 7.5000003562308848e-02),
            "wavelength=%s" % HWR.beamline.energy.get_wavelength(),
            "detector_distance=%s"
            % (HWR.beamline.detector.distance.get_value() / 1000.0),
            "omega_start=%0.4f" % start,
            "omega_increment=%0.4f" % osc_range,
        ]
        self.get_channel_object("set_image_header").setValue(header_info)

        self.stop()
        self.wait_ready()

        self.set_energy_threshold(HWR.beamline.energy.get_value())

        if osc_range < 1e-4:
            self.set_channel_value("acq_trigger_mode", "INTERNAL_TRIGGER")
        elif mesh:
            self.get_channel_object("acq_trigger_mode").setValue("EXTERNAL_TRIGGER_SEQUENCES")
            self.get_channel_object("acq_nb_sequences").setValue(mesh_num_lines)
        else:
            self.set_channel_value("acq_trigger_mode", "EXTERNAL_TRIGGER")

        self.get_channel_object("saving_frame_per_file").setValue(
            min(100, number_of_images)
        )
        self.get_channel_object("saving_mode").setValue("AUTO_FRAME")
        logging.info("Acq. nb frames = %d", number_of_images)
        self.get_channel_object("acq_nb_frames").setValue(number_of_images)
        self.get_channel_object("acq_expo_time").setValue(exptime)
        self.get_channel_object("saving_overwrite_policy").setValue("OVERWRITE")
        self.get_channel_object("saving_managed_mode").setValue("HARDWARE")

    def set_energy_threshold(self, energy):
        minE = self.getProperty("minE")
        if energy < minE:
            energy = minE

        working_energy_chan = self.get_channel_object("photon_energy")
        working_energy = working_energy_chan.getValue() / 1000.0
        if math.fabs(working_energy - energy) > 0.1:
            egy = int(energy * 1000.0)
            working_energy_chan.setValue(egy)

    @task
    def set_detector_filenames(self, frame_number, start, filename):
        prefix, suffix = os.path.splitext(os.path.basename(filename))
        prefix = "_".join(prefix.split("_")[:-1]) + "_"
        dirname = os.path.dirname(filename)
        if dirname.startswith(os.path.sep):
            dirname = dirname[len(os.path.sep) :]

        saving_directory = os.path.join(self.getProperty("buffer"), dirname)

        self.wait_ready()

        self.get_channel_object("saving_directory").setValue(saving_directory)
        self.get_channel_object("saving_prefix").setValue(
            prefix + "%01d" % frame_number
        )
        self.get_channel_object("saving_suffix").setValue(suffix)
        # self.get_channel_object("saving_next_number").setValue(frame_number)
        # self.get_channel_object("saving_index_format").setValue("%04d")
        self.get_channel_object("saving_format").setValue("HDF5")

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
