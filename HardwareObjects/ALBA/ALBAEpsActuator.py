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

STATE_OUT, STATE_IN, STATE_MOVING, STATE_FAULT, STATE_ALARM, STATE_UNKNOWN = (
    0,
    1,
    9,
    11,
    13,
    23,
)


class ALBAEpsActuator(BaseHardwareObjects.Device):

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

        try:
            self.actuator_channel = self.get_channel_object("actuator")
            self.actuator_channel.connect_signal("update", self.stateChanged)
        except KeyError:
            logging.getLogger().warning(
                "%s: cannot report EPS Actuator State", self.name()
            )

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
        state = self.actuator_channel.get_value()
        self.actuator_state = self.convert_state(state)
        return self.actuator_state

    def convert_state(self, state):
        if state == 0:
            act_state = STATE_OUT
        elif state == 1:
            act_state = STATE_IN
        else:
            act_state = STATE_UNKNOWN
        return act_state

    def stateChanged(self, value):
        #
        # emit signal
        #
        self.actuator_state = self.convert_state(value)
        self.emit("stateChanged", ((self.actuator_state),))

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

    def open(self):
        self.cmdIn()

    def close(self):
        self.cmdOut()

    def cmdIn(self):
        self.actuator_channel.set_value(1)

    def cmdOut(self):
        self.actuator_channel.set_value(0)


def test_hwo(hwo):
    print("Name is: ", hwo.getUserName())
    print("Shutter state is: ", hwo.get_state())
    print("Shutter status is: ", hwo.getStatus())

    # print "Opening it"
    # print hwo.open()
    # print "Closing it"
    # print hwo.close()
