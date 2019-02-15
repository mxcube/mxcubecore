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

from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Device
import logging
from taurus.core.tango.enums import DevState


class ALBAFrontLight(Device):

    def __init__(self,*args):
        Device.__init__(self,*args)
        self.limits = [None,None]

        self.state = None
        self.register_state = None

        self.current_level = None
        self.memorized_level = None
        self.previous_level = None
      
        self.default_off_threshold = 1
        self.off_threshold = None

    def init(self):

        self.level_channel = self.getChannelObject("light_level")
        self.state_channel = self.getChannelObject("state")
        threshold = self.getProperty("off_threshold", self.default_off_threshold)

        if threshold is not None:
            try:
                self.off_threshold = float(threshold)
            except:
                self.off_threshold = self.default_threshold
                logging.getLogger("HWR").info("OFF Threshold for front light is not valid. Using %s" % self.off_threshold)
 

        limits = self.getProperty("limits")
        if limits is not None:
            lims = limits.split(",")
            if len(lims) == 2:
                self.limits = map(float, lims)

        self.level_channel.connectSignal("update", self.level_changed)
        self.state_channel.connectSignal("update", self.register_state_changed)

    def isReady(self):
        return True
 
    def level_changed(self,value):
        self.current_level = value
        self.update_current_state()

        self.emit('levelChanged', self.current_level)

    def register_state_changed(self, value):
        logging.getLogger("HWR").debug("*** Register state changed, value = %s" % value)
        #self.register_state = str(value).lower()
        if value == DevState.ON:
            self.register_state = "on"
        elif value == DevState.OFF:
            self.register_state = "off"
        else:
            self.register_state = "fault"
        self.update_current_state()

    def update_current_state(self):
        if self.register_state == "on":  
             if self.off_threshold is not None and \
                self.current_level < 0.9 * self.off_threshold:
                 newstate = "off"
             else:
                 newstate = "on"
        elif self.register_state == "off":
             newstate = "off"
        else:
             newstate = "fault"

        if newstate != self.state:
            if newstate == "off":
                self.memorized_level = self.previous_level

        self.state = newstate
        self.emit('stateChanged', self.state)

        self.previous_level = self.current_level
            
    def getLimits(self):
        return self.limits

    def getState(self):
        self.register_state = str(self.state_channel.getValue()).lower()
        self.update_current_state()
        return self.state

    def getUserName(self):
        return self.username

    def getLevel(self):
        self.current_level = self.level_channel.getValue()
        return self.current_level

    def setLevel(self, level):
        logging.getLogger("HWR").debug("Setting level in %s to %s" % (self.username, level))
        self.level_channel.setValue(float(level))

    def setOn(self):
        logging.getLogger("HWR").debug("Setting front light on")
        if self.memorized_level is not None:
             if self.memorized_level < self.off_threshold:
                 value = self.off_threshold
             else:
                 value = self.memorized_level
             logging.getLogger("HWR").debug("   setting value to")
             self.level_channel.setValue(value)
        else:
             self.level_channel.setValue(self.off_threshold)

    def setOff(self):
        logging.getLogger("HWR").debug("Setting front light off")
        self.level_channel.setValue(0.0)

def test_hwo(hwo):
    print "\nLight control for \"%s\"\n" % hwo.getUserName()
    print "   Level limits are:",  hwo.getLimits()
    print "   Current level is:",  hwo.getLevel()
    print "   Current state is:",  hwo.getState()
    #hwo.setOn()
    #hwo.setLevel(15)
