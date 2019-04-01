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

"""EMBLFLux"""

import logging
from copy import deepcopy

import gevent
import numpy
from scipy.interpolate import interp1d

from HardwareRepository.HardwareObjects.abstract.AbstractFlux import AbstractFlux


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


class EMBLFlux(AbstractFlux):
    """
    Contains methods to read flux from a diode
    """

    def __init__(self, name):

        AbstractFlux.__init__(self, name)

        self.measured_flux_dict = None
        self.measured_flux_list = None
        self.current_flux_dict = None
        self.measuring = False

        self.flux_value = 0
        self.intensity_ranges = []
        self.intensity_value = None
        self.beam_info = None
        self.transmission_value = None

        self.origin_flux_value = None
        self.origin_beam_info = None
        self.origin_transmission = None

        self.chan_intens_range = None
        self.chan_intens_mean = None
        self.cmd_set_intens_acq_time = None
        self.cmd_set_intens_range = None
        self.cmd_set_intens_resolution = None

        self.aperture_hwobj = None
        self.back_light_hwobj = None
        self.beam_focusing_hwobj = None
        self.beam_info_hwobj = None
        self.beamstop_hwobj = None
        self.detector_hwobj = None
        self.detector_distance_hwobj = None
        self.diffractometer_hwobj = None
        self.energy_hwobj = None
        self.fast_shutter_hwobj = None
        self.transmission_hwobj = None
        self.session_hwobj = None
        self.safety_shutter_hwobj = None

        self.diode_calibration_amp_per_watt = interp1d(
            [4.0, 6.0, 8.0, 10.0, 12.0, 12.5, 15.0, 16.0, 20.0, 30.0],
            [
                0.2267,
                0.2116,
                0.1405,
                0.086,
                0.0484,
                0.0469,
                0.0289,
                0.0240,
                0.01248,
                0.00388,
            ],
        )

        self.diode_calibration_amp_per_watt = interp1d(
            [4.0, 6.0, 8.0, 10.0, 12.0, 12.5, 15.0, 16.0, 20.0, 30.0],
            [
                0.2267,
                0.2116,
                0.1405,
                0.086,
                0.0484,
                0.0469,
                0.0289,
                0.0240,
                0.01248,
                0.00388,
            ],
        )

        self.air_absorption_coeff_per_meter = interp1d(
            [4.0, 6.6, 9.2, 11.8, 14.4, 17.0, 19.6, 22.2, 24.8, 27.4, 30],
            [
                9.19440446,
                2.0317802,
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
        self.carbon_window_transmission = interp1d(
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
        self.dose_rate_per_10to14_ph_per_mmsq = interp1d(
            [4.0, 6.6, 9.2, 11.8, 14.4, 17.0, 19.6, 22.2, 24.8, 27.4, 30.0],
            [
                459000.0,
                162000.0,
                79000.0,
                45700.0,
                29300.0,
                20200.0,
                14600.0,
                11100.0,
                8610.0,
                6870.0,
                5520.0,
            ],
        )

    def init(self):
        """Reads config xml, initiates all necessary hwobj, channels and cmds
        """
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
        except BaseException:
            logging.getLogger("HWR").error("BeamlineTest: No intensity ranges defined")

        self.chan_intens_mean = self.getChannelObject("intensMean")
        self.chan_intens_range = self.getChannelObject("intensRange")

        self.cmd_set_intens_resolution = self.getCommandObject("setIntensResolution")
        self.cmd_set_intens_acq_time = self.getCommandObject("setIntensAcqTime")
        self.cmd_set_intens_range = self.getCommandObject("setIntensRange")

        self.back_light_hwobj = self.getObjectByRole("backlight")
        self.beam_info_hwobj = self.getObjectByRole("beam_info")
        self.beamstop_hwobj = self.getObjectByRole("beamstop")
        self.detector_hwobj = self.getObjectByRole("detector")
        self.detector_distance_hwobj = self.getObjectByRole("detector_distance")
        self.diffractometer_hwobj = self.getObjectByRole("diffractometer")
        self.energy_hwobj = self.getObjectByRole("energy")
        self.fast_shutter_hwobj = self.getObjectByRole("fast_shutter")
        self.transmission_hwobj = self.getObjectByRole("transmission")
        self.session_hwobj = self.getObjectByRole("session")
        self.aperture_hwobj = self.beam_info_hwobj.aperture_hwobj
        self.safety_shutter_hwobj = self.getObjectByRole("safety_shutter")
        self.beam_info_hwobj = self.getObjectByRole("beam_info")

        self.connect(self.beam_info_hwobj, "beamInfoChanged", self.beam_info_changed)
        self.connect(self.transmission_hwobj, "valueChanged", self.transmission_changed)
        self.connect(
            self.aperture_hwobj, "diameterIndexChanged", self.aperture_diameter_changed
        )
        self.beam_focusing_hwobj = self.getObjectByRole("beam_focusing")
        if self.beam_focusing_hwobj is not None:
            self.connect(
                self.beam_focusing_hwobj,
                "focusingModeChanged",
                self.focusing_mode_changed,
            )

    def aperture_diameter_changed(self, index, size):
        """
        On the diameter change chooses value from a measured list
        :param index: int
        :param size: (float, flaot)
        :return:
        """
        if self.measured_flux_list and not self.measuring:
            self.current_flux_dict = self.measured_flux_list[index]
            self.measured_flux_dict = self.measured_flux_list[index]
            self.update_flux_value()

    def beam_info_changed(self, beam_info):
        """

        :param beam_info:
        :return:
        """
        self.beam_info = beam_info
        self.update_flux_value()

    def transmission_changed(self, transmission):
        """
        Scales flux value if the transmission has been changed
        :param transmission: float
        :return:
        """
        self.transmission_value = transmission
        self.update_flux_value()

    def focusing_mode_changed(self, mode, size):
        """
        Resets flux value if the beamline mode changes
        :param mode: str
        :param size: (float, float)
        :return:
        """
        self.current_flux_dict = None
        self.measured_flux_dict = None
        self.emit(
            "fluxInfoChanged",
            {"measured": self.measured_flux_dict, "current": self.current_flux_dict},
        )

    def get_flux(self):
        """
        Returns flux value
        :return: float
        """
        if self.current_flux_dict is not None:
            return self.current_flux_dict["flux"]
        else:
            return 1

    def set_flux(self, flux_value):
        """
        Sets flux value
        :param flux_value: float
        :return:
        """
        self.flux_value = flux_value
        self.emit("fluxValueChanged", flux_value)

    def set_flux_info(self, flux_info):
        """
        Sets flux info
        :param flux_info: float
        :return:
        """
        self.flux_value = flux_info["measured"]["flux"]
        self.emit("fluxInfoChanged", flux_info)

    def update_flux_value(self):
        """
        Updates flux value
        :return:
        """
        if self.measured_flux_dict is not None:

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

            origin_area = (
                self.measured_flux_dict["size_x"] * self.measured_flux_dict["size_y"]
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
        """
        Starts measure flux method
        :param wait:
        :return:
        """
        gevent.spawn(self.measure_flux_task, wait)

    def measure_flux_task(self, wait=True):
        """
        Actual flux measure task
        :param wait:
        :return:
        """
        if not self.safety_shutter_hwobj.is_opened():
            msg = "Unable to measure flux! Safety shutter is closed."
            self.print_log("GUI", "error", msg)
            return

        if not self.detector_hwobj.is_cover_closed():
            msg = "Unable to measure flux! Detecor cover is open."
            self.print_log("GUI", "error", "Unable to measure flux!")
            self.print_log("GUI", "error", msg)
            return

        if self.session_hwobj.beamline_name == "P14":
            if self.detector_distance_hwobj.get_position() > 501:
                msg = "Detector is too far away for flux measurements." +\
                      "Move to 500 mm or closer."
                self.print_log("GUI", "error", msg)
                return

        self.measuring = True
        max_frame_rate = 1 / self.detector_hwobj.get_exposure_time_limits()[0]

        current_phase = self.diffractometer_hwobj.current_phase
        current_transmission = self.transmission_hwobj.getAttFactor()
        current_aperture_index = self.aperture_hwobj.get_diameter_index()

        self.emit("progressInit", "Measuring flux. Please wait...", 10, True)

        # Set transmission to 100%
        # -----------------------------------------------------------------
        self.emit("progressStep", 1, "Setting transmission to 100%")
        self.transmission_hwobj.set_value(100, timeout=20)

        # Close the fast shutter
        # -----------------------------------------------------------------
        self.fast_shutter_hwobj.closeShutter(wait=True)
        logging.getLogger("HWR").debug("Measure flux: Fast shutter closed")
        gevent.sleep(0.1)

        # Move back light in, check beamstop position
        # -----------------------------------------------------------------
        logging.getLogger("HWR").info("Measure flux: Moving backlight out...")
        self.emit("progressStep", 1, "Moving backlight out")
        self.back_light_hwobj.move_in()
        logging.getLogger("HWR").debug("Measure flux: Backlight moved out")

        beamstop_position = self.beamstop_hwobj.get_position()
        if beamstop_position == "BEAM":
            self.emit("progressStep", 2, "Moving beamstop OFF")
            self.beamstop_hwobj.set_position("OFF")
            self.diffractometer_hwobj.wait_device_ready(30)
            logging.getLogger("HWR").info("Measure flux: Beamstop moved off")

        # Check scintillator position
        # -----------------------------------------------------------------
        scintillator_position = self.diffractometer_hwobj.get_scintillator_position()
        if scintillator_position == "SCINTILLATOR":
            self.emit("progressStep", 3, "Setting the photodiode")
            self.diffractometer_hwobj.set_scintillator_position("PHOTODIODE")
            gevent.sleep(1)
            self.diffractometer_hwobj.wait_device_ready(30)
            logging.getLogger("HWR").debug(
                "Measure flux: Scintillator set to photodiode"
            )

        self.measured_flux_list = []

        # -----------------------------------------------------------------
        if self.session_hwobj.beamline_name == "P13":
            self.aperture_hwobj.set_in()
            self.diffractometer_hwobj.wait_device_ready(30)
            self.aperture_hwobj.set_diameter_index(0)
            self.fast_shutter_hwobj.openShutter(wait=True)

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
                self.diffractometer_hwobj.wait_device_ready(10)

                gevent.sleep(1.5)
                intens_value = self.chan_intens_mean.getValue(force=True)
                self.fast_shutter_hwobj.closeShutter(wait=True)
                # intens_range_now = self.chan_intens_range.getValue()
                intensity_value = intens_value[0] + 1.872e-5  # 2.780e-6
                self.measured_flux_list.append(self.get_flux_result(intensity_value))
                gevent.sleep(1)
            max_frame_rate = 25
        else:
            self.emit("progressStep", 5, "Measuring the intensity")
            current_aperture_index = 0
            self.fast_shutter_hwobj.openShutter(wait=True)
            logging.getLogger("HWR").debug("Measure flux: Fast shutter opened")

            gevent.sleep(0.5)
            intens_value = self.chan_intens_mean.getValue()

            #intens_range_now = self.chan_intens_range.getValue()
            self.fast_shutter_hwobj.closeShutter(wait=True)
            logging.getLogger("HWR").debug("Measure flux: Fast shutter closed")

            intensity_value = intens_value[0] + 2.780e-6
            self.measured_flux_list.append(self.get_flux_result(intensity_value))

        self.emit("progressStep", 10, "Restoring original state")
        self.print_log("GUI", "info", "Flux measurement results:")
        self.print_log(
            "GUI",
            "info",
            "Beam size | Intensity (A) | Flux (ph/s) | "
            + "Dose rate (KGy/s) | Time to reach 20 MGy (s) | "
            + "Number of frames @ %d Hz" % max_frame_rate,
        )

        for item in self.measured_flux_list:
            msg = "  *  %d x %d | %1.1e  | %1.1e  | %1.1e  | %.1f  | %d" % (
                item["size_x"] * 1000,
                item["size_y"] * 1000,
                item["intensity"],
                item["flux"],
                item["dose_rate"],
                item["time_to_reach_limit"],
                item["frames_to_reach_limit"],
            )
            if item["flux"] < 1e9:
                self.print_log("GUI", "error", msg)
            else:
                self.print_log("GUI", "info", msg)
        """
            self.aperture_hwobj.set_diameter_index(current_aperture_index)
            else:
                self.fast_shutter_hwobj.openShutter(wait=True)
                gevent.sleep(1.0)
                intens_value = self.chan_intens_mean.getValue()
                self.intensity_value = intens_value[0] + 2.830e-6
                self.measured_flux_list.append(self.get_flux_result(self.intensity_value))
                current_aperture_index = 0
                self.fast_shutter_hwobj.closeShutter(wait=True)
        else: #except Exception as ex:
            logging.getLogger("GUI").error("Unable to measure flux! %s" % str(ex))
            self.fast_shutter_hwobj.closeShutter()
            self.emit("progressStop", ())
            return
        """

        if len(self.measured_flux_list) > 1:
            for index, item in enumerate(self.measured_flux_list):
                msg = "  *  %d | %1.1e  | %1.1e  | %.1f  | %d" % (
                    item["size_x"] * 1000,
                    item["flux"],
                    item["dose_rate"],
                    item["time_to_reach_limit"],
                    item["frames_to_reach_limit"],
                )

                # low_value = item["flux"] < 1e9
                low_value = item["intensity"] - 1.872e-5 < 2e-7
                out_of_range = False

                if index == 0:
                    if (
                        self.measured_flux_list[0]["flux"]
                        <= self.measured_flux_list[-1]["flux"]
                        or self.measured_flux_list[0]["flux"]
                        <= self.measured_flux_list[1]["flux"]
                    ):
                        out_of_range = True
                if low_value or out_of_range:
                    msg += "(intensity: %1.1e)" % item["intensity"]
                    self.print_log("GUI", "error", msg)
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
        self.transmission_hwobj.set_value(current_transmission)
        self.diffractometer_hwobj.wait_device_ready(10)
        self.diffractometer_hwobj.set_phase(current_phase)
        self.emit("progressStop", ())

    def get_flux_result(self, intensity_value):
        """
        Returns flux result based on the measured intensity
        :param intensity_value:
        :return:
        """
        energy = self.energy_hwobj.getCurrentEnergy()
        detector_distance = self.detector_hwobj.get_distance()
        beam_size = self.beam_info_hwobj.get_beam_size()

        transmission = self.transmission_hwobj.getAttFactor()
        air_trsm = numpy.exp(
            -self.air_absorption_coeff_per_meter(energy) * detector_distance / 1000.0
        )
        carb_trsm = self.carbon_window_transmission(energy)
        flux = (
            0.624151
            * 1e16
            * intensity_value
            / self.diode_calibration_amp_per_watt(energy)
            / energy
            / air_trsm
            / carb_trsm
        )

        flux = flux * 1.8
        dose_rate = (
            1e-3
            * 1e-14
            * self.dose_rate_per_10to14_ph_per_mmsq(energy)
            * flux
            / beam_size[0]
            / beam_size[1]
        )
        max_frame_rate = 1 / self.detector_hwobj.get_exposure_time_limits()[0]

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
