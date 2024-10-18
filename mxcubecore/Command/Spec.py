# encoding: utf-8
#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

try:
    from SpecClient_gevent import SpecVariable
    from SpecClient_gevent.SpecCommand import SpecCommandA
    from SpecClient_gevent.SpecVariable import SpecVariableA
except ImportError:
    from SpecClient.SpecCommand import SpecCommandA
    from SpecClient.SpecVariable import SpecVariableA
    from SpecClient import SpecVariable

from mxcubecore.CommandContainer import (
    ChannelObject,
    CommandObject,
)

__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


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
            self.emit("commandReplyArrived", (reply.get_value(), str(self.name())))

    def beginWait(self):
        self.__cmdExecution = True
        self.emit("commandBeginWaitReply", (str(self.name()),))

    def abort(self):
        SpecCommandA.abort(self)

        self.__cmdExecution = False
        self.emit("commandAborted", (str(self.name()),))

    def is_connected(self):
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

    def is_connected(self):
        return SpecVariableA.isSpecConnected(self)

    def get_value(self):
        return SpecVariableA.get_value(self)
