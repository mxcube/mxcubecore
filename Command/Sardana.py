
import logging
import os
import time
import types
import Queue
from .. import saferef
import PyTango
import gevent
from gevent.monkey import patch_time

from ..CommandContainer import CommandObject, ChannelObject, ConnectionError

try:
    from sardana.taurus.core.tango.sardana import registerExtensions
    from taurus import Device, Attribute
    import taurus
except:
    logging.getLogger('HWR').warning("Sardana is not available in this computer.")
patch_time()

def processSardanaEvents():

    while not SardanaObject._eventsQueue.empty():
        try:
            ev = SardanaObject._eventsQueue.get_nowait()
        except Queue.Empty:
            break
        else:
            try:
                receiverCbRef = SardanaObject._eventReceivers[id(ev)]
                receiverCb = receiverCbRef()
                if receiverCb is not None:
                    try:
                        gevent.spawn(receiverCb, ev)
                    except AttributeError:
                        pass
            except KeyError:
                pass

def waitEndOfCommand( cmdobj ):
     while cmdobj.macrostate ==  SardanaMacro.RUNNING or cmdobj.macrostate == SardanaMacro.STARTED:
        time.sleep(0.05)
     return cmdobj.door.result

class AttributeEvent:
    def __init__(self, event):
        self.event = event

class SardanaObject(object):
    _eventsQueue = Queue.Queue()
    _eventReceivers = {}
    _eventsProcessingTimer = gevent.get_hub().loop.async()

    # start Sardana events processing timer
    _eventsProcessingTimer.start(processSardanaEvents)

    def objectListener(self, *args):
        ev = AttributeEvent(args)
        SardanaObject._eventReceivers[id(ev)] = saferef.safe_ref(self.update)
        SardanaObject._eventsQueue.put(ev)
        SardanaObject._eventsProcessingTimer.send()

class SardanaMacro(CommandObject, SardanaObject):

    macroStatusAttr = None
    INIT, STARTED, RUNNING, DONE = range(4)

    def __init__(self, name, macro, doorname = None, username = None, **kwargs):
        super(SardanaMacro,self).__init__(name,username,**kwargs)

        self.macro_format = macro   
        self.doorname = doorname  
        self.door = None
        self.init_device()
        self.macrostate = SardanaMacro.INIT
        self.t0 = 0
      
    def init_device(self): 
        self.door = Device(self.doorname)

        # 
        # DIRTY FIX to make compatible taurus listeners and existence of Tango channels/commands
        # as defined in Command/Tango.py
        # 
        if self.door.__class__ == taurus.core.tango.tangodevice.TangoDevice:
            dp = self.door.getHWObj()
            try:
                dp.subscribe_event = dp._subscribe_event
            except AttributeError:
                pass

        if self.macroStatusAttr == None:
            logging.getLogger('HWR').debug("Door connection ready 1. ")
            self.macroStatusAttr = self.door.getAttribute("State")
            self.macroStatusAttr.addListener(self.objectListener)
        logging.getLogger('HWR').debug("Door connection ready 2. ")

    def __call__(self, *args, **kwargs):

        if self.door is None:
            self.init_device()

        logging.getLogger('HWR').debug("Executing sardana macro 3.")
        
        try:
            fullcmd = self.macro_format % args 
            logging.getLogger('HWR').info("  - It will try to run: %s in Door %s" % (fullcmd, self.doorname))
        except:
            logging.getLogger('HWR').info("  - Wrong format for macro arguments. Macro is %s / args are (%s)" % (self.macro_format, str(args)))
            return
   
        try:
            import time
            self.t0 = time.time()
            self.door.runMacro( (fullcmd).split()  )
        except TypeError:
            logging.getLogger('HWR').error("%s. Cannot properly format macro code. Format is: %s, args are %s", str(self.name()), self.macro_format, str(args)) 
        except PyTango.DevFailed, error_dict:
            logging.getLogger('HWR').error("%s: Cannot run macro. %s", str(self.name()), error_dict) 
        except AttributeError, error_dict:
            logging.getLogger('HWR').error("%s: MacroServer not running?, %s", str(self.name()), error_dict) 
        except:
            logging.getLogger('HWR').exception("%s: an error occured when calling Tango command %s", str(self.name()), self.macro_format)
        else:
            logging.getLogger('HWR').debug("Macro started in %s seconds." % str(time.time() - self.t0))
            self.macrostate = SardanaMacro.STARTED
            self.emit('commandBeginWaitReply', (str(self.name()), ))
            logging.getLogger('HWR').debug("Macro done waiting in %s seconds." % str(time.time() - self.t0))

        if self.macrostate == SardanaMacro.STARTED:
            if True: #wait:
                 logging.getLogger('HWR').debug("Macro waiting to finish")
                 ret = waitEndOfCommand(self)
                 logging.getLogger('HWR').debug("Macro execution done in %s seconds." % str(time.time() - self.t0))
                 return ret

    def update(self, event):
        data = event.event[2]
        
        try:
            doorstate = str(data.value)
            logging.getLogger('HWR').debug("Door state changed %s. Macro state is %d" % (doorstate, self.macrostate))

            if self.macrostate == SardanaMacro.STARTED and doorstate == "RUNNING":
                self.macrostate = SardanaMacro.RUNNING
            elif self.macrostate == SardanaMacro.RUNNING and doorstate == "ON":
                self.macrostate = SardanaMacro.DONE
                logging.getLogger('HWR').debug("Macro finished in %s seconds." % str(time.time() - self.t0))
                ret = self.door.result
                self.emit('commandReplyArrived', (ret, str(self.name())))
            else:
                self.emit('commandFailed', (-1, str(self.name())))
        except:
            pass
            logging.getLogger('HWR').debug("Uggh")

    def abort(self):
        if self.door is not None:
            self.door.abortMacro()
        
    def isConnected(self):
        return self.door is not None
    
