"""Machine Current Tango Hardware Object
Example XML:
<device class = "MachCurrent">
  <username>label for users</username>
  <tangoname>orion:10000/fe/id(or d)/xx</tangoname>
  <channel type="tango" name="OperatorMsg" polling="2000">SR_Operator_Mesg</channel>
  <channel type="tango" name="Current" polling="2000">SR_Current</channel>
  <channel type="tango" name="FillingMode" polling="2000">SR_Filling_Mode</channel>
  <channel type="tango" name="RefillCountdown" polling="2000">SR_Refill_Countdown</channel>
</device>
"""

from mxcubecore import BaseHardwareObjects
import logging


class MachCurrent(BaseHardwareObjects.Device):
    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

        self.opmsg = ""

    def init(self):
        try:
            chanCurrent = self.get_channel_object("Current")
            chanCurrent.connectSignal("update", self.valueChanged)
            self.set_is_ready(True)
        except Exception as e:
            logging.getLogger("HWR").exception(e)

    def valueChanged(self, value):
        mach = value or self.getCurrent()

        try:
            # TODO get correct channels
            # opmsg = self.get_channel_object("OperatorMsg").getValue()
            opmsg = "no message"
            # fillmode = self.get_channel_object("FillingMode").getValue()
            fillmode = "unknown"
            # fillmode = fillmode.strip()

            # refill = self.get_channel_object("RefillCountdown").getValue()
            refill = "unknown"
        except Exception as e:
            logging.getLogger("HWR").exception(e)
            opmsg, fillmode, value, refill = ("", "", -1, -1)

        if opmsg and opmsg != self.opmsg:
            self.opmsg = opmsg
            logging.getLogger("user_level_log").info(self.opmsg)
        self.emit("valueChanged", (mach, opmsg, fillmode, refill))

    def getCurrent(self):
        try:
            value = self.get_channel_object("Current").getValue()
        except Exception as e:
            logging.getLogger("HWR").exception(e)
            value = -1

        return value

    def getMessage(self):
        try:
            # TODO Manage operator message
            # msg = self.get_channel_object("OperatorMsg").getValue()
            msg = "no message"
        except Exception as e:
            logging.getLogger("HWR").exception(e)
            msg = ""

        return msg

    def getFillMode(self):
        try:
            # TODO Manage FillMode
            # fmode = self.get_channel_object("FillingMode").getValue()
            fmode = "unknown"
        except Exception as e:
            logging.getLogger("HWR").exception(e)
            fmode = ""

        return fmode
