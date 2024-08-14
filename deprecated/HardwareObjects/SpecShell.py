"""Class

template:
  <procedure class="SpecShell">
    <specversion>spec host:spec name</specversion>
  </procedure>
"""

import logging
from mxcubecore.BaseHardwareObjects import HardwareObject

try:
    import SpecClient_gevent as SpecClient
except ImportError:
    import SpecClient

from qt import *


class SpecOutputVar(QObject, SpecClient.SpecVariable.SpecVariableA):
    def __init__(self, parent):
        QObject.__init__(self, parent)
        SpecClient.SpecVariable.SpecVariableA.__init__(self)

    def update(self, value):
        value = str(value).rstrip()
        if len(value):
            self.emit(PYSIGNAL("outputReceived"), (value,))


class SpecShell(HardwareObject):
    def __init__(self, *args):
        super().__init__(*args)
        self.isSpecReady = False

    def init(self):
        self.specShellCommand = None
        self.specShellLsdef = None
        self.commandRunning = False
        self.lsdefRunning = False
        self.lsdefBuffer = []
        self.lsdefCommands = None
        self.specOutput = SpecOutputVar(None)
        QObject.connect(
            self.specOutput, PYSIGNAL("outputReceived"), self.outputReceived
        )
        try:
            self.specConnection = SpecClient.SpecConnectionsManager.SpecConnectionsManager().get_connection(
                self.specversion
            )
        except AttributeError:
            self.specConnection = None
            logging.getLogger("HWR").error("SpecShell: you must specify a spec version")
        else:
            self.specOutput.connectToSpec(
                "output/tty",
                self.specversion,
                dispatchMode=SpecClient.SpecVariable.FIREEVENT,
                prefix=False,
            )

            SpecClient.SpecEventsDispatcher.connect(
                self.specConnection, "connected", self.sConnected
            )
            SpecClient.SpecEventsDispatcher.connect(
                self.specConnection, "disconnected", self.sDisconnected
            )
            if self.is_connected():
                self.sConnected()

    def sConnected(self):
        self.emit("connected", ())

        speccommand = SpecClient.SpecCommand.SpecCommand(
            "sleep", self.specConnection, 0
        )

        self.add_command(
            {"name": "SpecShellMacro", "type": "spec", "version": self.specversion},
            "sleep",
        )
        cmd = self.get_command_object("SpecShellMacro")
        cmd.connect_signal("commandReady", self.commandReady)
        cmd.connect_signal("commandNotReady", self.commandNotReady)
        cmd.connect_signal("commandReplyArrived", self.commandFinished)
        cmd.connect_signal("commandBeginWaitReply", self.commandStarted)
        cmd.connect_signal("commandFailed", self.commandFailed)
        cmd.connect_signal("commandAborted", self.commandAborted)
        self.specShellCommand = cmd

        self.add_command(
            {"name": "SpecShellLsdef", "type": "spec", "version": self.specversion},
            "lsdef *",
        )
        cmd = self.get_command_object("SpecShellLsdef")
        # cmd.connect_signal('commandReady',self.commandReady)
        # cmd.connect_signal('commandNotReady',self.commandNotReady)
        cmd.connect_signal("commandReplyArrived", self.commandFinished)
        cmd.connect_signal("commandBeginWaitReply", self.commandStarted)
        cmd.connect_signal("commandFailed", self.commandFailed)
        cmd.connect_signal("commandAborted", self.commandAborted)
        self.specShellLsdef = cmd

        """
        try:
            speccommand.executeCommand("sleep(0)")
        except SpecClient.SpecClientError.SpecClientError,diag:
            pass
        """

    def isConnected(self):
        return self.specConnection is not None and self.specConnection.isSpecConnected()

    def is_ready(self):
        return self.isSpecReady

    def isRunning(self):
        return self.commandRunning

    def sDisconnected(self):
        if self.commandRunning:
            self.emit("aborted", ())
            self.emit("failed", (None,))
            self.commandRunning = False

        self.specShellCommand = None
        self.lsdefCommands = None
        self.emit("disconnected", ())

    def commandReady(self):
        self.isSpecReady = True
        if self.specShellCommand is None:
            return
        if self.commandRunning:
            return
        self.emit("ready", ())

    def commandNotReady(self):
        self.isSpecReady = False
        if self.specShellCommand is None:
            return
        if self.commandRunning:
            return
        self.emit("busy", ())

    def commandFinished(self, result, command):
        if command == "SpecShellLsdef":
            self.lsdefRunning = False
            commands_list = []
            for buf in self.lsdefBuffer:
                try:
                    buf_list = buf.split()
                except Exception:
                    pass
                else:
                    i = 0
                    while i < len(buf_list):
                        cmd_name = buf_list[i]
                        try:
                            cmd_aux = buf_list[i + 1]
                        except Exception:
                            pass
                        else:
                            try:
                                left_par = cmd_aux[0]
                                right_par = cmd_aux[-1]
                                midle_num = cmd_aux[1:-1]
                            except Exception:
                                pass
                            else:
                                if left_par == "(" and right_par == ")":
                                    try:
                                        int(midle_num)
                                    except Exception:
                                        pass
                                    else:
                                        commands_list.append(cmd_name.lstrip("*"))
                        i += 2
            self.lsdefBuffer = []
            commands_list.sort()
            self.lsdefCommands = commands_list
            self.emit("allCommandsList", (commands_list,))
        self.commandRunning = False
        self.emit("finished", (result,))

    def commandStarted(self, command):
        if command == "SpecShellLsdef":
            self.lsdefBuffer = []
            self.lsdefRunning = True
        self.commandRunning = True
        self.emit("started", ())

    def commandFailed(self, result, command):
        if command == "SpecShellLsdef":
            self.lsdefRunning = False
            self.lsdefBuffer = []
            self.lsdefCommands = None
            self.emit("allCommandsList", ((),))
        self.commandRunning = False
        self.emit("failed", (result,))

    def commandAborted(self, command):
        if command == "SpecShellLsdef":
            self.lsdefRunning = False
            self.lsdefBuffer = []
            # self.emit('allCommandsList', ((),))
        self.commandRunning = False
        self.emit("aborted", ())

    def execute_command(self, command):
        try:
            self.specShellCommand.executeCommand(command)
        except SpecClient.SpecClientError.SpecClientError as diag:
            self.emit("failed", (None,))

    def abortCommand(self):
        if self.commandRunning:
            try:
                self.specShellCommand.abort()
            except SpecClient.SpecClientError.SpecClientError as diag:
                pass

    def outputReceived(self, output):
        if self.lsdefRunning:
            self.lsdefBuffer.append(output)
        else:
            self.emit("output", (output,))

    def getSpecVersion(self):
        try:
            ver = self.specversion
        except AttributeError:
            ver = None
        return ver

    def getUserCommands(self):
        cmds = []
        try:
            for cmd in self["usercmds"]:
                try:
                    cmd_args = cmd.args
                except Exception:
                    cmd_args = ""
                if len(cmd_args):
                    cmds.append("%s %s" % (cmd.method, cmd_args))
                else:
                    cmds.append(cmd.method)
        except Exception:
            pass
        return cmds

    def getAllCommands(self):
        if self.lsdefRunning:
            return
        if self.lsdefCommands is not None:
            self.emit("allCommandsList", (self.lsdefCommands,))
        else:
            try:
                self.specShellLsdef.executeCommand("lsdef *")
            except SpecClient.SpecClientError.SpecClientError as diag:
                self.emit("allCommandsList", ((),))
