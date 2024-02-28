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
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

import weakref
import logging

from mxcubecore.dispatcher import dispatcher


__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"

PROCEDURE_COMMAND_T = "CONTROLLER"
TWO_STATE_COMMAND_T = "INOUT"

ARGUMENT_TYPE_LIST = "List"
ARGUMENT_TYPE_JSON_SCHEMA = "JSONSchema"


class ConnectionError(Exception):
    """General Connection Error"""


class CommandObject:
    def __init__(self, name: str, username: Optional[str] = None, **kwargs) -> None:
        """
        Args:
            name (str): Name.
            username (Optional[str], optional): User name. Defaults to None.
        """
        self._name: str = name
        self._username: Union[str, None] = username
        self._arguments: Union[List[Tuple[str, str, Any, Any]], Any] = []
        self._combo_arguments_items: Dict[str, Any] = {}

        self.type: str = PROCEDURE_COMMAND_T
        self.argument_type: str = ARGUMENT_TYPE_LIST

    def set_argument_json_schema(self, json_schema_str: Any) -> None:
        """Set the JSON Schema.

        Args:
            json_schema_str (Any): JSON Schema.
        """
        self.argument_type = ARGUMENT_TYPE_JSON_SCHEMA
        self._arguments = json_schema_str

    def name(self) -> str:
        """Get command name.

        Returns:
            str: Command name.
        """
        return self._name

    def connect(self, signal_name: str, callable_func: Callable) -> None:
        """Connect to signal.

        Args:
            signal_name (str): Signal name.
            callable_func (Callable): Connection method.
        """
        try:
            dispatcher.disconnect(callable_func, signal_name, self)
        except Exception:
            pass
        dispatcher.connect(callable_func, signal_name, self)

    def emit(self, signal: str, *args) -> None:
        """Emit signal message.

        Args:
            signal (str): Signal name.
            *args (tuple): Message arguments.
        """
        signal = str(signal)

        if len(args) == 1:
            if isinstance(args[0], tuple):
                args = args[0]

        dispatcher.send(signal, self, *args)

    def add_argument(
        self,
        argName: str,
        argType: str,
        combo_items: Optional[Any] = None,
        onchange: Optional[Any] = None,
        valuefrom: Optional[Any] = None,
    ) -> None:
        """Add command argument.

        Args:
            argName (str): Name.
            argType (str): Type.
            combo_items (Optional[Any], optional): Combo items. Defaults to None.
            onchange (Optional[Any], optional): On change. Defaults to None.
            valuefrom (Optional[Any], optional): Value from. Defaults to None.
        """
        arg_names = [arg[0] for arg in self._arguments]
        if argName not in arg_names:
            self._arguments.append((argName, argType.lower(), onchange, valuefrom))
        if combo_items is not None:
            self._combo_arguments_items[argName] = combo_items

    def get_arguments(self) -> Union[List[Tuple[str, str, Any, Any]], Any]:
        """Get command arguments.

        Returns:
            Union[List[Tuple[str, str, Any, Any]], Any]: Command arguments.
        """
        return self._arguments

    def get_combo_argument_items(self, argName: str) -> Any:
        """Get combo argument items.

        Args:
            argName (str): Combo argument name.

        Returns:
            Any: Combo argument value.
        """
        return self._combo_arguments_items[argName]

    def userName(self) -> str:
        """Get user name.

        Returns:
            str: User name.
        """
        return self._username or str(self.name())

    def is_connected(self) -> bool:
        """Check if signal is connected.

        Returns:
            bool: True if connected, else False.
        """
        return False


