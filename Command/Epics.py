""" 
Epics channel/command support module

Classes:
- EpicsCommand
- EpicsChannel

Implementation based on the PV module of PyEpics 3.2.x
http://cars.uchicago.edu/software/python/pyepics3/

TO-DO:
------
Implementation based on Taco/Tango command and channel implementation,
unused attributes and methods to be cleaned up ...
"""

__author__ = 'Michael Hellmig'
__organization__ = 'Joint Berlin MX Lab, BESSY II, Helmholtz-Zentrum Berlin'

import logging
import Queue
import weakref
import new
import time
import types
import gevent
import gevent.event

from ..CommandContainer import CommandObject, ChannelObject, ConnectionError
from .. import Poller
from .. import saferef

try:
    import epics
except ImportError:
    logging.getLogger('HWR').warning("EPICS support is not available")


class EpicsCommand(CommandObject):
    """
    EpicsCommand
    --
    Implementation of a BlissFramework-compatbile Commands using the EPICS communication protocol
    """
    def __init__(self, name, pv_name, username = None, args = None, **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)

        self.pvName = pv_name
        self.deviceName = None
        self.device = None    

        if args is None:
            self.arglist = ()
        else:
            # not very nice...
            args = str(args)
            if not args.endswith(","):
              args+=","
            self.arglist = eval("("+args+")")

        self.imported = True
        self.pv_connected = None
        self.pv = epics.PV(pv_name)
        # self.pv.add_callback(callback=self.valueChanged_callback)
        self.pv.connection_callbacks.append(self.connectionStatusChanged_callback)
        logging.getLogger('HWR').debug("creating EPICS command PV %s", self.pvName)

    def init_device(self): 
        """
        Not implemented
        """
        pass

    def __call__(self, *args, **kwargs):
        """
        Process the PVs command.

        One scalar argument >args[0] can be used for the command.
        """
        # TO-DO: add error-handling including commandFailed signal, ref. TangoCommand
        self.emit('commandBeginWaitReply', (str(self.name()), ))

        if len(args) > 0 and len(self.arglist) > 0:
            logging.getLogger("HWR").error("%s: cannot execute command with arguments when 'args' is defined from XML", str(self.name()))
            self.emit('commandFailed', (-1, str(self.name()), ))
            return
        elif len(args)==0 and len(self.arglist) > 0:
            args = self.arglist 
        try:
            # use only one scalar attribute
            # self.pv.put(args[0], wait=False, callback=self.putComplete_callback)
            self.pv.put(args[0], callback=self.putComplete_callback)
        except:
            logging.getLogger('HWR').error("%s: an error occured when calling Epics command %s", str(self.name()), self.command)
        else:
            self.emit('commandReplyArrived', (0, str(self.name())))
            return 0
        self.emit('commandFailed', (-1, self.name()))

    def abort(self):
        """
        Not implemented
        """
        pass

    def isConnected(self):
        """
        Check the PVs connection status
   
        Parameters:
        n/a
        Result:
        True  <=> PV is connected
        False <=> otherwise
        """
        return self.pv_connected

    def connected(self):
        """
        Emit signal >connected< to inform the associated brick.
        """
        self.emit('connected', ())

    def disconnected(self):
        """
        Emit signal >disconnected< to inform the associated brick.
        """
        self.emit('disconnected', ())
	self.statusChanged(ready=False)

    def statusChanged(self, ready):
        """
        Emit the signals >commandReady</>commandNotReady< based on the status of the parameter >ready<.
        """
        if ready:
            self.emit('commandReady', ())
        else:
            self.emit('commandNotReady', ())

    def connectionStatusChanged_callback(self, pvname = None, conn = None, **kws):
        """
        Callback to be informed about connection status.
        """
        # TO-DO: add action if the connection to the PV is lost
        #        check transferred connection state in that situation
        # logging.exception("%s: PyEpics connection status changed: %s", pvname, repr(conn))
        self.pv_connected = conn
        if self.pv_connected:
            self.connected()
        else:
            self.disconnected()

    def putComplete_callback(self, pvname = None, **kws):
        """
        Emit signal >commandReplyArrived< to inform the brick after the command finished processing.
        """
        # is it possible to detect a failed command execution???
        self.emit('commandReplyArrived', ())
        self.statusChanged(True)
    

