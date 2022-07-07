# encoding: utf-8
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
"""
Example xml file:
<device class="EpicsMotor">
  <username>Detector Distance</username>
  <actuator_name>dtox</actuator_name>
  <channel type="epics" name="distanceDetector">Epics PV</channel>
  <tolerance>1e-2</tolerance>
</device>
"""

import enum
from ast import literal_eval

from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor
from mxcubecore.BaseHardwareObjects import HardwareObjectState
from gevent import sleep

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"



class EpicsMotor(AbstractMotor):
    """Epics Motor implementation"""

    def __init__(self, name):
        AbstractMotor.__init__(self, name)
        self.motor_position_channel = None
        self.motor_position = None
        self._nominal_limits = None, None

    def init(self):
        """Initialise the motor"""
        AbstractMotor.init(self)
        self.motor_position_channel = self.get_channel_object("detectorDistance")
        self.motor_position_channel.connectSignal("update", self.update_value)
        self.motor_position = self.get_value()
        limits = self.getProperty("default_limits")
        if limits:
            try:
                self._nominal_limits = tuple(literal_eval(limits))
            except TypeError:
                print("Invalid limits")
        self.username = self.getProperty("username")

        # init state to match motor's one
        self.update_state(HardwareObjectState.READY)

    def motor_position_changed(self, value):
        self.motor_position = value
        self.emit("valueChanged", (self.motor_position,))

    def get_state(self):
        """Get the motor state.
        Returns:
            (enum HardwareObjectState): Motor state.
        """
        state = HardwareObjectState.READY
        return state

    # def get_limits(self):
    #

    def _update_state(self, state=None):
        """Check if the state has changed. Emits signal stateChanged.
        Args:
            state (enum AxisState): state from a BLISS motor
        """
        self.update_state(state) if state is not None else self.update_state(HardwareObjectState.READY)

    def get_value(self):
        """Read the motor position.
        Returns:
            float: Motor position.
        """
        return self.motor_position_channel.getValue()

    def get_limits(self):
        """Returns motor low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit).
        """
        # TODO implement retrieval of limits..using PV info
        return self._nominal_limits
    #     # no limit = None, but None is a problematic value
    #     # for some GUI components (like MotorSpinBox), so
    #     # instead we return very large value.
    #
    #     # _low, _high = self.motor_obj.limits
    #     # _low = _low if _low else -1e6
    #     # _high = _high if _high else 1e6
    #     self._nominal_limits = (250, 1050)  # values in mm
    #     return self._nominal_limits

    # def get_velocity(self):
    #     """Read motor velocity.
    #     Returns:
    #         (float): velocity [unit/s]
    #     """
    #     self._velocity = self.motor_obj.velocity
    #     return self._velocity

    def _set_value(self, value):
        """Move motor to absolute value.
        Args:
            value (float): target value
        """
        self.motor_position_channel.setValue(value)
        self.update_value(value)


    def abort(self):
        """Stop the motor movement"""
        self.motor_position_channel.setValue('abort')

    def name(self):
        """Get the motor name. Should be removed when GUI ready"""
        return self.actuator_name
