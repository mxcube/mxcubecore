# -*- coding: utf-8 -*-
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
        #0:  'ON',
        #1:  'OFF',
        'False':    'CLOSED',
        'True':     'OPENED',
        '0':        'CLOSED',
        '1':        'OPENED',
        '4':        'INSERT',
        '5':        'EXTRACT',
        '6':        'MOVING',
        '7':        'STANDBY',
        '8':        'FAULT',
        '9':        'INIT',
        '10':       'RUNNING',
        '11':       'ALARM',
        '12':       'DISABLED',
        '13':       'UNKNOWN',
        '-1':       'FAULT',
        'None':     'UNKNOWN',
        'UNKNOWN':  'UNKNOWN',
        'CLOSE':    'CLOSED',
        'OPEN':     'OPENED',
        'INSERT':   'CLOSED',
        'EXTRACT':  'OPENED',
        'MOVING':   'MOVING',
        'RUNNING':  'MOVING',
        '_':        'AUTOMATIC',
        'FAULT':    'FAULT',
        'DISABLE':  'DISABLED',
        'OFF':      'FAULT',
        'STANDBY':  'STANDBY',
        'ON':       'UNKNOWN',
        'ALARM':    'ALARM' 
        }
    #shutterState = {
            #None: 'unknown',
            #'UNKNOWN': 'unknown',
            #'CLOSE': 'closed',
            #'OPEN': 'opened',
            #'INSERT': 'closed',
            #'EXTRACT': 'opened',
            #'MOVING': 'moving',
            #'RUNNING':'moving',
            #'_': 'automatic',
            #'FAULT': 'fault',
            #'DISABLE': 'disabled',
            #'OFF': 'fault',
            #'STANDBY': 'standby',
            #'ON': 'unknown'
            #}
    shutterStateString = {
        'ON':        'white',
        'OFF':       '#012345',
        'CLOSED':    '#FF00FF',
        'CLOSE':     '#FF00FF',
        'OPEN':      '#00FF00',
        'OPENED':    '#00FF00', 
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
        #debug MS 10.09.12
        print 'TangoShutter.py: __init__ print name',name
        print self
        
    def init(self):
        self.shutterStateValue = 'UNKNOWN'

        try:
            self.shutChannel = self.getChannelObject('State')
            self.shutChannel.connectSignal('update', self.shutterStateChanged)
        except KeyError:
            logging.getLogger().warning('%s: cannot report State', self.name())


    def shutterStateChanged(self, value):
        #
        # emit signal
        #
        self.shutterStateValue = str(value)
        retval =  self.getShutterState()
        self.emit('shutterStateChanged', (retval,))

        #self.emit('shutterStateChanged', (self.getShutterState(),))


    def getShutterState(self):
        logging.getLogger().debug( "getShutterState return : %s" % TangoShutter.shutterState[str(self.shutterStateValue)].lower() )
        #print "                      self.shutterStateValue=", self.shutterStateValue
        #print 'getShutterState TangoShutter.shutterState[self.shutterStateValue].lower()', TangoShutter.shutterState[str(self.shutterStateValue)].lower()
        return TangoShutter.shutterState[str(self.shutterStateValue)].lower()


    def isShutterOk(self):
        return not self.getShutterState() in ('OFF', 'UNKNOWN', 'MOVING', 'FAULT', 'INSERT', 'EXTRACT',
                                              'INIT', 'DISABLED', 'ERROR', 'ALARM', 'STANDBY')

    def openShutter(self):
        # Try getting open command configured in xml
        # If command is not defined or new MD2 (has no CloseFastShutter command. 
        # then try writing the channel
        try:
            opencmd = self.getCommandObject("Open")
            if opencmd is None:
                self.shutChannel.setValue(True)
            else:
                opencmd()
        except:
            self.shutChannel.setValue(True)

    def closeShutter(self):
        # Try getting close command configured in xml
        # If command is not defined or new MD2 (has no CloseFastShutter command. 
        # then try writing the channel
        try:
            closecmd = self.getCommandObject("Close")
            if closecmd is None:
                self.shutChannel.setValue(False)
            else:
                closecmd()
        except:
            self.shutChannel.setValue(False)

