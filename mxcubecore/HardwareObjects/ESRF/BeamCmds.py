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

    def get_arguments(self):
        if self.name() == "Anneal":
            self.add_argument("Time [s]", "float")

        return CommandObject.get_arguments(self)

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

    def get_arguments(self):
        if self.name() == "Anneal":
            self._arguments.append(("Time [s]", "float"))
        return self._arguments

    @task
    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))

        if (
            getattr(self._hwobj, "get_actuator_state")().lower()
            in TWO_STATE_COMMAND_ACTIVE_STATES
        ):
            cmd = getattr(self._hwobj, "actuatorOut")
        else:
            cmd = getattr(self._hwobj, "actuatorIn")

        self._cmd_execution = gevent.spawn(cmd)
        self._cmd_execution.link(self._cmd_done)

    def _cmd_done(self, cmd_execution):
        try:
            try:
                cmd_execution.get()
                res = getattr(self._hwobj, "get_actuator_state")().lower()
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

        if hasattr(self._hwobj, "get_actuator_state"):
            value = getattr(self._hwobj, "get_actuator_state")().lower()

        return value
