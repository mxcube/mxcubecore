import gevent
import time
import os
import math
from HardwareRepository.TaskUtils import task
import logging


class Eiger:
    def init(self, config, collect_obj):
        self.config = config
        self.collect_obj = collect_obj
        self.header = dict()

        lima_device = config.getProperty("lima_device")
        eiger_device = config.getProperty("eiger_device")

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
            self.addChannel(
                {"type": "tango", "name": channel_name, "tangoname": lima_device},
                channel_name,
            )

        for channel_name in ("photon_energy",):
            self.addChannel(
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
        self.addChannel(
            {"type": "tango", "name": "set_image_header", "tangoname": lima_device},
            "saving_common_header",
        )

        self.getCommandObject("prepare_acq").init_device()
        self.getCommandObject("prepare_acq").device.set_timeout_millis(5 * 60 * 1000)
        self.getChannelObject("photon_energy").init_device()

    def wait_ready(self):
        acq_status_chan = self.getChannelObject("acq_status")
        with gevent.Timeout(30, RuntimeError("Detector not ready")):
            while acq_status_chan.getValue() != "Ready":
                time.sleep(1)

    def last_image_saved(self):
        # return 0
        return self.getChannelObject("last_image_saved").getValue() + 1

    def get_deadtime(self):
        return float(self.config.getProperty("deadtime"))

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
        gate=False,
    ):
        diffractometer_positions = (
            self.collect_obj.bl_control.diffractometer.getPositions()
        )
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
        except BaseException:
            self.header["Phi"] = "0.0000 deg."
            self.header["Kappa"] = "0.0000 deg."
        self.header["Alpha"] = "0.0000 deg."
        self.header["Polarization"] = self.collect_obj.bl_config.polarisation
        self.header["Detector_2theta"] = "0.0000 deg."
        self.header["Angle_increment"] = "%0.4f deg." % osc_range
        # self.header["Start_angle"]="%0.4f deg." % start
        self.header["Transmission"] = self.collect_obj.get_transmission()
        self.header["Flux"] = self.collect_obj.get_flux()
        self.header["Detector_Voffset"] = "0.0000 m"
        self.header["Energy_range"] = "(0, 0) eV"
        self.header["Trim_directory:"] = "(nil)"
        self.header["Flat_field:"] = "(nil)"
        self.header["Excluded_pixels:"] = " badpix_mask.tif"
        self.header["N_excluded_pixels:"] = "= 321"
        self.header["Threshold_setting"] = (
            "%d eV" % self.getChannelObject("photon_energy").getValue()
        )
        self.header["Count_cutoff"] = "1048500"
        self.header["Tau"] = "= 0 s"
        self.header["Exposure_period"] = "%f s" % (exptime + self.get_deadtime())
        self.header["Exposure_time"] = "%f s" % exptime

        beam_x, beam_y = self.collect_obj.get_beam_centre()
        header_info = [
            "beam_center_x=%s" % (beam_x / 7.5000003562308848e-02),
            "beam_center_y=%s" % (beam_y / 7.5000003562308848e-02),
            "wavelength=%s" % self.collect_obj.get_wavelength(),
            "detector_distance=%s"
            % (self.collect_obj.get_detector_distance() / 1000.0),
            "omega_start=%0.4f" % start,
            "omega_increment=%0.4f" % osc_range,
        ]
        self.getChannelObject("set_image_header").setValue(header_info)

        self.stop()
        self.wait_ready()

        self.set_energy_threshold(energy)

        if gate:
            self.getChannelObject("acq_trigger_mode").setValue("EXTERNAL_GATE")
        else:
            if still:
                self.getChannelObject("acq_trigger_mode").setValue("INTERNAL_TRIGGER")
            else:
                self.getChannelObject("acq_trigger_mode").setValue("EXTERNAL_TRIGGER")

        self.getChannelObject("saving_frame_per_file").setValue(
            min(100, number_of_images)
        )
        self.getChannelObject("saving_mode").setValue("AUTO_FRAME")
        logging.info("Acq. nb frames = %d", number_of_images)
        self.getChannelObject("acq_nb_frames").setValue(number_of_images)
        self.getChannelObject("acq_expo_time").setValue(exptime)
        self.getChannelObject("saving_overwrite_policy").setValue("OVERWRITE")
        self.getChannelObject("saving_managed_mode").setValue("HARDWARE")

    def set_energy_threshold(self, energy):
        minE = self.config.getProperty("minE")
        if energy < minE:
            energy = minE

        working_energy_chan = self.getChannelObject("photon_energy")
        working_energy = working_energy_chan.getValue() / 1000.0
        if math.fabs(working_energy - energy) > 0.1:
            egy = int(energy * 1000.0)
            working_energy_chan.setValue(egy)

    @task
    def set_detector_filenames(
        self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path
    ):
        prefix, suffix = os.path.splitext(os.path.basename(filename))
        prefix = "_".join(prefix.split("_")[:-1]) + "_"
        dirname = os.path.dirname(filename)
        if dirname.startswith(os.path.sep):
            dirname = dirname[len(os.path.sep) :]

        saving_directory = os.path.join(self.config.getProperty("buffer"), dirname)

        self.wait_ready()

        self.getChannelObject("saving_directory").setValue(saving_directory)
        self.getChannelObject("saving_prefix").setValue(prefix + "%01d" % frame_number)
        self.getChannelObject("saving_suffix").setValue(suffix)
        # self.getChannelObject("saving_next_number").setValue(frame_number)
        # self.getChannelObject("saving_index_format").setValue("%04d")
        self.getChannelObject("saving_format").setValue("HDF5")

    @task
    def start_acquisition(self):
        logging.getLogger("user_level_log").info("Preparing acquisition")
        self.getCommandObject("prepare_acq")()
        logging.getLogger("user_level_log").info("Detector ready, continuing")
        return self.getCommandObject("start_acq")()

    def stop(self):
        try:
            self.getCommandObject("stop_acq")()
        except BaseException:
            pass
        time.sleep(1)
        self.getCommandObject("reset")()
