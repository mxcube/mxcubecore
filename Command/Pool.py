import logging
import Queue
import weakref
import qt
import types

from HardwareRepository.CommandContainer import (
    CommandObject,
    ChannelObject,
    ConnectionError,
)

try:
    import PyTango
except ImportError:
    logging.getLogger("HWR").warning("Tango support is not available.")


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
            return cmp((self.func_ref, self.obj_ref), (other.func_ref, other.obj_ref))
        else:
            return cmp(self, other)


class PoolCommand(CommandObject):
    def __init__(self, name, macroName, tangoname=None, username=None, **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)

        self.command = "RunMacro"
        self.deviceName = tangoname
        self.macroName = macroName

        try:
            self.device = PyTango.DeviceProxy(self.deviceName)
        except PyTango.DevFailed as traceback:
            last_error = traceback[-1]
            logging.getLogger("HWR").error(
                "%s: %s", str(self.name()), last_error["desc"]
            )
            self.device = None
        else:
            try:
                self.device.ping()
            except PyTango.ConnectionFailed:
                self.device = None
                raise ConnectionError

    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))

        if self.device is not None:
            try:
                tangoCmdObject = getattr(self.device, self.command)
                args = (self.macroName,) + args
                logging.getLogger("HWR").debug(
                    "%s: %s, args=%s", str(self.name()), tangoCmdObject, args
                )
                ret = tangoCmdObject(
                    args
                )  # eval('self.device.%s(*%s)' % (self.command, args))
            except PyTango.DevFailed as error_dict:
                logging.getLogger("HWR").error(
                    "%s: Tango, %s", str(self.name()), error_dict
                )
            except Exception:
                logging.getLogger("HWR").exception(
                    "%s: an error occured when calling Tango command %s",
                    str(self.name()),
                    self.command,
                )
            else:
                self.emit("commandReplyArrived", (ret, str(self.name())))
                return ret

        self.emit("commandFailed", (-1, self.name()))

    def abort(self):
        self.device.abort()
        self.emit("commandAborted", (str(self.name()),))
        pass

    def isConnected(self):
        return self.device is not None


def processTangoEvents():
    while not PoolChannel._tangoEventsQueue.empty():
        try:
            event = PoolChannel._tangoEventsQueue.get_nowait()
        except Queue.Empty:
            break
        else:
            try:
                receiverCbRef = PoolChannel._eventReceivers[id(event)]
                receiverCb = receiverCbRef()
                if receiverCb is not None:
                    try:
                        receiverCb(event.attr_value.value)
                    except AttributeError:
                        pass
            except KeyError:
                pass


class PoolChannel(ChannelObject):
    _tangoEventsQueue = Queue.Queue()
    _eventReceivers = {}
    _tangoEventsProcessingTimer = qt.QTimer()

    # start Tango events processing timer
    qt.QObject.connect(
        _tangoEventsProcessingTimer, qt.SIGNAL("timeout()"), processTangoEvents
    )
    _tangoEventsProcessingTimer.start(20)

    def __init__(
        self,
        name,
        attribute_name,
        tangoname=None,
        username=None,
        polling=None,
        timeout=10000,
        **kwargs
    ):
        ChannelObject.__init__(self, name, username, **kwargs)

        self.attributeName = attribute_name
        self.deviceName = tangoname
        self.device = None
        self.value = None
        self.polling = polling
        self.__connections = 0
        self.__value = None
        self.pollingTimer = None
        self.timeout = int(timeout)

        logging.getLogger("HWR").debug(
            "creating Tango attribute %s/%s, polling=%s, timeout=%d",
            self.deviceName,
            self.attributeName,
            polling,
            self.timeout,
        )

        try:
            self.device = PyTango.DeviceProxy(self.deviceName)
        except PyTango.DevFailed as traceback:
            last_error = traceback[-1]
            logging.getLogger("HWR").error(
                "%s: %s", str(self.name()), last_error["desc"]
            )
        else:
            try:
                self.device.ping()
            except PyTango.ConnectionFailed:
                self.device = None
                raise ConnectionError
            else:
                self.device.set_timeout_millis(self.timeout)

                if isinstance(polling, int):
                    self.pollingTimer = qt.QTimer()
                    self.pollingTimer.connect(
                        self.pollingTimer, qt.SIGNAL("timeout()"), self.poll
                    )
                    self.pollingTimer.start(polling)
                else:
                    if polling == "events":
                        # try to register event
                        try:
                            self.device.subscribe_event(
                                self.attributeName, PyTango.EventType.CHANGE, self, []
                            )
                        except PyTango.EventSystemFailed:
                            pass

    def push_event(self, event):
        PoolChannel._eventReceivers[id(event)] = BoundMethodWeakref(self.update)
        PoolChannel._tangoEventsQueue.put(event)

    def poll(self):
        try:
            value = self.device.read_attribute(self.attributeName).value
        except Exception:
            logging.getLogger("HWR").exception(
                "%s: could not poll attribute %s", str(self.name()), self.attributeName
            )

            self.pollingTimer.stop()
            if not hasattr(self, "_statePollingTimer"):
                self._statePollingTimer = qt.QTimer()
                self._statePollingTimer.connect(
                    self._statePollingTimer, qt.SIGNAL("timeout()"), self.statePolling
                )
            self.device.set_timeout_millis(50)
            self._statePollingTimer.start(5000)
            value = None
            self.emit("update", (None,))
        else:
            if value != self.value:
                self.update(value)

    def statePolling(self):
        """Called when polling has failed"""
        try:
            s = self.device.State()
        except Exception:
            pass
            # logging.getLogger("HWR").exception("Could not read State attribute")
        else:
            if s == PyTango.DevState.OFF:
                return

            self._statePollingTimer.stop()
            self.device.set_timeout_millis(self.timeout)
            logging.getLogger("HWR").info(
                "%s: restarting polling on attribute %s",
                self.name(),
                self.attributeName,
            )
            self.pollingTimer.start(self.polling)

    def update(self, value=None):
        if value is None:
            value = self.getValue()

        self.value = value
        self.emit("update", value)

    def getValue(self):
        self.value = self.device.read_attribute(self.attributeName).value

        return self.value

    def setValue(self, newValue):
        # newval = PyTango.AttributeValue()
        # newval.value = newValue
        # self.device.write_attribute(self.attributeName, newval)
        attr = PyTango.AttributeProxy(self.deviceName + "/" + self.attributeName)
        a = attr.read()
        a.value = newValue
        attr.write(a)

    def isConnected(self):
        return self.device is not None
