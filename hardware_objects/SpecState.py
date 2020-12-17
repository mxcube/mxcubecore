"""Class to notify the spec state

template:
  <procedure class="SpecState">
    <specversion>spec host:spec name</specversion>
  </procedure>
"""

import logging
from mx3core.BaseHardwareObjects import Procedure

try:
    import SpecClient_gevent as SpecClient
except ImportError:
    import SpecClient


class SpecState(Procedure):
    STATES = ("Disconnected", "Connected", "Busy", "Ready")

    def init(self):
        self.lastState = "Unknown"
        self.specDisconnected()
        try:
            self.specConnection = SpecClient.SpecConnectionsManager.SpecConnectionsManager().get_connection(
                self.specversion
            )
        except AttributeError:
            self.specConnection = None
            logging.getLogger("HWR").error("SpecState: you must specify a spec version")
        else:
            SpecClient.SpecEventsDispatcher.connect(
                self.specConnection, "connected", self.specConnected
            )
            SpecClient.SpecEventsDispatcher.connect(
                self.specConnection, "disconnected", self.specDisconnected
            )
            if self.specConnection.isSpecConnected():
                self.specConnected()

    def specConnected(self):
        self.emitSpecState("Connected")

        speccommand = SpecClient.SpecCommand.SpecCommand(
            "sleep", self.specConnection, None
        )
        self.add_command(
            {"name": "SpecStateMacro", "type": "spec", "version": self.specversion},
            "sleep",
        )
        cmd = self.get_command_object("SpecStateMacro")
        cmd.connect_signal("commandReady", self.commandReady)
        cmd.connect_signal("commandNotReady", self.commandNotReady)
        self.connectionStateMacro = cmd
        # try:
        #    speccommand.executeCommand("sleep(0)")
        # except SpecClient.SpecClientError.SpecClientError,diag:
        #    pass

    def specDisconnected(self):
        self.connectionStateMacro = None
        try:
            cmd = self.get_command_object("SpecStateMacro")
        except KeyError:
            pass
        else:
            if cmd is not None:
                cmd.disconnect_signal("commandReady", self.commandReady)
                cmd.disconnect_signal("commandNotReady", self.commandNotReady)
        self.emitSpecState("Disconnected")

    def is_connected(self):
        return self.specConnection is not None and self.specConnection.isSpecConnected()

    def is_ready(self):
        if self.is_connected():
            if self.connectionStateMacro is not None:
                return self.connectionStateMacro.isSpecReady()
        return False

    def get_state(self):
        return (self.lastState, self.specversion)

    def getVersion(self):
        try:
            version = self.specversion.split(":")
        except Exception:
            version = None
        return version

    def commandReady(self):
        self.emitSpecState("Ready")

    def commandNotReady(self):
        self.emitSpecState("Busy")

    def emitSpecState(self, entering):
        if entering == self.lastState:
            # logging.getLogger("HWR").debug('SpecState: %s already in %s' % (wwself.specversion,entering))
            return

        if self.lastState != "Unknown" and self.lastState != entering:
            # logging.getLogger("HWR").debug('SpecState: %s from %s to %s ' % (self.specversion,self.lastState,entering))
            signal_name = "specState%s" % self.lastState
            self.emit(signal_name, (False, self.specversion))
        # else:
        #    logging.getLogger("HWR").debug('SpecState: %s entering %s' % (self.specversion,entering))

        self.lastState = entering
        signal_name = "specState%s" % entering
        self.emit(signal_name, (True, self.specversion))
        self.emit("specStateChanged", (entering, self.specversion))
