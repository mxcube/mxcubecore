# -*- coding: utf-8 -*-
"""
File:  TangoShutter.py

Description:
---------------------------------------------------------------
Hardware Object to provide Shutter functionality through Tango
or other compatible system. In fact any combination of HardwareRepository
commands/states will work.

Two possible situations are supported by this hardware object:
    - One state attribute
    - Two action commands (in/out, open/close, insert/extract..)

 or
    - One read/write attribute with two states

Signals
---------------------------------------------------------------
This hardware object will emit signals:

    stateChanged(new_state)

The `new_state` will be one string out of:

    'closed',
    'opened',
    'standby',
    'alarm',
    'unknown',
    'fault',
    'disabled',
    'moving',
    'init',
    'automatic',
    'running',
    'insert',
    'extract',

The state strings will be converted from the state reported by the hardware by a conversion
table detailed below. This table is inspired in the Tango.DevState possible values, but also
in other cases like for example an attribute being True/False or other known real cases.

Methods
---------------------------------------------------------------
   openShutter()
   closeShutter()

Hardware to Shutter State conversion
---------------------------------------------------------------

The following table details the conversion to shutter states from
hardware state::

  --------- --------------- ---------------
  Hardware   Shutter         PyTango.DevState
  --------- --------------- -------------------
    False    'closed'
    True     'opened'
    0        'closed'
    1        'opened'
    4        'insert'
    5        'extract'
    6        'moving'
    7        'standby'
    8        'fault'
    9        'init'
   10        'running'
   11        'alarm'
   12        'disabled'
   13        'unknown'
   -1        'fault'
   None      'unknown'
  '_'        'automatic'
  'UNKNOWN'  'unknown'        UNKNOWN
  'CLOSE'    'closed'         CLOSE
  'OPEN'     'opened'         OPEN
  'INSERT'   'closed'         INSERT
  'EXTRACT'  'opened'         EXTRACT
  'MOVING'   'moving'         MOVING
  'RUNNING'  'moving'         MOVING
  'FAULT'    'fault'          FAULT
  'DISABLE'  'disabled'       DISABLE
  'ON'       'unknown'        ON
  'OFF'      'fault'          OFF
  'STANDBY'  'standby'        STANDBY
  'ALARM'    'alarm'          ALARM
  'INIT'     'init'           INIT
  --------- ---------------

XML Configuration Example:
---------------------------------------------------------------

* With state attribute and open/close commands

<device class = "TangoShutter">
  <username>FrontEnd</username>
  <tangoname>c-x1/sh-c1-4/1</tangoname>
  <command type="tango" name="Open">Open</command>
  <command type="tango" name="Close">Close</command>
  <channel type="tango" name="State" polling="1000">State</channel>
</device>

* With read/write attribute :

In the example the tango attribute is called "exper_shutter"

<device class = "TangoShutter">
  <username>Fast Shutter</username>
  <channel type="tango" name="State" tangoname="c-x2/sh-ex-12/fs" polling="events">exper_shutter</channel>
</device>

"""

from HardwareRepository import HardwareRepository as HWR
from HardwareRepository import BaseHardwareObjects

import logging


class TangoShutter(BaseHardwareObjects.Device):

    shutterState = {
        "FALSE": "closed",
        "TRUE": "opened",
        "0": "closed",
        "1": "opened",
        "4": "insert",
        "5": "extract",
        "6": "moving",
        "7": "standby",
        "8": "fault",
        "9": "init",
        "10": "running",
        "11": "alarm",
        "12": "disabled",
        "13": "unknown",
        "-1": "fault",
        "NONE": "unknown",
        "UNKNOWN": "unknown",
        "CLOSE": "closed",
        "OPEN": "opened",
        "INSERT": "closed",
        "EXTRACT": "opened",
        "MOVING": "moving",
        "RUNNING": "moving",
        "_": "automatic",
        "FAULT": "fault",
        "DISABLE": "disabled",
        "OFF": "fault",
        "STANDBY": "standby",
        "ON": "unknown",
        "ALARM": "alarm",
    }

    def init(self):
        self.state_value_str = "unknown"
        try:
            self.shutter_channel = self.get_channel_object("State")
            self.shutter_channel.connect_signal("update", self.shutterStateChanged)
        except KeyError:
            logging.getLogger().warning(
                "%s: cannot connect to shutter channel", self.name()
            )

        self.open_cmd = self.get_command_object("Open")
        self.close_cmd = self.get_command_object("Close")

    def shutterStateChanged(self, value):
        self.state_value_str = self._convert_state_to_str(value)
        self.emit("shutterStateChanged", (self.state_value_str,))

    def _convert_state_to_str(self, value):
        state = str(value).upper()
        state_str = self.shutterState.get(state, "unknown")
        return state_str

    def readShutterState(self):
        state = self.shutter_channel.get_value()
        return self._convert_state_to_str(state)

    def getShutterState(self):
        return self.state_value_str

    def openShutter(self):
        # Try getting open command configured in xml
        # If command is not defined then try writing the channel
        if self.open_cmd is not None:
            self.open_cmd()
        else:
            self.shutter_channel.setValue(True)

    def closeShutter(self):
        # Try getting close command configured in xml
        # If command is not defined try writing the channel
        if self.close_cmd is not None:
            self.close_cmd()
        else:
            self.shutter_channel.setValue(False)


def test():
    hwr = HWR.getHardwareRepository()
    hwr.connect()

    shut = hwr.get_hardware_object("/fastshutter")

    print(("Shutter State is: ", shut.readShutterState()))


if __name__ == "__main__":
    test()