class ChannelObject:
    def __init__(self, name: str, username: Optional[str] = None, **kwargs) -> None:
        """
        Args:
            name (str): Name.
            username (Optional[str], optional): User name. Defaults to None.
        """
        self._name: str = name
        self._username: Union[str, None] = username
        self._attributes: Dict[str, Any] = kwargs
        self._on_change: Union[
            Tuple[str, weakref.ref],
            None,
        ] = None
        self.__first_update: bool = True

    def name(self) -> str:
        """Get channel name.

        Returns:
            str: Channel name.
        """
        return self._name

    def connect_signal(self, signalName: str, callableFunc: Callable) -> None:
        """Connect signal.

        Args:
            signalName (str): Signal name.
            callableFunc (Callable): Connection method.
        """
        try:
            dispatcher.disconnect(callableFunc, signalName, self)
        except Exception:
            pass
        dispatcher.connect(callableFunc, signalName, self)

    def disconnect_signal(self, signalName: str, callableFunc: Callable) -> None:
        """Disconnect signal.

        Args:
            signalName (str): Signal name.
            callableFunc (Callable): Disconnection method.
        """
        try:
            dispatcher.disconnect(callableFunc, signalName, self)
        except Exception:
            pass

    def connect_notify(self, signal: str) -> None:
        """Connection notifier.

        Args:
            signal (str): Signal name.
        """
        if signal == "update" and self.is_connected():
            self.emit(signal, self.get_value())

    def emit(self, signal: str, *args) -> None:
        """Emit signal message.

        Args:
            signal (str): Signal name.
            *args (tuple): Message arguments.
        """
        signal = str(signal)

        if len(args) == 1:
            if isinstance(args[0], tuple):
                args = args[0]

        dispatcher.send(signal, self, *args)

    def userName(self) -> str:
        """Get user name.

        Returns:
            str: User name.
        """
        return self._username or str(self.name())

    def is_connected(self) -> bool:
        """Check if signal is connected.

        Returns:
            bool: True if connected, else False.
        """
        return False

    def update(self, value: Any) -> None:
        """Update command object.

        Args:
            value (Any): Updated value.
        """
        if self.__first_update:
            self.__first_update = False
            return

        if self._on_change is not None:
            cmd, container_ref = self._on_change
            container: "CommandContainer" = container_ref()
            if container is not None:
                cmdobj = container.get_command_object(cmd)
                if cmdobj is not None:
                    cmdobj(value)

    def get_value(self, force: bool = False):
        """Get channel value.

        Args:
            force (bool, optional): Force get value. Defaults to False.

        Raises:
            NotImplementedError: If method has not been implemented for this object.
        """
        # NBNB INCONSISTENT. funcxtion signature matches only
        # Tine and Mockup, but is inconsistent with other subclasses
        raise NotImplementedError


