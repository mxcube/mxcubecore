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
import logging
import gevent

from HardwareRepository.BaseHardwareObjects import Device

__credits__ = ["ALBA Synchrotron"]
__version__ = "2.3"
__category__ = "General"


class ALBABackLight(Device):

    def __init__(self, *args):
        Device.__init__(self, *args)

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
        self.default_minimum_level = 7.0

    def init(self):

        self.backlightin_channel = self.getChannelObject("backlightin")
        self.level_channel = self.getChannelObject("light_level")

        limits = self.getProperty("limits")

        if limits is not None:
            lims = limits.split(",")
            if len(lims) == 2:
                self.limits = map(float, lims)

        rest_level = self.getProperty("rest_level")

        if rest_level is not None:
            self.rest_level = rest_level
        else:
            self.rest_level = self.default_rest_level

        minimum_level = self.getProperty("minimum_level")
        if minimum_level is not None:
            self.minimum_level = float(minimum_level)
        else:
            self.minimum_level = self.default_minimum_level

        self.level_channel.connectSignal("update", self.level_changed)
        self.backlightin_channel.connectSignal("update", self.state_changed)

    def isReady(self):
        return True

    def level_changed(self, value):
        self.current_level = value
        self.emit('levelChanged', self.current_level)

    def state_changed(self, value):
        state = value
        if state != self.state:
            self.state = state
            if state:
                self.emit('stateChanged', "on")
            else:
                self.emit('stateChanged', "off")

    def _current_state(self):

        if self.actuator_status:
            return "off"
        else:
            return "on"

    def getLimits(self):
        return self.limits

    def getState(self):
        _state = self.backlightin_channel.getValue()
        if _state:
            return "on"
        else:
            return "off"

    def getUserName(self):
        return self.username

    def getLevel(self):
        self.current_level = self.level_channel.getValue()
        return self.current_level

    def setLevel(self, level):
        self.level_channel.setValue(float(level))

    def setOn(self):
        self.on_task = gevent.spawn(self._setOn)
        self.on_task.link(self._task_finished)
        self.on_task.link_exception(self._task_failed)

    def _setOn(self):
        if self.backlightin_channel.getValue() is False:
            self.set_backlight_in()
            wait_ok = self.wait_backlight_in()
            if not wait_ok:
                logging.getLogger("HWR").debug("could not set backlight in")
                return

        level = None
        if self.memorized_level:
            level = self.memorized_level

        if not level or level < self.minimum_level:
            level = self.minimum_level

        logging.getLogger("HWR").debug("setting light level to : %s" % level)
        self.setLevel(level)

    def set_backlight_in(self):
        self.backlightin_channel.setValue(True)

    def wait_backlight_in(self, state=True, timeout=10):
        t0 = time.time()
        elapsed = 0
        while elapsed < timeout:
            isin = self.backlightin_channel.getValue()
            if isin == state:
                logging.getLogger("HWR").debug(
                    "waiting for backlight took %s. In is: %s" %
                    (elapsed, isin))
                return True
            gevent.sleep(0.1)
            elapsed = time.time() - t0

        logging.getLogger("HWR").debug("Timeout waiting for backlight In")
        return False

    def _task_finished(self, g):
        logging.getLogger("HWR").debug("Backlight task finished")
        self._task = None

    def _task_failed(self, g):
        logging.getLogger("HWR").debug("Backlight task failed")
        self._task = None

    def setOff(self):
        if self.current_level:
            self.memorized_level = self.current_level
            self.setLevel(self.rest_level)
        self.backlightin_channel.setValue(False)


def test_hwo(hwo):

    print "\nLight control for \"%s\"\n" % hwo.getUserName()
    print "   Level limits are:", hwo.getLimits()
    print "   Current level is:", hwo.getLevel()
    print "   Current state is:", hwo.getState()
    print "   Setting backlight in"
