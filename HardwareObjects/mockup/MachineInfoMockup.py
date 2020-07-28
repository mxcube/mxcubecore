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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import os
import time
from random import uniform
from collections import OrderedDict

from gevent import spawn

from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository import HardwareRepository as HWR


__credits__ = ["MXCuBE collaboration"]
__version__ = "2.2."


class MachineInfoMockup(HardwareObject):
    """
    Descript. : Displays actual information about the beeamline
    """

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        """
        Descript. :
        """
        # Parameters
        # Intensity current ranges
        self.values_ordered_dict = OrderedDict()
        self.values_ordered_dict["current"] = {
            "value": 90.1,
            "value_str": "90.1 mA",
            "in_range": True,
            "title": "Machine current",
            "bold": True,
            "font": 14,
            "history": True,
        }

        self.values_ordered_dict["message"] = {
            "value": "Test message",
            "in_range": True,
            "title": "Machine state",
        }

        self.values_ordered_dict["temp"] = {
            "value": 24.4,
            "value_str": "24.4 C",
            "in_range": True,
            "title": "Hutch temperature",
        }

        self.values_ordered_dict["hum"] = {
            "value": 64.4,
            "value_str": "64.4 %",
            "in_range": True,
            "title": "Hutch humidity",
        }

        self.values_ordered_dict["flux"] = {
            "value": None,
            "value_str": "Remeasure flux!",
            "in_range": False,
            "title": "Flux",
        }

        self.values_ordered_dict["disk"] = {
            "value": "-",
            "in_range": True,
            "title": "Disk space",
            "align": "left",
        }

    def init(self):
        """
        Descript.
        """
        self.min_current = self.get_property("min_current", 80.1)
        self.min_current = self.get_property("max_current", 90.1)

        self.connect(HWR.beamline.flux, "fluxInfoChanged", self.flux_info_changed)

        self.re_emit_values()
        spawn(self.change_mach_current)

    def re_emit_values(self):
        """
        Updates storage disc information, detects if intensity
        and storage space is in limits, forms a value list
        and value in range list, both emited by qt as lists
        """
        self.emit("valuesChanged", self.values_ordered_dict)

    def get_current(self):
        return self.values_ordered_dict["current"]["value"]

    def get_current_value(self):
        return self.values_ordered_dict["current"]["value"]

    def get_message(self):
        return self.values_ordered_dict["message"]["value"]

    def change_mach_current(self):
        while True:
            self.values_ordered_dict["current"]["value"] = uniform(
                self.min_current, self.min_current
            )
            self.values_ordered_dict["current"]["value_str"] = (
                "%.1f mA" % self.values_ordered_dict["current"]["value"]
            )

            self.update_disk_space()
            self.re_emit_values()
            time.sleep(5)

    def flux_info_changed(self, flux_info):
        if flux_info["measured"] is None:
            self.values_ordered_dict["flux"]["value"] = 0
            self.values_ordered_dict["flux"]["value_str"] = "Remeasure flux!"
            self.values_ordered_dict["flux"]["in_range"] = False
        else:
            msg_str = "Flux: %.2E ph/s\n" % flux_info["measured"]["flux"]
            msg_str += "%d%% transmission, %dx%d beam" % (
                flux_info["measured"]["transmission"],
                flux_info["measured"]["size_x"] * 1000,
                flux_info["measured"]["size_y"] * 1000,
            )

            self.values_ordered_dict["flux"]["value"] = flux_info["measured"]["flux"]
            self.values_ordered_dict["flux"]["value_str"] = msg_str
            self.values_ordered_dict["flux"]["in_range"] = (
                flux_info["measured"]["flux"] > 1e6
            )
        self.re_emit_values()

    def update_disk_space(self):
        data_path = HWR.beamline.session.get_base_data_directory()
        data_path_root = "/%s" % data_path.split("/")[0]

        if os.path.exists(data_path_root):
            st = os.statvfs(data_path_root)
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            perc = st.f_bavail / float(st.f_blocks)
            txt = "Total: %s\nFree:  %s (%s)" % (
                self.sizeof_fmt(total),
                self.sizeof_fmt(free),
                "{0:.0%}".format(perc),
            )
        else:
            txt = "Not available"
        self.values_ordered_dict["disk"]["value_str"] = txt

    def sizeof_fmt(self, num):
        """Returns disk space formated in string"""

        for x in ["bytes", "KB", "MB", "GB"]:
            if num < 1024.0:
                return "%3.1f%s" % (num, x)
            num /= 1024.0
        return "%3.1f%s" % (num, "TB")

    def sizeof_num(self, num):
        """Returns disk space formated in exp value"""

        for x in ["m", chr(181), "n"]:
            if num > 0.001:
                num *= 1000.0
                return "%0.1f%s" % (num, x)
            num *= 1000.0
        return "%3.1f%s" % (num, " n")
