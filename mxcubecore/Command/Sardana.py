#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import

import logging
import os
from .. import saferef

import gevent
from gevent.event import Event
from gevent import monkey 
import Queue

from ..CommandContainer import CommandObject, ChannelObject, ConnectionError

from PyTango import DevFailed, ConnectionFailed
import PyTango

try:
    from sardana.taurus.core.tango.sardana import registerExtensions
    from taurus import Device, Attribute
    import taurus
    from taurus.core.tango.enums import DevState
    from taurus.core.tango.tangoattribute import TangoAttrValue
    """
    ON = 0
    OFF = 1
    CLOSE = 2
    OPEN = 3
    INSERT = 4
    EXTRACT = 5
    MOVING = 6
    STANDBY = 7
    FAULT = 8
    INIT = 9
    RUNNING = 10
    ALARM = 11
    DISABLE = 12
    UNKNOWN = 13

    """
except Exception as e:
    logging.getLogger('HWR').warning("%s" % str(e))

monkey.patch_all(thread=False, subprocess=False)


def process_sardana_events():

    while not SardanaObject._eventsQueue.empty():

        try:
            ev = SardanaObject._eventsQueue.get_nowait()
        except Queue.Empty:
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


# def waitEndOfCommand(cmd_obj):
#     while (cmd_obj.macrostate == SardanaMacro.RUNNING or
#            cmd_obj.macrostate == SardanaMacro.STARTED):
#         gevent.sleep(0.05)
#     return cmd_obj.door.result


def end_of_macro(macro_obj):
    macro_obj._reply_arrived_event.wait()


class AttributeEvent:
    def __init__(self, event):
        self.event = event


