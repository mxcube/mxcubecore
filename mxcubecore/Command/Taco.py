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

import logging
import weakref
import copy

from HardwareRepository.dispatcher import saferef
from .. import Poller
from HardwareRepository.CommandContainer import CommandObject, ChannelObject
from .. import TacoDevice_MTSafe as TacoDevice


__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


class TacoCommand(CommandObject):
    def __init__(
        self, name, command, taconame=None, username=None, args=None, dc=False, **kwargs
    ):
        CommandObject.__init__(self, name, username, **kwargs)

        self.command = command
        self.device_name = taconame
        self.data_collector = dc
        self.pollers = {}
        self.__value_changed_callback_ref = None
        self.__timeout_callback_ref = None

        if args is None:
            self.arg_list = ()
        else:
            # not very nice...
            args = str(args)
            if not args.endswith(","):
                args += ","
            self.arg_list = eval("(" + args + ")")

        self.connect_device()

    def connect_device(self):
        try:
            self.device = TacoDevice.TacoDevice(
                self.device_name, dc=self.data_collector
            )
        except Exception:
            logging.getLogger("HWR").exception(
                "Problem with Taco ; could not open Device %s", self.device_name
            )
            self.device = None

    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))

        if len(args) > 0 and len(self.arg_list) > 0:
            logging.getLogger("HWR").error(
                "%s: cannot execute command with arguments when 'args' is defined from XML",
                str(self.name()),
            )
            self.emit("commandFailed", (-1, str(self.name())))
            return
        elif len(args) == 0 and len(self.arg_list) > 0:
            args = self.arg_list

        if self.device is not None and self.device.imported:
            try:
                ret = eval("self.device.%s(*%s)" % (self.command, args))
            except Exception:
                logging.getLogger("HWR").error(
                    "%s: an error occured when calling Taco command %s",
                    str(self.name()),
                    self.command,
                )
            else:
                self.emit("commandReplyArrived", (ret, str(self.name())))
                return ret

        self.emit("commandFailed", (-1, str(self.name())))

    def _value_changed(self, value):
        self.value_changed(self.device_name, value)

    def value_changed(self, device_name, value):
        try:
            callback = self.__value_changed_callback_ref()
        except Exception:
            pass
        else:
            if callback is not None:
                callback(device_name, value)

    def on_polling_error(self, exception, poller_id):
        self.connect_device()
        poller = Poller.get_poller(poller_id)
        if poller is not None:
            try:
                poller.restart(1000)
            except Exception:
                pass

    def poll(
        self,
        polling_time=500,
        arguments_list=(),
        value_changed_callback=None,
        timeout_callback=None,
        direct=True,
        compare=True,
    ):
        self.__value_changed_callback_ref = saferef.safe_ref(value_changed_callback)

        poll_cmd = getattr(self.device, self.command)

        Poller.poll(
            poll_cmd,
            copy.deepcopy(arguments_list),
            polling_time,
            self._value_changed,
            self.on_polling_error,
            compare,
        )

    def stopPolling(self):
        pass

    def abort(self):
        pass

    def isConnected(self):
        return self.device is not None and self.device.imported


class TacoChannel(ChannelObject):
    """Emulation of a 'Taco channel' = a Taco command + polling"""

    def __init__(
        self,
        name,
        command,
        taconame=None,
        username=None,
        polling=None,
        args=None,
        **kwargs
    ):
        ChannelObject.__init__(self, name, username, **kwargs)

        self.command = TacoCommand(
            name + "_internalCmd", command, taconame, username, args, False, **kwargs
        )

        try:
            self.polling = int(polling)
        except Exception:
            self.polling = None
        else:
            self.command.poll(self.polling, self.command.arg_list, self.value_changed)

    def value_changed(self, deviceName, value):
        self.emit("update", value)

    def get_value(self):
        return self.command()

    def is_connected(self):
        return self.command.isConnected()
