# encoding: utf-8
#
#  Project name: MXCuBE
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

"""BlissShutter class - interface for shutter controlled by BLISS
Implements _set_value, get_value methods
Bliss states are: UNKNOWN, OPEN, CLOSED, FAULT
"MOVING", "DISABLE", "STANDBY", "RUNNING"
Example yml configuration:

.. code-block:: yaml

 class: BlissShutter.BlissShutter
 configuration:
   actuator_name: safshut
   type: tango
   username: Safety shutter
"""

import logging
from enum import (
    Enum,
    unique,
)

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.abstract.AbstractShutter import AbstractShutter

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


@unique
class BlissShutterStates(Enum):
    """Shutter states definitions."""

    OPEN = HardwareObjectState.READY, "OPEN"
    CLOSED = HardwareObjectState.READY, "CLOSED"
    MOVING = HardwareObjectState.BUSY, "MOVING"
    DISABLE = HardwareObjectState.WARNING, "DISABLE"
    AUTOMATIC = HardwareObjectState.READY, "RUNNING"
    UNKNOWN = HardwareObjectState.UNKNOWN, "RUNNING"
    FAULT = HardwareObjectState.WARNING, "FAULT"


class BlissShutter(AbstractShutter):
    """BLISS implementation of AbstractShutter"""

    SPECIFIC_STATES = BlissShutterStates
    # Only OPEN and CLOSED are user-commandable; the other values in VALUES
    # (MOVING, DISABLE, STANDBY, FAULT) are read-only status indicators.
    COMMANDABLE_VALUES = ("OPEN", "CLOSED")

    def __init__(self, name):
        super().__init__(name)
        self._bliss_obj = None
        self.shutter_type = None
        self.opening_mode = None

    def init(self):
        """Initialise the predefined values"""
        super().init()
        try:
            bliss_proxy = HWR.beamline.bliss_proxy
            bliss_proxy.hardware.register(self.actuator_name)
            self._bliss_obj = bliss_proxy.get_object(self.actuator_name)
        except Exception as exc:
            logging.getLogger("MX3.HWR").warning(
                "BlissShutter '%s': BLISS object '%s' not available (%s)",
                self.actuator_name,
                self.actuator_name,
                exc,
            )
            self._bliss_obj = None
            return
        # for now we only treat tango type shutter
        self.shutter_type = self.get_property("type", "tango")
        try:
            if self._bliss_obj.frontend:
                self.opening_mode = self._bliss_obj.mode
        except AttributeError:
            # there is no frontend property
            pass
        if self.shutter_type == "tango":
            self._initialise_values()

        self._bliss_obj.subscribe("property", self._on_property_changed)
        self._bliss_obj.subscribe("online", self._on_online_changed)

        self.update_state(self.get_state())
        self.update_value(self.get_value())

    def _on_online_changed(self, online: bool) -> None:
        """Callback for shutter online/offline events received via blissclient."""
        if not online:
            self.update_state(HardwareObjectState.UNKNOWN)
        else:
            self._update_state()

    def _on_property_changed(self, data: dict) -> None:
        """Callback for property changes received via blissclient."""
        if "state" in data:
            self._update_state()

    def _update_state(self):
        """Refresh state and value from the shutter object."""
        self.update_value(self.get_value())
        self.update_state(self.get_state())

    def _initialise_values(self):
        """Add the tango states to VALUES"""
        values_dict = {item.name: item.value for item in self.VALUES}
        values_dict.update(
            {
                "MOVING": "MOVING",
                "DISABLE": "DISABLE",
                "STANDBY": "STANDBY",
                "FAULT": "FAULT",
            }
        )
        self.VALUES = Enum("ValueEnum", values_dict)

    def get_state(self):
        """Get the device state.
        Returns:
            (enum 'HardwareObjectState'): Device state.
        """
        try:
            _state = self._bliss_obj.state or "UNKNOWN"
            return self.SPECIFIC_STATES[_state].value[0]
        except (AttributeError, KeyError):
            return self.STATES.UNKNOWN
        except Exception:
            return self.STATES.UNKNOWN

    def get_value(self):
        """Get the device value
        Returns:
            (Enum): Enum member, corresponding to the value or UNKNOWN.
        """
        try:
            _val = self._bliss_obj.state or "UNKNOWN"
        except Exception:
            _val = "UNKNOWN"
        return self.value_to_enum(_val)

    def _set_value(self, value):
        if self._bliss_obj is None:
            raise RuntimeError(
                f"BlissShutter '{self.actuator_name}' is offline — "
                "BLISS object not available"
            )
        if value.name == "OPEN":
            self._bliss_obj.open()
        elif value.name == "CLOSED":
            self._bliss_obj.close()

    def set_mode(self, value):
        """Set automatic or manual mode for a Frontend shutter
        Args:
            value (str): MANUAL or AUTOMATIC
        Raises: NotImplementedError: Not a Frontend shutter.
        """
        self._bliss_obj.mode = value
        self.opening_mode = value
