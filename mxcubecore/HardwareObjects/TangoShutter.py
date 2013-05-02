'''Tango Shutter Hardware Object
Example XML:
<device class = "TangoShutter">
  <username>label for users</username>
  <command type="tango" tangoname="my device" name="Open">Open</command>
  <command type="tango" tangoname="my device" name="Close">Close</command>
  <channel type="tango" name="State" tangoname="my device" polling="1000">State</channel>
</device>

'''


from HardwareRepository import BaseHardwareObjects
import logging

class TangoShutter(BaseHardwareObjects.Device):
    shutterState = {
        0:  'ON',
        1:  'OFF',
        2:  'CLOSED',
        3:  'OPENED',
        4:  'INSERT',
        5:  'EXTRACT',
        6:  'MOVING',
        7:  'STANDBY',
        8:  'FAULT',
        9:  'INIT',
        10: 'RUNNING',
        11: 'ALARM',
        12: 'DISABLED',
        13: 'UNKNOWN',
        -1: 'FAULT'
        }

    shutterStateString = {
        'ON':        'white',
        'OFF':       '#012345',
        'CLOSED':    '#FF00FF',
        'OPEN':      '#00FF00',
        'INSERT':    '#412345',
        'EXTRACT':   '#512345',
        'MOVING':    '#663300',
        'STANDBY':   '#009900',
        'FAULT':     '#990000',
        'INIT':      '#990000',
        'RUNNING':   '#990000',
        'ALARM':     '#990000',
        'DISABLED':  '#EC3CDD',
        'UNKNOWN':   'GRAY',
        'FAULT':     '#FF0000',
        }

    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

    def init(self):
        self.shutterStateValue = 13

        try:
            chanStatus = self.getChannelObject('State')
            chanStatus.connectSignal('update', self.shutterStateChanged)
        except KeyError:
            logging.getLogger().warning('%s: cannot report State', self.name())


    def shutterStateChanged(self, value):
        #
        # emit signal
        #
        self.shutterStateValue = value
        # print "emit : ",TangoShutter.shutterState[self.shutterStateValue]
        self.emit('shutterStateChanged', (self.getShutterState(),))


    def getShutterState(self):
        #print "getShutterState return :", TangoShutter.shutterState[self.shutterStateValue]
        #print "                      self.shutterStateValue=", self.shutterStateValue
        return TangoShutter.shutterState.get(self.shutterStateValue, "UNKNOWN").lower()


    def isShutterOk(self):
        return not self.getShutterState() in ('OFF', 'UNKNOWN', 'MOVING', 'FAULT', 'INSERT', 'EXTRACT',
                                              'INIT', 'DISABLED', 'ERROR', 'ALARM', 'STANDBY')

    def openShutter(self):
        self.getCommandObject("Open")()

    def closeShutter(self):
        self.getCommandObject("Close")()

