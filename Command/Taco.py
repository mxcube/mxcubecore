import atexit
import logging
import weakref
import threading
import time
import os
import qt

"""
try:
    import pyipc
except ImportError:
    logging.getLogger("HWR").warning("Cannot use Taco Poller, the requested modules are not available.")
    polling_queue = None
else:
    taco_cmd_objects = weakref.WeakValueDictionary()
    command_queue = pyipc.MessageQueue(100)
    polling_queue = pyipc.MessageQueue(110)

    # launch Taco Poller companion application as a child process
    import HardwareRepository
    taco_poller_app = os.path.join(os.path.dirname(HardwareRepository.__file__), "TacoPoller.py")
    if os.path.isfile(taco_poller_app):
        try:
            child_pid = os.spawnvpe(os.P_NOWAIT, "python", ("python", taco_poller_app, ), os.environ)
        except:
            logging.getLogger("HWR").error("Could not start Taco Poller, disabling Taco Poller.")
            polling_queue = None
        else:
            def receive_polling_results():
                _polling_result = polling_queue.receive_p(os.getpid())

                if _polling_result is not None:
                    ignored, polling_result = _polling_result
                    
                    taco_obj_id = polling_result["id"]

                    try:
                        taco_cmd_obj = taco_cmd_objects[taco_obj_id]
                    except KeyError:
                        pass
                    else:
                        if polling_result["type"] == "timeout":
                            taco_cmd_obj.timeout(taco_cmd_obj.deviceName)
                        elif polling_result["type"] == "error":
                            logging.getLogger("HWR").error("%s: %s", taco_cmd_obj.name(), polling_result["message"])
                        else:
                            taco_cmd_obj.valueChanged(taco_cmd_obj.deviceName, polling_result["value"])

            polling_timer = qt.QTimer(None)
            qt.QObject.connect(polling_timer, qt.SIGNAL("timeout()"), receive_polling_results)
            polling_timer.start(50)
    else:
        logging.getLogger("HWR").error("Could not start Taco Poller (%s), disabling Taco Poller." % taco_poller_app)
        polling_queue = None
"""

from HardwareRepository.CommandContainer import CommandObject, ChannelObject
from HardwareRepository import TacoDevice_MTSafe as TacoDevice

#keep reference to TacoPoller objects
#key - Taco device name
#value - corresponding Taco Poller object
_pollerObjects = {}
_eventReceivers = weakref.WeakKeyDictionary()

# define two custom events ;
# the events are emitted by TacoPoller objects to Command objects
VALUE_CHANGED_EVENT = qt.QEvent.User
TIMEOUT_EVENT = qt.QEvent.User + 1


class TacoDeviceValueChangedEvent(qt.QCustomEvent):
    def __init__(self, devName, value):
        qt.QCustomEvent.__init__(self, VALUE_CHANGED_EVENT)

        self.deviceName = devName
        self.value = value
    

class TimeoutEvent(qt.QCustomEvent):
    def __init__(self, devName):
        qt.QCustomEvent.__init__(self, TIMEOUT_EVENT)

        self.deviceName = devName
    

class QEventReceiver(qt.QObject):
    def __init__(self, cmd_object):
        qt.QObject.__init__(self)
        
        self.objectRef = weakref.ref(cmd_object)


    def customEvent(self, event):
        cmd_object = self.objectRef()

        if cmd_object is not None:
            if event.type() == VALUE_CHANGED_EVENT:
                try:
                    cmd_object.valueChanged(event.deviceName, event.value)
                except:
                    logging.getLogger("HWR").exception("Error while calling valueChanged on device %s", event.deviceName)
            elif event.type() == TIMEOUT_EVENT:
                try:
                    cmd_object.timeout(event.deviceName)
                except:
                    logging.getLogger("HWR").exception("Error while calling timeout on device %s", event.deviceName)
                    

def eventReceiver(cmd_object):
    if cmd_object not in _eventReceivers:
        _eventReceivers[cmd_object] = QEventReceiver(cmd_object)
    return _eventReceivers[cmd_object]


class BoundMethodWeakref:
    """Helper class to get a weakref to a bound method"""
    def __init__(self, bound_method):
        self.func_ref = weakref.ref(bound_method.im_func)
        self.obj_ref = weakref.ref(bound_method.im_self)

    def __call__(self):
        obj = self.obj_ref()
        if obj is not None:
            func = self.func_ref()
            if func is not None:
                return func.__get__(obj)


    def __hash__(self):
        return id(self)

    
    def __cmp__(self, other):
        if other.__class__ == self.__class__:
            return cmp( (self.func_ref, self.obj_ref), (other.func_ref, other.obj_ref) )
        else:
            return cmp(self, other)
   

def getWeakRef(callback):
    """Return a weak reference to a given callback function"""
    if callback is None:
        return None
    
    if hasattr(callback, 'im_self') and callback.im_self is not None:
        # bound method weakref
        reference = BoundMethodWeakref(callback)
    else:
        # function weakref
        reference = weakref.ref(callback)

    return reference


