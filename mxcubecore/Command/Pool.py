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
import qt

try:
    import Queue as queue
except ImportError:
    import queue


from mxcubecore.CommandContainer import (
    CommandObject,
    ChannelObject,
    ConnectionError,
)

try:
    import PyTango
except ImportError:
    logging.getLogger("HWR").warning("Tango support is not available.")


__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


class BoundMethodWeakref:
    def __init__(self, bound_method):
        self.func_ref = weakref.ref(bound_method.im_func)
        self.obj_ref = weakref.ref(bound_method.im_self)

    def __call__(self):
        obj = self.obj_ref()
        if obj is not None:
            func = self.func_ref()
            if func is not None:
                return func.__get__(obj)

    def __hash__(self):
        return id(self)

    def __cmp__(self, other):
        if other.__class__ == self.__class__:
            return cmp((self.func_ref, self.obj_ref), (other.func_ref, other.obj_ref))
        else:
            return cmp(self, other)


class PoolCommand(CommandObject):
    def __init__(self, name, macro_name, tango_name=None, username=None, **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)

        self.command = "RunMacro"
        self.device_name = tango_name
        self.macro_name = macro_name

        try:
            self.device = PyTango.DeviceProxy(self.device_name)
        except PyTango.DevFailed as traceback:
            last_error = traceback[-1]
            logging.getLogger("HWR").error(
                "%s: %s", str(self.name()), last_error["desc"]
            )
            self.device = None
        else:
            try:
                self.device.ping()
            except PyTango.ConnectionFailed:
                self.device = None
                raise ConnectionError

    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))

        if self.device is not None:
            try:
                tango_cmd_object = getattr(self.device, self.command)
                args = (self.macro_name,) + args
                logging.getLogger("HWR").debug(
                    "%s: %s, args=%s", str(self.name()), tango_cmd_object, args
                )
                ret = tango_cmd_object(
                    args
                )  # eval('self.device.%s(*%s)' % (self.command, args))
            except PyTango.DevFailed as error_dict:
                logging.getLogger("HWR").error(
                    "%s: Tango, %s", str(self.name()), error_dict
                )
            except Exception:
                logging.getLogger("HWR").exception(
                    "%s: an error occured when calling Tango command %s",
                    str(self.name()),
                    self.command,
                )
            else:
                self.emit("commandReplyArrived", (ret, str(self.name())))
                return ret

        self.emit("commandFailed", (-1, self.name()))

    def abort(self):
        self.device.abort()
        self.emit("commandAborted", (str(self.name()),))

    def is_connected(self):
        return self.device is not None


def process_tango_events():
    while not PoolChannel._tangoEventsQueue.empty():
        try:
            event = PoolChannel._tangoEventsQueue.get_nowait()
        except queue.Empty:
            break
        else:
            try:
                receiver_cb_ref = PoolChannel._eventReceivers[id(event)]
                receiver_cb = receiver_cb_ref()
                if receiver_cb is not None:
                    try:
                        receiver_cb(event.attr_value.value)
                    except AttributeError:
                        pass
            except KeyError:
                pass


class PoolChannel(ChannelObject):
    _tangoEventsQueue = queue.Queue()
    _eventReceivers = {}
    _tangoEventsProcessingTimer = qt.QTimer()

    # start Tango events processing timer
    qt.QObject.connect(
        _tangoEventsProcessingTimer, qt.SIGNAL("timeout()"), process_tango_events
    )
    _tangoEventsProcessingTimer.start(20)

    def __init__(
        self,
        name,
        attribute_name,
        tango_name=None,
        username=None,
        polling=None,
        timeout=10000,
        **kwargs
    ):
        ChannelObject.__init__(self, name, username, **kwargs)

        self.attribute_name = attribute_name
        self.device_name = tango_name
        self.device = None
        self.value = None
        self.polling = polling
        self.__connections = 0
        self.__value = None
        self.polling_timer = None
        self.timeout = int(timeout)

        logging.getLogger("HWR").debug(
            "creating Tango attribute %s/%s, polling=%s, timeout=%d",
            self.device_name,
            self.attribute_name,
            polling,
            self.timeout,
        )

        try:
            self.device = PyTango.DeviceProxy(self.device_name)
        except PyTango.DevFailed as traceback:
            last_error = traceback[-1]
            logging.getLogger("HWR").error(
                "%s: %s", str(self.name()), last_error["desc"]
            )
        else:
            try:
                self.device.ping()
            except PyTango.ConnectionFailed:
                self.device = None
                raise ConnectionError
            else:
                self.device.set_timeout_millis(self.timeout)

                if isinstance(polling, int):
                    self.polling_timer = qt.QTimer()
                    self.polling_timer.connect(
                        self.polling_timer, qt.SIGNAL("timeout()"), self.poll
                    )
                    self.polling_timer.start(polling)
                else:
                    if polling == "events":
                        # try to register event
                        try:
                            self.device.subscribe_event(
                                self.attribute_name, PyTango.EventType.CHANGE, self, []
                            )
                        except PyTango.EventSystemFailed:
                            pass

    def push_event(self, event):
        PoolChannel._eventReceivers[id(event)] = BoundMethodWeakref(self.update)
        PoolChannel._tangoEventsQueue.put(event)

    def poll(self):
        try:
            value = self.device.read_attribute(self.attribute_name).value
        except Exception:
            logging.getLogger("HWR").exception(
                "%s: could not poll attribute %s", str(self.name()), self.attribute_name
            )

            self.polling_timer.stop()
            if not hasattr(self, "_statepolling_timer"):
                self._statepolling_timer = qt.QTimer()
                self._statepolling_timer.connect(
                    self._statepolling_timer, qt.SIGNAL("timeout()"), self.state_polling
                )
            self.device.set_timeout_millis(50)
            self._statepolling_timer.start(5000)
            value = None
            self.emit("update", (None,))
        else:
            if value != self.value:
                self.update(value)

    def state_polling(self):
        """Called when polling has failed"""
        try:
            s = self.device.State()
        except Exception:
            pass
            # logging.getLogger("HWR").exception("Could not read State attribute")
        else:
            if s == PyTango.DevState.OFF:
                return

            self._statepolling_timer.stop()
            self.device.set_timeout_millis(self.timeout)
            logging.getLogger("HWR").info(
                "%s: restarting polling on attribute %s",
                self.name(),
                self.attribute_name,
            )
            self.polling_timer.start(self.polling)

    def update(self, value=None):
        if value is None:
            value = self.get_value()

        self.value = value
        self.emit("update", value)

    def get_value(self):
        self.value = self.device.read_attribute(self.attribute_name).value

        return self.value

    def set_value(self, new_value):
        # newval = PyTango.AttributeValue()
        # newval.value = newValue
        # self.device.write_attribute(self.attribute_name, newval)
        attr = PyTango.AttributeProxy(self.device_name + "/" + self.attribute_name)
        a = attr.read()
        a.value = new_value
        attr.write(a)

    def is_connected(self):
        return self.device is not None
