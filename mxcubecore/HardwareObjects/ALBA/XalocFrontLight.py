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
[Name] XalocFrontLight

[Description]
HwObj used to control the diffractometer front light.

[Signals]
- levelChanged
- stateChanged
"""

#from __future__ import print_function

import logging

from mxcubecore.BaseHardwareObjects import Device
from taurus.core.tango.enums import DevState

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"


class XalocFrontLight(Device):

    def __init__(self, *args):
        Device.__init__(self, *args)
        self.logger = logging.getLogger("HWR.XalocFrontLight")
        
        self.chan_level = None
        self.chan_state = None

        self.limits = [None, None]

        self.state = None
        self.dev_server_state = None # state of the device server controlling the light

        self.current_level = None

        self.default_off_threshold = 1 # threshold is 1 click above off value
        self.off_threshold = None

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        self.chan_level = self.get_channel_object("light_level")
        self.chan_state = self.get_channel_object("state")
        self.off_threshold = self.get_property("off_threshold", self.default_off_threshold)
        self.logger.debug("Off_threshold value = %s" % self.off_threshold)

        self.set_name('frontlight')

        limits = self.get_property("limits")
        if limits is not None:
            lims = limits.split(",")
            if len(lims) == 2:
                self.limits = map(float, lims)

        self.chan_level.connect_signal("update", self.level_changed)
        self.chan_state.connect_signal("update", self.dev_server_state_changed)

    def is_ready(self):
        return True

    def level_changed(self, value):
        #self.logger.debug("FrontLight level changed, value = %s" % value)
        self.current_level = float( value )
        self.update_current_state()

        self.emit('levelChanged', self.current_level)

    def dev_server_state_changed(self, value):
        #self.logger.debug("Device server state changed, value = %s" % value)
        self.dev_server_state = value
        if value != DevState.ON:
            self.logger.error("The device server of the front light is not ON")
            logging.getLogger('user_level_log').error("The device server of the front light is not ON. Call your LC")
        self.update_current_state()

    def update_current_state(self):
        #self.logger.debug("FrontLight state is %s, off_threshold = %s, state == DevState.ON %s" % ( str(self.dev_server_state), \
                            #str(self.off_threshold),  (self.dev_server_state == DevState.ON ) )
                         #)
        newstate = False
        if self.dev_server_state == DevState.ON:
            if self.off_threshold is not None:
                if self.current_level < 0.9 * self.off_threshold:
                    newstate = False
                else:
                    newstate = True
            else:
                newstate = True
        elif self.dev_server_state == DevState.OFF:
            newstate = False
        else:
            newstate = False

        if newstate != self.state:
            self.state = newstate
            self.emit('stateChanged', self.state)

    def get_limits(self):
        return self.limits

    def get_state(self):
        self.dev_server_state = str(self.chan_state.get_value()).lower()
        self.update_current_state()
        return self.state

    def get_user_name(self):
        return self.username

    def get_level(self):
        self.current_level = self.chan_level.get_value()
        return self.current_level

    def set_level(self, level):
        #self.logger.debug("Setting level in %s to %s" % (self.username, level))
        self.chan_level.set_value(float(level))

    def set_on(self):
        #self.logger.debug("Setting front light on with intensity %s" % str(self.limits[1] ) )
        self.chan_level.set_value( float( self.limits[1] ) )

    def set_off(self):
        #self.logger.debug("Setting front light off")
        self.chan_level.set_value( float( self.limits[0] ) )
        
    def re_emit_values(self):
        self.emit("stateChanged", self.state )
        self.emit("levelChanged", self.current_level )


def test_hwo(hwo):
    print("Light control for \"%s\"\n" % hwo.get_user_name())
    print("Level limits are:", hwo.get_limits())
    print("Current level is:", hwo.get_level())
    print("Current state is:", hwo.get_state())
