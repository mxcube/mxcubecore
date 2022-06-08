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

from __future__ import absolute_import

import logging
import os
# import time
# import types
from mxcubecore.dispatcher import saferef

import gevent
from gevent.event import Event

try:
    import Queue as queue
except ImportError:
    import queue

gevent_version = list(map(int, gevent.__version__.split('.')))


from mxcubecore.CommandContainer import (
    CommandObject,
    ChannelObject,
    ConnectionError,
)

from PyTango import DevFailed, ConnectionFailed
import PyTango

# from mxcubecore.TaskUtils import task

try:
    from sardana.taurus.core.tango.sardana import registerExtensions
    from taurus import Device, Attribute
    import taurus
except Exception:
    logging.getLogger("HWR").warning("Sardana is not available in this computer.")


__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


def processSardanaEvents():

    while not SardanaObject._eventsQueue.empty():

        try:
            ev = SardanaObject._eventsQueue.get_nowait()
        except queue.Empty:
            break
        else:
            try:
                receiver_cb_ref = SardanaObject._eventReceivers[id(ev)]
                receiver_cb = receiver_cb_ref()
                if receiver_cb is not None:
                    try:
                        gevent.spawn(receiver_cb, ev)
                    except AttributeError:
                        pass
            except KeyError:
                pass


def wait_end_of_command(cmdobj):
    while (
        cmdobj.macrostate == SardanaMacro.RUNNING
        or cmdobj.macrostate == SardanaMacro.STARTED
    ):
        gevent.sleep(0.05)
    return cmdobj.door.result


def end_of_macro(macobj):
    macobj._reply_arrived_event.wait()


class AttributeEvent:
    def __init__(self, event):
        self.event = event


class SardanaObject(object):
    _eventsQueue = queue.Queue()
    _eventReceivers = {}

    if gevent_version < [1, 3, 0]:
        _eventsProcessingTimer = getattr(gevent.get_hub().loop, "async")()
    else:
        _eventsProcessingTimer = gevent.get_hub().loop.async_()

    # start Sardana events processing timer
    _eventsProcessingTimer.start(processSardanaEvents)

    def object_listener(self, *args):
        ev = AttributeEvent(args)
        # NBNB self.update not defined
        SardanaObject._eventReceivers[id(ev)] = saferef.safe_ref(self.update)
        SardanaObject._eventsQueue.put(ev)
        SardanaObject._eventsProcessingTimer.send()


