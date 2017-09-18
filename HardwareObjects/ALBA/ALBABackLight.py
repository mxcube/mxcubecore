
from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Device
import logging
import gevent
import time

class ALBABackLight(Device):

    def __init__(self,*args):
        Device.__init__(self,*args)
        self.limits = [None,None]
        self.state = None
        self.current_level = None
        self.actuator_status = None
        self.register_state = None

        self.memorized_level = None
        self.default_rest_level = 0.0

    def init(self):

        self.ln2cover_channel = self.getChannelObject("ln2cover")
        self.level_channel = self.getChannelObject("light_level")
        self.actuator_channel = self.getChannelObject("actuator")
        self.state_channel = self.getChannelObject("state")

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

        self.level_channel.connectSignal("update", self.level_changed)
        self.actuator_channel.connectSignal("update", self.actuator_changed)
        self.state_channel.connectSignal("update", self.register_state_changed)

    def isReady(self):
        return True
 
    def level_changed(self,value):
        self.current_level = value
        self.emit('levelChanged', self.current_level)

    def register_state_changed(self,value):
        self.register_state = str(value).lower()
        state = self._current_state()
        if state != self.state:
            self.state = state
            self.emit('stateChanged', self.state)

    def actuator_changed(self, value):
        self.actuator_status = value
        state = self._current_state()  
        if state != self.state:
            self.state = state
            self.emit('stateChanged', self.state)

    def _current_state(self):

        state = None

        if self.actuator_status:
            state = "off" 
        else:
            state = "on" 

        return state
            
    def getLimits(self):
        return self.limits

    def getState(self):
        self.actuator_status = self.actuator_channel.getValue()
        self.register_state = str(self.state_channel.getValue()).lower()
        self.state = self._current_state()
        return self.state

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
        if self.ln2cover_channel.getValue() is False: 
            self.open_ln2cover()
            wait_ok = self.wait_ln2cover_open()
            if not wait_ok:
                print "could not open ln2cover"
                return

        self.actuator_channel.setValue(False)
        if self.memorized_level:
            logging.getLogger("HWR").debug("setting level to memorized value: %s" % self.memorized_level)
            self.setLevel(self.memorized_level)

    def open_ln2cover(self):
        self.ln2cover_channel.setValue(True)

    def wait_ln2cover_open(self, timeout=10):
        t0 = time.time()
        elapsed = 0 
        while elapsed < timeout:
             opened = self.ln2cover_channel.getValue() 
             if opened:
                 return True
             gevent.sleep(0.1)
             elapsed = time.time()-t0
             logging.getLogger("HWR").debug("waiting for ln2cover open. elapsed %s . is %s" % (elapsed,opened))

        logging.getLogger("HWR").debug("Timeout waiting for ln2cover open")
        return False
         
    def _task_finished(self,g):
        logging.getLogger("HWR").debug("Backlight task finished")
        self._task = None

    def _task_failed(self,g):
        logging.getLogger("HWR").debug("Backlight task failed")
        self._task = None

    def setOff(self):
        self.actuator_channel.setValue(True)
        if self.current_level:
            self.memorized_level = self.current_level
            self.setLevel(self.rest_level)

def test_hwo(hwo):
    print "\nLight control for \"%s\"\n" % hwo.getUserName()
    print "   Level limits are:",  hwo.getLimits()
    print "   Current level is:",  hwo.getLevel()
    print "   Current state is:",  hwo.getState()
    print "   Setting backlight on" 
    hwo.setOn()
    while gevent.wait(timeout=0.1):
        print "Waiting" 
        gevent.sleep(0.1)
    print "   Current state is:",  hwo.getState()
