try:
    from SpecClient_gevent.SpecCommand import SpecCommandA
    from SpecClient_gevent.SpecVariable import SpecVariableA
    from SpecClient_gevent import SpecVariable
except ImportError:
    from SpecClient.SpecCommand import SpecCommandA
    from SpecClient.SpecVariable import SpecVariableA
    from SpecClient import SpecVariable

from HardwareRepository.CommandContainer import CommandObject, ChannelObject


class SpecCommand(CommandObject, SpecCommandA):
    def __init__(self, name, command, version=None, username=None, **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)
        SpecCommandA.__init__(self, command, version)
        self.__cmdExecution = False

    def setSpecVersion(self, version):
        self.connectToSpec(version)

    def replyArrived(self, reply):
        SpecCommandA.replyArrived(self, reply)

        self.__cmdExecution = False

        if reply.error:
            self.emit("commandFailed", (reply.error_code, str(self.name())))
        else:
            self.emit("commandReplyArrived", (reply.getValue(), str(self.name())))

    def beginWait(self):
        self.__cmdExecution = True
        self.emit("commandBeginWaitReply", (str(self.name()),))

    def abort(self):
        SpecCommandA.abort(self)

        self.__cmdExecution = False
        self.emit("commandAborted", (str(self.name()),))

    def isConnected(self):
        return SpecCommandA.isSpecConnected(self)

    def connected(self):
        self.__cmdExecution = False
        self.emit("connected", ())

    def disconnected(self):
        if self.__cmdExecution:
            self.__cmdExecution = False
            self.emit("commandFailed", (-1, str(self.name())))

        self.emit("disconnected", ())
        self.statusChanged(ready=False)

    def statusChanged(self, ready):
        if ready:
            self.emit("commandReady", ())
        else:
            self.emit("commandNotReady", ())


class SpecChannel(ChannelObject, SpecVariableA):
    def __init__(
        self,
        name,
        varname,
        version=None,
        username=None,
        dispatchMode=SpecVariable.FIREEVENT,
        **kwargs
    ):
        ChannelObject.__init__(self, name, username, **kwargs)
        SpecVariableA.__init__(self, varname, version, dispatchMode)

    def setSpecVersion(self, version):
        self.connectToSpec(version)

    def update(self, value):
        ChannelObject.update(self, value)
        self.emit("update", (value,))

    def connected(self):
        self.emit("connected", ())

    def disconnected(self):
        self.emit("disconnected", ())

    def isConnected(self):
        return SpecVariableA.isSpecConnected(self)

    def getValue(self):
        return SpecVariableA.getValue(self)
