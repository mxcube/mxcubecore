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

__copyright__ = """Copyright The MXCuBE Collaboration"""
__license__ = "LGPLv3+"

import logging
import time

import gevent

from mxcubecore.HardwareObjects.abstract.AbstractTransmission import (
    AbstractTransmission,
)

log = logging.getLogger("HWR")


class P11Transmission(AbstractTransmission):
    """
    P11Transmission class for controlling transmission settings.

    This class extends the AbstractTransmission class and provides
    methods to interact with hardware for setting and reading the
    transmission values, as well as handling state changes.

    Attributes:
        chan_read_value (Channel): Channel object to read the current value.
        chan_set_value (Channel): Channel object to set the transmission value.
        chan_state (Channel): Channel object to track the state of the hardware.
    """

    def __init__(self, name):
        """
        Initializes the P11Transmission object with the given name.

        Args:
            name (str): The name of the transmission component.
        """
        super().__init__(name)
        self.chan_read_value = None
        self.chan_set_value = None
        self.chan_state = None

    def init(self):
        """
        Initializes the hardware channels and connects signals.

        This method sets up the communication channels for reading,
        setting, and tracking the transmission state. It connects
        signals to handle updates from the hardware.
        """
        self.chan_read_value = self.get_channel_object("chanRead")
        self.chan_set_value = self.get_channel_object("chanSet")
        self.chan_state = self.get_channel_object("chanState")

        if self.chan_read_value is not None:
            self.chan_read_value.connect_signal("update", self.re_emit_value)

        if self.chan_state is not None:
            self.chan_state.connect_signal("update", self.state_changed)

        self.re_emit_values()

    def re_emit_value(self, *args):
        """
        Re-emits the current transmission value and state.

        This method triggers the state and value updates to ensure
        the current hardware state and value are reflected in the software.

        Args:
            *args: Optional argument to handle extra signal data.
        """
        self.state_changed()
        # Value update is now handled in AbstractActuator, no need for value_changed method here

    def get_state(self):
        """
        Gets the current state of the transmission.

        Returns:
            str: The current state of the transmission ("READY", "BUSY", or "FAULT").
        """
        self.state_changed()
        return self._state

    def get_value(self):
        """
        Retrieves the current transmission value from the hardware.

        Returns:
            float: The current transmission value, multiplied by 100.
        """
        return self.chan_read_value.get_value() * 100.0

    def state_changed(self, state=None):
        """
        Handles state changes from the hardware.

        Args:
            state (str, optional): The new state from the hardware. If None, the state is fetched from the channel.
        """
        if state is None:
            state = self.chan_state.get_value()

        _str_state = str(state)

        if _str_state == "ON":
            _state = self.STATES.READY
        elif _str_state == "MOVING":
            _state = self.STATES.BUSY
        else:
            _state = self.STATES.FAULT

        self.update_state(_state)

    def _set_value(self, value):
        """
        Sets a new transmission value to the hardware.

        Args:
            value (float): The new transmission value to set.
        """
        value = value / 100.0
        self.chan_set_value.set_value(value)

        while self.get_state() == "MOVING":
            time.sleep(0.1)
            print("Changing transmission")
