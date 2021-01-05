"""
The ALBAFastShutter hardware object is a variation of the ALBAEpsActuator
where the command to open/close is done on a different channel than the
reading of the shutter state.

The interface is otherwise exactly the same as the ALBAEpsActuator

Example XML::

  <device class="ALBAFrontEnd">
    <username>Front Shutter</username>
    <taurusname>bl13/ct/eps-plc-01</taurusname>
    <channel type="sardana" polling="events" name="actuator">fe_open</channel>
    <channel type="sardana" name="open_command">OPEN_FE</channel>
    <channel type="sardana" name="close_command">CLOSE_FE</channel>
    <states>Open,Closed</states>
  </device>

"""

from mx3core import HardwareRepository as HWR
from mx3core import BaseHardwareObjects
import logging

from ALBAEpsActuator import ALBAEpsActuator


class ALBAFrontEnd(ALBAEpsActuator):
    def init(self):
        ALBAEpsActuator.init(self)

        self.open_channel = self.get_channel_object("open_command")
        self.close_channel = self.get_channel_object("close_command")

    def cmdIn(self):
        self.open_channel.set_value(True)
        # self.actuator_channel.set_value(1)

    def cmdOut(self):
        self.close_channel.set_value(True)
        # self.actuator_channel.set_value(0)


def test_hwo(hwo):
    print("Name is: ", hwo.getUserName())
    print("Shutter state is: ", hwo.get_state())
    print("Shutter status is: ", hwo.getStatus())

    # print "Opening it"
    # print hwo.open()
    # print "Closing it"
    # print hwo.close()
