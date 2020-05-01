# encoding: utf-8
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.
"""Detector API"""

import abc
import math
from HardwareRepository.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractDetector(HardwareObject):
    """Common base class for detectors"""

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self._temperature = None
        self._humidity = None
        self._exposure_time_limits = (None, None)
        self._pixel_size = (None, None)

        self._binning_mode = 0
        self._roi_mode = 0
        self._roi_modes_list = []

        self._distance_motor_hwobj = None
        self.width = None  # [pixel]
        self.height = None  # [pixel]
        self._det_radius = None
        self._det_metadata = {}

    def init(self):
        """Initialise some common paramerters"""
        self.width = self.getProperty("width")
        self.height = self.getProperty("height")

        try:
            self._det_metadata = self["beam"]
        except KeyError:
            pass

        try:
            self._distance_motor_hwobj = self.getObjectByRole("detector_distance")
        except KeyError:
            pass

        self._pixel_size = (self.getProperty("px"), self.getProperty("py"))

    @property
    def distance(self):
        """Property for contained detector_distance hardware object
        Returns:
            (AbstratctMotor): Hardware object.
        """
        return self._distance_motor_hwobj

    @abc.abstractmethod
    def has_shutterless(self):
        """Check if detector is capable of shutterless acquisition.
        Returns:
            (bool): True if detector is capable, False otherwise
        """
        return

    @abc.abstractmethod
    def prepare_acquisition(self, *args, **kwargs):
        """
        Prepares detector for acquisition
        """

    def last_image_saved(self):
        """
        Returns:
            str: path to last image
        """
        return None

    @abc.abstractmethod
    def start_acquisition(self):
        """
        Starts acquisition
        """

    def stop_acquisition(self):
        """
        Stops acquisition
        """

    def get_roi_mode(self):
        """
        Returns:
            (str): current ROI mode
        """
        return self._roi_mode

    def set_roi_mode(self, roi_mode):
        """
        Args:
            roi_mode (int): ROI mode to set.
        """
        self._roi_mode = roi_mode

    def get_roi_mode_name(self):
        """
        Returns:
            (str): current ROI mode name
        """
        return self._roi_modes_list[self._roi_mode]

    def get_roi_modes(self):
        """
        Returns:
            tuple(str): Tuple with valid ROI modes.
        """
        return tuple(self._roi_modes_list)

    def get_exposure_time_limits(self):
        """
        Returns:
            tuple(float, float): Exposure time lower and upper limit [s]
        """
        return self._exposure_time_limits

    def get_pixel_size(self):
        """
        Returns:
            tuple(float, float): Pixel size for dimension 1 and 2 (x, y) [mm].
        """
        return self._pixel_size

    def get_binning_mode(self):
        """
        Returns:
            (int): current binning mode
        """
        return self._binning_mode

    def set_binning_mode(self, value):
        """
        Args:
            value (int): binning mode
        """
        self._binning_mode = value

    def get_beam_position(self, distance=None):
        """Calculate the beam position for a given distance.
        Args:
            distance(float): Distance [mm]
        Returns:
            tuple(float, float): Beam position x,y coordinates [pixel].
        """
        distance = distance or self._distance_motor_hwobj.get_value()
        try:
            return (
                float(distance * self._det_metadata["ax"] + self._det_metadata["bx"]),
                float(distance * self._det_metadata["ay"] + self._det_metadata["by"]),
            )
        except KeyError:
            return None, None

    def get_radius(self, distance=None):
        """Get distance form the beam position to the nearest detector edge.
        Args:
            distance (float): Distance [mm]
        Returns:
            (float): Detector radius [mm]
        """
        distance = distance or self._distance_motor_hwobj.get_value()
        beam_x, beam_y = self.get_beam_position(distance)
        self._det_radius = min(
            self.width - beam_x, self.height - beam_y, beam_x, beam_y
        )
        return self._det_radius

    def get_outer_radius(self, distance=None):
        """Get distance from beam_position to the furthest point on the detector.
        Args:
            distance (float): Distance [mm]
        Returns:
            (float): Detector router adius [mm]
        """
        distance = distance or self._distance_motor_hwobj.get_value()
        beam_x, beam_y = self.get_beam_position(distance)
        max_delta_x  = max(beam_x, self.width - beam_x)
        max_delta_y = max(beam_y, self.height - beam_y)
        return math.sqrt(max_delta_x * max_delta_x + max_delta_y * max_delta_y)

    def get_metadata(self):
        """Returns relevant metadata.
        Returns:
            (dict): metadata
        """
        self._det_metadata["width"] = self.width
        self._det_metadata["height"] = self.height

        return self._det_metadata
