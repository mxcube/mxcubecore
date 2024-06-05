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
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

__copyright__ = """ Copyright © 2010 - 2023 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


from collections import OrderedDict

from mxcubecore.HardwareObjects.abstract.AbstractActuator import AbstractActuator
from mxcubecore.HardwareObjects.abstract.AbstractMotor import MotorStates
from mxcubecore.BaseHardwareObjects import HardwareObjectState


class MotorsNPosition(AbstractActuator):
    """
    <object class="MotorsNState">
        <username>Dummy</username>

        <motors>
            <object role="role1" href="/mot1"></object>
            <object role="role2" href="/mot2"></object>
        </motors>

        <deltas>
            <role1>0.1</role1>
            <role2>0.3</role1>
        </deltas>

        <positions>
            <position>
                <name>BEAM</name>
                <role1>0.12</role1>
                <role2>0.22</role2>
                <favproperty>I am in the Beam</favproperty>
            </position>

            <position>
                <name>OUTBEAM</name>
                <role1>2.3</role1>
                <role2>4.6</role2>
                <favproperty>I am out of Beam</favproperty>
            </position>
        </positions>

    </object>
    """

    default_delta = 0.01

    def __init__(self, name):
        AbstractActuator.__init__(self, name)

        self.motor_hwobjs = {}
        self.deltas = {}

        self._positions = OrderedDict()
        self._properties = OrderedDict()
        self.motorlist = []

        self.current_index = None

        self._last_position_name = None
        self._updating_multi_value = None

    def init(self):
        motorlist = self.get_property("motorlist").split(",")
        self.motorlist = [motor.strip() for motor in motorlist]

        for motorname in self.motorlist:
            motor_hwo = self.get_object_by_role(motorname)
            self.motor_hwobjs[motorname] = motor_hwo

            delta = self["deltas"].get_property(motorname, self.default_delta)
            self.deltas[motorname] = delta

            self.connect(motor_hwo, "stateChanged", self.motor_state_changed)
            self.connect(motor_hwo, "valueChanged", self.motor_value_changed)

        self.load_positions()

        self.update_multi_value()
        self.update_state(HardwareObjectState.READY)

    def load_positions(self):
        positions = self["positions"]

        for position in positions:
            name = position.get_property("name")

            self._positions[name] = {}
            self._properties[name] = {}

            for motorname in self.motorlist:
                pos = position.get_property(motorname)
                self._positions[name][motorname] = pos

            for prop in position.get_properties():
                if prop not in self.motorlist:
                    if prop != "name":
                        value = position.get_property(prop)
                        self._properties[name][prop] = value

    def get_position_list(self):
        return list(self._positions.keys())

    def get_property_value_by_index(self, position_index=None, property_name=None):
        """
        Returns the value of the property with the given property_name at the specified position_index.
        If the property_name or position_index is invalid, returns None.
        """
        if position_index is not None and 0 <= position_index < len(self._positions):
            position_name = list(self._positions.keys())[position_index]
            return self._properties.get(position_name, {}).get(property_name)
        return None

    def get_value(self):
        return self.update_multi_value()

    def set_position(self, posname):
        """
        Allow to move by providing in order (if previous not found):
               posname
               name
               index
        """

        # by posname - alias
        for posidx, name in enumerate(self._positions):
            if posname == self.get_property_value_by_index(posidx, "posname"):
                self._set_value(posidx)
                return

        # by name - label
        for posidx, name in enumerate(self._positions):
            if posname == name:
                self._set_value(posidx)
                return

        if isinstance(posname, int):
            if posname >= 0 and posname < len(self._positions):
                self._set_value(posname)
                return

        self.user_log.error(
            "Wrong position name %s selected for %s" % (posname, self.username)
        )

    def _set_value(self, value):
        if value >= 0 and value < len(self._positions):
            name = list(self._positions.keys())[value]
            for motorname in self.motorlist:
                pos = self._positions[name][motorname]
                motor_hwobj = self.motor_hwobjs[motorname]
                motor_hwobj.set_value(pos)

    def get_position(self):
        current_idx = self.get_value()
        if current_idx is not None and current_idx != -1:
            return list(self._positions.keys())[current_idx]


    def motor_state_changed(self, state):
        self.update_multi_state()

    def motor_value_changed(self, position=None):
        self.update_multi_value()

    def update_multi_value(self):
        if self._updating_multi_value:
            return
        self._updating_multi_value = True

        current_idx = -1
        current_pos = {
            motorname: self.motor_hwobjs[motorname].get_value()
            for motorname in self.motorlist
        }

        for idx, name in enumerate(self._positions):
            for motorname in self.motorlist:
                if motorname not in self._positions[name]:
                    continue

                position = self._positions[name][motorname]
                cur_pos = current_pos[motorname]
                delta = self.deltas[motorname]

                if abs(cur_pos - position) > delta:
                    break
            else:
                for motorname in self.motorlist:
                    position = self._positions[name][motorname]
                    self.log.debug("     - motor %s is at %s" % (motorname, position))
                current_idx = idx
                break

        if current_idx != self.current_index:
            self.current_index = current_idx
            self.update_value(current_idx)
        
        self._updating_multi_value = False

        return current_idx

    def update_multi_state(self):

        multi_state = HardwareObjectState.READY

        for motorname in self.motor_hwobjs:
            motor = self.motor_hwobjs[motorname]
            state = motor.get_state()

            self.log.debug(
                "MotorsNPosition - updating multi_state. motor (%s) is %s"
                % (motorname, str(state))
            )

            if state in (HardwareObjectState.FAULT, HardwareObjectState.UNKNOWN):
                multi_state = state
                break

            if state == HardwareObjectState.OFF:
                multi_state = state
                continue

            if state in (MotorStates.MOVING, HardwareObjectState.BUSY):
                if multi_state != HardwareObjectState.OFF:
                    multi_state = HardwareObjectState.BUSY
                    continue

        self.update_state(multi_state)

    def stop(self):
        """
        Descript. :
        """
        for motor in self.motor_hwobjs:
            motor.stop()

    def is_moving(self):
        """
        Descript. : True if the motor is currently moving
        """
        return self.get_state() == HardwareObjectState.BUSY
