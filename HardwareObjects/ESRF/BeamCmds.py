from HardwareRepository.TaskUtils import task
from HardwareRepository.CommandContainer import CommandObject
import gevent


PROCEDURE_COMMAND_T = "CONTROLLER"
TWO_STATE_COMMAND_T = "INOUT"
TWO_STATE_COMMAND_ACTIVE_STATES = ["in", "on", "enabled"]


class ControllerCommand(CommandObject):
    def __init__(self, name, cmd):
        CommandObject.__init__(self, name)
        self._cmd = cmd
        self._cmd_execution = None
        self.type = PROCEDURE_COMMAND_T

    def isConnected(self):
        return True

    def getArguments(self):
        if self.name() == "Anneal":
            self.addArgument("Time [s]", "float")

        return CommandObject.getArguments(self)

    @task
    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))
        self._cmd_execution = gevent.spawn(self._cmd, *args, **kwargs)
        self._cmd_execution.link(self._cmd_done)

    def _cmd_done(self, cmd_execution):
        try:
            try:
                res = cmd_execution.get()
            except BaseException:
                self.emit("commandFailed", (str(self.name()),))
            else:
                if isinstance(res, gevent.GreenletExit):
                    self.emit("commandFailed", (str(self.name()),))
                else:
                    self.emit("commandReplyArrived", (str(self.name()), res))
        finally:
            self.emit("commandReady")

    def abort(self):
        if self._cmd_execution and not self._cmd_execution.ready():
            self._cmd_execution.kill()

    def value(self):
        return None


class HWObjActuatorCommand(CommandObject):
    def __init__(self, name, hwobj):
        CommandObject.__init__(self, name)
        self._hwobj = hwobj
        self.type = TWO_STATE_COMMAND_T

    def isConnected(self):
        return True

    def getArguments(self):
        if self.name() == "Anneal":
            self._arguments.append(("Time [s]", "float"))
        return self._arguments

    @task
    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))

        if (
            getattr(self._hwobj, "get_value")().name.lower()
            in TWO_STATE_COMMAND_ACTIVE_STATES
        ):
            value = self._hwobj.VALUES.OUT
        else:
            value = self._hwobj.VALUES.IN
        cmd = getattr(self._hwobj, "set_value")(value)
        self._cmd_execution = gevent.spawn(cmd)
        self._cmd_execution.link(self._cmd_done)

    def _cmd_done(self, cmd_execution):
        try:
            try:
                cmd_execution.get()
                res = getattr(self._hwobj, "get_value")().name.lower()
            except BaseException:
                self.emit("commandFailed", (str(self.name()),))
            else:
                if isinstance(res, gevent.GreenletExit):
                    self.emit("commandFailed", (str(self.name()),))
                else:
                    self.emit("commandReplyArrived", (str(self.name()), res))
        finally:
            self.emit("commandReady")

    def abort(self):
        if self._cmd_execution and not self._cmd_execution.ready():
            self._cmd_execution.kill()

    def value(self):
        value = "UNKNOWN"

        if hasattr(self._hwobj, "get_value"):
            value = getattr(self._hwobj, "get_value")().name.lower()

        return value