class SardanaMacro(CommandObject, SardanaObject):

    macroStatusAttr = None
    INIT, STARTED, RUNNING, DONE = range(4)

    def __init__(self, name, macro, doorname=None, username=None, **kwargs):
        super(SardanaMacro, self).__init__(name, username, **kwargs)

        self._reply_arrived_event = Event()
        self.macro_format = macro
        self.doorname = doorname
        self.door = None
        self.init_device()
        self.macrostate = SardanaMacro.INIT
        self.doorstate = None
        self.t0 = 0

    def init_device(self):
        self.door = Device(self.doorname)
        self.door.set_timeout_millis(10000)

        #
        # DIRTY FIX to make compatible taurus listeners and existence of Tango channels/commands
        # as defined in Command/Tango.py
        #
        # if self.door.__class__ == taurus.core.tango.tangodevice.TangoDevice:
        #    dp = self.door.getHWObj()
        #    try:
        #        dp.subscribe_event = dp._subscribe_event
        #    except AttributeError:
        #        pass

        if self.macroStatusAttr is None:
            self.macroStatusAttr = self.door.getAttribute("State")
            self.macroStatusAttr.addListener(self.object_listener)

    def __call__(self, *args, **kwargs):

        self._reply_arrived_event.clear()
        self.result = None

        wait = kwargs.get("wait", False)

        if self.door is None:
            self.init_device()

        logging.getLogger("HWR").debug(
            "Executing sardana macro: %s" % self.macro_format
        )
        logging.getLogger("HWR").debug(
            "   args=%s / kwargs=%s" % (str(args), str(kwargs))
        )

        try:
            fullcmd = self.macro_format + " " + " ".join([str(a) for a in args])
        except Exception:
            import traceback

            logging.getLogger("HWR").info(traceback.format_exc())
            logging.getLogger("HWR").info(
                "  - Wrong format for macro arguments. Macro is %s / args are (%s)"
                % (self.macro_format, str(args))
            )
            return

        try:
            import time

            self.t0 = time.time()
            if self.doorstate in ["ON", "ALARM"]:
                self.door.runMacro(fullcmd.split())
                self.macrostate = SardanaMacro.STARTED
                self.emit("commandBeginWaitReply", (str(self.name()),))
            else:
                logging.getLogger("HWR").error(
                    "%s. Cannot execute. Door is not READY", str(self.name())
                )
                self.emit("commandFailed", (-1, self.name()))
        except TypeError:
            logging.getLogger("HWR").error(
                "%s. Cannot properly format macro code. Format is: %s, args are %s",
                str(self.name()),
                self.macro_format,
                str(args),
            )
            self.emit("commandFailed", (-1, self.name()))
        except DevFailed as error_dict:
            logging.getLogger("HWR").error(
                "%s: Cannot run macro. %s", str(self.name()), error_dict
            )
            self.emit("commandFailed", (-1, self.name()))
        except AttributeError as error_dict:
            logging.getLogger("HWR").error(
                "%s: MacroServer not running?, %s", str(self.name()), error_dict
            )
            self.emit("commandFailed", (-1, self.name()))
        except Exception:
            logging.getLogger("HWR").exception(
                "%s: an error occured when calling Tango command %s",
                str(self.name()),
                self.macro_format,
            )
            self.emit("commandFailed", (-1, self.name()))

        if wait:
            logging.getLogger("HWR").debug("... start waiting...")
            t = gevent.spawn(end_of_macro, self)
            t.get()
            logging.getLogger("HWR").debug("... end waiting...")

        return

    def update(self, event):
        data = event.event[2]

        try:
            if not isinstance(data, PyTango.DeviceAttribute):
                # Events different than a value changed on attribute.  Taurus sends an event with attribute info
                # logging.getLogger('HWR').debug("==========. Got an event, but it is not an attribute . it is %s" % type(data))
                # logging.getLogger('HWR').debug("doorstate event. type is %s" % str(type(data)))
                return

            # Handling macro state changed event
            doorstate = str(data.value)
            logging.getLogger("HWR").debug(
                "doorstate changed. it is %s" % str(doorstate)
            )

            if doorstate != self.doorstate:
                self.doorstate = doorstate

                # logging.getLogger('HWR').debug("self.doorstate is %s" % self.canExecute())
                self.emit("commandCanExecute", (self.can_execute(),))

                if doorstate in ["ON", "ALARM"]:
                    # logging.getLogger('HWR').debug("Macroserver ready for commands")
                    self.emit("commandReady", ())
                else:
                    # logging.getLogger('HWR').debug("Macroserver busy ")
                    self.emit("commandNotReady", ())

            if self.macrostate == SardanaMacro.STARTED and doorstate == "RUNNING":
                # logging.getLogger('HWR').debug("Macro server is running")
                self.macrostate = SardanaMacro.RUNNING
            elif self.macrostate == SardanaMacro.RUNNING and (
                doorstate in ["ON", "ALARM"]
            ):
                logging.getLogger("HWR").debug("Macro execution finished")
                self.macrostate = SardanaMacro.DONE
                self.result = self.door.result
                self.emit("commandReplyArrived", (self.result, str(self.name())))
                if doorstate == "ALARM":
                    self.emit("commandAborted", (str(self.name()),))
                self._reply_arrived_event.set()
            elif (
                self.macrostate == SardanaMacro.DONE
                or self.macrostate == SardanaMacro.INIT
            ):
                # already handled in the general case above
                pass
            else:
                logging.getLogger("HWR").debug("Macroserver state changed")
                self.emit("commandFailed", (-1, str(self.name())))
        except ConnectionFailed:
            logging.getLogger("HWR").debug("Cannot connect to door %s" % self.doorname)
            self.emit("commandFailed", (-1, str(self.name())))
        except Exception:
            import traceback

            logging.getLogger("HWR").debug(
                "SardanaMacro / event handling problem. Uggh. %s"
                % traceback.format_exc()
            )
            self.emit("commandFailed", (-1, str(self.name())))

    def abort(self):
        if self.door is not None:
            logging.getLogger("HWR").debug("SardanaMacro / aborting macro")
            self.door.abortMacro()
            # self.emit('commandReady', ())

    def is_connected(self):
        return self.door is not None

    def can_execute(self):
        return self.door is not None and (self.doorstate in ["ON", "ALARM"])


