import gevent
import time
import subprocess
import os
import logging

from PyTango import DeviceProxy
from mxcubecore.TaskUtils import task
from mxcubecore import HardwareRepository as HWR
from mxcubecore.CommandContainer import ConnectionError

from mxcubecore.HardwareObjects.abstract.AbstractDetector import AbstractDetector

from mxcubecore.BaseHardwareObjects import HardwareObjectState


class LimaPilatusDetector(AbstractDetector):
    def __init__(self, name):
        AbstractDetector.__init__(self, name)
        self.header = dict()
        self.start_angles = list()

    def init(self):
        AbstractDetector.init(self)

        lima_device = self.get_property("lima_device")
        pilatus_device = self.get_property("pilatus_device")

        if None in (lima_device, pilatus_device):
            return

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
                "last_image_saved",
                "image_roi",
            ):
                self.add_channel(
                    {"type": "tango", "name": channel_name, "tangoname": lima_device},
                    channel_name,
                )

            for channel_name in ("fill_mode", "threshold"):
                self.add_channel(
                    {
                        "type": "tango",
                        "name": channel_name,
                        "tangoname": pilatus_device,
                    },
                    channel_name,
                )

            pilatus_tg_device = DeviceProxy(pilatus_device)

            if hasattr(pilatus_tg_device, "working_energy"):
                self.add_channel(
                    {
                        "type": "tango",
                        "name": "working_energy",
                        "tangoname": pilatus_device,
                    },
                    "working_energy",
                )
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

            self.get_channel_object("image_roi").connect_signal(
                "update", self.roi_mode_changed
            )

            self.get_command_object("prepare_acq").set_device_timeout(10000)
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

    def roi_mode_changed(self, mode):
        """ROI mode change event"""
        self.roi_mode = self.roi_modes_list.index(str(mode))
        self.emit("detectorRoiModeChanged", (self.roi_mode,))

    def set_roi_mode(self, mode):
        """Sets roi mode

        :param mode: roi mode
        :type mode: str
        """
        # self.chan_roi_mode.set_value(self.roi_modes_list[mode])

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
        if mesh:
            trigger_mode = "EXTERNAL_GATE"
        # elif osc_range < 1e-4:
        #    trigger_mode = "INTERNAL_TRIGGER"
        else:
            trigger_mode = "EXTERNAL_TRIGGER"

        diffractometer_positions = HWR.beamline.diffractometer.get_positions()
        self.start_angles = list()
        for i in range(number_of_images):
            self.start_angles.append("%0.4f deg." % (start + osc_range * i))
        self.header = {}
        self.header["file_comments"] = comment
        self.header["N_oscillations"] = number_of_images
        self.header["Oscillation_axis"] = "omega"
        self.header["Chi"] = "0.0000 deg."
        kappa_phi = diffractometer_positions.get("kappa_phi", -9999)
        if kappa_phi is None:
            kappa_phi = -9999
        kappa = diffractometer_positions.get("kappa", -9999)
        if kappa is None:
            kappa = -9999
        self.header["Phi"] = "%0.4f deg." % kappa_phi
        self.header["Kappa"] = "%0.4f deg." % kappa
        self.header["Alpha"] = "0.0000 deg."
        self.header["Polarization"] = HWR.beamline.collect.bl_config.polarisation
        self.header["Detector_2theta"] = "0.0000 deg."
        self.header["Angle_increment"] = "%0.4f deg." % osc_range
        self.header["Transmission"] = HWR.beamline.transmission.get_value()

        self.header["Flux"] = HWR.beamline.flux.get_value()
        self.header["Beam_xy"] = "(%.2f, %.2f) pixels" % self.get_beam_position()
        self.header["Detector_Voffset"] = "0.0000 m"
        self.header["Energy_range"] = "(0, 0) eV"
        self.header["Detector_distance"] = "%f m" % (self.distance.get_value() / 1000.0)
        self.header["Wavelength"] = "%f A" % HWR.beamline.energy.get_wavelength()
        self.header["Trim_directory:"] = "(nil)"
        self.header["Flat_field:"] = "(nil)"
        self.header["Excluded_pixels:"] = " badpix_mask.tif"
        self.header["N_excluded_pixels:"] = "= 321"
        self.header["Threshold_setting"] = "%d eV" % self.get_channel_value("threshold")
        self.header["Count_cutoff"] = "1048500"
        self.header["Tau"] = "= 0 s"
        self.header["Exposure_period"] = "%f s" % (exptime + self.get_deadtime())
        self.header["Exposure_time"] = "%f s" % exptime

        self.reset()
        self.wait_ready()

        self.set_energy_threshold(HWR.beamline.energy.get_value())

        self.set_channel_value("acq_trigger_mode", trigger_mode)

        if self.get_property("set_latency_time", False):
            self.set_channel_value("latency_time", self.get_deadtime())

        self.set_channel_value("saving_mode", "AUTO_FRAME")
        self.set_channel_value("acq_nb_frames", number_of_images)
        self.set_channel_value("acq_expo_time", exptime)
        self.set_channel_value("saving_overwrite_policy", "OVERWRITE")

    def set_energy_threshold(self, energy):
        """Set the energy threshold.
        Args:
            energy (int): Energy [eV] or [keV]
        """
        minE = self.get_property("minE")
        # some versions of Lima Pilatus server take the energy ergument in keV
        # some in eV. From minE we can set a convertion factor.
        factor = 1000 if minE > 100 else 1.0

        energy_threshold = self.get_channel_value("energy_threshold")

        # check if need to convert energy in eV.
        if energy < 100:
            energy *= factor

        if energy < minE:
            energy = minE

        if abs(energy_threshold - energy) > 0.1:
            self.set_channel_value("energy_threshold", energy)
            while abs(self.get_channel_value("energy_threshold") - energy) > 0.1:
                time.sleep(1)

        self.set_channel_value("fill_mode", "ON")

    @task
    def set_detector_filenames(self, frame_number, start, filename):
        prefix, suffix = os.path.splitext(os.path.basename(filename))
        prefix = "_".join(prefix.split("_")[:-1]) + "_"
        dirname = os.path.dirname(filename)
        if dirname.startswith(os.path.sep):
            dirname = dirname[len(os.path.sep) :]

        saving_directory = os.path.join(self.get_property("buffer", "/"), dirname)

        subprocess.Popen(
            "ssh %s@%s mkdir --parents %s"
            % (os.environ["USER"], self.get_property("control"), saving_directory),
            shell=True,
            stdin=None,
            stdout=None,
            stderr=None,
            close_fds=True,
        ).wait()

        self.set_channel_value("saving_directory", saving_directory)
        self.set_channel_value("saving_prefix", prefix)
        self.set_channel_value("saving_suffix", suffix)
        self.set_channel_value("saving_next_number", frame_number)
        self.set_channel_value("saving_index_format", "%04d")
        self.set_channel_value("saving_format", "CBF")
        self.set_channel_value("saving_header_delimiter", ["|", ";", ":"])

        headers = list()

        for i, start_angle in enumerate(self.start_angles):
            header = "\n%s\n" % self.get_property("serial")
            header += "# %s\n" % time.strftime("%Y/%b/%d %T")
            header += "\n%s\n" % self.get_property("sensor")
            header += "\n%s\n" % self.get_property("pixel_size")
            self.header["Start_angle"] = start_angle

            for key, value in self.header.items():
                header += "# %s %s\n" % (key, value)

            headers.append("%d : array_data/header_contents|%s;" % (i, header))

        self.header = headers

    def start_acquisition(self):
        self.wait_ready()
        self.execute_command("stop_acq")
        self.execute_command("prepare_acq")
        self.execute_command("set_image_header", self.header)
        self.execute_command("start_acq")
        self._emit_status()

    def stop_acquisition(self):
        try:
            self.execute_command("stop_acq")
        except Exception:
            pass

        time.sleep(1)
        self.execute_command("reset")

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

        status = {
            "acq_satus": acq_status.upper(),
        }

        return status

    def _emit_status(self):
        self.emit("statusChanged", self.status)

    def recover_from_failure(self):
        self.prepare_acquisition(
            False,
            0,
            0,
            0.5,
            None,
            1,
            "",
            HWR.beamline.energy.get_value(),
            "INTERNAL_TRIGGER",
        )
        self.start_acquisition()
        self.wait_ready()
        self.stop_acquisition()
