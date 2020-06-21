"""Tango Shutter Hardware Object
Example XML::

  <device class="ALBAEpsActuator">
    <username>Photon Shutter</username>
    <taurusname>bl13/ct/eps-plc-01</taurusname>
    <channel type="sardana" polling="events" name="actuator">pshu</channel>
    <states>Open,Closed</states>
  </device>


Public Interface:
   Commands:
       int get_state()
           Description:
               returns current state
           Output:
               integer value describing the state
               current states correspond to:
                      0: out
                      1: in
                      9: moving
                     11: alarm
                     13: unknown
                     23: fault

       string getStatus()
           Description:
               returns current state as a string that can contain a more
               descriptive information about current state

           Output:
               status string

       cmdIn()
           Executes the command associated to the "In" action
       cmdOut()
           Executes the command associated to the "Out" action

   Signals:
       stateChanged

"""

from HardwareRepository import HardwareRepository as HWR
from HardwareRepository import BaseHardwareObjects
import logging
import time

STATE_OUT, STATE_IN, STATE_MOVING, STATE_FAULT, STATE_ALARM, STATE_UNKNOWN = (
    0,
    1,
    9,
    11,
    13,
    23,
)


class ALBAFastShutter(BaseHardwareObjects.Device):

    states = {
        STATE_OUT: "out",
        STATE_IN: "in",
        STATE_MOVING: "moving",
        STATE_FAULT: "fault",
        STATE_ALARM: "alarm",
        STATE_UNKNOWN: "unknown",
    }

    default_state_strings = ["Out", "In"]

    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

    def init(self):

        self.actuator_state = STATE_UNKNOWN
        self.actuator_value = None
        self.motor_position = None
        self.motor_state = None

        try:
            self.nistart_cmd = self.get_command_object("nistart")
            self.nistop_cmd = self.get_command_object("nistop")

            self.actuator_channel = self.get_channel_object("actuator")
            self.motorpos_channel = self.get_channel_object("motorposition")
            self.motorstate_channel = self.get_channel_object("motorstate")

            self.actuator_channel.connect_signal("update", self.stateChanged)
            self.motorpos_channel.connect_signal("update", self.motorPositionChanged)
            self.motorstate_channel.connect_signal("update", self.motorStateChanged)
        except KeyError:
            logging.getLogger().warning("%s: cannot report FrontEnd State", self.name())

        try:
            state_string = self.get_property("states")
            if state_string is None:
                self.state_strings = self.default_state_strings
            else:
                states = state_string.split(",")
                self.state_strings = states[1].strip(), states[0].strip()
        except BaseException:
            import traceback

            logging.getLogger("HWR").warning(traceback.format_exc())
            self.state_strings = self.default_state_strings

    def get_state(self):
        if self.actuator_state == STATE_UNKNOWN:
            self.actuator_value = self.actuator_channel.get_value()
            self.motor_position = self.motorpos_channel.get_value()
            self.motor_state = self.motorstate_channel.get_value()
            self.update_state()
        return self.actuator_state

    def update_state(self):

        if None in [self.actuator_value, self.motor_position, self.motor_state]:
            act_state = STATE_UNKNOWN
        elif str(self.motor_state) == "MOVING":
            act_state = STATE_MOVING
        elif str(self.motor_state) != "ON" or abs(self.motor_position) > 0.01:
            act_state = STATE_ALARM
        else:
            state = self.actuator_value.lower()

            if state == "high":
                act_state = STATE_OUT
            else:
                act_state = STATE_IN

        if act_state != self.actuator_state:
            self.actuator_state = act_state
            self.emitStateChanged()

    def stateChanged(self, value):
        self.actuator_value = value
        self.update_state()

    def motorPositionChanged(self, value):
        self.motor_position = value
        self.update_state()

    def motorStateChanged(self, value):
        self.motor_state = value
        self.update_state()

    def emitStateChanged(self):
        #
        # emit signal
        #
        self.emit("fastStateChanged", ((self.actuator_state),))

    def getMotorPosition(self):
        if self.motor_position is None:
            self.motor_position = self.motorpos_channel.get_value()
        return self.motor_position

    def getMotorState(self):
        if self.motor_state is None:
            self.motor_state = self.motorstate_channel.get_value()
        return self.motor_state

    def getUserName(self):
        return self.username

    def getStatus(self):
        """
        """
        state = self.get_state()

        if state in [STATE_OUT, STATE_IN]:
            return self.state_strings[state]
        elif state in self.states:
            return self.states[state]
        else:
            return "Unknown"

    def cmdIn(self):
        self.open()

    def cmdOut(self):
        self.close()

    def close(self):
        self.motorpos_channel.setValue(0)
        self.set_ttl("High")

    def open(self):
        self.motorpos_channel.setValue(0)
        self.set_ttl("Low")

    def set_ttl(self, value):
        self.nistop_cmd()
        self.actuator_channel.setValue(value)
        self.nistart_cmd()

    def is_open(self):
        if self.actuator_state == STATE_IN:
            return True
        else:
            return False

    def is_close(self):
        if self.actuator_state == STATE_OUT:
            return True
        else:
            return False


def test_hwo(hwo):
    print("Name is: ", hwo.getUserName())

    print("Shutter state is: ", hwo.get_state())
    print("Shutter status is: ", hwo.getStatus())
    print("Motor position is: ", hwo.getMotorPosition())
    print("Motor state is: ", hwo.getMotorState())
    # hwo.open()
    # time.sleep(2)
    # print "is_open?" , hwo.is_open()
    # print "is_close?" , hwo.is_close()


if __name__ == "__main__":
    test()