class CommandContainer:
    """Mixin class for generic command and channel containers"""

    def __init__(self) -> None:
        self.__commands: Dict[str, CommandObject] = {}
        self.__channels: Dict[str, ChannelObject] = {}
        self.__commands_to_add: List[Tuple[Dict[str, Any], Union[str, None]]] = []
        self.__channels_to_add: List[Tuple[Dict[str, Any], str]] = []

    def __getattr__(self, attr: str) -> CommandObject:
        try:
            return self.__dict__["_CommandContainer__commands"][attr]
        except KeyError:
            raise AttributeError(attr)

    def get_channel_object(
        self,
        channel_name: str,
        optional: bool = False,
    ) -> Union[ChannelObject, None]:
        """Get channel.

        Args:
            channel_name (str): Channel name.
            optional (bool, optional): If a missing channel should be logged
            as an error. Defaults to False.

        Returns:
            Union[ChannelObject, None]: Channel object or None if not found.
        """
        channel = self.__channels.get(channel_name)
        if channel is None and not optional:
            msg = "%s: Unable to get channel %s" % (self.name(), channel_name)
            logging.getLogger("user_level_log").error(msg)
            # raise Exception(msg)
        return channel

    def get_channel_names_list(self) -> List[str]:
        """Get a list of all channel names.

        Returns:
            List[str]: Channel names.
        """
        return list(self.__channels.keys())

    def add_channel(
        self,
        attributes_dict: Dict[str, Any],
        channel: str,
        add_now: bool = True,
    ) -> Union[ChannelObject, None]:
        """Add channel.

        Args:
            attributes_dict (Dict[str, Any]): Channel attributes.
            channel (str): Channel name.
            add_now (bool, optional): Whether the channel should be added now.
            Defaults to True.

        Raises:
            ConnectionError: If a connection error occured while adding the channel.

        Returns:
            Union[ChannelObject, None]: Channel object or None if adding later.
        """
        if not add_now:
            self.__channels_to_add.append((attributes_dict, channel))
            return
        channel_name: str = attributes_dict["name"]
        channel_type: str = attributes_dict["type"]
        channel_on_change: Union[Any, None] = attributes_dict.get("onchange", None)
        if channel_on_change is not None:
            del attributes_dict["onchange"]
        channel_value_from: Union[Any, None] = attributes_dict.get("valuefrom", None)
        if channel_value_from is not None:
            del attributes_dict["valuefrom"]
        channel_value_from = attributes_dict.get("valuefrom", None)
        del attributes_dict["name"]
        del attributes_dict["type"]

        new_channel: Union[ChannelObject, None] = None
        if self.__channels.get(channel_name) is not None:
            return self.__channels[channel_name]

        if channel_type.lower() == "spec":
            if "version" not in attributes_dict:
                try:
                    attributes_dict["version"] = self.specversion
                except AttributeError:
                    pass

            try:
                from mxcubecore.Command.Spec import SpecChannel

                new_channel = SpecChannel(channel_name, channel, **attributes_dict)
            except Exception:
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
                from mxcubecore.Command.Taco import TacoChannel

                new_channel = TacoChannel(channel_name, channel, **attributes_dict)
            except Exception:
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
                from mxcubecore.Command.Tango import TangoChannel

                new_channel = TangoChannel(channel_name, channel, **attributes_dict)
            except ConnectionError:
                logging.getLogger().error(
                    "%s: could not connect to device server %s (hint: is it running ?)",
                    self.name(),
                    attributes_dict["tangoname"],
                )
                raise ConnectionError
            except Exception:
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

                from mxcubecore.Command.Exporter import ExporterChannel

                new_channel = ExporterChannel(channel_name, channel, **attributes_dict)
            except Exception:
                logging.getLogger().exception(
                    "%s: cannot add exporter channel %s (hint: check attributes)",
                    self.name(),
                    channel_name,
                )
        elif channel_type.lower() == "epics":
            try:
                from mxcubecore.Command.Epics import EpicsChannel

                new_channel = EpicsChannel(channel_name, channel, **attributes_dict)
            except Exception:
                logging.getLogger().exception(
                    "%s: cannot add EPICS channel %s (hint: check PV name)",
                    self.name(),
                    channel_name,
                )
        elif channel_type.lower() == "tine":
            if "tinename" not in attributes_dict:
                try:
                    attributes_dict["tinename"] = self.tine_name
                except AttributeError:
                    pass

            try:
                from mxcubecore.Command.Tine import TineChannel

                new_channel = TineChannel(channel_name, channel, **attributes_dict)
            except Exception:
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
                from mxcubecore.Command.Sardana import SardanaChannel

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
            except Exception:
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
                from mxcubecore.Command.Mockup import MockupChannel

                new_channel = MockupChannel(channel_name, channel, **attributes_dict)
            except Exception:
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

    def set_channel_value(self, channel_name: str, value: Any) -> None:
        """Set channel value.

        Args:
            channel_name (str): Channel name.
            value (Any): Value to set.
        """
        self.__channels[channel_name].set_value(value)

    def get_channel_value(self, channel_name: str) -> Any:
        """Get channel value.

        Args:
            channel_name (str): Channel name.

        Returns:
            Any: Channel value.
        """
        return self.__channels[channel_name].get_value()

    def get_channels(self) -> Generator[ChannelObject, None, None]:
        """Get object channels.

        Yields:
            Generator[ChannelObject, None, None]: Object channels.
        """
        for chan in self.__channels.values():
            yield chan

    def get_command_object(self, cmd_name: str) -> Union[CommandObject, None]:
        """Get command object.

        Args:
            cmd_name (str): Command name.

        Returns:
            Union[CommandObject, None]: Command object or None if not found.
        """
        try:
            return self.__commands.get(cmd_name)
        except Exception as e:
            return None

    def get_commands(self) -> Generator[CommandObject, None, None]:
        """Get object commands.

        Yields:
            Generator[CommandObject, None, None]: Command objects.
        """
        for cmd in self.__commands.values():
            yield cmd

    def get_command_names_list(self) -> List[str]:
        """Get list of command names.

        Returns:
            List[str]: Command names.
        """
        return list(self.__commands.keys())

    def add_command(
        self,
        arg1: Dict[str, Any],
        arg2: Optional[str] = None,
        add_now: bool = True,
    ) -> Union[CommandObject, None]:
        """Add command.

        Args:
            arg1 (Dict[str, Any]): Command attributes.
            arg2 (Optional[str], optional): Command name. Defaults to None.
            add_now (bool, optional): Whether to add command now. Defaults to True.

        Raises:
            ConnectionError: If a connection error occured while adding the command.

        Returns:
            Union[CommandObject, None]: Command object or None if adding later.
        """
        if not add_now:
            self.__commands_to_add.append((arg1, arg2))
            return
        new_command: Union[CommandObject, None] = None

        cmd_name: str
        cmd_type: str
        cmd: Union[str, None]
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
                from mxcubecore.Command.Spec import SpecCommand

                new_command = SpecCommand(cmd_name, cmd, **attributes_dict)
            except Exception:
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
                from mxcubecore.Command.Taco import TacoCommand

                new_command = TacoCommand(cmd_name, cmd, **attributes_dict)
            except Exception:
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
                from mxcubecore.Command.Tango import TangoCommand

                new_command = TangoCommand(cmd_name, cmd, **attributes_dict)
            except ConnectionError:
                logging.getLogger().error(
                    "%s: could not connect to device server %s (hint: is it running ?)",
                    self.name(),
                    attributes_dict["tangoname"],
                )
                raise ConnectionError
            except Exception:
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

                from mxcubecore.Command.Exporter import ExporterCommand

                new_command = ExporterCommand(cmd_name, cmd, **attributes_dict)
            except Exception:
                logging.getLogger().exception(
                    "%s: cannot add command %s (hint: check attributes)",
                    self.name(),
                    cmd_name,
                )
        elif cmd_type.lower() == "epics":
            try:
                from mxcubecore.Command.Epics import EpicsCommand

                new_command = EpicsCommand(cmd_name, cmd, **attributes_dict)
            except Exception:
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

            from mxcubecore.Command.Sardana import SardanaCommand, SardanaMacro

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
                except Exception:
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
                except Exception:
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
                from mxcubecore.Command.Pool import PoolCommand

                new_command = PoolCommand(cmd_name, cmd, **attributes_dict)
            except ConnectionError:
                logging.getLogger().error(
                    "%s: could not connect to device server %s (hint: is it running ?)",
                    self.name(),
                    attributes_dict["tangoname"],
                )
                raise ConnectionError
            except Exception:
                logging.getLogger().exception(
                    '%s: could not add command "%s" (hint: check command attributes)',
                    self.name(),
                    cmd_name,
                )
        elif cmd_type.lower() == "tine":
            if "tinename" not in attributes_dict:
                try:
                    attributes_dict["tinename"] = self.tine_name
                except AttributeError:
                    pass

            try:
                from mxcubecore.Command.Tine import TineCommand

                new_command = TineCommand(cmd_name, cmd, **attributes_dict)
            except Exception:
                logging.getLogger().exception(
                    '%s: could not add command "%s" (hint: check command attributes)',
                    self.name(),
                    cmd_name,
                )

        elif cmd_type.lower() == "mockup":
            try:
                from mxcubecore.Command.Mockup import MockupCommand

                new_command = MockupCommand(cmd_name, cmd, **attributes_dict)
            except Exception:
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

    def _add_channels_and_commands(self) -> None:
        """Add pending channels and commands."""
        [self.add_channel(*args) for args in self.__channels_to_add]
        [self.add_command(*args) for args in self.__commands_to_add]
        self.__channels_to_add = []
        self.__commands_to_add = []

    def execute_command(self, command_name: str, *args, **kwargs) -> Any:
        """Execute command.

        Args:
            command_name (str): Command name.
            *args (tuple): Arguments to pass through to the command to be executed.
            **kwargs (Dict[str, Any]): Named arguments to pass through to the
            command to be executed.

        Raises:
            AttributeError: If command not found.

        Returns:
            Any: Execution output.
        """
        if command_name in self.__commands:
            return self.__commands[command_name](*args, **kwargs)
        else:
            raise AttributeError