class TacoPoller(qt.QThread): #(threading.Thread):
    def __init__(self, device):
        #threading.Thread.__init__(self)
        qt.QThread.__init__(self)
        
        #self.stopEvent = threading.Event()
        self.keepRunning = False
        self.mutex = qt.QMutex() #threading.Lock()

        self.pollingTime = 1E6
        self.device = device
        self.polledCommands = {}
    

    def stop(self):
        #if self.isAlive():
        if self.running():
            #print 'stopping poller for device %s' % self.device.devname
            
            #self.stopEvent.set()
            self.keepRunning = False
            
            #self.join()
            self.wait()


    def run(self):
        #while not self.stopEvent.isSet():
        self.keepRunning = True
        
        while self.keepRunning:
            if self.device.imported:
                try:
                    #print 'acquiring lock', self.device.devname
                    self.mutex.lock()
                    #self.mutex.acquire()
                    
                    for commandObjectRef, compiledCommandsList in self.polledCommands.iteritems():
                        for commandDict in compiledCommandsList:
                            command = commandDict['command']
                            oldValue = commandDict['value']
                            compare = commandDict['compare']

                            try:
                                exec(command)    
                            except TacoDevice.Dev_Exception:
                                continue
                            except:
                                logging.getLogger('HWR').exception('Error while polling device %s', self.device.devname)
                                continue
                            else:
                                if not self.keepRunning: #self.stopEvent.isSet():
                                    break

                                #print 'ok, command executed'
                                
                                if ((not compare) or oldValue != newValue):
                                    commandDict['value'] = newValue
                                    
                                    commandObject = commandObjectRef()
                                    if commandObject is not None:
                                        #
                                        # post value changed event
                                        #
                                        valueChangedEvent = TacoDeviceValueChangedEvent(self.device.devname, newValue)
                                        #print str(commandObject.name()), 'new value is', len(newValue) > 50 and newValue[0:10] or newValue
                                        #print 'posting event'

                                        self.postEvent(eventReceiver(commandObject), valueChangedEvent)

                                        del commandObject #just delete the reference we just created
                                else:
                                    #
                                    # post timeout event
                                    #
                                    commandObject = commandObjectRef()
                                    if commandObject is not None:
                                        timeoutEvent = TimeoutEvent(self.device.devname)
                                        self.postEvent(eventReceiver(commandObject), timeoutEvent)
                                        
                                        del commandObject #just delete the reference we just created
                        if not self.keepRunning: #self.stopEvent.isSet():
                            break
                    if not self.keepRunning: #self.stopEvent.isSet():
                        break
                finally:
                    self.mutex.unlock()
                    #self.mutex.release()
                    #print 'releasing lock', self.device.devname
            else:
                self.stop()
                return

            #time.sleep(self.pollingTime/1000.)
            qt.QThread.msleep(self.pollingTime)
            

    def addCommand(self, commandObject, pollingTime, argumentsList, compare):
        """Add a command object to be polled

        Polling time should be given in milliseconds"""
        self.pollingTime = min(self.pollingTime, pollingTime) # / 1000.0)

        #print 'adding command %s for device %s' % (str(commandObject.name()), commandObject.deviceName)

        def commandObjectDestroyed(ref):
            #print 'command object destroyed'

            try:
                #self.mutex.acquire()
                self.mutex.lock()
                # weakreferences to the same objects
                # have same hash value, so we have to
                # make sure we do not try to remove an
                # already-removed command
                if ref in self.polledCommands:
                    del self.polledCommands[ref]
            finally:
                self.mutex.unlock()
                #self.mutex.release()
                
            if len(self.polledCommands) == 0:
                self.stop()
                
                del _pollerObjects[self.device.devname]
                
        commandObjectRef = weakref.ref(commandObject, commandObjectDestroyed)

        try:
            compiledCommand = compile('newValue = self.device.%s(*%s)' % (str(commandObject.command), tuple(argumentsList)), '<string>', 'exec')
        except SyntaxError:
            logging.getLogger('HWR').error('%s: invalid polling command %s for device %s', str(commandObject.name()), commandObject.command, commandObject.deviceName)
        else:
            try:
                #print 'waiting'
                self.mutex.lock() #self.mutex.acquire()
                #print 'ok'
                
                try:
                    self.polledCommands[commandObjectRef].append( {'command': compiledCommand, 'value': None, 'compare': compare } )
                except KeyError:
                    self.polledCommands[commandObjectRef] = [ { 'command': compiledCommand, 'value': None, 'compare': compare } ]
            finally:
                self.mutex.unlock() #self.mutex.release()
                
            if not self.running(): #self.isAlive():
                #return 
		#print 'starting polling thread %s' % commandObject.deviceName
                self.start()


    def removeCommand(self, commandObject):
        commandObjectRef = weakref.ref(commandObject)

        try:
            self.mutex.lock()

            for cmdRef in self.polledCommands.keys():
                if cmdRef == commandObjectRef:
                    del self.polledCommands[cmdRef]
                    break

            if len(self.polledCommands) == 0:
                self.stop()
                
                del _pollerObjects[self.device.devname]
        finally:
            self.mutex.unlock()
                 
        

