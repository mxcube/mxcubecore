from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.TaskUtils import task
from HardwareRepository.CommandContainer import CommandObject
import gevent
import logging


class ControllerCommand(CommandObject):
    def __init__(self, name, cmd):
        CommandObject.__init__(self, name)
        self._cmd = cmd
        self._cmd_execution = None

    def isConnected(self):
        return True

    def get_arguments(self):
        if self.name() == "Anneal":
            self._arguments.append(("Time [s]", "float"))
        return self._arguments

    @task
    def __call__(self, *args, **kwargs):
        logging.getLogger("user_level_log").info("Starting %s" % self.name())
        self.emit("commandBeginWaitReply", (str(self.name()),))
        self._cmd_execution = gevent.spawn(self._cmd, *args, **kwargs)
        self._cmd_execution.link(self._cmd_done)

    def _cmd_done(self, cmd_execution):
        try:
            try:
                res = cmd_execution.get()
            except Exception:
                logging.getLogger("user_level_log").exception(
                    str(self.name()) + " failed!"
                )
                self.emit("commandFailed", (str(self.name()),))
            else:
                logging.getLogger("user_level_log").info(
                    str(self.name()) + " finished successfully."
                )
                if isinstance(res, gevent.GreenletExit):
                    self.emit("commandFailed", (str(self.name()),))
                else:
                    self.emit("commandReplyArrived", (str(self.name()), res))
        finally:
            self.emit("commandReady")

    def abort(self):
        if self._cmd_execution and not self._cmd_execution.ready():
            self._cmd_execution.kill()


class ID30BeamCmds(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def init(self):
        controller = self.get_object_by_role("controller")
        self.centrebeam = ControllerCommand("Centre beam", controller.centrebeam)
        self.quick_realign = ControllerCommand(
            "Quick realign", controller.quick_realign
        )
        self.anneal = ControllerCommand("Anneal", controller.anneal_procedure)

    def get_commands(self):
        return [self.centrebeam, self.quick_realign, self.anneal]
