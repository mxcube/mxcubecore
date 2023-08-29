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
import gevent
import gevent.event

try:
    import Queue as queue
except ImportError:
    import queue


from mxcubecore.CommandContainer import (
    CommandObject,
    ChannelObject,
    ConnectionError,
)
from mxcubecore import Poller
from mxcubecore.dispatcher import saferef
import numpy

gevent_version = list(map(int, gevent.__version__.split(".")))

try:
    import PyTango
    from PyTango.gevent import DeviceProxy
except ImportError:
    logging.getLogger("HWR").warning("Tango support is not available.")


__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"

log = logging.getLogger("HWR")


class TangoCommand(CommandObject):
    def __init__(self, name, command, tangoname=None, username=None, **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)

        self.command = command
        self.device_name = tangoname
        self.device = None

    def init_device(self):
        try:
            self.device = DeviceProxy(self.device_name)
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
        if self.device is None:
            # TODO: emit commandFailed
            # beware of infinite recursion with Sample Changer
            # (because of procedure exception cleanup...)
            self.init_device()

        try:
            tango_cmd_object = getattr(self.device, self.command)
            ret = tango_cmd_object(
                *args
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
        pass

    def set_device_timeout(self, timeout):
        if self.device is None:
            self.init_device()
        self.device.set_timeout_millis(timeout)

    def is_connected(self):
        return self.device is not None


def process_tango_events():
    while not TangoChannel._tangoEventsQueue.empty():
        try:
            ev = TangoChannel._tangoEventsQueue.get_nowait()
        except queue.Empty:
            break
        else:
            try:
                receiverCbRef = TangoChannel._eventReceivers[id(ev)]
                receiverCb = receiverCbRef()
                if receiverCb is not None:
                    try:
                        gevent.spawn(receiverCb, ev.event.attr_value.value)
                    except AttributeError:
                        pass
            except KeyError:
                pass


class E:
    def __init__(self, event):
        self.event = event


class TangoChannel(ChannelObject):
    _tangoEventsQueue = queue.Queue()
    _eventReceivers = {}

    #if gevent_version < [1,3,0]:
        #_tangoEventsProcessingTimer = gevent.get_hub().loop.async()
    #else:
    _tangoEventsProcessingTimer = gevent.get_hub().loop.async_()

    # start Tango events processing timer
    _tangoEventsProcessingTimer.start(process_tango_events)

    def __init__(
        self,
        name,
        attribute_name,
        tangoname=None,
        username=None,
        polling=None,
        timeout=10000,
        **kwargs
    ):
        ChannelObject.__init__(self, name, username, **kwargs)

        self.attribute_name = attribute_name
        self.device_name = tangoname
        self.device = None
        self.value = Poller.NotInitializedValue
        self.polling = polling
        self.polling_timer = None
        self.polling_events = False
        self.timeout = int(timeout)
        self.read_as_str = kwargs.get("read_as_str", False)
        self._device_initialized = gevent.event.Event()
        logging.getLogger("HWR").debug(
            "creating Tango attribute %s/%s, polling=%s, timeout=%d",
            self.device_name,
            self.attribute_name,
            polling,
            self.timeout,
        )
        self.init_device()
        self.continue_init(None)
        """
        self.init_poller = Poller.poll(self.init_device,
                                       polling_period = 3000,
                                       value_changed_callback = self.continue_init,
                                       error_callback = self.init_poll_failed,
                                       start_delay=100)
        """

    def init_poll_failed(self, e, poller_id):
        self._device_initialized.clear()
        logging.warning(
            "%s/%s (%s): could not complete init. (hint: device server is not running, or has to be restarted)",
            self.device_name,
            self.attribute_name,
            self.name(),
        )
        self.init_poller = self.init_poller.restart(3000)

    def continue_init(self, _):
        # self.init_poller.stop()

        if isinstance(self.polling, int):
            self.raw_device = DeviceProxy(self.device_name)

            Poller.poll(
                self.poll,
                polling_period=self.polling,
                value_changed_callback=self.update,
                error_callback=self.poll_failed,
            )
        else:
            if self.polling == "events":
                # try to register event
                try:
                    self.polling_events = True
                    # logging.getLogger("HWR").debug("subscribing to CHANGE event for %s", self.attribute_name)
                    self.device.subscribe_event(
                        self.attribute_name,
                        PyTango.EventType.CHANGE_EVENT,
                        self,
                        [],
                        True,
                    )
                    # except PyTango.EventSystemFailed:
                    #   pass
                except Exception:
                    logging.getLogger("HWR").exception("could not subscribe event")
        self._device_initialized.set()

    def init_device(self):
        try:
            self.device = DeviceProxy(self.device_name)
        except PyTango.DevFailed as traceback:
            self.imported = False
            last_error = traceback[-1]
            logging.getLogger("HWR").error(
                "%s: %s", str(self.name()), last_error["desc"]
            )
        else:
            self.imported = True
            try:
                self.device.ping()
            except PyTango.ConnectionFailed:
                self.device = None
                raise ConnectionError
            else:
                self.device.set_timeout_millis(self.timeout)

                # check that the attribute exists (to avoid Abort in PyTango grrr)
                if not self.attribute_name.lower() in [
                    attr.name.lower() for attr in self.device.attribute_list_query()
                ]:
                    logging.getLogger("HWR").error(
                        "no attribute %s in Tango device %s",
                        self.attribute_name,
                        self.device_name,
                    )
                    self.device = None

    def push_event(self, event):
        # logging.getLogger("HWR").debug("%s | attr_value=%s, event.errors=%s, quality=%s", self.name(), event.attr_value, event.errors,event.attr_value is None and "N/A" or event.attr_value.quality)
        if (
            event.attr_value is None
            or event.err
            or event.attr_value.quality != PyTango.AttrQuality.ATTR_VALID
        ):
            # logging.getLogger("HWR").debug("%s, receving BAD event... attr_value=%s, event.errors=%s, quality=%s", self.name(), event.attr_value, event.errors, event.attr_value is None and "N/A" or event.attr_value.quality)
            return
        else:
            pass
            # logging.getLogger("HWR").debug("%s, receiving good event", self.name())
        ev = E(event)
        TangoChannel._eventReceivers[id(ev)] = saferef.safe_ref(self.update)
        TangoChannel._tangoEventsQueue.put(ev)
        TangoChannel._tangoEventsProcessingTimer.send()

    def poll(self):

        if self.read_as_str:
            value = self.raw_device.read_attribute(
                self.attribute_name, PyTango.DeviceAttribute.ExtractAs.String
            ).value
            # value = self.device.read_attribute_as_str(self.attribute_name).value
        else:
            value = self.raw_device.read_attribute(self.attribute_name).value

        return value

    def poll_failed(self, e, poller_id):
        self.emit("update", None)
        """
        emit_update = True
        if self.value is None:
          emit_update = False
        else:
          self.value = None

        try:
            self.init_device()
        except:
            pass

        poller = Poller.get_poller(poller_id)
        if poller is not None:
            poller.restart(1000)

        try:
          raise e
        except:
          logging.exception("%s: Exception happened while polling %s", self.name(), self.attribute_name)

        if emit_update:
          # emit at the end => can raise exceptions in callbacks
          self.emit('update', None)
        """

    def get_info(self):
        self._device_initialized.wait(timeout=3)
        return self.device.get_attribute_config(self.attribute_name)

    def update(self, value=Poller.NotInitializedValue):

        if isinstance(value, numpy.ndarray):
            value = value
        elif value == Poller.NotInitializedValue:
            value = self.get_value()
        elif isinstance(value, tuple):
            value = list(value)

        self.value = value
        self.emit("update", value)

    def get_value(self):
        if self.read_as_str:
            value = self.device.read_attribute(
                self.attribute_name, PyTango.DeviceAttribute.ExtractAs.String
            ).value
        else:
            value = self.device.read_attribute(self.attribute_name).value

        
        if isinstance(value, numpy.ndarray):
            if any(value != self.value):
                self.update(value)
        elif value != self.value:
            self.update(value)

        return value

    def set_value(self, new_value):
        self.device.write_attribute(self.attribute_name, new_value)
        # attr = PyTango.AttributeProxy(self.device_name + "/" + self.attribute_name)
        # a = attr.read()
        # a.value = newValue
        # attr.write(a)

    def is_connected(self):
        return self.device is not None
