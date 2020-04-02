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

import gevent

from HardwareRepository.HardwareObjects.abstract.AbstractMachineInfo import (
    AbstractMachineInfo,
)

class MachineInfoMockupTEST(AbstractMachineInfo):
    """Display actual information about the beamline"""

    def __init__(self, name):
        AbstractMachineInfo.__init__(self, name)

    def get_current(self):
        """Override method."""
        return 123.45

    def get_message(self):
        """Override method."""
        return 'Beam Delivered'

    def get_temperature(self):
        """Override method."""
        return 24.4

    def get_humidity(self):
        """Override method."""
        return 64.4

    def get_flux(self):
        """Override method."""
        return 2000000.0

    def in_range_flux(self, value):
        """Override method."""
        return value > 1E6

    def in_range_disk_space(self, value):
        """Override method."""
        free_bytes = value[1]
        return free_bytes > 4 * 1024^3 # At least 4 GB to be in range

def test():
    import sys

    from HardwareRepository import HardwareRepository as HWR

    hwr = HWR.getHardwareRepository()
    hwr.connect()
    conn = hwr.getHardwareObject(sys.argv[1])

    print(("Machine info dict: ", conn.get_value()))
    print(("Current: ", conn.get_current()))
    print(("Message: ", conn.get_message()))
    print(("Temperature: ", conn.get_temperature()))
    print(("Humidity: ", conn.get_humidity()))
    print(("Flux: ", conn.get_flux()))
    print(("Disk (bytes): ", conn.get_disk()))

    #while True:
    #    gevent.wait(timeout=0.1)

if __name__ == "__main__":
    test()
