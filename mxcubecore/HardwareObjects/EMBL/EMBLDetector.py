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

"""EMBLDetector"""

import ast
import logging

import gevent

from HardwareRepository.HardwareObjects.abstract.AbstractDetector import (
    AbstractDetector,
)
from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


class EMBLDetector(AbstractDetector, HardwareObject):
    """Detector class. Contains all information about detector
    """

    def __init__(self, name):

        AbstractDetector.__init__(self)
        HardwareObject.__init__(self, name)

        self.collect_name = None
        self.shutter_name = None
        self.temp_treshold = None
        self.hum_treshold = None
        self.cover_state = None
        self.binning_mode = None
        self.pixel_size_mm_x = None
        self.pixel_size_mm_y = None

        self.binding_mode = 1
        self.tolerance = None
        self.temperature = 0
        self.humidity = 0
        self.actual_frame_rate = None
        self.pixel_min = None
        self.pixel_max = None
        self.roi_modes_list = []
        self.roi_mode = None

        self.chan_beam_xy = None
        self.chan_cover_state = None
        self.chan_temperature = None
        self.chan_humidity = None
        self.chan_status = None
        self.chan_roi_mode = None
        self.chan_frame_rate = None
        self.chan_actual_frame_rate = None

        self.cmd_close_cover = None
        self.cmd_restart_daq = None

        self.distance_motor_hwobj = None

    def init(self):
        self.cover_state = "unknown"
        self.collect_name = self.get_property("collectName")
        self.shutter_name = self.get_property("shutterName")
        self.tolerance = self.get_property("tolerance")
        self.temp_treshold = self.get_property("tempThreshold")
        self.hum_treshold = self.get_property("humidityThreshold")
        self.pixel_min = self.get_property("px_min")
        self.pixel_max = self.get_property("px_max")
        self.roi_modes_list = ast.literal_eval(self.get_property("roiModes"))
        self.binning_mode = "Unbinned"

        self.pixel_size_mm_x = self.get_property("px")
        self.pixel_size_mm_y = self.get_property("py")

        self.distance_motor_hwobj = self.get_object_by_role("distance_motor")

        self.chan_cover_state = self.get_channel_object("chanCoverState", optional=True)
        if self.chan_cover_state is not None:
            self.chan_cover_state.connect_signal("update", self.cover_state_changed)
        self.chan_temperature = self.get_channel_object("chanTemperature")
        self.chan_temperature.connect_signal("update", self.temperature_changed)
        self.chan_humidity = self.get_channel_object("chanHumidity")
        self.chan_humidity.connect_signal("update", self.humidity_changed)
        self.chan_status = self.get_channel_object("chanStatus")
        self.chan_status.connect_signal("update", self.status_changed)
        self.chan_roi_mode = self.get_channel_object("chanRoiMode")
        self.chan_roi_mode.connect_signal("update", self.roi_mode_changed)
        self.chan_frame_rate = self.get_channel_object("chanFrameRate")
        self.chan_frame_rate.connect_signal("update", self.frame_rate_changed)
        self.frame_rate_changed(self.chan_frame_rate.get_value())

        self.chan_actual_frame_rate = self.get_channel_object(
            "chanActualFrameRate", optional=True
        )
        if self.chan_actual_frame_rate is not None:
            self.chan_actual_frame_rate.connect_signal(
                "update", self.actual_frame_rate_changed
            )

        self.chan_beam_xy = self.get_channel_object("chanBeamXY")

        self.cmd_close_cover = self.get_command_object("cmdCloseCover")
        self.cmd_restart_daq = self.get_command_object("cmdRestartDaq")

    def has_shutterless(self):
        """Return True if has shutterless mode"""
        return self.get_property("hasShutterless")

    def get_collect_name(self):
        """Returns collection name"""
        return self.collect_name

    def get_shutter_name(self):
        """Returns shutter name"""
        return self.shutter_name

    def temperature_changed(self, value):
        """Updates temperatur value"""
        if self.temperature is None or abs(self.temperature - value) > self.tolerance:
            self.temperature = value
            self.emit("temperatureChanged", (value, value < self.temp_treshold))
            self.status_changed("dummy")

    def humidity_changed(self, value):
        """Update humidity value"""
        if self.humidity is None or abs(self.humidity - value) > self.tolerance:
            self.humidity = value
            self.emit("humidityChanged", (value, value < self.hum_treshold))
            self.status_changed("dummy")

    def status_changed(self, status):
        """Status changed event"""
        status = "uninitialized"
        status_message = "Detector: "

        if self.chan_status is not None:
            status = self.chan_status.get_value()

        if self.temperature > self.temp_treshold:
            msg = "Detector: Temperature %0.2f is greater than allowed %0.2f" % (
                self.temperature,
                self.temp_treshold,
            )
            logging.getLogger("GUI").warning(msg)
            status_message = "Temperature has exceeded threshold.\n"

        if self.humidity > self.hum_treshold:
            msg = "Detector: Humidity %0.2f is greater than allowed %0.2f" % (
                self.humidity,
                self.hum_treshold,
            )
            logging.getLogger("GUI").warning(msg)
            status_message = status_message + "Humidity has exceeded threshold.\n"

        if status == "calibrating":
            status_message = status_message + "Calibrating. Please wait...\n"
            logging.getLogger("GUI").warning(status_message)

        self.emit("statusChanged", (status, status_message))

    def roi_mode_changed(self, mode):
        """ROI mode change event"""
        self.roi_mode = self.roi_modes_list.index(str(mode))
        self.emit("detectorRoiModeChanged", (self.roi_mode,))

    def frame_rate_changed(self, frame_rate):
        """Updates frame rate"""
        if frame_rate is not None:
            self.exposure_time_limits[0] = 1 / float(frame_rate)
            self.exposure_time_limits[1] = 6000

        self.emit("expTimeLimitsChanged", (self.exposure_time_limits,))

    def actual_frame_rate_changed(self, value):
        """Updates actual frame rate"""
        self.actual_frame_rate = value
        self.emit("frameRateChanged", value)

    def set_roi_mode(self, mode):
        """Sets roi mode

        :param mode: roi mode
        :type mode: str
        """
        self.chan_roi_mode.set_value(self.roi_modes_list[mode])

    def get_beam_centre(self):
        """Returns beam center coordinates"""
        beam_x = 0
        beam_y = 0
        if self.chan_beam_xy is not None:
            value = self.chan_beam_xy.get_value()
            beam_x = value[0]
            beam_y = value[1]
        return beam_x, beam_y

    def get_beam_centre_pix(self):
        beam_x, beam_y = self.get_beam_centre()
        return beam_x / 0.075, beam_y / 0.075

    def get_pixel_size_mm(self):
        """Returns pixel size in mm"""
        return self.pixel_size_mm_x, self.pixel_size_mm_y

    def cover_state_changed(self, state):
        """Updates guillotine state"

        :param state: guillotine state (close, opened, ..)
        :type state: str
        """
        if isinstance(state, (list, tuple)):
            state = state[1]

        if state == 0:
            self.cover_state = "closed"
        elif state == 1:
            self.cover_state = "opened"
        elif state == 2:
            self.cover_state = "closing"
        elif state == 3:
            self.cover_state = "opening"
        return self.cover_state

    def get_cover_state(self):
        """Returns cover state

        :return: str
        """
        return self.cover_state_changed(self.chan_cover_state.get_value())

    def is_cover_closed(self):
        """Returns True if cover is closed

        :return: bool
        """
        self.get_cover_state()
        return self.cover_state == "closed"

    def close_cover(self, wait=True):
        """Closes detector cover

        :param wait: wait
        :type wait: bool
        :return: None
        """
        if self.get_cover_state() != "closed":
            self.cmd_close_cover([0, 0])
            if wait:
                # with gevent.Timeout(15, Exception("Timeout waiting for detector cover
                # to close")):
                while self.get_cover_state() != "closed":
                    gevent.sleep(0.05)

    def restart_daq(self):
        """Restarts detector DAQ

        :return: None
        """
        self.cmd_restart_daq(0)

    def re_emit_values(self):
        """Reemits signals"""
        self.emit("detectorRoiModeChanged", (self.roi_mode,))
        temp = self.chan_temperature.get_value()
        self.emit("temperatureChanged", (temp, temp < self.temp_treshold))
        hum = self.chan_humidity.get_value()
        self.emit("humidityChanged", (hum, hum < self.hum_treshold))
        self.status_changed("")
        self.emit("expTimeLimitsChanged", (self.exposure_time_limits,))
        self.emit("frameRateChanged", self.actual_frame_rate)
