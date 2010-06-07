import logging
import Queue
import weakref
import new
import qt
import types

from HardwareRepository.CommandContainer import CommandObject, ChannelObject, ConnectionError

try:
    import PyTango
except ImportError:
    logging.getLogger('HWR').warning("Tango support is not available.")
else:
    # install our device proxy cache for PyTango
    _DeviceProxy = PyTango.DeviceProxy
    _DeviceProxy._subscribe_event = PyTango.DeviceProxy.subscribe_event
    _devices_cache = weakref.WeakValueDictionary()

    def DeviceProxy(device_name, *args):
      # return a proxy to a Tango device - if a proxy to the same
      # device already exists, it is returned from the cache
      device_name = device_name.lower()
      try:
        return _devices_cache[device_name]
      except KeyError:
        dev = _DeviceProxy(device_name, *args)
        dev._device_callbacks = {}
        class SuperCallback:
          def __init__(self, callbacks_dict):
            self.callbacks_dict = callbacks_dict
            self.last_events = {}
          def push_event(self, event):
            if event.attr_value is None:
                # an error occured, ignore bad event
                return
            attr_name = event.attr_value.name.lower()
            self.last_events[attr_name] = event
            callbacks = self.callbacks_dict[attr_name]
            for cb_ref in callbacks:
              cb = cb_ref()
              if cb is not None:
                try:
                  cb.push_event(event)
                except:
                  continue

        dev._super_callback = SuperCallback(dev._device_callbacks)

        _devices_cache[device_name] = dev

        return dev

    def good_subscribe_event(self, attribute_name, event_type, callback, *args):
      attribute_name = attribute_name.lower()
      if not attribute_name in self._device_callbacks:
        # first time registration
        self._device_callbacks[attribute_name] = [weakref.ref(callback)]
        self._subscribe_event(attribute_name, event_type, self._super_callback, *args)
        return
      self._device_callbacks[attribute_name].append(weakref.ref(callback))
      ev = self._super_callback.last_events.get(attribute_name)
      if ev is not None:
        callback.push_event(ev)

    _DeviceProxy.subscribe_event = new.instancemethod(good_subscribe_event, None, _DeviceProxy)
    PyTango.DeviceProxy = DeviceProxy
                    
class BoundMethodWeakref:
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


class TangoCommand(CommandObject):
    def __init__(self, name, command, tangoname = None, username = None, **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)
        
        self.command = command
        self.deviceName = tangoname
        
        try:
            self.device = PyTango.DeviceProxy(self.deviceName)
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
        
        if self.device is not None:
            try:
                tangoCmdObject = getattr(self.device, self.command)
                ret = tangoCmdObject(*args) #eval('self.device.%s(*%s)' % (self.command, args))
            except PyTango.DevFailed, error_dict:
                logging.getLogger('HWR').error("%s: Tango, %s", str(self.name()), error_dict) 
            except:
                logging.getLogger('HWR').error("%s: an error occured when calling Tango command %s", str(self.name()), self.command)
            else:
                self.emit('commandReplyArrived', (ret, str(self.name())))
                return ret
        
        self.emit('commandFailed', (-1, self.name()))


    def abort(self):
        pass
        

    def isConnected(self):
        return self.device is not None

    
def processTangoEvents():
        while not TangoChannel._tangoEventsQueue.empty():
          try:
            ev = TangoChannel._tangoEventsQueue.get_nowait()
          except Queue.Empty:
            break
          else:
            try:
                receiverCbRef = TangoChannel._eventReceivers[id(ev)]
                receiverCb = receiverCbRef()
                if receiverCb is not None:
                    try:
                        receiverCb(ev.event.attr_value.value)
                    except AttributeError:
                        pass
            except KeyError:
                pass


class E:
          def __init__(self, event):
            self.event = event


