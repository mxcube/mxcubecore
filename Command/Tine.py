import logging
import types
import Queue
import weakref
import qt
from HardwareRepository import HardwareRepository
from HardwareRepository.CommandContainer import CommandObject, ChannelObject

try:
    import _tine as tine
except ImportError: 
    logging.getLogger('HWR').error("TINE support is not available.")
else:
    pass

                    

class TineCommand(CommandObject):
    def __init__(self, name, command_name, tinename = None, username = None, ListArgs=None, timeout=1000, **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)
        self.commandName = command_name
        self.tineName = tinename
        self.timeout = int(timeout)
	
    def __call__(self, *args, **kwargs):
        self.emit('commandBeginWaitReply', (str(self.name()), ))
        if ( len(args) == 0):
           commandArgument = []     
        else:
	   commandArgument = args[0]
	try :
	   ret = tine.set(self.tineName, self.commandName, commandArgument, self.timeout) 
	   self.emit('commandReplyArrived', (ret, str(self.name())))
	except IOError as strerror:
           logging.getLogger("HWR").error("%s" %strerror)
           self.emit('commandFailed', ("hallo", self.name()))
	   

    def abort(self):
        pass
        
    def isConnected(self):
        return True


def emitTineChannelUpdates():
  while not TineChannel.updates.empty():
    try:
       channel_obj_ref, value = TineChannel.updates.get()
    except Queue.Empty:
       break
    else:
       channel_object = channel_obj_ref()
       if channel_object is not None:
         try:
           channel_object.emit("update", (value, ))
         except:
           logging.getLogger("HWR").exception("Exception while emitting new value for channel %s", channel_object.name())
         

class TineChannel(ChannelObject):    
    updates = Queue.Queue()
    updates_emitter = qt.QTimer()

    qt.QObject.connect(updates_emitter, qt.SIGNAL('timeout()'), emitTineChannelUpdates)
    _updates_emitter.start(20)

    def __init__(self, name, attribute_name, tinename = None, username = None, timeout=1000, **kwargs):
        ChannelObject.__init__(self, name, username, **kwargs)
 
        self.attributeName = attribute_name
        self.tineName = tinename
        self.timeout = int(timeout)
        self.value = None
	self.oldvalue = None
        self.__value = None
       
        try:
           self.linkid = tine.attach(self.tineName, self.attributeName, self.tineEventCallback, 0, self.timeout)
        except IOError as strerror:
           logging.getLogger("HWR").error("%s" %strerror)
        except ValueError:
           logging.getLogger("HWR").error("TINE attach object is not callable") 

    def __del__(self):
       try:
          tine.detach(self.linkid)
          self.linkid = -1
       except IOError as strerror:
           logging.getLogger("HWR").error("%s" %strerror)
       
    def tineEventCallback(self, id, cc, data_list):
        if cc == 0:
            self.update(data_list)
        else:
            logging.getLogger("HWR").error("Tine event callback error %s, Channel: %s, Server: %s/%s" %(str(cc),self.name(),self.tineName,self.attributeName))
          
    def update(self, value = None):
        if value is None:
            value = self.getValue()
        self.value = value
	if (value != self.oldvalue):
            TineChannel.updates.put((weakref.ref(self), value))
            self.oldvalue = value

    def getValue(self):
        if self.value is None:
            try:
               self.value = tine.get(self.tineName, self.attributeName, self.timeout)
            except IOError as strerror:
               logging.getLogger("HWR").error("%s" %strerror)
        return self.value
    
    def setValue(self, newValue):
        listData = newValue
        try:
           ret = tine.set(self.tineName, self.attributeName, listData, self.timeout)
        except IOError as strerror:
           logging.getLogger("HWR").error("%s" %strerror)

    def isConnected(self):
        # TO DO : implement this properly
        return True
