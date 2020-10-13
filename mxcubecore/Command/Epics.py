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

from saferef import *

from Poller import *

# from .CommandContainer import CommandObject, ChannelObject
from HardwareRepository.CommandContainer import CommandObject, ChannelObject

try:
    import epics
except ImportError:
    logging.getLogger("HWR").warning("EPICS support not available.")


__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


class EpicsCommand(CommandObject):
    def __init__(self, name, pv_name, username=None, args=None, **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)

        self.pv_name = pv_name
        self.read_as_str = kwargs.get("read_as_str", False)
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

        if len(self.arg_list) > 1:
            logging.getLogger("HWR").error(
                "EpicsCommand: ftm only scalar arguments are supported."
            )
            return

        self.pv = epics.PV(pv_name, auto_monitor=True)
        self.pv_connected = self.pv.connect()
        self.value_changed(self.pv.get(as_string=self.read_as_str))
        logging.getLogger("HWR").debug(
            "EpicsCommand: creating pv %s: read_as_str = %s",
            self.pv_name,
            self.read_as_str,
        )

    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))

        if len(args) > 0 and len(self.arg_list) > 0:
            # arguments given both given in command call _AND_ in the xml file
            logging.getLogger("HWR").error(
                "%s: cannot execute command with arguments when 'args' is defined from XML",
                str(self.name()),
            )
            self.emit("commandFailed", (-1, str(self.name())))
            return
        elif len(args) == 0 and len(self.arg_list) > 0:
            # no argument given in the command call but inside the xml file -> use the
            # default argument from the xml file
            args = self.arg_list

        # LNLS
        # if self.pv is not None and self.pv_connected:
        if self.pv is not None:
            if len(args) == 0:
                # no arguments available -> get the pv's current value
                try:
                    ret = self.pv.get(as_string=self.read_as_str)
                except Exception:
                    logging.getLogger("HWR").error(
                        "%s: an error occured when calling Epics command %s",
                        str(self.name()),
                        self.pv_name,
                    )
                else:
                    self.emit("commandReplyArrived", (ret, str(self.name())))
                    return ret
            else:
                # use the given argument to change the pv's value
                try:
                    # LNLS
                    # self.pv.put(args[0], wait = True)
                    self.pv.put(args[0], wait=False)
                except Exception:
                    logging.getLogger("HWR").error(
                        "%s: an error occured when calling Epics command %s",
                        str(self.name()),
                        self.pv_name,
                    )
                else:
                    self.emit("commandReplyArrived", (0, str(self.name())))
                    return 0
        self.emit("commandFailed", (-1, str(self.name())))

    def value_changed(self, value):
        try:
            callback = self.__value_changed_callback_ref()
        except Exception:
            pass
        else:
            if callback is not None:
                callback(value)

    def on_polling_error(self, exception, poller_id):
        # try to reconnect the pv
        self.pv.connect()
        poller = Poller.get_poller(poller_id)
        if poller is not None:
            try:
                poller.restart(1000)
            except Exception:
                pass

    def get_pv_value(self):
        # wrapper function to pv.get() in order to supply additional named parameter
        return self.pv.get(as_string=self.read_as_str)

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

        # store the call to get as a function object
        # poll_cmd = self.pv.get
        poll_cmd = self.get_pv_value

        Poller.poll(
            poll_cmd,
            copy.deepcopy(arguments_list),
            polling_time,
            self.value_changed,
            self.on_polling_error,
            compare,
        )

    def stop_polling(self):
        pass

    def abort(self):
        pass

    def is_connected(self):
        return self.pv_connected


class EpicsChannel(ChannelObject):
    """Emulation of a 'Epics channel' = an Epics command + polling"""

    def __init__(self, name, command, username=None, polling=None, args=None, **kwargs):
        ChannelObject.__init__(self, name, username, **kwargs)

        self.command = EpicsCommand(
            name + "_internalCmd", command, username, args, **kwargs
        )

        try:
            self.polling = int(polling)
        except Exception:
            self.polling = None
        else:
            self.command.poll(self.polling, self.command.arg_list, self.value_changed)

    def value_changed(self, value):
        self.emit("update", value)

    def get_value(self):
        return self.command()

    def set_value(self, value):
        self.command(value)

    def is_connected(self):
        return self.command.isConnected()
