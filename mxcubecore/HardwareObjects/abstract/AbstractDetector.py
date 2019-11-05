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

import abc

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
        self._exposure_time_limits = [None, None]
        self._pixel_size = 0

        self._distance_limits = [None, None]
        self._binning_mode = 0
        self._roi_mode = 0
        self._roi_modes_list = []

        self._distance_motor_hwobj = None

    def init(self):
        self._distance_motor_hwobj = self.getObjectByRole("detector_distance")

    @property
    def distance(self):
        """Property for contained detector_distance hwobj

        NBNB Temnporary hack. This should eb configured pro[perly

        Returns:
            AbstratctActuator
        """
        return self._distance_motor_hwobj

    @abc.abstractmethod
    def get_distance_limits(self):
        """
        Returns:
            tuple[float, float]: tuple containing the pair lower limit, upper limit in mm
        """
        return

    @abc.abstractmethod
    def has_shutterless(self):
        """
        Returns:
            bool: True if detector is capable of shutterless acquisition False otherwise
        """
        return

    @abc.abstractmethod
    def prepare_acquisition(self, *args, **kwargs):
        """
        Prepares detector for acquisition
        """
        return

    @abc.abstractmethod
    def last_image_saved(self):
        """
        Returns:
            str: path to last image
        """
        return

    @abc.abstractmethod
    def start_acquisition(self):
        """
        Starts acquisition
        """
        return

    @abc.abstractmethod
    def stop_acquisition(self):
        """
        Stops acquisition
        """

    @abc.abstractmethod
    def wait_ready(self):
        """
        Blocks until detector is ready
        """
        return

    def get_roi_mode(self):
        """
        Returns:
            str" current ROI mode
        """
        return self._roi_mode

    def set_roi_mode(self, roi_mode):
        """
        Args:
            roi_mode (int): ROI mode to set
        """
        self._roi_mode = roi_mode

    def get_roi_mode_name(self):
        """
        Returns:
            str: current ROI mode name
        """
        return self._roi_modes_list[self._roi_mode]

    def get_roi_modes(self):
        """
        Returns:
            tuple[str]: Tuple with valid ROI modes
        """
        return tuple(self._roi_modes_list)

    def get_exposure_time_limits(self):
        """
        Returns:
            tuple[float, float]: Exposure time lower and upper limit in s
        """
        return self._exposure_time_limits

    def get_pixel_size(self):
        """
        Returns:
            tuple(float, float): Pixel size in mm for dimension 1 and dimension 2 (x, y)
        """
        return self._pixel_size

    def get_binning_mode(self):
        """
        Returns:
            int: current binning mode
        """
        return self._binning_mode

    def set_binning_mode(self, value):
        """
        Args:
            value (int): binning mode
        """
        self._binning_mode = value
    