class EpicsChannel(ChannelObject):
    """
    EpicsChannel
    --
    Implementation of a BlissFramework-compatbile Channel using the EPICS communication protocol

    Both an event-based approach as well as polling is implemented.

    ATTENTION: polling is not working for all PVs, situations, to be debugged
    """
    def __init__(self, name, pv_name, username = None, polling = None, timeout = 10000, **kwargs):
        """
        EpicsChannel constructor

        creates the link to the PV to be watched
        """
        ChannelObject.__init__(self, name, username, **kwargs)
 
        self.pvName = pv_name
        self.deviceName = None
        self.device = None
        self.value = Poller.NotInitializedValue
        self.polling = polling
        self.pollingTimer = None
        self.pollingEvents = False
        self.timeout = int(timeout)
        self.read_as_str = kwargs.get("read_as_str", False)
        self._device_initialized = gevent.event.Event()
         
        self.imported = True
        self.pv_connected = None
        self.pv = epics.PV(pv_name)

        logging.getLogger('HWR').debug("creating EPICS PV %s, polling=%s, timeout=%s", self.pvName, polling, self.timeout)
        self.init_poller = Poller.poll(self.init_device,
                                       polling_period = 3000,
                                       value_changed_callback = self.continue_init,
                                       error_callback = self.init_poll_failed,
                                       start_delay=100)


    def init_poll_failed(self, e, poller_id):
        """
        Polling helper function
        --
        Tries to restart polling after 3 seconds.
        """
        self._device_initialized.clear()
        logging.getLogger('HWR').warning("PV %s(%s): could not complete init.", self.pvName, self.name())
        self.init_poller = self.init_poller.restart(3000)

    def continue_init(self, _):
        """
        Polling helper function
        --
        Actually starts the polling of the PV in the >self.polling< time interval.
        """
        self.init_poller.stop()

        if type(self.polling) == types.IntType:
             Poller.poll(self.poll,
                         polling_period = self.polling,
                         value_changed_callback = self.update,
                         error_callback = self.pollFailed)
        else:
            if self.polling=="events":
                self.pv.add_callback(callback=self.valueChanged_callback)
                self.pv.connection_callbacks.append(self.connectionStatusChanged_callback)
                self.poll()
        self._device_initialized.set()

    def init_device(self):
        """
        Not implemented.
        """
        pass

    def poll(self):
        """
        Read the current value of the PV using the get method after the timer has elapsed.

        Parameters:
        n/a
        Result:
        PV's current value after pv.get()
        """
        value = self.pv.get(as_string = self.read_as_str)
        self.emit('update', value)
        return value

    def pollFailed(self, e, poller_id):
        """
        Error handling for polling

        Tries to restart polling again.
        """
        emit_update = True
        if self.value is None:
          emit_update = False
        else:
          self.value = None

        try:
            self.init_device()
        except:
            pass
       
        poller = Poller.get_poller(poller_id)
        if poller is not None:
            poller.restart(1000)

        try:
          raise e
        except:
          logging.exception("%s: Exception happened while polling %s", self.name(), self.pvName)

        if emit_update: 
          # emit at the end => can raise exceptions in callbacks
          self.emit('update', None)

    def getInfo(self):
        """
        ???
        """
        self._device_initialized.wait(timeout=3)
        pass

    def update(self, value = Poller.NotInitializedValue):
        """
        Slot to be called if the polling interval is elapsed.

        Signal >update< is emitted to inform the Brick.
        """
        if value == Poller.NotInitializedValue:
            value = self.getValue()
        if type(value) == types.TupleType:
          value = list(value)

        self.value = value
        self.emit('update', value)
        
    def getValue(self):
        """
        Reads the PVs current value.
        """
        self._device_initialized.wait(timeout=3)

        value = self.pv.get(as_string = self.read_as_str)
        return value

    def setValue(self, newValue):
        """
        Modify the PVs value.
        """
        self.pv.put(newValue)
    
    def isConnected(self):
        """
        Check the PVs connection status
   
        Parameters:
        n/a
        Result:
        True  <=> PV is connected
        False <=> otherwise
        """
        return self.pv_connected

    def valueChanged_callback(self, pvname = None, value = None, char_value = None, **kw):
        """
        Slot to be called if PV value changes. Used for event processing.
        Emit signal >update< to inform the brick about the change
        """
        # logging.getLogger('HWR').debug("PyEpics valueChanged_callback: PV %s = %s.", pvname, char_value)
        if self.read_as_str:
            self.value = char_value
        else:
            self.value = value
        self.emit('update', self.value)

    def connectionStatusChanged_callback(self, pvname = None, conn = None, **kws):
        """
        Callback to be informed about connection status.
        """
        # TO-DO: add action if the connection to the PV is lost
        #        check transferred connection state in that situation
        self.pv_connected = conn
        logging.getLogger('HWR').debug("%s: PyEpics connection status changed: %s", pvname, repr(conn))
