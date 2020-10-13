#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

import tine
import numpy
import gevent
import logging

from copy import deepcopy
from datetime import datetime
from scipy.interpolate import interp1d

from HardwareRepository.HardwareObjects.abstract.AbstractFlux import AbstractFlux

from HardwareRepository import HardwareRepository as HWR


__credits__ = ["EMBL Hamburg"]
__category__ = "General"

diode_calibration_amp_per_watt = interp1d(
    [4.0, 6.0, 8.0, 10.0, 12.0, 12.5, 15.0, 16.0, 20.0, 30.0],
    [0.2267, 0.2116, 0.1405, 0.086, 0.0484, 0.0469, 0.0289, 0.0240, 0.01248, 0.00388],
)

diode_calibration_amp_per_watt = interp1d(
    [4.0, 6.0, 8.0, 10.0, 12.0, 12.5, 15.0, 16.0, 20.0, 30.0],
    [0.2267, 0.2116, 0.1405, 0.086, 0.0484, 0.0469, 0.0289, 0.0240, 0.01248, 0.00388],
)

air_absorption_coeff_per_meter = interp1d(
    [
        4.0,
        4.2,
        4.4,
        4.6,
        4.8,
        5.0,
        5.4,
        5.8,
        6.2,
        6.6,
        7.0,
        8.0,
        9.2,
        11.8,
        14.4,
        17.0,
        19.6,
        22.2,
        24.8,
        27.4,
        30,
    ],
    [
        9.19440446,
        7.94983601,
        6.91804807,
        6.10374226,
        5.32906528,
        4.71308953,
        3.73630655,
        3.00942560,
        2.45767288,
        2.0317802,
        1.69805057,
        1.12911273,
        0.73628084,
        0.34554261,
        0.19176669,
        0.12030697,
        0.08331135,
        0.06203213,
        0.04926173,
        0.04114024,
        0.0357374,
    ],
)

carbon_window_transmission = interp1d(
    [4.0, 6.6, 9.2, 11.8, 14.4, 17.0, 19.6, 22.2, 24.8, 27.4, 30],
    [
        0.74141,
        0.93863,
        0.97775,
        0.98946,
        0.99396,
        0.99599,
        0.99701,
        0.99759,
        0.99793,
        0.99815,
        0.99828,
    ],
)

# # Replacec by AbstractFLux.dose_rate_per_photon_per_mmsq (same values0
#
# dose_rate_per_10to14_ph_per_mmsq = interp1d(
#     [4.0, 6.6, 9.2, 11.8, 14.4, 17.0, 19.6, 22.2, 24.8, 27.4, 30.0],
#     [
#         459000.0,
#         162000.0,
#         79000.0,
#         45700.0,
#         29300.0,
#         20200.0,
#         14600.0,
#         11100.0,
#         8610.0,
#         6870.0,
#         5520.0,
#     ],
# )


