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

"""
[Name]
XalocBackLight

[Description]
Hardware Object used to operate the diffractometer backlight.

[Emitted signals]
- levelChanged
- stateChanged
"""

#from __future__ import print_function

import time
import logging
import gevent

from mxcubecore.BaseHardwareObjects import Device

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"


class XalocBackLight(Device):

    def __init__(self, *args):
        Device.__init__(self, *args)
        self.logger = logging.getLogger("HWR.XalocBackLight")
        
        self.backlightin_channel = None
        self.level_channel = None

        self.limits = [None, None]
        self.state = None
        self.current_level = None
        self.actuator_status = None
        self.register_state = None

        self.memorized_level = None
        self.rest_level = None
        self.default_rest_level = 0.0
        self.minimum_level = None
        self.default_minimum_level = 30.0

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        self.backlightin_channel = self.get_channel_object("backlightin")
        self.level_channel = self.get_channel_object("light_level")

        self.set_name('backlight')
        
        limits = self.get_property("limits")

        if limits is not None:
            lims = limits.split(",")
            if len(lims) == 2:
                self.limits = map(float, lims)

        rest_level = self.get_property("rest_level")

        if rest_level is not None:
            self.rest_level = rest_level
        else:
            self.rest_level = self.default_rest_level

        minimum_level = self.get_property("minimum_level")
        if minimum_level is not None:
            self.minimum_level = float(minimum_level)
        else:
            self.minimum_level = self.default_minimum_level

        self.level_channel.connect_signal("update", self.level_changed)
        self.backlightin_channel.connect_signal("update", self.state_changed)

    def is_ready(self):
        return True
       
    isReady = is_ready

    def level_changed(self, value):
        self.current_level = value
        self.emit('levelChanged', self.current_level)

    def state_changed(self, value):
        #self.logger.debug("Backlight state is %s" % value)
        state = value
        if state != self.state:
            self.state = state
            self.emit('stateChanged', value)

    def _current_state(self):
        if self.actuator_status:
            return False
        else:
            return True

    def get_limits(self):
        return self.limits

    def get_state(self):
        _state = self.backlightin_channel.get_value()
        _level_on = self.level_channel.get_value() > 0
        if _state and _level_on:
            return True
        else:
            return False

    def get_user_name(self):
        return self.username

    def get_level(self):
        self.current_level = self.level_channel.get_value()
        return self.current_level

    def set_level(self, level):
        self.level_channel.set_value(float(level))

    def set_on(self):
        #self.logger.debug("backlight in %s", self.backlightin_channel.get_value() )
        self.on_task = gevent.spawn(self._setOn)
        self.on_task.link(self._task_finished)
        self.on_task.link_exception(self._task_failed)

    def _setOn(self):
        if self.backlightin_channel.get_value() is False:
            #self.logger.debug( "Set backlight in" )
            self.set_backlight_in()
            wait_ok = self.wait_backlight_in()
            if not wait_ok:
                self.logger.debug("Could not set backlight in")
                return

        level = None
        if self.memorized_level:
            level = self.memorized_level

        if not level or level < self.minimum_level:
            level = self.minimum_level

        #self.logger.debug("Setting light level to : %s" % level)
        self.set_level(level)

    def set_backlight_in(self):
        self.backlightin_channel.set_value(True)

    def wait_backlight_in(self, state=True, timeout=10):
        t0 = time.time()
        elapsed = 0
        while elapsed < timeout:
            isin = self.backlightin_channel.get_value()
            if isin == state:
                self.logger.debug(
                    "Waiting for backlight took %s. In is: %s" %
                    (elapsed, isin))
                return True
            gevent.sleep(0.1)
            elapsed = time.time() - t0

        self.logger.debug("Timeout waiting for backlight In")
        return False

    def _task_finished(self, g):
        self.logger.debug("Backlight task finished")
        self._task = None

    def _task_failed(self, g):
        self.logger.debug("Backlight task failed")
        self._task = None

    def set_off(self):
        if self.current_level:
            self.memorized_level = self.current_level
            self.set_level(self.rest_level)
        self.backlightin_channel.set_value(False)

    def re_emit_values(self):
        self.emit("stateChanged", self.state )
        self.emit("levelChanged", self.current_level )

def test_hwo(hwo):

    print("Light control for \"%s\"\n" % hwo.get_user_name())
    print("Level limits are:", hwo.get_limits())
    print("Current level is:", hwo.get_level())
    print("Current state is:", hwo.get_state())
