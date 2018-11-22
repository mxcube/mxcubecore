#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import tine
import numpy
import gevent
import logging

from copy import deepcopy
from datetime import datetime
from scipy.interpolate import interp1d

from AbstractFlux import AbstractFlux


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


class EMBLFlux(AbstractFlux):
    def __init__(self, name):
        AbstractFlux.__init__(self, name)

        self.measured_flux_dict = None
        self.measured_flux_list = None
        self.current_flux_dict = None
        self.flux_value = 1

        self.ampl_chan_index = None
        self.intensity_ranges = []
        self.intensity_value = None

        self.origin_flux_value = None
        self.origin_beam_info = None
        self.origin_transmission = None

        self.chan_intens_range = None
        self.chan_intens_mean = None
        self.cmd_set_intens_acq_time = None
        self.cmd_set_intens_range = None
        self.cmd_set_intens_resolution = None

        self.back_light_hwobj = None
        self.beam_info_hwobj = None
        self.beamstop_hwobj = None
        self.detector_hwobj = None
        self.diffractometer_hwobj = None
        self.energy_hwobj = None
        self.fast_shutter_hwobj = None
        self.transmission_hwobj = None
        self.session_hwobj = None

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
        self.diffractometer_hwobj = self.getObjectByRole("diffractometer")
        self.energy_hwobj = self.getObjectByRole("energy")
        self.fast_shutter_hwobj = self.getObjectByRole("fast_shutter")
        self.transmission_hwobj = self.getObjectByRole("transmission")
        self.session_hwobj = self.getObjectByRole("session")
        self.aperture_hwobj = self.beam_info_hwobj.aperture_hwobj

        # P14
        """
        self.connect(self.beam_info_hwobj,
                     "beamInfoChanged",
                     self.beam_info_changed)
        """
        self.connect(self.transmission_hwobj, "valueChanged", self.transmission_changed)
        self.connect(
            self.aperture_hwobj, "diameterIndexChanged", self.aperture_diameter_changed
        )

    def aperture_diameter_changed(self, index, size):
        if self.measured_flux_list and not self.measuring:
            self.current_flux_dict = self.measured_flux_list[index]
            self.measured_flux_dict = self.measured_flux_list[index]
            self.update_flux_value()

    def beam_info_changed(self, beam_info):
        self.beam_info = beam_info
        self.update_flux_value()

    def transmission_changed(self, transmission):
        self.transmission = transmission
        self.update_flux_value()

    def get_flux(self):
        return self.flux_value

        if self.current_flux_dict is not None:
            return self.current_flux_dict["flux"]
        else:
            return 1

    def set_flux(self, flux_value):
        # self.result_dict = flux_dict
        # self.update_flux_value()
        self.flux_value = flux_value
        self.emit("fluxValueChanged", flux_value)

    def set_flux_info(self, flux_info):
        self.emit("fluxInfoChanged", flux_info)

    def update_flux_value(self):
        if self.measured_flux_dict is not None:

            self.current_flux_dict = deepcopy(self.measured_flux_dict)
            if int(self.transmission) != int(self.measured_flux_dict["transmission"]):
                self.current_flux_dict["flux"] = (
                    self.measured_flux_dict["flux"]
                    * self.transmission
                    / self.measured_flux_dict["transmission"]
                )
                self.current_flux_dict["transmission"] = self.transmission
                """
                 if self.origin_beam_info != self.beam_info:
                    if self.origin_beam_info['shape'] == 'ellipse':
                        origin_area = 3.141592 * pow(self.origin_beam_info['size_x'] / 2, 2)
                    else:
                        origin_area = self.origin_beam_info['size_x'] * \
                                      self.origin_beam_info['size_y']

                    if self.beam_info['shape'] == 'ellipse':
                        current_area = 3.141592 * pow(self.beam_info['size_x'] / 2, 2)
                    else:
                        current_area = self.beam_info['size_x'] * \
                                       self.beam_info['size_y']
                    self.flux_value = self.flux_value * current_area / \
                                      origin_area
                 """
            self.emit(
                "fluxChanged",
                {
                    "measured": self.measured_flux_dict,
                    "current": self.current_flux_dict,
                },
            )

    def measure_flux(self, wait=True):
        gevent.spawn(self.measure_flux_task, wait)

    def measure_flux_task(self, wait=True):
        try:
            self.measuring = True
            intens_value = 0
            current_phase = self.diffractometer_hwobj.current_phase
            current_transmission = self.transmission_hwobj.get_value()
            current_aperture_index = self.aperture_hwobj.get_diameter_index()

            self.emit("progressInit", "Measuring flux. Please wait...", 10, True)

            self.emit("progressStep", 1, "Setting transmission to 100%")
            self.transmission_hwobj.setTransmission(100, timeout=20)

            # 1. close guillotine and fast shutter -------------------------------
            if not self.detector_hwobj.is_cover_closed():
                self.print_log(
                    "GUI",
                    "error",
                    "Unable to measure flux!" + "Close the detecor cover to continue",
                )
                self.emit("progressStop", ())
                return

            # 2. move back light in, check beamstop position ----------------------
            self.emit("progressStep", 1, "Moving backlight in")
            self.back_light_hwobj.move_in()
            self.aperture_hwobj.set_diameter_index(0)

            beamstop_position = self.beamstop_hwobj.get_position()
            if beamstop_position == "BEAM":
                self.emit("progressStep", 2, "Moving beamstop OFF")
                self.beamstop_hwobj.set_position("OFF")
                self.diffractometer_hwobj.wait_device_ready(30)

            # 3. check scintillator position --------------------------------------
            scintillator_position = (
                self.diffractometer_hwobj.get_scintillator_position()
            )
            if scintillator_position == "SCINTILLATOR":
                # TODO add state change when scintillator position changed
                self.emit("progressStep", 3, "Setting the photodiode")
                self.diffractometer_hwobj.set_scintillator_position("PHOTODIODE")
                gevent.sleep(0.5)
                self.diffractometer_hwobj.wait_device_ready(30)

            # TODO move in the apeture for P13
            if self.session_hwobj.beamline_name == "P13":
                # self.bl_hwobj.diffractometer_hwobj.set_capillary_position("BEAM")
                self.aperture_hwobj.set_in()
                self.diffractometer_hwobj.wait_device_ready(30)
                self.ampl_chan_index = 0

                self.fast_shutter_hwobj.openShutter(wait=True)

                self.measured_flux_list = []
                for index, diameter_size in enumerate(
                    self.aperture_hwobj.get_diameter_list()
                ):
                    # 5. open the fast shutter -----------------------------------------
                    self.emit(
                        "progressStep",
                        4 + index,
                        "Measuring flux with %d micron aperture" % diameter_size,
                    )
                    logging.getLogger("GUI").info(
                        "Measuring flux with %d micron aperture" % diameter_size
                    )
                    # TODO replace with beam area
                    beamsize = (diameter_size / 1000.0, diameter_size / 1000.0)
                    self.aperture_hwobj.set_diameter_index(index)
                    self.diffractometer_hwobj.wait_device_ready(10)

                    gevent.sleep(1.5)
                    intens_value = self.chan_intens_mean.getValue(force=True)
                    # intens_range_now = self.chan_intens_range.getValue()
                    intensity_value = intens_value[0] + 1.872e-5  # 2.780e-6
                    self.measured_flux_list.append(
                        self.get_flux_result(intensity_value, beamsize)
                    )
                    gevent.sleep(0.5)

                self.fast_shutter_hwobj.closeShutter(wait=True)

        except Exception as ex:
            logging.getLogger("GUI").error("Unable to measure flux! %s" % str(ex))
            self.fast_shutter_hwobj.closeShutter()
            self.emit("progressStop", ())
            return

        max_frame_rate = 1 / self.detector_hwobj.get_exposure_time_limits()[0]

        self.emit("progressStep", 10, "Restoring original state")
        self.print_log("GUI", "info", "Flux measurement results:")
        self.print_log(
            "GUI",
            "info",
            "Aperture | Intensity (A) | Flux (ph/s) | "
            + "Dose rate (KGy/s) | Time to reach 20 MGy (s) | "
            + "Number of frames @ %d Hz" % max_frame_rate,
        )

        for item in self.measured_flux_list:
            msg = "  *  %d | %1.1e  | %1.1e  | %1.1e  | %.1f  | %d" % (
                item["beam_size"][0] * 1000,
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

        self.measured_flux_dict = self.measured_flux_list[current_aperture_index]
        self.current_flux_dict = self.measured_flux_list[current_aperture_index]

        self.emit(
            "fluxChanged",
            {"measured": self.measured_flux_dict, "current": self.current_flux_dict},
        )
        self.measuring = False

        # 7 Restoring previous states ----------------------------------------
        self.transmission_hwobj.setTransmission(current_transmission)
        self.diffractometer_hwobj.wait_device_ready(10)
        self.diffractometer_hwobj.set_phase(current_phase)
        self.aperture_hwobj.set_diameter_index(current_aperture_index)
        self.emit("progressStop", ())

    def get_flux_result(self, intensity_value, beam_size):
        energy = self.energy_hwobj.getCurrentEnergy()
        detector_distance = self.detector_hwobj.get_distance()
        beam_size = self.beam_info_hwobj.get_beam_size()
        transmission = self.transmission_hwobj.get_value()
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
            "beam_size": beam_size,
            "transmission": transmission,
            "intensity": intensity_value,
            "flux": flux,
            "dose_rate": dose_rate,
            "time_to_reach_limit": 20000.0 / dose_rate,
            "frames_to_reach_limit": int(max_frame_rate * 20000.0 / dose_rate),
            "max_frame_rate": max_frame_rate,
        }

        return result