class EMBLFlux(AbstractFlux):
    def __init__(self, name):

        AbstractFlux.__init__(self, name)

        self.measured_flux_dict = None
        self.measured_flux_list = None
        self.current_flux_dict = None

        self.flux_value = 0
        # self.ampl_chan_index = None
        self.intensity_ranges = []
        self.intensity_value = None

        self.flux_record_status = None

        self.origin_flux_value = None
        self.origin_beam_info = None
        self.origin_transmission = None
        self.measuring = False
        self.transmission_value = None

        self.chan_intens_range = None
        self.chan_intens_mean = None
        self.cmd_set_intens_acq_time = None
        self.cmd_set_intens_range = None
        self.cmd_set_intens_resolution = None

        self.back_light_hwobj = None
        self.beam_focusing_hwobj = None
        self.beamstop_hwobj = None

    def init(self):
        """Reads config xml, initiates all necessary hwobj, channels and cmds
        """
        super(EMBLFlux, self).init()
        self.intensity_ranges = []
        self.measured_flux_dict = None
        self.measured_flux_list = []
        self.current_flux_dict = None

        try:
            for intens_range in self["intensity"]["ranges"]:
                temp_intens_range = {}
                temp_intens_range["max"] = intens_range.CurMax
                temp_intens_range["index"] = intens_range.CurIndex
                temp_intens_range["offset"] = intens_range.CurOffset
                self.intensity_ranges.append(temp_intens_range)
            self.intensity_ranges = sorted(
                self.intensity_ranges, key=lambda item: item["max"]
            )
        except Exception:
            logging.getLogger("HWR").error("BeamlineTest: No intensity ranges defined")

        self.chan_intens_mean = self.get_channel_object("intensMean")
        self.chan_intens_mean.connect_signal("update", self.intens_mean_changed)

        self.chan_intens_range = self.get_channel_object("intensRange")
        self.chan_flux_transmission = self.get_channel_object("fluxTransmission")

        self.cmd_set_intens_resolution = self.get_command_object("setIntensResolution")
        self.cmd_set_intens_acq_time = self.get_command_object("setIntensAcqTime")
        self.cmd_set_intens_range = self.get_command_object("setIntensRange")
        self.cmd_flux_record = self.get_command_object("fluxRecord")

        self.back_light_hwobj = self.get_object_by_role("backlight")
        self.beamstop_hwobj = self.get_object_by_role("beamstop")
        self.aperture_hwobj = HWR.beamline.beam.aperture

        self.connect(
            HWR.beamline.transmission, "valueChanged", self.transmission_changed
        )

        # self.init_flux_values()

        self.chan_flux_status = self.get_channel_object("fluxStatus")
        self.chan_flux_status.connect_signal("update", self.flux_status_changed)

        self.chan_flux_message = self.get_channel_object("fluxMessage")
        self.chan_flux_message.connect_signal("update", self.flux_message_changed)

        self.connect(HWR.beamline.beam, "beamInfoChanged", self.beam_info_changed)

        self.connect(
            self.aperture_hwobj, "diameterIndexChanged", self.aperture_diameter_changed
        )

        self.beam_focusing_hwobj = self.get_object_by_role("beam_focusing")
        if self.beam_focusing_hwobj is not None:
            self.connect(
                self.beam_focusing_hwobj,
                "focusingModeChanged",
                self.focusing_mode_changed,
            )

        self.init_flux_values()

    def init_flux_values(self):
        if not self.chan_flux_status.get_value():
            logging.getLogger("GUI").error(
                "No valid flux value available. Please remeasure flux!"
            )
            return
        flux_values = self.cmd_flux_record.get()
        flux_transmission = self.chan_flux_transmission.get_value()
        aperture_diameter_list = self.aperture_hwobj.get_diameter_list()

        self.measured_flux_list = []
        for index, flux_value in enumerate(flux_values):
            self.measured_flux_list.append(
                {
                    "flux": flux_value,
                    "transmission": flux_transmission,
                    "size_x": aperture_diameter_list[index] / 1000.0,
                    "size_y": aperture_diameter_list[index] / 1000.0,
                }
            )

    def flux_message_changed(self, message):
        if message is not "":
            logging.getLogger("GUI").error("Flux-record message: %s" % message)

    def flux_status_changed(self, status):
        if not status and self.flux_record_status:
            logging.getLogger("GUI").error(
                "Flux value invalidated. Please remeasure flux!"
            )
            self.reset_flux()
        self.flux_record_status = status

    def aperture_diameter_changed(self, index, size):
        """Updates flux if the aperture diameter has been changed"""
        if self.measured_flux_list and not self.measuring:
            if len(self.measured_flux_list) > 1:
                self.measured_flux_dict = self.measured_flux_list[index]
                self.update_flux_value()

    def beam_info_changed(self, beam_info):
        """Updates flux value if the beam size changes"""
        self.beam_info = beam_info
        self.update_flux_value()

    def transmission_changed(self, transmission):
        """Updates flux value if the transmission has been changed"""
        self.transmission_value = transmission
        self.update_flux_value()

    def intens_mean_changed(self, value):
        pass

    def focusing_mode_changed(self, mode, size):
        logging.getLogger("GUI").warning(
            "Beamline focus mode changed. Please remeasure flux!"
        )
        self.reset_flux()

    def reset_flux(self):
        self.current_flux_dict = None
        self.measured_flux_dict = None
        self.measured_flux_list = []
        self.emit(
            "fluxInfoChanged",
            {"measured": self.measured_flux_dict, "current": self.current_flux_dict},
        )

    def get_value(self):
        """Returns flux value as float"""
        if self.current_flux_dict is not None:
            return self.current_flux_dict["flux"]
        else:
            return 1

    def update_flux_value(self):
        if self.measured_flux_dict is not None and self.transmission_value is not None:
            self.current_flux_dict = deepcopy(self.measured_flux_dict)
            if int(self.transmission_value) != int(
                self.measured_flux_dict["transmission"]
            ):
                self.current_flux_dict["flux"] = (
                    self.measured_flux_dict["flux"]
                    * self.transmission_value
                    / self.measured_flux_dict["transmission"]
                )
                self.current_flux_dict["transmission"] = self.transmission_value

            if len(self.measured_flux_list) == 1:
                origin_area = (
                    self.measured_flux_dict["size_x"]
                    * self.measured_flux_dict["size_y"]
                )
                current_area = self.beam_info["size_x"] * self.beam_info["size_y"]
                if origin_area != current_area:
                    self.current_flux_dict["size_x"] = self.beam_info["size_x"]
                    self.current_flux_dict["size_y"] = self.beam_info["size_y"]
                    self.current_flux_dict["flux"] = (
                        self.measured_flux_dict["flux"] * current_area / origin_area
                    )
            self.emit(
                "fluxInfoChanged",
                {
                    "measured": self.measured_flux_dict,
                    "current": self.current_flux_dict,
                },
            )

    def measure_flux(self, wait=True):
        gevent.spawn(self.measure_flux_task, wait)

    def measure_flux_task(self, wait=True):
        if not HWR.beamline.safety_shutter.is_opened():
            msg = "Unable to measure flux! Safety shutter is closed."
            self.print_log("GUI", "error", msg)
            return

        if not HWR.beamline.detector.is_cover_closed():
            msg = "Unable to measure flux! Detecor cover is open."
            self.print_log("GUI", "error", "Unable to measure flux!")
            self.print_log("GUI", "error", msg)
            return

        if HWR.beamline.session.beamline_name == "P14":
            if HWR.beamline.detector.distance.get_value() > 501:
                self.print_log(
                    "GUI",
                    "error",
                    "Detector is too far away for flux measurements. Move to 500 mm or closer.",
                )
                return

        self.measuring = True
        intens_value = 0
        max_frame_rate = 1 / HWR.beamline.detector.get_exposure_time_limits()[0]

        current_phase = HWR.beamline.diffractometer.current_phase
        current_transmission = HWR.beamline.transmission.get_value()
        current_aperture_index = self.aperture_hwobj.get_diameter_index()

        self.emit("progressInit", "Measuring flux. Please wait...", 10, True)

        # Set transmission to 100%
        # -----------------------------------------------------------------
        self.emit("progressStep", 1, "Setting transmission to 100%")

        HWR.beamline.transmission.set_value(100, timeout=20)

        # Close the fast shutter
        # -----------------------------------------------------------------
        HWR.beamline.fast_shutter.closeShutter(wait=True)
        logging.getLogger("HWR").debug("Measure flux: Fast shutter closed")
        gevent.sleep(0.2)
        HWR.beamline.diffractometer.wait_device_ready(10)

        # Move back light in, check beamstop position
        # -----------------------------------------------------------------
        logging.getLogger("HWR").info("Measure flux: Moving backlight out...")
        self.emit("progressStep", 1, "Moving backlight out")
        self.back_light_hwobj.move_in()
        logging.getLogger("HWR").debug("Measure flux: Backlight moved out")

        beamstop_position = self.beamstop_hwobj.get_value()
        if beamstop_position == "BEAM":
            self.emit("progressStep", 2, "Moving beamstop OFF")
            self.beamstop_hwobj.set_position("OFF")
            HWR.beamline.diffractometer.wait_device_ready(30)
            logging.getLogger("HWR").info("Measure flux: Beamstop moved off")

        # Check scintillator position
        # -----------------------------------------------------------------
        scintillator_position = HWR.beamline.diffractometer.get_scintillator_position()
        if scintillator_position == "SCINTILLATOR":
            self.emit("progressStep", 3, "Setting the photodiode")
            HWR.beamline.diffractometer.set_scintillator_position("PHOTODIODE")
            gevent.sleep(1)
            HWR.beamline.diffractometer.wait_device_ready(30)
            logging.getLogger("HWR").debug(
                "Measure flux: Scintillator set to photodiode"
            )

        self.measured_flux_list = []

        # -----------------------------------------------------------------
        if HWR.beamline.session.beamline_name == "P13":
            self.aperture_hwobj.set_in()
            HWR.beamline.diffractometer.wait_device_ready(30)
            self.aperture_hwobj.set_diameter_index(0)
            HWR.beamline.fast_shutter.openShutter(wait=True)

            for index, diameter_size in enumerate(
                self.aperture_hwobj.get_diameter_list()
            ):
                # 5. open the fast shutter -----------------------------------------
                self.emit(
                    "progressStep",
                    4 + index,
                    "Measuring flux with %d micron aperture" % diameter_size,
                )
                self.aperture_hwobj.set_diameter_index(index)
                HWR.beamline.diffractometer.wait_device_ready(10)

                gevent.sleep(1)
                intens_value = self.chan_intens_mean.get_value(force=True)
                logging.getLogger("HWR").info("Measured current: %s" % intens_value)
                # HWR.beamline.fast_shutter.closeShutter(wait=True)
                intensity_value = intens_value[0] + 1.860e-5  # 2.780e-6
                self.measured_flux_list.append(self.get_flux_result(intensity_value))
                gevent.sleep(1)
            HWR.beamline.fast_shutter.closeShutter(wait=True)

            try:
                self.cmd_flux_record([_x["flux"] for _x in self.measured_flux_list])
                gevent.sleep(2)
            except Exception:
                pass

            max_frame_rate = 25
        else:
            self.emit("progressStep", 5, "Measuring the intensity")
            current_aperture_index = 0
            HWR.beamline.fast_shutter.openShutter(wait=True)
            logging.getLogger("HWR").debug("Measure flux: Fast shutter opened")

            gevent.sleep(0.5)
            intens_value = self.chan_intens_mean.get_value()

            intens_range_now = self.chan_intens_range.get_value()
            HWR.beamline.fast_shutter.closeShutter(wait=True)
            logging.getLogger("HWR").debug("Measure flux: Fast shutter closed")

            intensity_value = intens_value[0] + 2.780e-6
            self.measured_flux_list.append(self.get_flux_result(intensity_value))

        self.emit("progressStep", 10, "Restoring original state")
        self.print_log("GUI", "info", "Flux measurement results:")
        self.print_log(
            "GUI",
            "info",
            "Beam size | Flux (ph/s) | "
            + "Dose rate (KGy/s) | Time to reach 20 MGy (s) | "
            + "Number of frames @ %d Hz" % max_frame_rate,
        )

        for index, item in enumerate(self.measured_flux_list):
            msg = "  * %d x %d | %1.1e  | %1.1e  | %.1f  | %d" % (
                item["size_x"] * 1000,
                item["size_y"] * 1000,
                item["flux"],
                item["dose_rate"],
                item["time_to_reach_limit"],
                item["frames_to_reach_limit"],
            )

            if index > 0:
                # low_value = item["flux"] < 1e9
                # low_value = item["intensity"] - 1.860e-5 < 1e-6
                low_value = item["intensity"] < 1e-6
                out_of_range = False

                if (
                    self.measured_flux_list[0]["flux"]
                    <= self.measured_flux_list[-1]["flux"]
                    or self.measured_flux_list[index - 1]["flux"]
                    <= self.measured_flux_list[index]["flux"]
                ):
                    out_of_range = True
                if low_value or out_of_range:
                    msg += " (intensity: %1.1e)" % item["intensity"]
                    self.print_log("GUI", "error", msg)
                else:
                    self.print_log("GUI", "info", msg)
            else:
                self.print_log("GUI", "info", msg)

        self.measured_flux_dict = self.measured_flux_list[current_aperture_index]
        self.current_flux_dict = self.measured_flux_list[current_aperture_index]

        self.emit(
            "fluxInfoChanged",
            {"measured": self.measured_flux_dict, "current": self.current_flux_dict},
        )
        self.measuring = False

        # 7 Restoring previous states ----------------------------------------
        HWR.beamline.transmission.set_value(current_transmission)
        HWR.beamline.diffractometer.set_phase(current_phase)
        HWR.beamline.diffractometer.wait_device_ready(10)
        if HWR.beamline.session.beamline_name == "P13":
            self.aperture_hwobj.set_diameter_index(current_aperture_index)
        self.emit("progressStop", ())

    def get_flux_result(self, intensity_value):
        energy = HWR.beamline.energy.get_value()
        detector_distance = HWR.beamline.detector.distance.get_value()
        beam_size = HWR.beamline.beam.get_beam_size()
        transmission = HWR.beamline.transmission.get_value()

        air_trsm = numpy.exp(
            -air_absorption_coeff_per_meter(energy) * detector_distance / 1000.0
        )
        carb_trsm = carbon_window_transmission(energy)
        flux = (
            0.624151
            * 1e16
            * intensity_value
            / diode_calibration_amp_per_watt(energy)
            / energy
            / air_trsm
            / carb_trsm
        )

        flux = flux * 1.8
        dose_rate = (
            1e-3
            # * 1e-14
            * self.dose_rate_per_photon_per_mmsq(energy)
            * flux
            / beam_size[0]
            / beam_size[1]
        )
        max_frame_rate = 1 / HWR.beamline.detector.get_exposure_time_limits()[0]

        result = {
            "energy": energy,
            "detector_distance": detector_distance,
            "size_x": beam_size[0],
            "size_y": beam_size[1],
            "transmission": transmission,
            "intensity": intensity_value,
            "flux": flux,
            "dose_rate": dose_rate,
            "time_to_reach_limit": 20000.0 / dose_rate,
            "frames_to_reach_limit": int(max_frame_rate * 20000.0 / dose_rate),
            "max_frame_rate": max_frame_rate,
        }

        return result
