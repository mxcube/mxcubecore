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
import logging
from HardwareRepository.BaseHardwareObjects import Device


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3"
__category__ = "General"


class MDFastShutter(Device):
    shutterState = {
        3: 'unknown',
        1: 'closed',
        0: 'opened',
        46: 'disabled'} 

    def __init__(self, name):
        Device.__init__(self, name)
        self.chan_shutter_state = None
        self.chan_current_phase = None

        self.states_dict = None
        self.state = None
        self.current_phase = None 

    def init(self):
        self.states_dict = {False: "closed",
                            True: "opened"}

        self.chan_current_phase = self.getChannelObject("chanCurrentPhase")
        if self.chan_current_phase is not None:
            self.current_phase = self.chan_current_phase.getValue()
            self.connect(self.chan_current_phase, "update", self.current_phase_changed)

        self.chan_shutter_state = self.getChannelObject("chanShutterState")
        if self.chan_shutter_state:
            self.chan_shutter_state.connectSignal("update", self.shutter_state_changed)

    def shutter_state_changed(self, value):
        self.state_bit = value
        if self.current_phase == "BeamLocation":
            self.state = self.states_dict.get(value, "unknown")
        else:
            self.state = "disabled"
        self.emit('shutterStateChanged', (self.state, self.state.title()))

    def current_phase_changed(self, value):
        self.current_phase = value
        if self.chan_shutter_state: 
            self.shutter_state_changed(self.chan_shutter_state.getValue()) 
    
    def getShutterState(self):
        self.shutter_state_changed(self.chan_shutter_state.getValue())
        return self.state

    def openShutter(self, wait=True):
        self.chan_shutter_state.setValue(True) 
        with gevent.Timeout(10, Exception("Timeout waiting for fast shutter open")):
               while not self.state_bit:
                     gevent.sleep(0.1)

    def is_opened(self):
        return self.state == "opened"

    def closeShutter(self, wait=True):
        self.shutter_state_changed(self.chan_shutter_state.getValue())

        if self.is_opened():
            self.chan_shutter_state.setValue(False)
            with gevent.Timeout(10, Exception("Timeout waiting for fast shutter close")):
                   while self.state_bit:
                         gevent.sleep(0.1)

