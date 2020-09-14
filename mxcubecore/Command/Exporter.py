import logging
import gevent
from gevent.queue import Queue
from warnings import warn
from HardwareRepository.CommandContainer import CommandObject, ChannelObject
from .exporter import ExporterClient

exporter_clients = {}


def start_exporter(address, port, timeout=3, retries=1):
    global exporter_clients
    if not (address, port) in exporter_clients:
        client = Exporter(address, port, timeout)
        exporter_clients[(address, port)] = client
        client.start()
        return client
    else:
        return exporter_clients[(address, port)]


class ExporterCommand(CommandObject):
    def __init__(
        self, name, command, username=None, address=None, port=None, timeout=3, **kwargs
    ):
        CommandObject.__init__(self, name, username, **kwargs)
        self.command = command
        self.__exporter = start_exporter(address, port, timeout)

    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))

        try:
            ret = self.__exporter.execute(self.command, args, kwargs.get("timeout", -1))
        except BaseException:
            # logging.getLogger('HWR').exception("%s: an error occured when calling Exporter command %s", str(self.name()), self.command)
            self.emit("commandFailed", (-1, self.name()))
            raise
        else:
            self.emit("commandReplyArrived", (ret, str(self.name())))
            return ret

    def abort(self):
        # TODO: implement async commands
        pass

    def get_state(self):
        return self.__exporter.get_state()

    def isConnected(self):
        return self.__exporter.isConnected()


class Exporter(ExporterClient.ExporterClient):
    STATE_EVENT = "State"
    STATUS_EVENT = "Status"
    VALUE_EVENT = "Value"
    POSITION_EVENT = "Position"
    MOTOR_STATES_EVENT = "MotorStates"

    STATE_READY = "Ready"
    STATE_INITIALIZING = "Initializing"
    STATE_STARTING = "Starting"
    STATE_RUNNING = "Running"
    STATE_MOVING = "Moving"
    STATE_CLOSING = "Closing"
    STATE_REMOTE = "Remote"
    STATE_STOPPED = "Stopped"
    STATE_COMMUNICATION_ERROR = "Communication Error"
    STATE_INVALID = "Invalid"
    STATE_OFFLINE = "Offline"
    STATE_ALARM = "Alarm"
    STATE_FAULT = "Fault"
    STATE_UNKNOWN = "Unknown"

    def __init__(self, address, port, timeout=3, retries=1):
        ExporterClient.ExporterClient.__init__(
            self, address, port, ExporterClient.PROTOCOL.STREAM, timeout, retries
        )

        self.started = False
        self.callbacks = {}
        self.events_queue = Queue()
        self.events_processing_task = None

    def start(self):
        pass
        # self.started=True
        # self.reconnect()

    def stop(self):
        # self.started=False
        self.disconnect()

    def execute(self, *args, **kwargs):
        ret = ExporterClient.ExporterClient.execute(self, *args, **kwargs)
        return self._to_python_value(ret)

    def get_state(self):
        return self.execute("getState")

    def readProperty(self, *args, **kwargs):
        ret = ExporterClient.ExporterClient.readProperty(self, *args, **kwargs)
        return self._to_python_value(ret)

    def reconnect(self):
        return
        if self.started:
            try:
                self.disconnect()
                self.connect()
            except BaseException:
                gevent.sleep(1.0)
                self.reconnect()

    def onDisconnected(self):
        pass  # self.reconnect()

    def register(self, name, cb):
        if callable(cb):
            self.callbacks.setdefault(name, []).append(cb)
        if not self.events_processing_task:
            self.events_processing_task = gevent.spawn(self.processEventsFromQueue)

    def _to_python_value(self, value):
        if value is None:
            return

        # IK TODO make this with eval
        if "\x1f" in value:
            value = self.parseArray(value)
            try:
                value = map(int, value)
            except BaseException:
                try:
                    value = map(float, value)
                except BaseException:
                    pass
        else:
            try:
                value = int(value)
            except BaseException:
                try:
                    value = float(value)
                except BaseException:
                    try:
                        if value == "false":
                            value = False
                        elif value == "true":
                            value = True
                    except BaseException:
                        pass
        return value

    def onEvent(self, name, value, timestamp):
        self.events_queue.put((name, value))

    def processEventsFromQueue(self):
        while True:
            try:
                name, value = self.events_queue.get()
            except BaseException:
                return

            for cb in self.callbacks.get(name, []):
                try:
                    cb(self._to_python_value(value))
                except BaseException:
                    logging.exception(
                        "Exception while executing callback %s for event %s", cb, name
                    )
                    continue


class ExporterChannel(ChannelObject):
    def __init__(
        self,
        name,
        attribute_name,
        username=None,
        address=None,
        port=None,
        timeout=3,
        **kwargs
    ):
        ChannelObject.__init__(self, name, username, **kwargs)

        self.__exporter = start_exporter(address, port, timeout)

        self.attributeName = attribute_name
        self.value = None

        self.__exporter.register(attribute_name, self.update)

        logging.getLogger("HWR").debug(
            "Attaching Exporter channel: %s %s " % (address, name)
        )

        self.update()

    def update(self, value=None):
        value = value or self.get_value()
        if isinstance(value, tuple):
            value = list(value)

        self.value = value
        self.emit("update", value)

    def get_value(self):
        value = self.__exporter.readProperty(self.attributeName)
        return value

    def set_value(self, value):
        self.__exporter.writeProperty(self.attributeName, value)

    def isConnected(self):
        return self.__exporter.isConnected()

    """ obsolete, keep for backward compatibility """

    def getValue(self):
        warn("getValue is deprecated. Use get_value instead", DeprecationWarning)
        return self.get_value()

    def setValue(self, newValue):
        warn("setValue is deprecated. Use set_value instead", DeprecationWarning)
        self.set_value(newValue)
