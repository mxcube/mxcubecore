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

from HardwareRepository.BaseHardwareObjects import Device

__credits__ = ["ALBA"]
__version__ = "2.3."
__category__ = "General"


class ALBATransmission(Device):

    def __init__(self, *args):
        Device.__init__(self, *args)
        self.chan_transmission = None
        self.chan_state = None
        self.transmission = None

    def init(self):
        self.chan_transmission = self.getChannelObject("transmission")
        self.chan_state = self.getChannelObject("state")

        self.chan_transmission.connectSignal("update", self.transmissionChanged)
        self.chan_state.connectSignal("update", self.stateChanged)

    def isReady(self):
        return True

    def transmissionChanged(self, value):
        self.transmission = value
        self.emit('attFactorChanged', self.transmission)

    def stateChanged(self, value):
        self.state = value
        self.emit('attStateChanged', self.state)

    def getAttState(self):
        self.state = self.chan_state.getValue()
        return self.state

    def getAttFactor(self):
        return self.get_value()

    def get_value(self):
        self.transmission = self.chan_transmission.getValue()
        return self.transmission

    def set_value(self, value):
        self.transmission = value
        self.chan_transmission.setValue(value)

    def setTransmission(self, value):
        self.set_value(value)

    def update_values(self):
        value = self.get_value()
        self.emit('attFactorChanged', value)


def test_hwo(hwo):
    print "Transmission is: ", hwo.get_value()
    print "Transmission state is: ", hwo.getAttState()