class TacoCommand(CommandObject):
    def __init__(self, name, command, taconame = None, username = None, args=None, dc=False, **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)
        
        self.command = command
        self.deviceName = taconame
        self.__valueChangedCallbackRef = None
        self.__timeoutCallbackRef = None

        if args is None:
            self.arglist = ()
        else:
            # not very nice...
            args = str(args)
            if not args.endswith(","):
              args+=","
            self.arglist = eval("("+args+")")

        try:
            self.device = TacoDevice.TacoDevice(self.deviceName, dc=dc)
        except:
            logging.getLogger('HWR').exception('Problem with Taco ; could not open Device %s', self.deviceName)
            self.device = None
            

    def __call__(self, *args, **kwargs):
        self.emit('commandBeginWaitReply', (str(self.name()), ))
       
        if len(args) > 0 and len(self.arglist) > 0:
            logging.getLogger("HWR").error("%s: cannot execute command with arguments when 'args' is defined from XML", str(self.name()))
            self.emit('commandFailed', (-1, str(self.name()), ))
            return
        elif len(args)==0 and len(self.arglist) > 0:
            args = self.arglist 

        if self.device is not None and self.device.imported:
            try:
                ret = eval('self.device.%s(*%s)' % (self.command, args))
            except:
                logging.getLogger('HWR').error("%s: an error occured when calling Taco command %s", str(self.name()), self.command)
            else:
                self.emit('commandReplyArrived', (ret, str(self.name())))
                return ret
        
        self.emit('commandFailed', (-1, str(self.name()), ))


    def valueChanged(self, deviceName, value):
        try:
            callback = self.__valueChangedCallbackRef()
        except:
            pass
        else:
            if callback is not None:
                callback(deviceName, value)
                    

    def timeout(self, deviceName):
        try:
            callback = self.__timeoutCallbackRef()
        except:
            pass
        else:
            if callback is not None:
                callback(deviceName)
                    

    def poll(self, pollingTime=500, argumentsList=(), valueChangedCallback=None, timeoutCallback=None, direct=True, compare=True):
        if not direct and polling_queue is None:
            # if there is no polling_queue support, use the good old 'direct' method
            direct = True
            
        if direct:
            if self.device is None:
                return
        
            try:
                poller = _pollerObjects[self.device.devname]
            except KeyError:
                poller = TacoPoller(self.device)
                
                _pollerObjects[self.device.devname] = poller
            
            self.__valueChangedCallbackRef = getWeakRef(valueChangedCallback)
            self.__timeoutCallbackRef = getWeakRef(timeoutCallback)

            poller.addCommand(self, pollingTime, argumentsList, compare=compare)
        else:
            logging.getLogger("HWR").debug("polling device %s using external Taco Poller application", self.deviceName)
            
            # use the TacoPoller companion application
            command_queue.send_p({'type':'add','pid': os.getpid(), 'id': id(self), 'device': self.deviceName , 'command': self.command, 'argumentsList': argumentsList, 'pollingFrequency': pollingTime})
            

    def stopPolling(self):
        try:
            poller = _pollerObjects[self.device.devname]
        except KeyError:
            return
        else:
            poller.removeCommand(self)
            

    def abort(self):
        pass
        

    def isConnected(self):
        return self.device is not None and self.device.imported


class TacoChannel(ChannelObject):
    """Emulation of a 'Taco channel' = a Taco command + polling"""
    def __init__(self, name, command, taconame = None, username = None, polling=None, args=None, **kwargs):
        ChannelObject.__init__(self, name, username, **kwargs)
 
        self.command = command
        self.deviceName = taconame
        
        if args is None:
            self.arglist = ()
        else:
            # not very nice...
            args = str(args)
            if not args.endswith(","):
              args+=","
            self.arglist = eval("("+args+")")

        try:
            self.device = TacoDevice.TacoDevice(self.deviceName)
        except:
            logging.getLogger('HWR').exception('Problem with Taco ; could not open Device %s', self.deviceName)
            self.device = None
            
        self.value = None
        try:
            self.polling = int(polling)
        except:
            self.polling = None
            
        if not None in (self.polling, self.device):
            try:
                poller = _pollerObjects[self.device.devname]
            except KeyError:
                poller = TacoPoller(self.device)
                
                _pollerObjects[self.device.devname] = poller
            
            poller.addCommand(self, self.polling, self.arglist, compare=True)
                

    def valueChanged(self, deviceName, value):
        self.emit("update", value)


    def timeout(self, deviceName):
        pass


    def getValue(self):
        if self.device is not None and self.device.imported:
            try:
                ret = eval('self.device.%s%s' % (self.command, self.arglist))
            except:
                logging.getLogger('HWR').error("%s: an error occured when calling Taco command %s", str(self.name()), self.command)
            else:
                return ret

 
    def isConnected(self):
        return self.device is not None and self.device.imported




