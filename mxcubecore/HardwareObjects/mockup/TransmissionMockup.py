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

__credits__ = ["The MxCuBE collaboration"]
__copyright__ = """ Copyright 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"
__version__ = "2.3."
__api__ = "3"
__category__ = "Actuator"


from HardwareRepository.TaskUtils import task
from HardwareRepository.HardwareObjects.abstract.AbstractActuator import \
    (AbstractActuator)


class TransmissionMockup(AbstractActuator):

    def __init__(self, name):
        AbstractActuator.__init__(self, name)

    def init(self):
        AbstractActuator.init(self)
        self.log.debug("Initializing")
        self.update_limits((0, 1))
        self.update_state(self.STATES.READY)

    def get_value(self):
        """Read the transmission value.
        Returns:
            Normalized transmission value.
        """
        return self._nominal_value

    @task
    def _set_value(self, value):
        """
        Sets the hardware to target a given transmission.
        Args:
            value: target normalized transmission value
        """
        self._nominal_value = value

    def abort(self):
        pass

    def get_state(self):
        return self.STATES.READY
