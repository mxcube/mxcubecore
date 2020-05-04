# -*- coding: utf-8 -*-
#
#  Project: MXCuBE
#  https://github.com/mxcube.
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""Resolution abstract implementation.
Overloaded methods: get_state, get_value, get_limits.
Implemented methods: _set_value, distance_to_resolution, resolution_to_distance.
Emited signals: valueChanged.
Hardware object used: energy and detecor.
The detector object can be defined in the configuration file. If not, the
one set from the beamline configuration is used.
"""

import abc
import logging
from numpy import arcsin, arctan, sin, sqrt, tan
from HardwareRepository import HardwareRepository as HWR
from HardwareRepository.HardwareObjects.abstract.AbstractMotor import AbstractMotor

__copyright__ = """ Copyright © 2010-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractResolution(AbstractMotor):
    """Abstract Resolution class"""

    __metaclass__ = abc.ABCMeta
    unit = "Å"

    def __init__(self, name):
        super(AbstractResolution, self).__init__(name)
        self._hwr_detector = None
        self._hwr_energy = None

    def init(self):
        """Initialisation"""
        super(AbstractResolution, self).init()
        self._hwr_detector = self.getObjectByRole("detector") or HWR.beamline.detector
        self._hwr_energy = HWR.beamline.energy

        self.connect(self._hwr_detector.distance, "stateChanged", self.update_state)
        self.connect(self._hwr_detector.distance, "valueChanged", self.update_distance)
        self.connect(self._hwr_energy, "valueChanged", self.update_energy)
        self.connect(self._hwr_energy, "stateChanged", self.update_state)

    def get_state(self):
        """Get the state of the distance motor.
        Returns:
            (enum 'MotorStates'): Motor state.
        """
        return self._hwr_detector.distance.get_state()

    def get_value(self):
        """Read the value.
        Returns:
            (float): value.
        """
        if self._nominal_value is None:
            _distance = self._hwr_detector.distance.get_value()
            self._nominal_value = self.distance_to_resolution(_distance)
        return self._nominal_value

    def get_limits(self):
        """Return resolution low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit).
        """
        _low, _high = self._hwr_detector.distance.get_limits()

        self._limits = (
            self.distance_to_resolution(_low),
            self.distance_to_resolution(_high),
        )
        return self._limits

    def set_limits(self, limits):
        """Resolution limits are not settable.
           Set the detector distance limits instead
        Raises:
            NotImplementedError
        """
        raise NotImplementedError

    def _set_value(self, value):
        """Move resolution to value.
        Args:
            value (float): target value [Å]
        """
        distance = self.resolution_to_distance(value)
        msg = "Move resolution to {} ({} mm)".format(value, distance)
        logging.getLogger().info(msg)
        self._hwr_detector.distance.set_value(distance)

    def _calculate_resolution(self, radius, distance):
        """Calculate the resolution as function of the detector radius and the distance.
        Args:
            radius (float): Detector radius [mm]
            distance (float): Distance from the sample to the detector [mm]
        Returns:
            (float): Resolution [Å]
        """
        _wavelength = self._hwr_energy.get_wavelength()
        try:
            ttheta = arctan(radius / distance)
            if ttheta:
                return _wavelength / (2 * sin(ttheta / 2))
        except (TypeError, ZeroDivisionError):
            logging.getLogger().exception("Error while calculating resolution")
        return None

    def distance_to_resolution(self, distance=None):
        """Convert distance to resolution.
        Args:
            distance (float): Distance [mm].
        Returns:
            (float): Resolution [Å].
        """
        distance = distance or self._hwr_detector.distance.get_value()

        return self._calculate_resolution(
            self._hwr_detector.get_radius(distance), distance
        )

    def resolution_to_distance(self, resolution=None):
        """Convert resolution to distance.
        Args:
            resolution(float): Resolution [Å].
        Returns:
            (float): distance [mm].
        """
        resolution = resolution or self._nominal_value
        _wavelength = self._hwr_detector.get_wavelength()

        try:
            ttheta = 2 * arcsin(_wavelength / (2 * resolution))
            return self._hwr_detector.get_radius() / ttheta
        except (KeyError, ZeroDivisionError):
            return None

    def get_value_at_corner(self):
        """Get the resolution at the corners of the detector.
        Returns:
            (float): Resolution [Å]
        """
        _distance = self._hwr_detector.distance.get_value()
        corner_distance = self._hwr_detector.get_outer_radius()
        return self._calculate_resolution(corner_distance, _distance)

    def update_distance(self, value=None):
        """Update the resolution when distance changed.
        Args:
            value (float): Detector distance [mm].
        """
        value = value or self._hwr_detector.distance.get_value()
        self._nominal_value = self.distance_to_resolution(value)
        self.emit("valueChanged", (self._nominal_value,))

    def update_energy(self, value):
        """Update the resolution when energy changed.
        Args:
            value(float): Energy [keV]
        """
        value = value or self._hwr_energy.get_value()
        _wavelength = self._hwr_energy._calculate_wavelength(value)
        _distance = self._hwr_detector.distance.get_value()
        _radius = self._hwr_detector.get_radius(_distance)
        try:
            ttheta = arctan(_radius / _distance)
            if ttheta:
                self._nominal_value = _wavelength / (2 * sin(ttheta / 2))
                self.emit("valueChanged", (self._nominal_value,))
        except (TypeError, ZeroDivisionError):
            logging.getLogger().exception("Error while calculating resolution")

    def abort(self):
        """Abort the distance motor movement"""
        self._hwr_detector.distance.abort()

    def stop(self):
        """Stop the distance motor movement"""
        self.self._hwr_detector.distance.stop()
