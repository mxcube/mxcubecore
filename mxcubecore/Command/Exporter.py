import logging
import weakref
import new
import qt
import types
import Queue
from embl import ExporterClient
import threading

from HardwareRepository.CommandContainer import CommandObject, ChannelObject, ConnectionError

# at the moment, there is only 1 exporter client for all 
exporter_client = None

def start_exporter(address, port, timeout=3, retries=1):
  global exporter_client
  if exporter_client is None:
     exporter_client = Exporter(address, port, timeout)
     exporter_client.start()

"""
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
"""

class ExporterCommand(CommandObject):
    def __init__(self, name, command, username = None, address = None, port = None, timeout=3,  **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)
        
        self.command = command
       
        start_exporter(address, port, timeout) 


    def __call__(self, *args, **kwargs):
        self.emit('commandBeginWaitReply', (str(self.name()), ))
        
        try:
            ret = exporter_client.execute(self.command, args, kwargs.get("timeout", -1))
        except:
            logging.getLogger('HWR').exception("%s: an error occured when calling Exporter command %s", str(self.name()), self.command)
        else:
            self.emit('commandReplyArrived', (ret, str(self.name())))
            return ret
        
        self.emit('commandFailed', (-1, self.name()))


    def abort(self):
        # TODO: implement async commands
        pass
        

    def get_state(self):
        return exporter_client.get_state()

    def isConnected(self):
        return exporter_client.isConnected()

    
class Exporter(ExporterClient.ExporterClient):
    STATE_EVENT                     = "State"
    STATUS_EVENT                    = "Status"
    VALUE_EVENT                     = "Value"
    POSITION_EVENT                  = "Position"
    MOTOR_STATES_EVENT              = "MotorStates"

    STATE_READY =               "Ready"
    STATE_INITIALIZING =        "Initializing"
    STATE_STARTING =            "Starting"
    STATE_RUNNING =             "Running"
    STATE_MOVING =              "Moving"
    STATE_CLOSING =             "Closing"
    STATE_REMOTE =              "Remote"
    STATE_STOPPED =             "Stopped"
    STATE_COMMUNICATION_ERROR = "Communication Error"
    STATE_INVALID =             "Invalid"
    STATE_OFFLINE =             "Offline"
    STATE_ALARM =               "Alarm"
    STATE_FAULT =               "Fault"
    STATE_UNKNOWN =             "Unknown"

    def __init__(self, address, port, timeout=3, retries=1):
      ExporterClient.ExporterClient.__init__(self, address, port, ExporterClient.PROTOCOL.STREAM, timeout, retries)

      self.started = False
      self.callbacks = {}
      self.timer = None #qt.QTimer()
      self.events_queue = Queue.Queue()

    def start(self):
        self.started=True
        self.reconnect()

    def stop(self):
        self.started=False
        self.disconnect()

    def execute(self, *args, **kwargs):
        ret = ExporterClient.ExporterClient.execute(self, *args, **kwargs)
        return self._to_python_value(ret)

    def get_state(self):
        return self.execute("getState") 

    def readProperty(self, *args, **kwargs):
        ret = ExporterClient.ExporterClient.readProperty(self, *args, **kwargs)
        return self._to_python_value(ret)

    def onConnected(self):
        pass

    def onDisconnected(self):
        if self.started:
            self.reconnect()

    def reconnect(self):
        if self.started:
            try:
                self.disconnect()
                self.connect()
            except:
                t = threading.Timer(1.0, self.onDisconnected)
                t.start()

    def register(self, name, cb):
       if callable(cb): 
         self.callbacks.setdefault(name, []).append(cb) 
       if not self.timer:
         self.timer = qt.QTimer()
         qt.QObject.connect(self.timer, qt.SIGNAL("timeout()"), self.processEventsFromQueue)
         self.timer.start(20)

   
    def _to_python_value(self, value):
        if '\x1f' in value:
          value = self.parseArray(value)
          try:
            value = map(int, value)
          except:
            try:
              value = map(float, value)
            except:
              pass
        else:
          try:
            value = int(value)
          except:
            try:
              value = float(value)
            except:
              pass
        return value


    def onEvent(self, name, value, timestamp):
        self.events_queue.put((name, value))


    def processEventsFromQueue(self):
        while True:
          try:
            name, value = self.events_queue.get_nowait()
          except:
            return
          #logging.info("RECEIVED EVENT %s = %s", name, value)

          for cb in self.callbacks.get(name, []):
            try:
              cb(self._to_python_value(value))
            except:
              logging.exception("Exception while executing callback %s for event %s", cb, name)
              continue
        

class ExporterChannel(ChannelObject):
    def __init__(self, name, attribute_name, username = None, address = None, port = None, timeout=3, **kwargs):
        ChannelObject.__init__(self, name, username, **kwargs)

        start_exporter(address, port, timeout)

        self.attributeName = attribute_name
        self.value = None

        exporter_client.register(attribute_name, self.update)        

        self.update()


    def update(self, value = None):
        if value is None:
            value = self.getValue()
        if type(value) == types.TupleType:
          value = list(value)

        self.value = value
        self.emit('update', value)
        

    def getValue(self):
        value = exporter_client.readProperty(self.attributeName) 
            
        return value

    
    def setValue(self, newValue):
        exporter_client.writeProperty(self.attributeName, newValue)
       
 
    def isConnected(self):
        return exporter_client.isConnected()

