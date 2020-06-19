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

"""CommandContainer module

Classes:
- CommandContainer, a special mixin class to be used with
Hardware Objects. It defines a container
for command launchers and channels (see Command package).
- C*Object, command launcher & channel base class
"""

from __future__ import absolute_import

import weakref
import logging
from warnings import warn

from HardwareRepository.dispatcher import dispatcher


__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


class ConnectionError(Exception):
    pass

class CommandObject:
    def __init__(self, name, username=None, **kwargs):
        self._name = name
        self._username = username
        self._arguments = []
        self._combo_arguments_items = {}

    def name(self):
        return self._name

    def connect_signal(self, signal_name, callable_func):
        try:
            dispatcher.disconnect(callable_func, signal_name, self)
        except BaseException:
            pass
        dispatcher.connect(callable_func, signal_name, self)

    def emit(self, signal, *args):
        signal = str(signal)

        if len(args) == 1:
            if isinstance(args[0], tuple):
                args = args[0]

        dispatcher.send(signal, self, *args)

    def add_argument(
        self, argName, argType, combo_items=None, onchange=None, valuefrom=None
    ):
        arg_names = [arg[0] for arg in self._arguments]
        if argName not in arg_names:
            self._arguments.append((argName, argType.lower(), onchange, valuefrom))
        if combo_items is not None:
            self._combo_arguments_items[argName] = combo_items

    def get_arguments(self):
        return self._arguments

    def userName(self):
        return self._username or str(self.name())

    def is_connected(self):
        return False


class ChannelObject:
    def __init__(self, name, username=None, **kwargs):
        self._name = name
        self._username = username
        self._attributes = kwargs
        self._on_change = None
        self.__first_update = True

    def name(self):
        return self._name

    def connect_signal(self, signalName, callableFunc):
        try:
            dispatcher.disconnect(callableFunc, signalName, self)
        except BaseException:
            pass
        dispatcher.connect(callableFunc, signalName, self)

    def disconnect_signal(self, signalName, callableFunc):
        try:
            dispatcher.disconnect(callableFunc, signalName, self)
        except BaseException:
            pass

    def connect_notify(self, signal):
        if signal == "update" and self.is_connected():
            self.emit(signal, self.getValue())

    def emit(self, signal, *args):
        signal = str(signal)

        if len(args) == 1:
            if isinstance(args[0], tuple):
                args = args[0]

        dispatcher.send(signal, self, *args)

    def userName(self):
        return self._username or str(self.name())

    def is_connected(self):
        return False

    def update(self, value):
        if self.__first_update:
            self.__first_update = False
            return

        if self._on_change is not None:
            cmd, container_ref = self._on_change
            container = container_ref()
            if container is not None:
                cmdobj = container.get_command_object(cmd)
                if cmdobj is not None:
                    cmdobj(value)

    def get_value(self, force=False):
        raise NotImplementedError


