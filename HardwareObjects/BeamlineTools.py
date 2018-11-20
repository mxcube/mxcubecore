#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
"""

from HardwareRepository.BaseHardwareObjects import HardwareObject

__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]
__version__ = "2.2."


class BeamlineTools(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.tools_list = []

    def init(self):
        for tool in self["tools"]:
            if tool.getProperty("separator"):
                self.tools_list.append("separator")
            else:
                tool_dict = {
                    "hwobj": self.getObjectByRole(tool.getProperty("hwobj")),
                    "display": tool.getProperty("display"),
                    "method": tool.getProperty("method"),
                }
                if tool.getProperty("icon"):
                    tool_dict["icon"] = tool.getProperty("icon")
                if tool.getProperty("confirmation"):
                    tool_dict["confirmation"] = tool.getProperty("confirmation")
                if tool.getProperty("expertMode"):
                    tool_dict["expertMode"] = tool.getProperty("expertMode")
                self.tools_list.append(tool_dict)

    def get_tools_list(self):
        return self.tools_list
