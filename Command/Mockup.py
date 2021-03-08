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

import time
import logging
import Queue
import weakref

from mxcubecore.CommandContainer import CommandObject, ChannelObject


__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


class MockupCommand(CommandObject):
    def __init__(self, name, command_name, list_args=None, timeout=1000, **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)

        self.command_name = command_name
        self.result = None

    def __call__(self, *args, **kwargs):
        self.result = args[0]

    def get(self):
        return self.result

    def abort(self):
        pass

    def is_connected(self):
        return True


class MockupChannel(ChannelObject):
    def __init__(self, name, username=None, timeout=1000, **kwargs):
        ChannelObject.__init__(self, name, username, **kwargs)

        self.timeout = int(timeout)
        self.value = kwargs["default_value"]

    def get_value(self, force=False):
        return self.value

    def set_value(self, new_value):
        self.value = new_value
        self.emit("update", self.value)

    def is_connected(self):
        return self.linkid > 0
