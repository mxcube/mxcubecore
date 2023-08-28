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

__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"

from mxcubecore.HardwareObjects.abstract.AbstractEnergy import AbstractEnergy
from mxcubecore.HardwareObjects.mockup.ActuatorMockup import ActuatorMockup

import logging

log = logging.getLogger("HWR")


class P11Energy(AbstractEnergy):

    _default_energy = 12.0

    def __init__(self, name):
        super(P11Energy, self).__init__(name)

    def init(self):
        self.chan_energy = self.get_channel_object("chanEnergy")
        if self.chan_energy is not None:
            self.chan_energy.connectSignal("update", self.energy_position_changed)

        self.chan_status = self.get_channel_object("chanStatus")
        if self.chan_status is not None:
            self.chan_status.connectSignal("update", self.energy_state_changed)

        limits = self.get_property("limits", None)

        try:
            limits = list(map(float, limits.split(",")))
        except Exception as e:
            log.error("P11Transmission - cannot parse limits: {}".format(str(e)))
            limits = None

        if limits is None:
            log.error(
                "P11Transmission - Cannot read LIMITS from configuration xml file.  Check values"
            )
            return
        else:
            self.set_limits(limits)

        self.re_emit_values()

    def re_emit_values(self):
        self._nominal_value = None
        self._state = None
        self.energy_state_changed()
        self.energy_position_changed()

    def is_ready(self):
        return self._state == self.STATES.READY

    def energy_state_changed(self, state=None):
        if state is None:
            state = self.chan_status.getValue()

        _state = str(state)

        if _state == "ON":
            self._state = self.STATES.READY
        elif _state == "MOVING":
            self._state = self.STATES.BUSY
        elif _state == "DISABLED":
            self._state = self.STATES.OFF
        else:
            self._state = self.STATES.FAULT

        self.emit("stateChanged", self._state)

    def energy_position_changed(self, pos=None):
        """
        Event called when energy value has been changed
        :param pos: float
        :return:
        """
        if pos is None:
            pos = self.chan_energy.getValue()

        energy = pos / 1000.0

        if self._nominal_value is None or abs(energy - self._nominal_value) > 1e-3:
            self._nominal_value = energy
            self._wavelength_value = 12.3984 / energy
            if self._wavelength_value is not None:
                self.emit(
                    "energyChanged", (self._nominal_value, self._wavelength_value)
                )
                self.emit("valueChanged", (self._nominal_value,))

    def _set_value(self, value):
        """
        Implementation pending
        """
        pass

    def get_value(self):
        """
        Returns current energy in keV
        :return: float
        """

        value = self._default_energy
        if self.chan_energy is not None:
            try:
                value = self.chan_energy.getValue()
                return value / 1000
            except Exception:
                logging.getLogger("HWR").exception(
                    "Energy: could not read current energy"
                )
                return None
        return value

    # def get_limits(self):
    # return my_limits


def test_hwo(hwo):
    print("Energy is: {0} keV".format(hwo.get_value()))
