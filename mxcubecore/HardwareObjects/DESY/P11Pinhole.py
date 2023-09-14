
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

"""P11Shutter"""


from mxcubecore.HardwareObjects.MotorsNPosition import MotorsNPosition
from configparser import ConfigParser

import copy


__credits__ = ["DESY P11"]
__license__ = "LGPLv3+"
__category__ = "General"


class P11Pinhole(MotorsNPosition):
    def __init__(self,name):

        super(P11Pinhole,self).__init__(name)

        self._config_file = None
        

    def init(self):
        """Initilise the predefined values"""

        # if simulation is set - open and close will be mere software flags

        self._config_file = self.get_property("config_file")

        super(P11Pinhole,self).init()


    def load_positions(self):

        config = ConfigParser()
        config.read(self._config_file)

        if not "Pinholes" in config:
            return

        names = config["Pinholes"]["pinholesizelist"].split(",")
        names[0] = "Down"

        units = ["micron",] * len(names)
        units[0] = ""

        posnames = copy.copy(names)
        posnames[1:] = [ "{}um".format(posname) for posname in posnames[1:] ]

        yposlist = map(int, config["Pinholes"]["pinholeyposlist"].split(","))
        zposlist = map(int, config["Pinholes"]["pinholezposlist"].split(","))

        for name, posname, unit, ypos, zpos in zip(names, posnames, units, yposlist, zposlist):
            self._positions[name] = {}
            self._properties[name] = {}

            self._positions[name]["pinholey"] = ypos
            self._positions[name]["pinholez"] = zpos
            self._positions[name]["unit"] = unit
            self._positions[name]["posname"] = posname