class TangoChannel(ChannelObject):
    _tangoEventsQueue = Queue.Queue()
    _eventReceivers = {}
    _tangoEventsProcessingTimer = qt.QTimer()

    # start Tango events processing timer
    qt.QObject.connect(_tangoEventsProcessingTimer, qt.SIGNAL('timeout()'), processTangoEvents)
    _tangoEventsProcessingTimer.start(20)
    
    def __init__(self, name, attribute_name, tangoname = None, username = None, polling=None, timeout=10000, **kwargs):
        ChannelObject.__init__(self, name, username, **kwargs)
 
        self.attributeName = attribute_name
        self.deviceName = tangoname
        self.device = None
        self.value = None
        self.polling = polling
        self.__connections = 0
        self.__value = None
        self.pollingTimer = None
        self.pollingEvents=False
        self.timeout = int(timeout)
        self.read_as_str = kwargs.get("read_as_str", False)
         
        #logging.getLogger("HWR").debug("creating Tango attribute %s/%s, polling=%s, timeout=%d", self.deviceName, self.attributeName, polling, self.timeout)
 
        try:
            self.device = PyTango.DeviceProxy(self.deviceName)
        except PyTango.DevFailed, traceback:
            self.imported = False
            last_error = traceback[-1]
            logging.getLogger('HWR').error("%s: %s", str(self.name()), last_error['desc'])
        else:
            self.imported = True
            try:
                self.device.ping()
            except PyTango.ConnectionFailed:
                self.device = None
                raise ConnectionError
            else:
                self.device.set_timeout_millis(self.timeout)

                # check that the attribute exists (to avoid Abort in PyTango grrr)
                if not self.attributeName.lower() in [attr.name.lower() for attr in self.device.attribute_list_query()]:
                    logging.getLogger("HWR").error("no attribute %s in Tango device %s", self.attributeName, self.deviceName)
                    self.device=None
                    return
    
                if type(polling) == types.IntType:
                   self.pollingTimer = qt.QTimer()
                   self.pollingTimer.connect(self.pollingTimer, qt.SIGNAL("timeout()"), self.poll)          
                   self.pollingTimer.start(polling)
                else:
                   if polling=="events":
                      # try to register event
                      try:
                         self.pollingEvents=True
                         #logging.getLogger("HWR").debug("subscribing to CHANGE event for %s", self.attributeName)
                         self.device.subscribe_event(self.attributeName, PyTango.EventType.CHANGE_EVENT, self, [], True)
                      #except PyTango.EventSystemFailed:            
                      #   pass
                      except:
                         logging.getLogger("HWR").exception("could not subscribe event")
                   
    def push_event(self, event):
        #logging.getLogger("HWR").debug("%s | attr_value=%s, event.errors=%s, quality=%s", self.name(), event.attr_value, event.errors,event.attr_value is None and "N/A" or event.attr_value.quality)
        if event.attr_value is None or event.err or event.attr_value.quality != PyTango.AttrQuality.ATTR_VALID:
          #logging.getLogger("HWR").debug("%s, receving BAD event... attr_value=%s, event.errors=%s, quality=%s", self.name(), event.attr_value, event.errors, event.attr_value is None and "N/A" or event.attr_value.quality)
          return
        else:
          pass
          #logging.getLogger("HWR").debug("%s, receiving good event", self.name())
        ev = E(event)
        TangoChannel._eventReceivers[id(ev)] = BoundMethodWeakref(self.update)
	TangoChannel._tangoEventsQueue.put(ev)
       
 
    def poll(self):
        try:
           if self.read_as_str:
               value = self.device.read_attribute(self.attributeName, PyTango.DeviceAttribute.ExtractAs.String).value
               #value = self.device.read_attribute_as_str(self.attributeName).value
           else:
	       value = self.device.read_attribute(self.attributeName).value
        except:
           logging.getLogger("HWR").exception("%s: could not poll attribute %s", str(self.name()), self.attributeName)

           self.pollingTimer.stop()
           if not hasattr(self, "_statePollingTimer"):
             self._statePollingTimer = qt.QTimer()
             self._statePollingTimer.connect(self._statePollingTimer, qt.SIGNAL("timeout()"), self.statePolling)
           self.device.set_timeout_millis(50)
           self._statePollingTimer.start(5000)
           value = None
           self.emit("update", (None, ))
        else:
           if value != self.value:
              self.update(value)
  
    def getInfo(self):
        return self.device.get_attribute_config(self.attributeName)

    def statePolling(self):
      """Called when polling has failed"""
      try:
        s = self.device.State()
      except:
        pass
        #logging.getLogger("HWR").exception("Could not read State attribute")
      else:
        if s == PyTango.DevState.OFF:
          return

        self._statePollingTimer.stop()
        self.device.set_timeout_millis(self.timeout)
        logging.getLogger("HWR").info("%s: restarting polling on attribute %s", self.name(), self.attributeName)
        self.pollingTimer.start(self.polling)


    def update(self, value = None):
        if value is None:
            value = self.getValue()
        if type(value) == types.TupleType:
          value = list(value)

        self.value = value
        self.emit('update', value)
        

    def getValue(self):
        if self.read_as_str:
           self.value = self.device.read_attribute(self.attributeName, PyTango.DeviceAttribute.ExtractAs.String).value
           #self.value = self.device.read_attribute_as_str(self.attributeName).value 
        else:
           self.value = self.device.read_attribute(self.attributeName).value
            
        return self.value

    
    def setValue(self, newValue):
        self.device.write_attribute(self.attributeName, newValue)
        #attr = PyTango.AttributeProxy(self.deviceName + "/" + self.attributeName)
        #a = attr.read()
        #a.value = newValue
        #attr.write(a)
       
 
    def isConnected(self):
        return self.device is not None

