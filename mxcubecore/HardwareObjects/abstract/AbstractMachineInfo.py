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
"""Abstract machine info class"""

import abc
from ast import literal_eval

from mxcubecore.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractMachineInfo(HardwareObject):
    """Abstract machine info - information coming from the accelerator source.
       It provides only few common to all accelerators parameters.

    Emits:
        valueChanged: ("valueChanged", (value,))

    Attributes:
        _mach_info_dict: Dictionary with all the defined parameters.
        _mach_info_keys: List of keys to be present in the above dictionary.

    Note:
        The methods to be used to fill the _mach_info_dict should start with
        get_ (e.g. get_current for reading the current)
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        super().__init__(name)
        self._mach_info_dict = {}
        self._mach_info_keys = []

    def init(self):
        """Get the attributes to be defined as keys in the _machine_info_dict"""
        attr = self.get_property("parameters")
        if attr:
            self._check_attributes(literal_eval(attr))
        else:
            # at least current should be in the list
            self._check_attributes(["current"])

    @abc.abstractmethod
    def get_current(self) -> float:
        """Read the ring current.

        Returns:
            Current [mA].
        """
        return 0

    def get_message(self) -> str:
        """Read the operator's message.

        Returns:
            Message.
        """
        return ""

    def get_lifetime(self) -> float:
        """Read the lifetime.

        Returns:
            Lifetime [s].
        """
        return 0

    def get_topup_remaining(self) -> float:
        """Read the top-up remaining time.

        Returns:
            Top-up remaining [s].
        """
        return 0

    def get_fill_mode(self) -> str:
        """Read the fill mode as text.

        Returns:
            Machine fill mode
        """
        return ""

    def get_value(self) -> dict:
        """Read machine info summary as dictionary.

        Returns:
            Copy of the _mach_info_dict.
        """
        for val in dir(self):
            if val.startswith("get_"):
                if val[4:] in self._mach_info_keys:
                    self._mach_info_dict.update({val[4:]: getattr(self, val)()})
        return self._mach_info_dict.copy()

    def _check_attributes(self, attr_list=None):
        """Check if all the keys in the configuration file have
        implemented read method. Remove the undefined.
        """
        attr_list = attr_list or self._mach_info_keys

        for attr_key in attr_list:
            try:
                getattr(self, f"get_{attr_key}")
            except AttributeError:
                attr_list.remove(attr_key)
        self._mach_info_keys = attr_list

    def update_value(self, value=None):
        """Emits signal valueChanged.

        Args:
            value(dict): Dictionary with all the value
        """
        if value is None:
            value = self.get_value()

        self.emit("valueChanged", (value,))
