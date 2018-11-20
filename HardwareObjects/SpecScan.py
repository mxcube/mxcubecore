try:
    from SpecClient_gevent import SpecEventsDispatcher
    from SpecClient_gevent import SpecConnectionsManager
except ImportError:
    from SpecClient import SpecEventsDispatcher
    from SpecClient import SpecConnectionsManager

from HardwareRepository.BaseHardwareObjects import Procedure


class SpecScan(Procedure):
    def __init__(self, name):
        Procedure.__init__(self, name)

        self.specConnection = None

    def setSpecVersion(self, specVersion):
        scanCmd = self.getCommandObject("start")
        scanCmd.setSpecVersion(specVersion)

        if specVersion is not None:
            self.specConnection = SpecConnectionsManager.SpecConnectionsManager().getConnection(
                specVersion
            )

            if self.specConnection is not None:
                SpecEventsDispatcher.connect(
                    self.specConnection, "connected", self.connected
                )
                SpecEventsDispatcher.connect(
                    self.specConnection, "disconnected", self.disconnected
                )

                if self.specConnection.isSpecConnected():
                    self.connected()

    def connected(self):
        pass

    def isConnected(self):
        return self.specConnection is not None and self.specConnection.isSpecConnected()

    def disconnected(self):
        pass

    def scanDimension(self):
        return self.getProperty("dimension")

    def isAbsolute(self):
        raise NotImplementedError

    def isRelative(self):
        return not self.isAbsolute()

    def allowDifferentNbPoints(self):
        return False

    def abortScan(self):
        scanCmd = self.getCommandObject("start")
        scanCmd.abort()

    def startScan(self, *args):
        scanCmd = self.getCommandObject("start")
        scanCmd.connectSignal("commandReplyArrived", self.scanDone)
        scanCmd.connectSignal("commandFailed", self.scanDone)
        scanCmd.connectSignal("commandBeginWaitReply", self.scanStarted)
        scanCmd.connectSignal("commandAborted", self.scanAborted)

        scanCmd(*args)

    def scanDone(self):
        self.emit("scanDone", ())

    def scanStarted(self):
        self.emit("scanStarted", ())

    def scanAborted(self):
        self.emit("scanAborted", ())
