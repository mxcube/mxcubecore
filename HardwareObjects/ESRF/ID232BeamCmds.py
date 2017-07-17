from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.TaskUtils import *
from HardwareRepository.CommandContainer import CommandObject
import gevent

class ControllerCommand(CommandObject):
    def __init__(self, name, cmd):
        CommandObject.__init__(self, name)
        self._cmd = cmd
	self._cmd_execution = None

    def isConnected(self):
        return True

    def getArguments(self):
        if self.name() == 'Anneal':
            self._arguments.append(("Time [s]", "float"))
        return self._arguments

    @task
    def __call__(self, *args, **kwargs):
        self.emit('commandBeginWaitReply', (str(self.name()), ))
        self._cmd_execution = gevent.spawn(self._cmd, *args, **kwargs)
        self._cmd_execution.link(self._cmd_done)

    def _cmd_done(self, cmd_execution):
        try:
            try:
                res = cmd_execution.get()
            except:
                self.emit('commandFailed', (str(self.name()), ))
            else: 
                if isinstance(res, gevent.GreenletExit):
                    self.emit('commandFailed', (str(self.name()), ))
                else:
                    self.emit('commandReplyArrived', (str(self.name()), res))
        finally:
            self.emit('commandReady')

    def abort(self):
        if self._cmd_execution and not self._cmd_execution.ready():
            self._cmd_execution.kill()
        

class ID232BeamCmds(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def init(self):
        controller = self.getObjectByRole("controller")
        self.centrebeam = ControllerCommand("Centre beam", controller.centrebeam)
        #self.quick_realign = ControllerCommand("Quick realign", controller.quick_realign)
        #self.anneal = ControllerCommand("Anneal", controller.anneal_procedure)

    def getCommands(self):
        return [self.centrebeam] #, self.quick_realign, self.anneal]

        