class SardanaObject(object):
    _eventsQueue = Queue.Queue()
    _eventReceivers = {}
    _eventsProcessingTimer = gevent.get_hub().loop.async()
    _eventsProcessingTimer.start(process_sardana_events)

    def listener_obj(self, *args):
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
        self.door_name = doorname
        self.door = None
        self.init_device()
        self.macro_state = SardanaMacro.INIT
        self.door_state = None
        self.t0 = 0
        self.result = None

    def init_device(self): 
        self.door = Device(self.door_name)
        self.door.set_timeout_millis(10000)

        if self.macroStatusAttr is None:
            self.macroStatusAttr = self.door.getAttribute("State")
            self.macroStatusAttr.addListener(self.listener_obj)

    def __call__(self, *args, **kwargs):

        self._reply_arrived_event.clear()
        self.result = None

        wait = kwargs.get('wait', False)

        if self.door is None:
            self.init_device()

        logging.getLogger('HWR').debug("Running Sardana macro: %s" % self.macro_format)
        logging.getLogger('HWR').debug("args=%s / kwargs=%s" % (str(args), str(kwargs)))
        
        try:
            full_cmd = self.macro_format + " " + " ".join([str(a) for a in args])
        except Exception as e:
            import traceback
            logging.getLogger('HWR').info("%s" % str(e))
            logging.getLogger('HWR').info("Wrong format for macro arguments."
                                          "Macro is %s / args are (%s)" %
                                          (self.macro_format, str(args)))
            return
   
        try:
            import time
            self.t0 = time.time()
            if self.door_state in [DevState.ON, DevState.ALARM]:
                self.door.runMacro(full_cmd.split())
                self.macro_state = SardanaMacro.STARTED
                self.emit('commandBeginWaitReply', (str(self.name()), ))
            else:
                logging.getLogger('HWR').error("%s. Cannot execute. Door is not READY",
                                               str(self.name()) )
                logging.getLogger('HWR').error("Door state is %s" % self.door_state)
                self.emit('commandFailed', (-1, self.name()))
        except TypeError:
            logging.getLogger('HWR').error("%s. Cannot properly format macro code."
                                           "Format is: %s, args are %s",
                                           str(self.name()),
                                           self.macro_format, str(args))
            self.emit('commandFailed', (-1, self.name()))
        except DevFailed as e:
            logging.getLogger('HWR').error("%s: Cannot run macro. %s",
                                           str(self.name()), str(e))
            self.emit('commandFailed', (-1, self.name()))
        except AttributeError as e:
            logging.getLogger('HWR').error("%s: MacroServer not running?, %s",
                                           str(self.name()), str(e))
            self.emit('commandFailed', (-1, self.name()))
        except Exception as e:
            logging.getLogger('HWR').exception("%s: an error occurred when calling"
                                               "Tango command %s", str(self.name()),
                                               self.macro_format)
            self.emit('commandFailed', (-1, self.name()))

        if wait:
            logging.getLogger('HWR').debug("... start waiting...")
            t = gevent.spawn(end_of_macro, self)
            t.get()
            logging.getLogger('HWR').debug("... end waiting...")

        return 

    def update(self, event):
        data = event.event[2]

        try:
            if type(data) != PyTango.DeviceAttribute and type(data) != TangoAttrValue:
                # logging.getLogger('HWR').debug("*** Event type %s" % type(data))
                # logging.getLogger('HWR').debug("*** Event value %s" % str(data.value))
                return

            # Handling macro state changed event
            door_state = data.rvalue
            logging.getLogger('HWR').debug("doorstate changed, now is %s"
                                           % str(door_state))

            if door_state != self.door_state:
                self.door_state = door_state
                self.emit('commandCanExecute', (self.canExecute(),))

                if door_state in [DevState.ON, DevState.ALARM]:
                    self.emit('commandReady', ())
                else:
                    self.emit('commandNotReady', ())
            
            if (self.macro_state == SardanaMacro.STARTED and
                    door_state == DevState.RUNNING):
                self.macro_state = SardanaMacro.RUNNING
            elif (self.macro_state == SardanaMacro.RUNNING and
                  (door_state in [DevState.ON, DevState.ALARM])):
                logging.getLogger('HWR').debug("Macro execution finished")
                self.macro_state = SardanaMacro.DONE
                self.result = self.door.result
                self.emit('commandReplyArrived', (self.result, str(self.name())))
                if door_state == DevState.ALARM:
                    self.emit('commandAborted', (str(self.name()), ))
                self._reply_arrived_event.set()
            elif (self.macro_state == SardanaMacro.DONE or
                  self.macro_state == SardanaMacro.INIT):
                # already handled in the general case above
                pass
            else:
                logging.getLogger('HWR').debug("Macroserver state changed")
                self.emit('commandFailed', (-1, str(self.name())))
        except ConnectionFailed:
            logging.getLogger('HWR').debug("Cannot connect to door %s" % self.door_name)
            self.emit('commandFailed', (-1, str(self.name())))
        except Exception as e:
            logging.getLogger('HWR').debug("Sardana Macro / event handling problem. %s"
                                           % str(e))
            self.emit('commandFailed', (-1, str(self.name())))

    def abort(self):
        if self.door is not None:
            logging.getLogger('HWR').debug("Sardana Macro / aborting macro")
            self.door.abortMacro()

    def isConnected(self):
        return self.door is not None

    def canExecute(self):
        return self.door is not None and (self.door_state in ["ON", "ALARM"])

    
class SardanaCommand(CommandObject):

    def __init__(self, name, command, taurusname=None, username=None, **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)
        
        self.command = command
        self.taurus_name = taurusname
        self.device = None    

    def init_device(self): 

        try:
            self.device = Device(self.taurus_name)
        except DevFailed as e:
            last_error = e[-1]
            logging.getLogger('HWR').error("%s: %s",
                                           str(self.name()), last_error['desc'])
            self.device = None
        else:
            try:
                self.device.ping()
            except ConnectionFailed:
                self.device = None
                raise ConnectionError

    def __call__(self, *args, **kwargs):

        self.emit('commandBeginWaitReply', (str(self.name()), ))

        if self.device is None:
            self.init_device()

        try:
            cmd_object = getattr(self.device, self.command)
            ret = cmd_object(*args)
        except DevFailed as e:
            logging.getLogger('HWR').error("%s: Tango, %s", str(self.name()), str(e))
        except Exception as e:
            logging.getLogger('HWR').exception("%s: an error occurred when calling"
                                               " Sardana command %s", str(self.name()),
                                               self.command)
        else:
            self.emit('commandReplyArrived', (ret, str(self.name())))
            return ret
        self.emit('commandFailed', (-1, self.name()))

    def abort(self):
        pass
        
    def isConnected(self):
        return self.device is not None


