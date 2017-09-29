import time
import logging
import types
import Queue
import weakref
import gevent

from HardwareRepository import HardwareRepository
from HardwareRepository.CommandContainer import CommandObject, ChannelObject
import atexit


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
           logging.getLogger("HWR").error("%s" % strerror)
           self.emit('commandFailed', (strerror))

    def get(self):
        result = None
        try:
            result = tine.get(self.tineName, self.commandName, self.timeout)
        except IOError as strerror:
            logging.getLogger("HWR").error("%s" %strerror)
        except:
            pass
        return result

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
         
def do_tine_channel_update(sleep_time):
    while True:
        emitTineChannelUpdates()
        time.sleep(sleep_time)

class TineChannel(ChannelObject):    
    attach = {
        "timer"      : tine.attach,
        "event"      : tine.notify,
        "datachange" : tine.update
    }

    updates = Queue.Queue()
    #updates_emitter = QtCore.QTimer()
    #QtCore.QObject.connect(updates_emitter, QtCore.SIGNAL('timeout()'), emitTineChannelUpdates)
    #updates_emitter.start(20)
    updates_emitter = gevent.spawn(do_tine_channel_update, 0.2)

    def __init__(self, name, attribute_name, tinename = None, username = None, timeout=1000, **kwargs):
        ChannelObject.__init__(self, name, username, **kwargs)
 
        self.attributeName = attribute_name
        self.tineName = tinename
        self.timeout = int(timeout)
        self.value = None
        self.oldvalue = None
 
        self.callback_fail_counter = 0
       
        logging.getLogger("HWR").debug('Attaching TINE channel: %s %s'%(self.tineName, self.attributeName))
        if kwargs.get('size'):
            self.linkid = TineChannel.attach[kwargs.get("attach", "timer")](\
                 self.tineName, self.attributeName, self.tineEventCallback,
                 tine.UNASSIGNED_CALLBACKID, self.timeout, int(kwargs['size']))
        else:
            self.linkid = TineChannel.attach[kwargs.get("attach", "timer")](\
                 self.tineName, self.attributeName, self.tineEventCallback,
                 tine.UNASSIGNED_CALLBACKID, self.timeout)
        #except IOError as strerror:
        #   logging.getLogger("HWR").error("%s" %strerror)
        #except ValueError:
        #   logging.getLogger("HWR").error("TINE attach object is not callable")

        if self.linkid > 0 and kwargs.get("attach", "timer") == "datachange":
            tolerance = kwargs.get("tolerance", 0.0)
            try:
                tine.tolerance(self.linkid, 0.0, float (tolerance.rstrip("%")))
            except AttributeError:
                if tolerance != 0.0:
                    tine.tolerance(self.linkid, float (tolerance), 0.0)

        atexit.register(self.__del__)

    def __del__(self):
       try:
          tine.detach(self.linkid)
          logging.getLogger("HWR").debug('TINE channel %s %s detached'%(self.tineName,self.attributeName))
          self.linkid = -1
       except IOError as strerror:
           logging.getLogger("HWR").error("%s detaching %s %s"%(strerror,self.tineName,self.attributeName))
       except:
           logging.getLogger("HWR").error("Exception on detaching %s %s"%(self.tineName,self.attributeName))
       
    def tineEventCallback(self, id, cc, data_list):
        if cc == 0:
            self.callback_fail_counter = 0
            self.update(data_list)
        else:
            self.callback_fail_counter = self.callback_fail_counter + 1
            logging.getLogger("HWR").error("Tine event callback error %s, Channel: %s, Server: %s/%s" %(str(cc),self.name(),self.tineName,self.attributeName))
            if self.callback_fail_counter >= 3:
               logging.getLogger("HWR").error("Repeated tine event callback errors %s, Channel: %s, Server: %s/%s" %(str(cc),self.name(),self.tineName,self.attributeName))
          
    def update(self, value = None):
        if value is None:
            value = self.getValue()
        self.value = value
        if value != self.oldvalue:
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
        if self.linkid > 0:
            return True 
        else:
            return False

    def setOldValue(self, oldValue):
        self.oldvalue = oldValue

