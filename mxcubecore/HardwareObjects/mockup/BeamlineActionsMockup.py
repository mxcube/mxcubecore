from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.TaskUtils import task
from HardwareRepository.CommandContainer import CommandObject
import gevent
import logging


class SimulatedAction:
    def __call__(self, *args, **kw):
        gevent.sleep(3)
        return args


class SimulatedActionError:
    def __call__(self, *args, **kw):
        raise RuntimeError("Simulated error")


class LongSimulatedAction:
    def __call__(self, *args, **kw):
        for i in range(10):
            gevent.sleep(1)
            logging.getLogger("user_level_log").info("%d, sleeping for 1 second", i + 1)

        return args


class ControllerCommand(CommandObject):
    def __init__(self, name, cmd, username=None, klass=SimulatedAction):
        CommandObject.__init__(self, name, username)
        self._cmd = klass()
        self._cmd_execution = None
        self.type = "CONTROLLER"

        if self.name() == "Anneal":
            self.add_argument("Time [s]", "float")
        if self.name() == "Test":
            self.add_argument("combo test", "combo", [{"value1": 0, "value2": 1}])

    def isConnected(self):
        return True

    @task
    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))
        self._cmd_execution = gevent.spawn(self._cmd, *args, **kwargs)
        self._cmd_execution.link(self._cmd_done)

    def _cmd_done(self, cmd_execution):
        try:
            try:
                res = cmd_execution.get()
            except Exception:
                logging.getLogger("HWR").exception(
                    "%s: execution failed", str(self.username)
                )
                self.emit("commandFailed", (str(self.name()),))
            else:
                if isinstance(res, gevent.GreenletExit):
                    # command aborted
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


class BeamlineActionsMockup(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def init(self):
        self.centrebeam = ControllerCommand("centrebeam", None, "Centre beam")
        self.quick_realign = ControllerCommand(
            "realign", None, "Quick realign", klass=LongSimulatedAction
        )
        self.anneal = ControllerCommand("Anneal", None, klass=SimulatedActionError)
        self.combotest = ControllerCommand("Test", None, "Test with combo box")

    def get_commands(self):
        return [self.centrebeam, self.quick_realign, self.anneal, self.combotest]