class SardanaCommand(CommandObject):
    def __init__(self, name, command, taurusname=None, username=None, **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)

        self.command = command
        self.taurusname = taurusname
        self.device = None

    def init_device(self):

        try:
            self.device = Device(self.taurusname)
        except DevFailed as traceback:
            last_error = traceback[-1]
            logging.getLogger("HWR").error(
                "%s: %s", str(self.name()), last_error["desc"]
            )
            self.device = None
        else:
            try:
                self.device.ping()
            except ConnectionFailed:
                self.device = None
                raise ConnectionError

    def __call__(self, *args, **kwargs):

        self.emit("commandBeginWaitReply", (str(self.name()),))

        if self.device is None:
            self.init_device()

        try:
            cmdObject = getattr(self.device, self.command)
            ret = cmdObject(*args)
        except DevFailed as error_dict:
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

    def is_connected(self):
        return self.device is not None


class SardanaChannel(ChannelObject, SardanaObject):
    def __init__(
        self, name, attribute_name, username=None, uribase=None, polling=None, **kwargs
    ):

        super(SardanaChannel, self).__init__(name, username, **kwargs)

        class ChannelInfo(object):
            def __init__(self):
                super(ChannelInfo, self).__init__()

        self.attribute_name = attribute_name
        self.model = os.path.join(uribase, attribute_name)
        self.attribute = None

        self.value = None
        self.polling = polling

        self.info = ChannelInfo()
        self.info.minval = None
        self.info.maxval = None

        self.init_device()

    def init_device(self):

        try:
            self.attribute = Attribute(self.model)
            #
            # DIRTY FIX to make compatible taurus listeners and existence of Tango channels/commands
            # as defined in Command/Tango.py
            #
            # if self.attribute.__class__ == taurus.core.tango.tangoattribute.TangoAttribute:
            #    dev = self.attribute.getParentObj()
            #    dp = dev.getHWObj()
            #    try:
            #        dp.subscribe_event = dp._subscribe_event
            #    except AttributeError:
            #        pass
            # logging.getLogger("HWR").debug("initialized")
        except DevFailed as traceback:
            self.imported = False
            return

        # read information
        try:
            if taurus.Release.version_info[0] == 3:
                ranges = self.attribute.getConfig().getRanges()
                if ranges is not None and ranges[0] != "Not specified":
                    self.info.minval = float(ranges[0])
                if ranges is not None and ranges[-1] != "Not specified":
                    self.info.maxval = float(ranges[-1])
            elif taurus.Release.version_info[0] > 3:  # taurus 4 and beyond
                minval, maxval = self.attribute.ranges()
                self.info.minval = minval.magnitude
                self.info.maxval = maxval.magnitude
        except Exception:
            import traceback

            logging.getLogger("HWR").info("info initialized. Cannot get limits")
            logging.getLogger("HWR").info("%s" % traceback.format_exc())

        # prepare polling
        # if the polling value is a number set it as the taurus polling period

        if self.polling:
            if isinstance(self.polling, int):
                self.attribute.changePollingPeriod(self.polling)

            self.attribute.addListener(self.object_listener)

    def get_value(self):
        return self._read_value()

    def set_value(self, new_value):
        self._write_value(new_value)

    def _write_value(self, new_value):
        self.attribute.write(new_value)

    def _read_value(self):
        value = self.attribute.read().value
        return value

    def get_info(self):
        try:
            b = dir(self.attribute)
            (
                self.info.minval,
                self.info.maxval,
            ) = self.attribute._TangoAttribute__attr_config.get_limits()
        except Exception:
            import traceback

            logging.getLogger("HWR").info("%s" % traceback.format_exc())
        return self.info

    def update(self, event):

        data = event.event[2]

        try:
            new_value = data.value

            if new_value is None:
                new_value = self.get_value()

            if isinstance(new_value, tuple):
                new_value = list(new_value)

            self.value = new_value
            self.emit("update", self.value)
        except AttributeError:
            # No value in data... this is probably a connection error
            pass

    def is_connected(self):
        return self.attribute is not None

    def channel_listener(self, *args):
        ev = AttributeEvent(args)
        SardanaChannel._eventReceivers[id(ev)] = saferef.safe_ref(self.update)
        SardanaChannel._eventsQueue.put(ev)
        SardanaChannel._eventsProcessingTimer.send()