class CommandContainer:
    """Mixin class for generic command and channel containers"""

    def __init__(self):
        self.__commands = {}
        self.__channels = {}
        self.__commands_to_add = []
        self.__channels_to_add = []

    def __getattr__(self, attr):
        try:
            return self.__dict__["_CommandContainer__commands"][attr]
        except KeyError:
            raise AttributeError(attr)

    def get_channel_object(self, channel_name, optional=False):
        channel = self.__channels.get(channel_name)
        if channel is None and not optional:
            msg = "%s: Unable to get channel %s" % (self.name(), channel_name)
            logging.getLogger("user_level_log").error(msg)
            # raise Exception(msg)
        return channel

    def get_channel_names_list(self):
        return list(self.__channels.keys())

    def add_channel(self, attributes_dict, channel, add_now=True):
        if not add_now:
            self.__channels_to_add.append((attributes_dict, channel))
            return
        channel_name = attributes_dict["name"]
        channel_type = attributes_dict["type"]
        channel_on_change = attributes_dict.get("onchange", None)
        if channel_on_change is not None:
            del attributes_dict["onchange"]
        channel_value_from = attributes_dict.get("valuefrom", None)
        if channel_value_from is not None:
            del attributes_dict["valuefrom"]
        channel_value_from = attributes_dict.get("valuefrom", None)
        del attributes_dict["name"]
        del attributes_dict["type"]

        new_channel = None
        if self.__channels.get(channel_name) is not None:
            return self.__channels[channel_name]

        if channel_type.lower() == "spec":
            if "version" not in attributes_dict:
                try:
                    attributes_dict["version"] = self.specversion
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Spec import SpecChannel

                new_channel = SpecChannel(channel_name, channel, **attributes_dict)
            except BaseException:
                logging.getLogger().error(
                    "%s: cannot add channel %s (hint: check attributes)",
                    self.name(),
                    channel_name,
                )
        elif channel_type.lower() == "taco":
            if "taconame" not in attributes_dict:
                try:
                    attributes_dict["taconame"] = self.taconame
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Taco import TacoChannel

                new_channel = TacoChannel(channel_name, channel, **attributes_dict)
            except BaseException:
                logging.getLogger().error(
                    "%s: cannot add channel %s (hint: check attributes)",
                    self.name(),
                    channel_name,
                )
        elif channel_type.lower() == "tango":
            if "tangoname" not in attributes_dict:
                try:
                    attributes_dict["tangoname"] = self.tangoname
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Tango import TangoChannel

                new_channel = TangoChannel(channel_name, channel, **attributes_dict)
            except ConnectionError:
                logging.getLogger().error(
                    "%s: could not connect to device server %s (hint: is it running ?)",
                    self.name(),
                    attributes_dict["tangoname"],
                )
                raise ConnectionError
            except BaseException:
                logging.getLogger().exception(
                    "%s: cannot add channel %s (hint: check attributes)",
                    self.name(),
                    channel_name,
                )
        elif channel_type.lower() == "exporter":
            if "exporter_address" not in attributes_dict:
                try:
                    attributes_dict["exporter_address"] = self.exporter_address
                except AttributeError:
                    pass
            host, port = attributes_dict["exporter_address"].split(":")

            try:
                attributes_dict["address"] = host
                attributes_dict["port"] = int(port)
                del attributes_dict["exporter_address"]

                from HardwareRepository.Command.Exporter import ExporterChannel

                new_channel = ExporterChannel(channel_name, channel, **attributes_dict)
            except BaseException:
                logging.getLogger().exception(
                    "%s: cannot add exporter channel %s (hint: check attributes)",
                    self.name(),
                    channel_name,
                )
        elif channel_type.lower() == "epics":
            try:
                from HardwareRepository.Command.Epics import EpicsChannel

                new_channel = EpicsChannel(channel_name, channel, **attributes_dict)
            except BaseException:
                logging.getLogger().exception(
                    "%s: cannot add EPICS channel %s (hint: check PV name)",
                    self.name(),
                    channel_name,
                )
        elif channel_type.lower() == "tine":
            if "tinename" not in attributes_dict:
                try:
                    attributes_dict["tinename"] = self.tinename
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Tine import TineChannel

                new_channel = TineChannel(channel_name, channel, **attributes_dict)
            except BaseException:
                logging.getLogger("HWR").exception(
                    "%s: cannot add TINE channel %s (hint: check attributes)",
                    self.name(),
                    channel_name,
                )

        elif channel_type.lower() == "sardana":

            if "taurusname" not in attributes_dict:
                try:
                    attributes_dict["taurusname"] = self.taurusname
                except AttributeError:
                    pass
            uribase = attributes_dict["taurusname"]

            try:
                from HardwareRepository.Command.Sardana import SardanaChannel

                logging.getLogger().debug(
                    "Creating a sardanachannel - %s / %s / %s",
                    self.name(),
                    channel_name,
                    str(attributes_dict),
                )
                new_channel = SardanaChannel(
                    channel_name, channel, uribase=uribase, **attributes_dict
                )
                logging.getLogger().debug("Created")
            except BaseException:
                logging.getLogger().exception(
                    "%s: cannot add SARDANA channel %s (hint: check PV name)",
                    self.name(),
                    channel_name,
                )

        elif channel_type.lower() == "mockup":
            if "default_value" not in attributes_dict:
                try:
                    attributes_dict["default_value"] = float(self.default_value)
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Mockup import MockupChannel

                new_channel = MockupChannel(channel_name, channel, **attributes_dict)
            except BaseException:
                logging.getLogger("HWR").exception(
                    "%s: cannot add Mockup channel %s (hint: check attributes)",
                    self.name(),
                    channel_name,
                )

        if new_channel is not None:
            if channel_on_change is not None:
                new_channel._on_change = (channel_on_change, weakref.ref(self))
            else:
                new_channel._on_change = None
            if channel_value_from is not None:
                new_channel._valuefrom = (channel_value_from, weakref.ref(self))
            else:
                new_channel._valuefrom = None

            self.__channels[channel_name] = new_channel

            return new_channel
        else:
            logging.getLogger().exception("Channel is None")

    def set_channel_value(self, channel_name, value):
        self.__channels[channel_name].set_value(value)

    def get_channel_value(self, channel_name):
        return self.__channels[channel_name].get_value()

    def get_channels(self):
        for chan in self.__channels.values():
            yield chan

    def get_command_object(self, cmd_name):
        try:
            return self.__commands.get(cmd_name)
        except Exception as e:
            return None

    def get_commands(self):
        for cmd in self.__commands.values():
            yield cmd

    def get_command_namesList(self):
        return list(self.__commands.keys())

    def add_command(self, arg1, arg2=None, add_now=True):
        if not add_now:
            self.__commands_to_add.append((arg1, arg2))
            return
        new_command = None

        if isinstance(arg1, dict):
            attributes_dict = arg1
            cmd = arg2

            cmd_name = attributes_dict["name"]
            cmd_type = attributes_dict["type"]
            del attributes_dict["name"]
            del attributes_dict["type"]
        else:
            attributes_dict = {}
            attributes_dict.update(arg1.get_properties())

            try:
                cmd_name = attributes_dict["name"]
                cmd_type = attributes_dict["type"]
                cmd = attributes_dict["toexecute"]
            except KeyError as err:
                logging.getLogger().error(
                    '%s: cannot add command: missing "%s" property',
                    self.name(),
                    err.args[0],
                )
                return
            else:
                del attributes_dict["name"]
                del attributes_dict["type"]
                del attributes_dict["toexecute"]

        if cmd_type.lower() == "spec":
            if "version" not in attributes_dict:
                try:
                    attributes_dict["version"] = self.specversion
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Spec import SpecCommand

                new_command = SpecCommand(cmd_name, cmd, **attributes_dict)
            except BaseException:
                logging.getLogger().exception(
                    '%s: could not add command "%s" (hint: check command attributes)',
                    self.name(),
                    cmd_name,
                )
        elif cmd_type.lower() == "taco":
            if "taconame" not in attributes_dict:
                try:
                    attributes_dict["taconame"] = self.taconame
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Taco import TacoCommand

                new_command = TacoCommand(cmd_name, cmd, **attributes_dict)
            except BaseException:
                logging.getLogger().exception(
                    '%s: could not add command "%s" (hint: check command attributes)',
                    self.name(),
                    cmd_name,
                )
        elif cmd_type.lower() == "tango":
            if "tangoname" not in attributes_dict:
                try:
                    attributes_dict["tangoname"] = self.tangoname
                except AttributeError:
                    pass
            try:
                from HardwareRepository.Command.Tango import TangoCommand

                new_command = TangoCommand(cmd_name, cmd, **attributes_dict)
            except ConnectionError:
                logging.getLogger().error(
                    "%s: could not connect to device server %s (hint: is it running ?)",
                    self.name(),
                    attributes_dict["tangoname"],
                )
                raise ConnectionError
            except BaseException:
                logging.getLogger().exception(
                    '%s: could not add command "%s" (hint: check command attributes)',
                    self.name(),
                    cmd_name,
                )

        elif cmd_type.lower() == "exporter":
            if "exporter_address" not in attributes_dict:
                try:
                    attributes_dict["exporter_address"] = self.exporter_address
                except AttributeError:
                    pass
            host, port = attributes_dict["exporter_address"].split(":")

            try:
                attributes_dict["address"] = host
                attributes_dict["port"] = int(port)
                del attributes_dict["exporter_address"]

                from HardwareRepository.Command.Exporter import ExporterCommand

                new_command = ExporterCommand(cmd_name, cmd, **attributes_dict)
            except BaseException:
                logging.getLogger().exception(
                    "%s: cannot add command %s (hint: check attributes)",
                    self.name(),
                    cmd_name,
                )
        elif cmd_type.lower() == "epics":
            try:
                from HardwareRepository.Command.Epics import EpicsCommand

                new_command = EpicsCommand(cmd_name, cmd, **attributes_dict)
            except BaseException:
                logging.getLogger().exception(
                    "%s: cannot add EPICS channel %s (hint: check PV name)",
                    self.name(),
                    cmd_name,
                )

        elif cmd_type.lower() == "sardana":

            doorname = None
            taurusname = None
            cmd_type = None
            door_first = False
            tango_first = False

            if "doorname" not in attributes_dict:
                try:
                    attributes_dict["doorname"] = self.doorname
                    doorname = self.doorname
                except AttributeError:
                    pass
            else:
                door_first = True
                doorname = attributes_dict["doorname"]

            if "taurusname" not in attributes_dict:
                try:
                    attributes_dict["taurusname"] = self.taurusname
                    taurusname = self.taurusname
                except AttributeError:
                    pass
            else:
                tango_first = True
                taurusname = attributes_dict["taurusname"]

            if "cmd_type" in attributes_dict:
                cmd_type = attributes_dict["cmd_type"]

            # guess what kind of command to create
            if cmd_type is None:
                if taurusname is not None and doorname is None:
                    cmd_type = "command"
                elif doorname is not None and taurusname is None:
                    cmd_type = "macro"
                elif doorname is not None and taurusname is not None:
                    if door_first:
                        cmd_type = "macro"
                    elif tango_first:
                        cmd_type = "command"
                    else:
                        cmd_type = "macro"
                else:
                    logging.getLogger().error(
                        "%s: incomplete sardana command declaration. ignored",
                        self.name(),
                    )

            from HardwareRepository.Command.Sardana import SardanaCommand, SardanaMacro

            if cmd_type == "macro" and doorname is not None:
                try:
                    new_command = SardanaMacro(cmd_name, cmd, **attributes_dict)
                except ConnectionError:
                    logging.getLogger().error(
                        "%s: could not connect to sardana door %s (hint: is it running ?)",
                        self.name(),
                        attributes_dict["doorname"],
                    )
                    raise ConnectionError
                except BaseException:
                    logging.getLogger().exception(
                        '%s: could not add command "%s" (hint: check command attributes)',
                        self.name(),
                        cmd_name,
                    )
            elif cmd_type == "command" and taurusname is not None:
                try:
                    new_command = SardanaCommand(cmd_name, cmd, **attributes_dict)
                except ConnectionError:
                    logging.getLogger().error(
                        "%s: could not connect to sardana device %s (hint: is it running ?)",
                        self.name(),
                        taurusname,
                    )
                    raise ConnectionError
                except BaseException:
                    logging.getLogger().exception(
                        '%s: could not add command "%s" (hint: check command attributes)',
                        self.name(),
                        cmd_name,
                    )
            else:
                logging.getLogger().error(
                    "%s: incomplete sardana command declaration. ignored", self.name()
                )

        elif cmd_type.lower() == "pool":
            if "tangoname" not in attributes_dict:
                try:
                    attributes_dict["tangoname"] = self.tangoname
                except AttributeError:
                    pass
            try:
                from HardwareRepository.Command.Pool import PoolCommand

                new_command = PoolCommand(cmd_name, cmd, **attributes_dict)
            except ConnectionError:
                logging.getLogger().error(
                    "%s: could not connect to device server %s (hint: is it running ?)",
                    self.name(),
                    attributes_dict["tangoname"],
                )
                raise ConnectionError
            except BaseException:
                logging.getLogger().exception(
                    '%s: could not add command "%s" (hint: check command attributes)',
                    self.name(),
                    cmd_name,
                )
        elif cmd_type.lower() == "tine":
            if "tinename" not in attributes_dict:
                try:
                    attributes_dict["tinename"] = self.tinename
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Tine import TineCommand

                new_command = TineCommand(cmd_name, cmd, **attributes_dict)
            except BaseException:
                logging.getLogger().exception(
                    '%s: could not add command "%s" (hint: check command attributes)',
                    self.name(),
                    cmd_name,
                )

        elif cmd_type.lower() == "mockup":
            try:
                from HardwareRepository.Command.Mockup import MockupCommand

                new_command = MockupCommand(cmd_name, cmd, **attributes_dict)
            except BaseException:
                logging.getLogger().exception(
                    '%s: could not add command "%s" (hint: check command attributes)',
                    self.name(),
                    cmd_name,
                )

        if new_command is not None:
            self.__commands[cmd_name] = new_command

            if not isinstance(arg1, dict):
                i = 1
                for arg in arg1.get_objects("argument"):
                    on_change = arg.get_property("onchange")
                    if on_change is not None:
                        on_change = (on_change, weakref.ref(self))
                    value_from = arg.get_property("valuefrom")
                    if value_from is not None:
                        value_from = (value_from, weakref.ref(self))

                    try:
                        combo_items = arg["type"]["item"]
                    except IndexError:
                        try:
                            new_command.add_argument(
                                arg.get_property("name"),
                                arg.type,
                                onchange=on_change,
                                valuefrom=value_from,
                            )
                        except AttributeError:
                            logging.getLogger().error(
                                '%s, command "%s": could not add argument %d, missing type or name',
                                self.name(),
                                cmd_name,
                                i,
                            )
                            continue
                    else:
                        if isinstance(combo_items, list):
                            combo_items = []
                            for item in combo_items:
                                name = item.get_property("name")
                                value = item.get_property("value")
                                if name is None or value is None:
                                    logging.getLogger().error(
                                        "%s, command '%s': could not add argument %d, missing combo item name or value",
                                        self.name(),
                                        cmd_name,
                                        i,
                                    )
                                    continue
                                else:
                                    combo_items.append((name, value))
                        else:
                            name = combo_items.get_property("name")
                            value = combo_items.get_property("value")
                            if name is None or value is None:
                                combo_items = ((name, value),)
                            else:
                                logging.getLogger().error(
                                    "%s, command '%s': could not add argument %d, missing combo item name or value",
                                    self.name(),
                                    cmd_name,
                                    i,
                                )
                                continue

                        new_command.add_argument(
                            arg.get_property("name"),
                            "combo",
                            combo_items,
                            on_change,
                            value_from,
                        )

                    i += 1

            return new_command

    def _add_channels_and_commands(self):
        [self.add_channel(*args) for args in self.__channels_to_add]
        [self.add_command(*args) for args in self.__commands_to_add]
        self.__channels_to_add = []
        self.__commands_to_add = []

    def execute_command(self, command_name, *args, **kwargs):
        if command_name in self.__commands:
            return self.__commands[command_name](*args, **kwargs)
        else:
            raise AttributeError
