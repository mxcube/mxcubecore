'''Machine Current Tango Hardware Object
Example XML:
<device class = "MachCurrent">
  <username>label for users</username>
  <tangoname>orion:10000/fe/id(or d)/xx</tangoname>
  <channel type="tango" name="OperatorMsg" polling="2000">SR_Operator_Mesg</channel>
  <channel type="tango" name="Current" polling="2000">SR_Current</channel>
  <channel type="tango" name="FillingMode" polling="2000">SR_Filling_Mode</channel>
  <channel type="tango" name="RefillCountdown" polling="2000">SR_Refill_Countdown</channel>
</device>
'''

from HardwareRepository import BaseHardwareObjects
import logging

class MachCurrent(BaseHardwareObjects.Device):
    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)
        self.opmsg = ''

    def init(self):
        try:
            chanCurrent = self.getChannelObject('Current')
            chanCurrent.connectSignal('update', self.valueChanged)
            self.setIsReady(True)
        except KeyError:
            logging.getLogger().warning('%s: cannot read current', self.name())
    
    def valueChanged(self, value):
        mach = value
        opmsg = self.getChannelObject('OperatorMsg').getValue()
        fillmode = self.getChannelObject('FillingMode').getValue()
        fillmode = fillmode.strip()
        
        refill = self.getChannelObject('RefillCountdown').getValue()

        if opmsg and opmsg != self.opmsg:
            self.opmsg = opmsg
            logging.getLogger('HWR').info("<b>"+self.opmsg+"</b>")
            logging.getLogger('user_level_log').info("<b>"+self.opmsg+"</b>")

        self.emit('valueChanged', (mach, opmsg, fillmode, refill))

    def getCurrent(self):
        return self.getChannelObject('Current').getValue()

    def getMessage(self):
        return self.getChannelObject('OperatorMsg').getValue()

    def getFillMode(self):
        return self.getChannelObject('FillingMode').getValue()