class SardanaCommand(CommandObject):

    def __init__(self, name, command, taurusname = None, username = None, **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)
        
        self.command = command
        self.taurusname = taurusname
        self.device = None    

        logging.getLogger('HWR').debug("Creating command %s on device %s" % (self.command, self.taurusname))
     
    def init_device(self): 

        try:
            self.device = Device(self.taurusname)
        except PyTango.DevFailed, traceback:
            last_error = traceback[-1]
            logging.getLogger('HWR').error("%s: %s", str(self.name()), last_error['desc'])
            self.device = None
        else:
            try:
                self.device.ping()
            except PyTango.ConnectionFailed:
                self.device = None
                raise ConnectionError

    def __call__(self, *args, **kwargs):

        self.emit('commandBeginWaitReply', (str(self.name()), ))

        if self.device is None:
            self.init_device()

        try:
            cmdObject = getattr(self.device, self.command)
            ret = cmdObject(*args) 
        except PyTango.DevFailed, error_dict:
            logging.getLogger('HWR').error("%s: Tango, %s", str(self.name()), error_dict)
        except:
            logging.getLogger('HWR').exception("%s: an error occured when calling Tango command %s", str(self.name()), self.command)
        else:
            self.emit('commandReplyArrived', (ret, str(self.name())))
            return ret
        self.emit('commandFailed', (-1, self.name()))

    def abort(self):
        pass
        
    def isConnected(self):
        return self.device is not None
    
class SardanaChannel(ChannelObject, SardanaObject):

    def __init__(self, name, attribute_name, username=None, uribase = None, polling=None, **kwargs):

        logging.getLogger("HWR").debug("creating Sardana channel %s, uribase=%s", attribute_name, uribase )

        #ChannelObject.__init__(self, name, username, **kwargs)
        super(SardanaChannel, self).__init__(name,username,**kwargs)
 
        self.attributeName = attribute_name
        self.model = os.path.join( uribase, attribute_name )
        self.attribute = None

        self.value = None
        self.polling = polling

        logging.getLogger("HWR").debug("creating Sardana model %s, polling=%s", self.model, polling)

        self.init_device()

    def init_device(self):

        logging.getLogger("HWR").info("initializing sardana channel device")

        try:
            self.attribute = Attribute(self.model)
            # 
            # DIRTY FIX to make compatible taurus listeners and existence of Tango channels/commands
            # as defined in Command/Tango.py
            # 
            if self.attribute.__class__ == taurus.core.tango.tangoattribute.TangoAttribute:
                dev = self.attribute.getParentObj()
                dp = dev.getHWObj()
                try:
                    dp.subscribe_event = dp._subscribe_event
                except AttributeError:
                    pass
            logging.getLogger("HWR").info("initialized")
        except PyTango.DevFailed, traceback:
            self.imported = False
            return
        
        # prepare polling
        if self.polling:
             if type(self.polling) == types.IntType:
                  self.attribute.changePollingPeriod(self.polling)
             logging.getLogger("HWR").debug("listener added for attribute %s" % self.attributeName )
             self.attribute.addListener(self.objectListener)
                  
    def getValue(self):
        return self._readValue()

    def setValue(self, newValue):
        self._writeValue(newValue)
 
    def _writeValue(self, newValue):
        self.attribute.write(newValue)
            
    def _readValue(self):
        value = self.attribute.read().value
        return value
            
    def update(self, event):

        data = event.event[2]
        
        try:
            newvalue = data.value

            if newvalue == None:
                newvalue = self.getValue()
    
            if type(newvalue) == types.TupleType:
                newvalue = list(newvalue)
    
            self.value = newvalue
            self.emit('update', self.value)
        except AttributeError:
            # No value in data... this is probably a connection error
            pass

    def isConnected(self):
        return self.attribute is not None

    def channelListener(self,*args):
        ev = AttributeEvent(args)
        SardanaChannel._eventReceivers[id(ev)] = saferef.safe_ref(self.update)
        SardanaChannel._eventsQueue.put(ev)
        SardanaChannel._eventsProcessingTimer.send()
