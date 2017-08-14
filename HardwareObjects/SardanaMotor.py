import logging
import time
from HardwareRepository.BaseHardwareObjects import Device
from AbstractMotor import AbstractMotor
from gevent import Timeout
from PyTango import DevState

"""
Interfaces Sardana Motor objects.
taurusname is the only obligatory property.
<device class="SardanaMotor">
    <username>Dummy</username>
    <motor_name>Dummy</motor_name>
    <taurusname>exp_dmy01</taurusname>
    <threshold>0.005</threshold>
    <interval>2000</interval>
</device>
"""

class SardanaMotor(AbstractMotor, Device):

    suffix_position = "Position"
    suffix_state = "State"
    suffix_stop = "Stop"

    state_map = {
        DevState.ON: AbstractMotor.READY,
        DevState.OFF: AbstractMotor.UNUSABLE,
        DevState.CLOSE: AbstractMotor.UNUSABLE,
        DevState.OPEN: AbstractMotor.UNUSABLE,
        DevState.INSERT: AbstractMotor.UNUSABLE,
        DevState.EXTRACT: AbstractMotor.UNUSABLE,
        DevState.MOVING: AbstractMotor.MOVING,
        DevState.STANDBY: AbstractMotor.UNUSABLE,
        DevState.FAULT: AbstractMotor.UNUSABLE,
        DevState.INIT: AbstractMotor.UNUSABLE,
        DevState.RUNNING: AbstractMotor.UNUSABLE,
        DevState.ALARM: AbstractMotor.UNUSABLE,
        DevState.DISABLE: AbstractMotor.UNUSABLE,
        DevState.UNKNOWN: AbstractMotor.UNUSABLE,
    }

    def __init__(self, name):
        AbstractMotor.__init__(self)
        Device.__init__(self, name)
        self.stop_command = None
        self.position_channel = None
        self.state_channel = None
        self.taurusname = ""
        self.motor_position = 0.0
        self.threshold = 0.0018
        self.polling = 2000
        self.limit_upper = None
        self.limit_lower = None

    def init(self):
        try:
            self.taurusname = self.getProperty("taurusname")
        except KeyError:
            logging.getLogger("HWR").warning(
                    "SardanaMotor: taurusname not defined")
            return
        try:
            self.motor_name = self.getProperty("motor_name")
        except KeyError:
            logging.getLogger("HWR").info(
                    "SardanaMotor: motor_name not defined")
            self.motor_name = self.name()
        try:
            self.threshold = self.getProperty("threshold")
        except KeyError:
            logging.getLogger("HWR").info(
                    "SardanaMotor: no threshold defined, setting to %f",
                self.threshold)
        try:
            self.polling = self.getProperty("interval")
        except KeyError:
            logging.getLogger("HWR").info(
                    "SardanaMotor: no polling interval defined, setting to %f",
                    self.polling)
        self.stop_command = self.addCommand({
                    "type": "sardana",
                    "name": self.motor_name + SardanaMotor.suffix_stop,
                    "taurusname": self.taurusname
                }, "Stop")
        self.position_channel = self.addChannel({
                    "type": "sardana",
                    "name": self.motor_name + SardanaMotor.suffix_position,
                    "taurusname": self.taurusname, "polling": self.polling,
                }, "Position")
        self.state_channel = self.addChannel({
                    "type": "sardana",
                    "name": self.motor_name + SardanaMotor.suffix_state,
                    "taurusname": self.taurusname, "polling": self.polling,
                }, "State")
        self.position_channel.connectSignal("update", self.motor_position_changed)
        self.state_channel.connectSignal("update", self.motor_state_changed)
        self.limits = (self.position_channel.getInfo().minval,
                self.position_channel.getInfo().maxval)

        try:
            self.limit_lower, self.limit_upper = map(float, self.limits)
        except:
            self.limit_lower, self.limit_upper = self.static_limits

    def updateState(self):
        """
        Descript. : forces position and state update
        """
        self.motor_position_changed()
        self.motor_state_changed()

    def motor_state_changed(self, state=None):
        """
        Descript. : called by the state channels update event
                    checks if the motor is at it's limit,
                    and sets the new device state
        """
        motor_state = self.motor_state
        if state is not None:
            motor_state = SardanaMotor.state_map[state]
        else:
            motor_state = SardanaMotor.state_map[self.state_channel.getValue()]
        if motor_state != AbstractMotor.UNUSABLE and \
                (self.motor_position >= self.limit_upper or \
                self.motor_position <= self.limit_lower):
            motor_state = AbstractMotor.ONLIMIT
        self.setIsReady(motor_state > AbstractMotor.UNUSABLE)
        if motor_state != self.motor_state:
            self.motor_state = motor_state
            self.emit('stateChanged', (motor_state, ))

    def motor_position_changed(self, position=None):
        """
        Descript. : called by the position channels update event
                    if the position change exceeds threshold,
                    positionChanged is fired
        """
        if position is None:
            position = self.position_channel.getValue()
        if abs(self.motor_position - position) >= self.threshold:
            self.motor_position = position
            self.emit('positionChanged', (position, ))
            self.motor_state_changed()

    def getState(self):
        """
        Descript. : returns the current motor state
        """
        self.motor_state_changed()
        return self.motor_state

    def getLimits(self):
        """
        Descript. : returns motor limits. If no limits channel defined then
                    static_limits is returned
        """
        try:
            #return (float(self.limit_lower), float(self.limit_upper))
            return (self.limit_lower, self.limit_upper)
        except:
            return (None,None)

    def getPosition(self):
        """
        Descript. : returns the current position
        """
        self.motor_position = self.position_channel.getValue()
        return self.motor_position

    def getDialPosition(self):
        """
        Descript. :
        """
        return self.getPosition()

    def move(self, absolute_position):
        """
        Descript. : move to the given position
        """
        self.position_channel.setValue(absolute_position)

    def moveRelative(self, relative_position):
        """
        Descript. : move for the given distance
        """
        self.move(self.getPosition() + relative_position)

    def syncMove(self, position, timeout=None):
        """
        Descript. : move to the given position and wait till it's reached
        """
        self.move(position)
        try:
            self.wait_end_of_move(timeout)
        except:
            raise Timeout

    def syncMoveRelative(self, relative_position, timeout=None):
        """
        Descript. : move for the given distance and wait till it's reached
        """
        self.syncMove(self.getPosition() + relative_position, timeout)

    def stop(self):
        """
        Descript. : stops the motor immediately
        """
        self.stop_command()

    def is_moving(self):
        """
        Descript. : True if the motor is currently moving
        """
        return self.isReady() and self.getState() == AbstractMotor.MOVING

    def wait_end_of_move(self, timeout=None):
        """
        Descript. : waits till the motor stops
        """
        with Timeout(timeout):
            time.sleep(0.1)
            while self.is_moving():
                time.sleep(0.1)

def test_hwo(hwo):
    print hwo.getLimits() 
