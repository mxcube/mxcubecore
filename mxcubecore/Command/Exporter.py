# -*- coding: utf-8 -*-
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Exporter, ExporterChannel and ExporterCommand implementation """

# from warnings import warn
import logging

import gevent
from gevent.queue import Queue

from mxcubecore.CommandContainer import (
    ChannelObject,
    CommandObject,
)

from .exporter import ExporterClient
from .exporter.StandardClient import PROTOCOL

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"

EXPORTER_CLIENTS = {}


def start_exporter(address, port, timeout=3, retries=1):
    """Start the exporter"""
    global EXPORTER_CLIENTS
    if (address, port) not in EXPORTER_CLIENTS:
        client = Exporter(address, port, timeout)
        EXPORTER_CLIENTS[(address, port)] = client
        client.start()
        return client
    return EXPORTER_CLIENTS[(address, port)]


class Exporter(ExporterClient.ExporterClient, object):
    """Exporter class"""

    STATE_EVENT = "State"
    STATUS_EVENT = "Status"
    VALUE_EVENT = "Value"
    POSITION_EVENT = "Position"
    MOTOR_STATES_EVENT = "MotorStates"

    STATE_READY = "Ready"
    STATE_INITIALIZING = "Initializing"
    STATE_STARTING = "Starting"
    STATE_RUNNING = "Running"
    STATE_MOVING = "Moving"
    STATE_CLOSING = "Closing"
    STATE_REMOTE = "Remote"
    STATE_STOPPED = "Stopped"
    STATE_COMMUNICATION_ERROR = "Communication Error"
    STATE_INVALID = "Invalid"
    STATE_OFFLINE = "Offline"
    STATE_ALARM = "Alarm"
    STATE_FAULT = "Fault"
    STATE_UNKNOWN = "Unknown"

    def __init__(self, address, port, timeout=3, retries=1):
        super(Exporter, self).__init__(address, port, PROTOCOL.STREAM, timeout, retries)

        self.started = False
        self.callbacks = {}
        self.events_queue = Queue()
        self.events_processing_task = None

    def start(self):
        """Start"""

    def stop(self):
        """Stop"""
        self.disconnect()

    def execute(self, *args, **kwargs):
        """Execute"""
        ret = ExporterClient.ExporterClient.execute(self, *args, **kwargs)
        return self._to_python_value(ret)

    def get_state(self):
        """Read the state"""
        return self.execute("getState")

    def read_property(self, *args, **kwargs):
        """Read a property"""
        ret = ExporterClient.ExporterClient.read_property(self, *args, **kwargs)
        return self._to_python_value(ret)

    def reconnect(self):
        """Reconnect"""
        return

    def on_disconnected(self):
        """Actions on disconnect"""

    def register(self, name, cb):
        """Register to a callback"""
        if callable(cb):
            self.callbacks.setdefault(name, []).append(cb)
        if not self.events_processing_task:
            self.events_processing_task = gevent.spawn(self.process_events_from_queue)

    def _to_python_value(self, value):
        """Convert exporter value to python one
        Args:
            value (str): String from the exporter
        """
        if value is None:
            return value

        if "\x1f" in value:
            value = self.parse_array(value)
            try:
                value = list(map(int, value))
            except (TypeError, ValueError):
                try:
                    value = list(map(float, value))
                except (TypeError, ValueError):
                    pass
        else:
            if value == "false":
                value = False
            elif value == "true":
                value = True
            else:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        pass
        return value

    def on_event(self, name, value, timestamp):
        """Put the event in the queue
        Args:
            name: Name
            value: Value
            timestamp: Timestamp
        """
        self.events_queue.put((name, value))

    def process_events_from_queue(self):
        """Process events from the queue"""
        while True:
            try:
                name, value = self.events_queue.get()
            except Exception:
                return

            for cb in self.callbacks.get(name, []):
                try:
                    cb(self._to_python_value(value))
                except Exception:
                    msg = "Exception while executing callback {} for event {}".format(
                        cb, name
                    )
                    logging.exception(msg)
                    continue


class ExporterCommand(CommandObject):
    """Command implementation for Exporter"""

    def __init__(
        self, name, command, username=None, address=None, port=None, timeout=3, **kwargs
    ):
        CommandObject.__init__(self, name, username, **kwargs)
        self.command = command
        self.__exporter = start_exporter(address, port, timeout)
        msg = "Attaching Exporter command: {} {}".format(address, name)
        logging.getLogger("HWR").debug(msg)

    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))

        try:
            ret = self.__exporter.execute(self.command, args, kwargs.get("timeout", -1))
        except Exception:
            self.emit("commandFailed", (-1, self.name()))
            raise
        else:
            self.emit("commandReplyArrived", (ret, str(self.name())))
            return ret

    def abort(self):
        """Abort"""

    def get_state(self):
        """FRead the state
        Returns:
            (str): State
        """
        return self.__exporter.get_state()

    def is_connected(self):
        """Check if connected.
        Returns:
            (bool): True if connected
        """
        return self.__exporter.is_connected()


class ExporterChannel(ChannelObject):
    """Channel implementation for Exporter"""

    def __init__(
        self,
        name,
        attribute_name,
        username=None,
        address=None,
        port=None,
        timeout=3,
        **kwargs
    ):
        ChannelObject.__init__(self, name, username, **kwargs)

        self.__exporter = start_exporter(address, port, timeout)
        self.attribute_name = attribute_name
        self.value = None

        self.__exporter.register(attribute_name, self.update)

        msg = "Attaching Exporter channel: {} {} ".format(address, name)
        logging.getLogger("HWR").debug(msg)

        self.update()

    def update(self, value=None):
        """Emit signal update when value changed"""
        value = value or self.get_value()
        if isinstance(value, tuple):
            value = list(value)

        self.value = value
        self.emit("update", value)

    def get_value(self):
        """Get the value
        Returns:
            (str): The value
        """
        value = self.__exporter.read_property(self.attribute_name)
        return value

    def set_value(self, value):
        """Set a value
        Args:
            value (str): Value to set
        """
        self.__exporter.write_property(self.attribute_name, value)

    def is_connected(self):
        """Check if connected.
        Returns:
            (bool): True if connected.
        """
        return self.__exporter.is_connected()