class SardanaChannel(ChannelObject, SardanaObject):

    def __init__(self, name, attribute_name, username=None, uribase=None, polling=None,
                 **kwargs):

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

        except DevFailed as e:
            logging.getLogger('HWR').error('Cannot create attribute\n%s' % str(e))
            return
        
        # read information
        try:
            if taurus.Release.version_info[0] == 3:
                ranges = self.attribute.getConfig().getRanges()
                if ranges is not None and ranges[0] != "Not specified":
                    self.info.minval = float(ranges[0])
                if ranges is not None and ranges[-1] != "Not specified":
                    self.info.maxval = float(ranges[-1])
            elif taurus.Release.version_info[0] > 3:   # taurus 4 and beyond
                try:
                    range = getattr(self.attribute, 'range')
                    if all(range):
                        self.info.minval = range[0].magnitude
                        self.info.maxval = range[1].magnitude
                except Exception as ee:
                    logging.getLogger("HWR").error("Exception trying to get range\n%s" %
                                                   str(ee))
        except Exception as e:
            logging.getLogger("HWR").info("info initialized. Cannot get limits")
            logging.getLogger("HWR").info("%s" % str(e))

        # prepare polling
        if self.polling:
            if isinstance(self.polling, int):
                self.attribute.changePollingPeriod(self.polling)
             
            self.attribute.addListener(self.listener_obj)
                  
    def getValue(self):
        return self._readValue()

    def setValue(self, new_value):
        self._writeValue(new_value)
 
    def _writeValue(self, new_value):
        self.attribute.write(new_value)
            
    def _readValue(self):
        value = None
        if taurus.Release.version_info[0] == 3:
            value = self.attribute.read().value
        elif taurus.Release.version_info[0] > 3:  # taurus 4 and beyond
            try:
                magnitude = getattr(self.attribute.rvalue, 'magnitude')
                value = magnitude
            except Exception:
                value = self.attribute.rvalue
        return value
            
    def getInfo(self):
        try:
            if taurus.Release.version_info[0] == 3:
                ranges = self.attribute.getConfig().getRanges()
                if ranges is not None and ranges[0] != "Not specified":
                    self.info.min_val = float(ranges[0])
                if ranges is not None and ranges[-1] != "Not specified":
                    self.info.max_val = float(ranges[-1])
            elif taurus.Release.version_info[0] > 3:   # taurus 4 and beyond
                try:
                    range = getattr(self.attribute, 'range')
                    self.info.min_val = range[0].magnitude
                    self.info.max_val = range[1].magnitude
                except Exception as e:
                    logging.getLogger("HWR").debug("Range not defined for {0}".
                                                   format(self.attribute.fullname))
                    logging.getLogger("HWR").info("%s" % str(e))

        except Exception as e:
            logging.getLogger("HWR").info("info initialized. Cannot get limits")
            logging.getLogger("HWR").info("%s" % str(e))
        return self.info

    def update(self, event):
        data = event.event[2]
        new_value = None
        try:
            if taurus.Release.version_info[0] == 3:
                new_value = data.value
            elif taurus.Release.version_info[0] > 3:  # taurus 4 and beyond
                try:
                    new_value = data.rvalue.magnitude
                except Exception:
                    new_value = data.rvalue

            if new_value is None:
                new_value = self.getValue()
    
            if isinstance(new_value, ()):
                new_value = list(new_value)
    
            self.value = new_value
            self.emit('update', self.value)
        except AttributeError:
            # No value in data... this is probably a connection error
            pass

    def isConnected(self):
        return self.attribute is not None
