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

import sys
import time
import logging

if sys.version_info[0] == 2:
    import Queue as queue
else:
    import queue

import weakref
import gevent

from mxcubecore.CommandContainer import CommandObject, ChannelObject
import atexit

import tine


class TineCommand(CommandObject):
    def __init__(
        self,
        name,
        command_name,
        tinename=None,
        username=None,
        ListArgs=None,
        timeout=1000,
        **kwargs
    ):
        CommandObject.__init__(self, name, username, **kwargs)
        self.commandName = command_name
        self.tineName = tinename
        self.timeout = int(timeout)

    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))
        if len(args) == 0:
            commandArgument = []
        else:
            commandArgument = args[0]
        try:
            # logging.getLogger("HWR").info("Tine command %s sent" % self.commandName)
            ret = tine.set(
                self.tineName, self.commandName, commandArgument, self.timeout
            )
            # logging.getLogger("HWR").info("Tine command %s reply arrived" % self.commandName)
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
        result = None
        try:
            result = tine.get(self.tineName, self.commandName, self.timeout)
        except IOError as strerror:
            logging.getLogger("HWR").error("%s" % strerror)
        except Exception:
            pass
        return result

    def abort(self):
        pass

    def is_connected(self):
        return True


def emitTineChannelUpdates():
    while not TineChannel.updates.empty():
        try:
            channel_obj_ref, value = TineChannel.updates.get()
        except queue.Empty:
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
        emitTineChannelUpdates()
        time.sleep(sleep_time)


class TineChannel(ChannelObject):
    attach = {"timer": tine.attach, "event": tine.notify, "datachange": tine.update}

    updates = queue.Queue()
    # updates_emitter = QtCore.QTimer()
    # QtCore.QObject.connect(updates_emitter, QtCore.SIGNAL('timeout()'), emitTineChannelUpdates)
    # updates_emitter.start(20)
    updates_emitter = gevent.spawn(do_tine_channel_update, 0.1)

    def __init__(
        self, name, attribute_name, tinename=None, username=None, timeout=1000, **kwargs
    ):
        ChannelObject.__init__(self, name, username, **kwargs)

        self.attributeName = attribute_name
        self.tineName = tinename
        self.timeout = int(timeout)
        self.value = None
        self.oldvalue = None

        self.callback_fail_counter = 0

        self.show_callback_error = False
        self.verbose_error_message = None

        logging.getLogger("HWR").debug(
            "Attaching TINE channel: %s %s" % (self.tineName, self.attributeName)
        )

        if kwargs.get("verbose"):
            logging.getLogger("HWR").debug(
                "GUI logging TINE channel: %s %s" % (self.tineName, self.attributeName)
            )
            self.show_callback_error = True
            if kwargs.get("message"):
                self.verbose_error_message = kwargs.get("message")

        if kwargs.get("size"):
            self.linkid = TineChannel.attach[kwargs.get("attach", "timer")](
                self.tineName,
                self.attributeName,
                self.tineEventCallback,
                self.timeout,
                int(kwargs["size"]),
            )
        else:
            self.linkid = TineChannel.attach[kwargs.get("attach", "timer")](
                self.tineName, self.attributeName, self.tineEventCallback, self.timeout
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
                "TINE channel %s %s detached" % (self.tineName, self.attributeName)
            )
            self.linkid = -1
        except IOError as strerror:
            logging.getLogger("HWR").error(
                "%s detaching %s %s" % (strerror, self.tineName, self.attributeName)
            )
        except Exception:
            logging.getLogger("HWR").error(
                "Exception on detaching %s %s" % (self.tineName, self.attributeName)
            )

    def tineEventCallback(self, id, cc, data_list):
        if cc == 0:
            self.callback_fail_counter = 0
            self.update(data_list)
        elif (
            cc != 103
        ):  #  was str(cc) # and self.attributeName not in ("dozor-pass", "ff-ssim"):
            self.callback_fail_counter = self.callback_fail_counter + 1
            if self.show_callback_error:
                logging.getLogger("GUI").error(
                    "Tine event callback error %s, Channel: %s, Server: %s/%s"
                    % (str(cc), self.name(), self.tineName, self.attributeName)
                )
                if self.verbose_error_message is not None:
                    logging.getLogger("GUI").error("%s" % self.verbose_error_message)

            else:
                logging.getLogger("HWR").error(
                    "Tine event callback error %s, Channel: %s, Server: %s/%s"
                    % (str(cc), self.name(), self.tineName, self.attributeName)
                )

            """
            if self.callback_fail_counter >= 3:
                logging.getLogger("HWR").error(
                    "Repeated tine event callback errors %s, Channel: %s, Server: %s/%s"
                    % (str(cc), self.name(), self.tineName, self.attributeName)
                )
            """

    def update(self, value=None):

        # if self.tineName.split("/")[2] == 'ics':
        #   print '>>>>>>>>>>>>>>>>>>', self.attributeName, value, self.value, self.oldvalue

        if value is None:
            logging.getLogger("HWR").warning(
                "Update with value None on: %s %s" % (self.tineName, self.attributeName)
            )
            value = self.get_value()
        self.value = value

        if value != self.oldvalue:
            TineChannel.updates.put((weakref.ref(self), value))
            self.oldvalue = value
            # if self.tineName == "/P14/BCUIntensity/Device0":
            #    logging.getLogger("HWR").debug('----------------- %s %s' %(self.attributeName,self.value))

    def get_value(self, force=False):
        # logging.getLogger("HWR").debug('TINE channel %s, %s get at val=%s'%(self.tineName,self.attributeName,self.value))
        # if self.tineName == "/P14/BCUIntensity/Device0":
        #   print self.attributeName, self.value

        # GB: if forced while having a value already, i.e. well after connecting a channel, do a real synchronous get and return
        if force:
            if self.value is not None:
                logging.getLogger("HWR").warning(
                    "Executing synch get on: %s %s"
                    % (self.tineName, self.attributeName)
                )
                return self._synchronous_get()
            else:
                logging.getLogger("HWR").warning(
                    "Attempting to force unconnected channel: %s %s"
                    % (self.tineName, self.attributeName)
                )
                return None

        # GB: if there is no value yet, wait and hope it will appear somehow:
        _counter = 10
        while self.value is None and _counter <= 100:
            time.sleep(0.020)
            logging.getLogger("HWR").warning(
                "No update after %d ms on: %s %s, executing synchronous get"
                % (_counter * 20, self.tineName, self.attributeName)
            )
            # but now tine lib should be standing the get, so we try....

            self.value = self._synchronous_get()
            # time.sleep(0.02)
            _counter += 1
        if self.value is None:
            logging.getLogger("HWR").warning(
                "Gave up waiting for a first update on: %s %s"
                % (self.tineName, self.attributeName)
            )
        return self.value

    def _synchronous_get(self):
        try:
            value = tine.get(self.tineName, self.attributeName, self.timeout)
            return value
        except IOError as strerror:
            logging.getLogger("HWR").error("%s" % strerror)

    def set_value(self, newValue):
        listData = newValue
        try:
            ret = tine.set(self.tineName, self.attributeName, listData, self.timeout)
        except IOError as strerror:
            logging.getLogger("HWR").error("%s" % strerror)

    def is_connected(self):
        return self.linkid > 0

    def set_old_value(self, oldValue):
        self.oldvalue = oldValue
