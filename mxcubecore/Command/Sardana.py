from __future__ import absolute_import

import logging
import os
import time
import types
from .. import saferef

import gevent
from gevent.event import Event
from gevent import monkey
import Queue

from HardwareRepository.CommandContainer import (
    CommandObject,
    ChannelObject,
    ConnectionError,
)

from PyTango import DevFailed, ConnectionFailed
import PyTango

# from HardwareRepository.TaskUtils import task

try:
    from sardana.taurus.core.tango.sardana import registerExtensions
    from taurus import Device, Attribute
    import taurus
except BaseException:
    logging.getLogger("HWR").warning("Sardana is not available in this computer.")

monkey.patch_all(thread=False, subprocess=False)


def processSardanaEvents():

    while not SardanaObject._eventsQueue.empty():

        try:
            ev = SardanaObject._eventsQueue.get_nowait()
        except Queue.Empty:
            break
        else:
            try:
                receiverCbRef = SardanaObject._eventReceivers[id(ev)]
                receiverCb = receiverCbRef()
                if receiverCb is not None:
                    try:
                        gevent.spawn(receiverCb, ev)
                    except AttributeError:
                        pass
            except KeyError:
                pass


def waitEndOfCommand(cmdobj):
    while (
        cmdobj.macrostate == SardanaMacro.RUNNING
        or cmdobj.macrostate == SardanaMacro.STARTED
    ):
        gevent.sleep(0.05)
    return cmdobj.door.result


def endOfMacro(macobj):
    macobj._reply_arrived_event.wait()


class AttributeEvent:
    def __init__(self, event):
        self.event = event


class SardanaObject(object):
    _eventsQueue = Queue.Queue()
    _eventReceivers = {}
    _eventsProcessingTimer = gevent.get_hub().loop.async()

    # start Sardana events processing timer
    _eventsProcessingTimer.start(processSardanaEvents)

    def objectListener(self, *args):
        ev = AttributeEvent(args)
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
            self.macroStatusAttr.addListener(self.objectListener)

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
        except BaseException:
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
        except BaseException:
            logging.getLogger("HWR").exception(
                "%s: an error occured when calling Tango command %s",
                str(self.name()),
                self.macro_format,
            )
            self.emit("commandFailed", (-1, self.name()))

        if wait:
            logging.getLogger("HWR").debug("... start waiting...")
            t = gevent.spawn(endOfMacro, self)
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
                self.emit("commandCanExecute", (self.canExecute(),))

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
        except BaseException:
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

    def isConnected(self):
        return self.door is not None

    def canExecute(self):
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
        except BaseException:
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

    def isConnected(self):
        return self.device is not None


class SardanaChannel(ChannelObject, SardanaObject):
    def __init__(
        self, name, attribute_name, username=None, uribase=None, polling=None, **kwargs
    ):

        super(SardanaChannel, self).__init__(name, username, **kwargs)

        class ChannelInfo(object):
            def __init__(self):
                super(ChannelInfo, self).__init__()

        self.attributeName = attribute_name
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
        except BaseException:
            import traceback

            logging.getLogger("HWR").info("info initialized. Cannot get limits")
            logging.getLogger("HWR").info("%s" % traceback.format_exc())

        # prepare polling
        # if the polling value is a number set it as the taurus polling period

        if self.polling:
            if isinstance(self.polling, int):
                self.attribute.changePollingPeriod(self.polling)

            self.attribute.addListener(self.objectListener)

    def getValue(self):
        return self._readValue()

    def setValue(self, newValue):
        self._writeValue(newValue)

    def _writeValue(self, newValue):
        self.attribute.write(newValue)

    def _readValue(self):
        value = self.attribute.read().value
        return value

    def getInfo(self):
        try:
            b = dir(self.attribute)
            (
                self.info.minval,
                self.info.maxval,
            ) = self.attribute._TangoAttribute__attr_config.get_limits()
        except BaseException:
            import traceback

            logging.getLogger("HWR").info("%s" % traceback.format_exc())
        return self.info

    def update(self, event):

        data = event.event[2]

        try:
            newvalue = data.value

            if newvalue is None:
                newvalue = self.getValue()

            if isinstance(newvalue, types.TupleType):
                newvalue = list(newvalue)

            self.value = newvalue
            self.emit("update", self.value)
        except AttributeError:
            # No value in data... this is probably a connection error
            pass

    def isConnected(self):
        return self.attribute is not None

    def channelListener(self, *args):
        ev = AttributeEvent(args)
        SardanaChannel._eventReceivers[id(ev)] = saferef.safe_ref(self.update)
        SardanaChannel._eventsQueue.put(ev)
        SardanaChannel._eventsProcessingTimer.send()
