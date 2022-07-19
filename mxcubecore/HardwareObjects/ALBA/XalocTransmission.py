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
[Name]
XalocTransmission

[Description]
Specific HwObj to setup the beamline transmission

[Emitted signals]
- valueChanged
- stateChanged
"""

#from __future__ import print_function

import logging

from mxcubecore.BaseHardwareObjects import Device, HardwareObjectState

__credits__ = ["ALBA"]
__version__ = "3"
__category__ = "General"


class XalocTransmission(Device):

    #Taurus 4.1.1 DevState
    #ALARM = 11
    #CLOSE = 2
    #DISABLE = 12
    #EXTRACT = 5
    #FAULT = 8
    #INIT = 9
    #INSERT = 4
    #MOVING = 6
    #OFF = 1
    #ON = 0
    #OPEN = 3
    #RUNNING = 10
    #STANDBY = 7
    #UNKNOWN = 13

    # BaseHardwareObjects.HardwareObjectState(enum.Enum):
    #UNKNOWN = 0
    #WARNING = 1
    #BUSY = 2
    #READY = 3
    #FAULT = 4
    #OFF = 5

    Tango2HWO_State = [ 
                        HardwareObjectState.READY,    # 0 DevState.ON
                        HardwareObjectState.OFF,      # 1 DevState.OFF
                        HardwareObjectState.READY,   # 2 DevState.CLOSE
                        HardwareObjectState.READY,   # 3 DevState.OPEN
                        HardwareObjectState.BUSY,     # 4 DevState.INSERT
                        HardwareObjectState.BUSY,     # 5 DevState.EXTRACT
                        HardwareObjectState.BUSY,     # 6 DevState.MOVING
                        HardwareObjectState.READY,    # 7 DevState.STANDBY
                        HardwareObjectState.FAULT,    # 8 DevState.FAULT
                        HardwareObjectState.BUSY,     # 9 DevState.INIT
                        HardwareObjectState.BUSY,     # 10 DevState.RUNNING
                        HardwareObjectState.FAULT,    # 11 DevState.ALARM
                        HardwareObjectState.OFF,      # 12 DevState.DISABLE
                        HardwareObjectState.UNKNOWN   # 13 DevState.UNKNOWN
                      ]
    
    def __init__(self, *args):
        Device.__init__(self, *args)
        self.logger = logging.getLogger("HWR.XalocTransmission")
        self.chan_transmission = None
        self.chan_state = None

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        self.chan_transmission = self.get_channel_object("transmission")
        self.chan_state = self.get_channel_object("state")

        self.chan_transmission.connect_signal("update", self.transmission_changed)
        self.chan_state.connect_signal("update", self.state_changed)
        
        self.update_values()

    def is_ready(self):
        return True

    def transmission_changed(self, value):
        self.emit('valueChanged', value)

    def state_changed(self, value):
        #TODO: translate DevState to Hardware Object states
        
        self.emit('stateChanged', self.Tango2HWO_State[ value ] )

    #def getAttState(self):
        #self.state = self.chan_state.get_value()
        #return self.state

    #def getAttFactor(self):
        #return self.get_value()

    def get_value(self):
        return self.chan_transmission.get_value()

    def get_state(self):
        return self.chan_state.get_value()
    
    def set_value(self, value):
        self.chan_transmission.set_value(value)

    def set_transmission(self, value):
        self.set_value(value)

    def update_values(self):
        value = self.get_value()
        self.transmission_changed( value )
        state = self.get_state()
        self.state_changed( state )


def test_hwo(hwo):
    print("Transmission is: ", hwo.get_value())
    print("Transmission state is: ", hwo.getAttState())
