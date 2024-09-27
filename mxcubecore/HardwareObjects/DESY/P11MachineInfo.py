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
import gevent
from mxcubecore.HardwareObjects.abstract.AbstractMachineInfo import AbstractMachineInfo
from mxcubecore.HardwareObjects.TangoMachineInfo import TangoMachineInfo
from mxcubecore.HardwareObjects.TangoMachineInfo import TangoMachineInfo
from PyQt5.QtCore import QObject, pyqtSignal


class P11MachineInfo(TangoMachineInfo, QObject):
    # Declare the signal
    valuesChanged = pyqtSignal(dict)

    # Declare the signal
    machineCurrentChanged = pyqtSignal(float, bool)

    def __init__(self, *args, **kwargs):
        """Initializes the P11MachineInfo and QObject."""
        # Initialize both parent classes explicitly
        TangoMachineInfo.__init__(
            self, *args, **kwargs
        )  # Initialize the TangoMachineInfo class
        QObject.__init__(self)  # Initialize the QObject class

    def init(self):
        """Initialize Tango channels for machine info."""
        super().init()

        self.emit_values()  # Emit initial values after init
        gevent.spawn(self.periodic_update)

    def periodic_update(self):
        while True:
            self.emit_values()
            gevent.sleep(3)

    def emit_values(self):
        """Emit the current machine info values."""
        values_dict = {
            "current": {
                "title": "Current (mA)",
                "value": self.get_current() or 0,  # Ensure value is not None
            },
            "lifetime": {"title": "Lifetime (h)", "value": self.get_lifetime() or 0},
            "energy": {
                "title": "Energy (GeV)",
                "value": self.get_maschine_energy() or 0,
            },
            "message": {
                "title": "Message",
                "value": self.get_message() or "No message",
            },
        }

        logging.info(f"Emitting machine info values: {values_dict}")
        self.valuesChanged.emit(values_dict)  # Emit the valuesChanged signal

    def get_value(self):
        """Returns a dictionary of the current machine information."""
        try:
            self._mach_info_dict = {}  # Initialize dictionary

            # Fetch the current values from their respective methods
            self._mach_info_dict["current"] = self.get_current() or 0
            self._mach_info_dict["lifetime"] = self.get_lifetime() or 0
            self._mach_info_dict["energy"] = self.get_maschine_energy() or 0
            self._mach_info_dict["message"] = self.get_message() or "No message"

            logging.info(
                f"Machine Info Dictionary: {self._mach_info_dict}"
            )  # Log the populated dictionary
            return self._mach_info_dict  # Return the dictionary with machine info

        except Exception as e:
            logging.error(f"Error getting machine values: {e}")
            return {}  # Return empty dictionary if there's an error

    def get_current(self):
        try:
            current_value = (
                self.current.get_value()
            )  # Fetch the value from the Tango hardware
            return round(current_value, 2)
        except AttributeError:
            logging.error("Error reading 'current': Attribute 'current' not found.")
            return 0

    def get_lifetime(self):
        try:
            lifetime_value = self.lifetime.get_value()  # Fetch lifetime value
            return round(lifetime_value, 2)
        except AttributeError:
            logging.error("Error reading 'lifetime': Attribute 'lifetime' not found.")
            return 0

    def get_maschine_energy(self):
        try:
            energy_value = self.energy.get_value()  # Fetch energy value
            return round(energy_value, 2)
        except AttributeError:
            logging.error("Error reading 'energy': Attribute 'energy' not found.")
            return 0

    def get_message(self):
        try:
            message_value = self.message.get_value()  # Fetch message from hardware
            return message_value
        except AttributeError:
            logging.error("Error reading 'message': Attribute 'message' not found.")
            return "Message unavailable"

    def update_current(self, current_value, in_range):
        # Emit the signal with the current machine value and its range status
        self.machineCurrentChanged.emit(current_value, in_range)
