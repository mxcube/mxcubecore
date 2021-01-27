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

"""
"""

from mxcubecore.BaseHardwareObjects import HardwareObject

__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE collaboration"]
__version__ = "2.2."


class BeamlineTools(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.tools_list = []

    def init(self):
        for tool in self["tools"]:
            if tool.get_property("separator"):
                self.tools_list.append("separator")
            else:
                tool_dict = {
                    "hwobj": self.get_object_by_role(tool.get_property("hwobj")),
                    "display": tool.get_property("display"),
                    "method": tool.get_property("method"),
                }
                if tool.get_property("icon"):
                    tool_dict["icon"] = tool.get_property("icon")
                if tool.get_property("confirmation"):
                    tool_dict["confirmation"] = tool.get_property("confirmation")
                if tool.get_property("expertMode"):
                    tool_dict["expertMode"] = tool.get_property("expertMode")
                self.tools_list.append(tool_dict)

    def get_tools_list(self):
        return self.tools_list
