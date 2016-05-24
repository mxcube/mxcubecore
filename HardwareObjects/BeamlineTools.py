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
[Name] BeamlineTools

[Description]

[Channels]

[Commands]

[Emited signals]

[Functions]
 
[Included Hardware Objects]
-----------------------------------------------------------------------
| name                 | signals        | functions
-----------------------------------------------------------------------
-----------------------------------------------------------------------
"""

from HardwareRepository.BaseHardwareObjects import HardwareObject

__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]
__version__ = "2.2."


class BeamlineTools(HardwareObject):
    """
    Description:
    """

    def __init__(self, name):
        """
        Descrip. :
        """
        HardwareObject.__init__(self, name)
        self.tools_list = []

    def init(self):
        """
        Descrip. :
        """
        for tool in self['tools']:
            self.tools_list.append({'hwobj': self.getObjectByRole(tool.hwobj),
                                    'display': tool.display,
                                    'method': tool.method,
                                    'icon': tool.icon})

    def get_tools_list(self):
        return self.tools_list
