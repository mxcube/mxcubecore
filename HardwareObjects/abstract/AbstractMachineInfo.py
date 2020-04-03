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

import abc, os

from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository import HardwareRepository as HWR

class AbstractMachineInfo(HardwareObject):
    """Abstract machine info"""

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._current = None
        self._message = None
        self._temperature = None
        self._humidity = None
        self._flux = None
        self._values = {}

    def init(self):
        """Initialise some parameters."""
        self._values["current"] = {
            "value": None,
            "value_str": "-- mA",
            "in_range": False,
            "title": "Machine current",
            "bold": True,
            "font": 14,
            "history": True,
        }
        self._values["message"] = {
            "value": 'None',
            "in_range": True,
            "title": "Machine state",
        }
        self._values["temp"] = {
            "value": None,
            "value_str": "-- °C",
            "in_range": False,
            "title": "Hutch temperature",
        }
        self._values["hum"] = {
            "value": None,
            "value_str": "-- %",
            "in_range": False,
            "title": "Hutch humidity",
        }
        self._values["flux"] = {
            "value": None,
            "value_str": 'None',
            "in_range": False,
            "title": "Flux",
        }
        self._values["disk"] = {
            "value": None,
            "value_str": "Not available",
            "in_range": False,
            "title": "Disk space",
            "align": "left",
        }

    @abc.abstractmethod
    def get_current(self):
        """Read current.
        Returns:
            value: Current.
        """
        return None

    @abc.abstractmethod
    def get_message(self):
        """Read message.
        Returns:
            value: Message.
        """
        return None

    @abc.abstractmethod
    def get_temperature(self):
        """Read hutch temperature.
        Returns:
            value: Hutch temperature.
        """
        return None

    @abc.abstractmethod
    def get_humidity(self):
        """Read hutch humidity.
        Returns:
            value: Hutch humidity.
        """
        return None

    @abc.abstractmethod
    def get_flux(self):
        """Read flux.
        Returns:
            value: Flux.
        """
        return None

    @abc.abstractmethod
    def in_range_flux(self, value):
        """Check if flux value is in range.
        Args:
            value: value
        Returns:
            (bool): True if in range.
        """
        return True

    def sizeof_fmt(self, num):
        """Return disk space formated in string"""
        for x in ["bytes", "KB", "MB", "GB"]:
            if num < 1024.0:
                return "{:3.1f}{}".format(num, x)
            num /= 1024.0
        return "{:3.1f}{}".format(num, "TB")

    def get_disk_space(self):
        """Retrieve disk space info.
        Returns:
            value: Tuple of total (bytes), free (bytes) and used (%) of disk
            space.
        """
        data_path = HWR.beamline.session.get_base_data_directory()
        data_path_root = "/%s" % data_path.split("/")[0]
        if os.path.exists(data_path_root):
            st = os.statvfs(data_path_root)
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            perc = st.f_bavail / float(st.f_blocks)
            return (total, free, perc)
        return None

    @abc.abstractmethod
    def in_range_disk_space(self, value):
        """Check disk space is in range.
        Args:
            value: value
        Returns:
            (bool): True if in range.
        """
        return True

    def get_value(self):
        """Read machine info.
        Returns:
            value: dict
        """
        current = self.get_current()
        self._current = current
        self._values['current']['value'] = current
        try:
            float(current)
            self._values['current']['value_str'] = \
            "%3.2f mA" % current
            self._values['current']['in_range'] = True
        except TypeError:
            self._values['current']['value_str'] = str(current)
            self._values['current']['in_range'] = False

        msg = self.get_message()
        self._message = msg
        self._values['message']['value'] = msg
        self._values['message']['in_range'] = (msg is not None)

        temp = self.get_temperature()
        self._temperature = temp
        self._values['temp']['value'] = temp
        try:
            float(temp)
            self._values['temp']['value_str'] = "%2.1f °C" % temp
            self._values['temp']['in_range'] = True
        except TypeError:
            self._values['temp']['value_str'] = str(temp)
            self._values['temp']['in_range'] = False

        hum = self.get_humidity()
        self._humidity = hum
        self._values['hum']['value'] = hum
        try:
            float(hum)
            self._values['hum']['value_str'] = "{:2.1f} %".format(hum)
            self._values['hum']['in_range'] = True
        except TypeError:
            self._values['hum']['value_str'] = str(hum)
            self._values['hum']['in_range'] = False

        flux = self.get_flux()
        self._flux = flux
        self._values['flux']['value'] = flux
        try:
            float(flux)
            self._values['flux']['value_str'] = \
            "{:.2E} ph/s".format(flux)
            self._values['flux']['in_range'] = \
            self.in_range_flux(flux)
        except TypeError:
            self._values['flux']['value_str'] = str(flux)
            self._values['flux']['in_range'] = False

        disk = self.get_disk_space()
        self._disk = disk
        try:
            total_str = self.sizeof_fmt(disk[0])
            free_str = self.sizeof_fmt(disk[1])
            perc_str = "{0:.0%}".format(disk[2])
            disk_txt = "Total: {}\nFree:  {} ({})".format(total_str, free_str,
            perc_str)
            in_range = self.in_range_disk_space(disk)
        except TypeError:
            disk_txt = "Not available"
            in_range = False
        self._values["disk"]["value"] = disk
        self._values["disk"]["value_str"] = disk_txt
        self._values["disk"]["in_range"] = in_range

        return self._values

    def update_value(self, value=None):
        """Check if the value has changed. Emits signal valueChanged.
        Args:
            value: value
        """
        if value is None:
            value = self.get_value()

        self._values = value
        self.emit("valueChanged", value)

        # Compatibility signals. To be removed.
        self.emit("valuesChanged", value) # mxcube2
        self.emit("machInfoChanged", value) # mxcube3

# Compatibility methods. To be removed.

    # mxcube2
    def get_current_value(self):
        self.get_current()

    def update_values(self, value=None):
        self.update_value()

    # mxcube3
    def getCurrent(self):
        self.get_current()

    def _update_me(self):
        self.update_value()
