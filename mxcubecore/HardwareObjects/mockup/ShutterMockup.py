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

import time
import random
from HardwareRepository.HardwareObjects.abstract.AbstractNState import AbstractNState, OpenCloseEnum


class ShutterMockup(AbstractNState):
    """
    ShutterMockup for simulating a simple open/close shutter. For more detailed
    method documentation see AbstractShutter
    """
    def __init__(self, name):
        AbstractNState.__init__(self, name)
        self.setProperty("state_definition", "OpenCloseEnum")

    def _set_value(self, value):
        time.sleep(random.uniform(0.1, 1.0))

    def  get_predefined_values(self):
        return {"OPEN": "open", "CLOSED": "closed"}

