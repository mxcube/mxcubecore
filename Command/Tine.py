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
import atexit

import gevent
import tine

from HardwareRepository.CommandContainer import CommandObject, ChannelObject


__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


class TineCommand(CommandObject):
    def __init__(
        self,
        name,
        command_name,
        tinename=None,
        username=None,
        list_args=None,
        timeout=1000,
        **kwargs
    ):
        CommandObject.__init__(self, name, username, **kwargs)
        self.command_name = command_name
        self.tine_name = tinename
        self.timeout = int(timeout)

    def __call__(self, *args, **kwargs):
        """executes Tine cmd

        Raises:
            strerror: [description]
            ex: [description]
        """

        self.emit("commandBeginWaitReply", (str(self.name()),))
        if len(args) == 0:
            command_argument = []
        else:
            command_argument = args[0]
        try:
            ret = tine.set(
                self.tine_name, self.command_name, command_argument, self.timeout
            )
            self.emit("commandReplyArrived", (ret, str(self.name())))
        except IOError as strerror:
            logging.getLogger("user_level_log").exception("TINE: %s" % strerror)
            self.emit("commandFailed", (strerror))
            raise strerror
        except Exception as ex:
            logging.getLogger("user_level_log").exception("TINE: error: %s" % str(ex))
            self.emit("commandFailed", (str(ex)))
            raise ex

    def get(self):
        """Returns result of cmd execution

        Returns:
            [type]: [description]
        """
        result = None
        try:
            result = tine.get(self.tine_name, self.command_name, self.timeout)
        except IOError as strerror:
            logging.getLogger("HWR").error("%s" % strerror)
        except BaseException:
            pass
        return result

    def abort(self):
        pass

    def is_connected(self):
        return True


def emit_tine_channel_updates():
    while not TineChannel.updates.empty():
        try:
            channel_obj_ref, value = TineChannel.updates.get()
        except Queue.Empty:
            break
        else:
            channel_object = channel_obj_ref()
            if channel_object is not None:
                try:
                    channel_object.emit("update", (value,))
                except BaseException:
                    logging.getLogger("HWR").exception(
                        "Exception while emitting new value for channel %s",
                        channel_object.name(),
                    )


def do_tine_channel_update(sleep_time):
    while True:
        emit_tine_channel_updates()
        time.sleep(sleep_time)


class TineChannel(ChannelObject):
    attach = {"timer": tine.attach, "event": tine.notify, "datachange": tine.update}

    updates = Queue.Queue()
    # updates_emitter = QtCore.QTimer()
    # QtCore.QObject.connect(updates_emitter, QtCore.SIGNAL('timeout()'), emit_tine_channel_updates)
    # updates_emitter.start(20)
    updates_emitter = gevent.spawn(do_tine_channel_update, 0.1)

    def __init__(
        self, name, attribute_name, tinename=None, username=None, timeout=1000, **kwargs
    ):
        ChannelObject.__init__(self, name, username, **kwargs)

        self.attribute_name = attribute_name
        self.tine_name = tinename
        self.timeout = int(timeout)
        self.value = None
        self.old_value = None

        self.callback_fail_counter = 0

        logging.getLogger("HWR").debug(
            "Attaching TINE channel: %s %s" % (self.tine_name, self.attribute_name)
        )
        if kwargs.get("size"):
            self.linkid = TineChannel.attach[kwargs.get("attach", "timer")](
                self.tine_name,
                self.attribute_name,
                self.tine_event_callback,
                self.timeout,
                int(kwargs["size"]),
            )
        else:
            self.linkid = TineChannel.attach[kwargs.get("attach", "timer")](
                self.tine_name,
                self.attribute_name,
                self.tine_event_callback,
                self.timeout,
            )
        # except IOError as strerror:
        #   logging.getLogger("HWR").error("%s" %strerror)
        # except ValueError:
        #   logging.getLogger("HWR").error("TINE attach object is not callable")

        if self.linkid > 0 and kwargs.get("attach", "timer") == "datachange":
            tolerance = kwargs.get("tolerance", 0.0)
            try:
                tine.tolerance(self.linkid, 0.0, float(tolerance.rstrip("%")))
            except AttributeError:
                if tolerance != 0.0:
                    tine.tolerance(self.linkid, float(tolerance), 0.0)

        # TODO Remove this sleep. Tine lib bug when after attach directly get is called
        # time.sleep(0.025)

        atexit.register(self.__del__)

    def __del__(self):
        try:
            tine.detach(self.linkid)
            logging.getLogger("HWR").debug(
                "TINE channel %s %s detached" % (self.tine_name, self.attribute_name)
            )
            self.linkid = -1
        except IOError as strerror:
            logging.getLogger("HWR").error(
                "%s detaching %s %s" % (strerror, self.tine_name, self.attribute_name)
            )
        except BaseException:
            logging.getLogger("HWR").error(
                "Exception on detaching %s %s" % (self.tine_name, self.attribute_name)
            )

    def tine_event_callback(self, id, cc, data_list):
        if cc == 0:
            self.callback_fail_counter = 0
            self.update(data_list)
        elif str(cc) != 103 and self.attribute_name not in ("dozor-pass", "ff-ssim"):
            self.callback_fail_counter = self.callback_fail_counter + 1
            logging.getLogger("HWR").error(
                "Tine event callback error %s, Channel: %s, Server: %s/%s"
                % (str(cc), self.name(), self.tine_name, self.attribute_name)
            )
            if self.callback_fail_counter >= 3:
                logging.getLogger("HWR").error(
                    "Repeated tine event callback errors %s, Channel: %s, Server: %s/%s"
                    % (str(cc), self.name(), self.tine_name, self.attribute_name)
                )

    def update(self, value=None):
        if value is None:
            msg = "Update with value None on: %s %s" % (
                self.tine_name,
                self.attribute_name,
            )
            logging.getLogger("HWR").warning(msg)
            value = self.get_value()
        self.value = value

        if value != self.oldvalue:
            TineChannel.updates.put((weakref.ref(self), value))
            self.oldvalue = value

    def get_value(self, force=False):
        if force:
            if self.value is not None:
                logging.getLogger("HWR").warning(
                    "Executing synch get on: %s %s"
                    % (self.tine_name, self.attribute_name)
                )
                return self._synchronous_get()
            else:
                logging.getLogger("HWR").warning(
                    "Attempting to force unconnected channel: %s %s"
                    % (self.tine_name, self.attribute_name)
                )
                return None

        # GB: if there is no value yet, wait and hope it will appear somehow:
        _counter = 0
        while self.value is None and _counter <= 10:
            logging.getLogger("HWR").warning(
                "Waiting for a first update on: %s %s"
                % (self.tine_name, self.attribute_name)
            )
            # but now tine lib should be standing the get, so we try....
            # self.value = self._synchronous_get()
            time.sleep(0.02)
            _counter += 1
        if self.value is None:
            logging.getLogger("HWR").warning(
                "Gave up waiting for a first update on: %s %s"
                % (self.tine_name, self.attribute_name)
            )
        return self.value

    def _synchronous_get(self):
        try:
            value = tine.get(self.tine_name, self.attribute_name, self.timeout)
            return value
        except IOError as strerror:
            logging.getLogger("HWR").error("%s" % strerror)

    def set_value(self, new_value):
        listData = newValue
        try:
            ret = tine.set(self.tine_name, self.attribute_name, listData, self.timeout)
        except IOError as strerror:
            logging.getLogger("HWR").error("%s" % strerror)

    def is_connected(self):
        return self.linkid > 0

    def set_old_value(self, old_value):
        self.oldvalue = old_value
