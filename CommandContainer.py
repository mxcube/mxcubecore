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


__author__ = "Matias Guijarro"
__version__ = 1.0


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

    def connectSignal(self, signalName, callableFunc):
        try:
            dispatcher.disconnect(callableFunc, signalName, self)
        except BaseException:
            pass
        dispatcher.connect(callableFunc, signalName, self)

    def emit(self, signal, *args):
        signal = str(signal)

        if len(args) == 1:
            if isinstance(args[0], tuple):
                args = args[0]

        dispatcher.send(signal, self, *args)

    def addArgument(
        self, argName, argType, combo_items=None, onchange=None, valuefrom=None
    ):
        arg_names = [arg[0] for arg in self._arguments]
        if argName not in arg_names:
            self._arguments.append((argName, argType.lower(), onchange, valuefrom))
        if combo_items is not None:
            self._combo_arguments_items[argName] = combo_items

    def getArguments(self):
        return self._arguments

    def getComboArgumentItems(self, argName):
        return self._combo_arguments_items[argName]

    def userName(self):
        return self._username or str(self.name())

    def isConnected(self):
        return False


class ChannelObject(object):
    def __init__(self, name, username=None, **kwargs):
        self._name = name
        self._username = username
        self._attributes = kwargs
        self._onchange = None
        self.__firstUpdate = True

    def name(self):
        return self._name

    def connectSignal(self, signalName, callableFunc):
        try:
            dispatcher.disconnect(callableFunc, signalName, self)
        except BaseException:
            pass
        dispatcher.connect(callableFunc, signalName, self)

    def disconnectSignal(self, signalName, callableFunc):
        try:
            dispatcher.disconnect(callableFunc, signalName, self)
        except BaseException:
            pass

    def connectNotify(self, signal):
        if signal == "update" and self.isConnected():
            self.emit(signal, self.getValue())

    def emit(self, signal, *args):
        signal = str(signal)

        if len(args) == 1:
            if isinstance(args[0], tuple):
                args = args[0]

        dispatcher.send(signal, self, *args)

    def userName(self):
        return self._username or str(self.name())

    def isConnected(self):
        return False

    def update(self, value):
        if self.__firstUpdate:
            self.__firstUpdate = False
            return

        if self._onchange is not None:
            cmd, container_ref = self._onchange
            container = container_ref()
            if container is not None:
                cmdobj = container.get_command_object(cmd)
                if cmdobj is not None:
                    cmdobj(value)

    def getValue(self, force=False):
        raise NotImplementedError


class CommandContainer:
    """Mixin class for generic command and channel containers"""

    def __init__(self):
        self.__commands = {}
        self.__channels = {}
        self.__commandsToAdd = []
        self.__channelsToAdd = []

    def __getattr__(self, attr):
        try:
            return self.__dict__["_CommandContainer__commands"][attr]
        except KeyError:
            raise AttributeError(attr)

    def get_channel_object(self, channelName, optional=False):
        channel = self.__channels.get(channelName)
        if channel is None and not optional:
            msg = "%s: Unable to get channel %s" % (self.name(), channelName)
            logging.getLogger("user_level_log").error(msg)
            # raise Exception(msg)
        return channel

    def get_channel_names_list(self):
        return list(self.__channels.keys())

    def add_channel(self, attributesDict, channel, addNow=True):
        if not addNow:
            self.__channelsToAdd.append((attributesDict, channel))
            return
        channelName = attributesDict["name"]
        channelType = attributesDict["type"]
        channelOnChange = attributesDict.get("onchange", None)
        if channelOnChange is not None:
            del attributesDict["onchange"]
        channelValueFrom = attributesDict.get("valuefrom", None)
        if channelValueFrom is not None:
            del attributesDict["valuefrom"]
        channelValueFrom = attributesDict.get("valuefrom", None)
        del attributesDict["name"]
        del attributesDict["type"]

        newChannel = None
        if self.__channels.get(channelName) is not None:
            return self.__channels[channelName]

        if channelType.lower() == "spec":
            if "version" not in attributesDict:
                try:
                    attributesDict["version"] = self.specversion
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Spec import SpecChannel

                newChannel = SpecChannel(channelName, channel, **attributesDict)
            except BaseException:
                logging.getLogger().error(
                    "%s: cannot add channel %s (hint: check attributes)",
                    self.name(),
                    channelName,
                )
        elif channelType.lower() == "taco":
            if "taconame" not in attributesDict:
                try:
                    attributesDict["taconame"] = self.taconame
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Taco import TacoChannel

                newChannel = TacoChannel(channelName, channel, **attributesDict)
            except BaseException:
                logging.getLogger().error(
                    "%s: cannot add channel %s (hint: check attributes)",
                    self.name(),
                    channelName,
                )
        elif channelType.lower() == "tango":
            if "tangoname" not in attributesDict:
                try:
                    attributesDict["tangoname"] = self.tangoname
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Tango import TangoChannel

                newChannel = TangoChannel(channelName, channel, **attributesDict)
            except ConnectionError:
                logging.getLogger().error(
                    "%s: could not connect to device server %s (hint: is it running ?)",
                    self.name(),
                    attributesDict["tangoname"],
                )
                raise ConnectionError
            except BaseException:
                logging.getLogger().exception(
                    "%s: cannot add channel %s (hint: check attributes)",
                    self.name(),
                    channelName,
                )
        elif channelType.lower() == "exporter":
            if "exporter_address" not in attributesDict:
                try:
                    attributesDict["exporter_address"] = self.exporter_address
                except AttributeError:
                    pass
            host, port = attributesDict["exporter_address"].split(":")

            try:
                attributesDict["address"] = host
                attributesDict["port"] = int(port)
                del attributesDict["exporter_address"]

                from HardwareRepository.Command.Exporter import ExporterChannel

                newChannel = ExporterChannel(channelName, channel, **attributesDict)
            except BaseException:
                logging.getLogger().exception(
                    "%s: cannot add exporter channel %s (hint: check attributes)",
                    self.name(),
                    channelName,
                )
        elif channelType.lower() == "epics":
            try:
                from HardwareRepository.Command.Epics import EpicsChannel

                newChannel = EpicsChannel(channelName, channel, **attributesDict)
            except BaseException:
                logging.getLogger().exception(
                    "%s: cannot add EPICS channel %s (hint: check PV name)",
                    self.name(),
                    channelName,
                )
        elif channelType.lower() == "tine":
            if "tinename" not in attributesDict:
                try:
                    attributesDict["tinename"] = self.tinename
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Tine import TineChannel

                newChannel = TineChannel(channelName, channel, **attributesDict)
            except BaseException:
                logging.getLogger("HWR").exception(
                    "%s: cannot add TINE channel %s (hint: check attributes)",
                    self.name(),
                    channelName,
                )

        elif channelType.lower() == "sardana":

            if "taurusname" not in attributesDict:
                try:
                    attributesDict["taurusname"] = self.taurusname
                except AttributeError:
                    pass
            uribase = attributesDict["taurusname"]

            try:
                from HardwareRepository.Command.Sardana import SardanaChannel

                logging.getLogger().debug(
                    "Creating a sardanachannel - %s / %s / %s",
                    self.name(),
                    channelName,
                    str(attributesDict),
                )
                newChannel = SardanaChannel(
                    channelName, channel, uribase=uribase, **attributesDict
                )
                logging.getLogger().debug("Created")
            except BaseException:
                logging.getLogger().exception(
                    "%s: cannot add SARDANA channel %s (hint: check PV name)",
                    self.name(),
                    channelName,
                )

        elif channelType.lower() == "mockup":
            if "default_value" not in attributesDict:
                try:
                    attributesDict["default_value"] = float(self.default_value)
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Mockup import MockupChannel

                newChannel = MockupChannel(channelName, channel, **attributesDict)
            except BaseException:
                logging.getLogger("HWR").exception(
                    "%s: cannot add Mockup channel %s (hint: check attributes)",
                    self.name(),
                    channelName,
                )

        if newChannel is not None:
            if channelOnChange is not None:
                newChannel._onchange = (channelOnChange, weakref.ref(self))
            else:
                newChannel._onchange = None
            if channelValueFrom is not None:
                newChannel._valuefrom = (channelValueFrom, weakref.ref(self))
            else:
                newChannel._valuefrom = None

            self.__channels[channelName] = newChannel

            return newChannel
        else:
            logging.getLogger().exception("Channel is None")

    def set_channel_value(self, channel_name, value):
        self.__channels[channel_name].setValue(value)

    def get_channel_value(self, channel_name):
        return self.__channels[channel_name].getValue()

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

    def add_command(self, arg1, arg2=None, addNow=True):
        if not addNow:
            self.__commandsToAdd.append((arg1, arg2))
            return
        newCommand = None

        if isinstance(arg1, dict):
            attributesDict = arg1
            cmd = arg2

            cmdName = attributesDict["name"]
            cmdType = attributesDict["type"]
            del attributesDict["name"]
            del attributesDict["type"]
        else:
            attributesDict = {}
            attributesDict.update(arg1.getProperties())

            try:
                cmdName = attributesDict["name"]
                cmdType = attributesDict["type"]
                cmd = attributesDict["toexecute"]
            except KeyError as err:
                logging.getLogger().error(
                    '%s: cannot add command: missing "%s" property',
                    self.name(),
                    err.args[0],
                )
                return
            else:
                del attributesDict["name"]
                del attributesDict["type"]
                del attributesDict["toexecute"]

        if cmdType.lower() == "spec":
            if "version" not in attributesDict:
                try:
                    attributesDict["version"] = self.specversion
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Spec import SpecCommand

                newCommand = SpecCommand(cmdName, cmd, **attributesDict)
            except BaseException:
                logging.getLogger().exception(
                    '%s: could not add command "%s" (hint: check command attributes)',
                    self.name(),
                    cmdName,
                )
        elif cmdType.lower() == "taco":
            if "taconame" not in attributesDict:
                try:
                    attributesDict["taconame"] = self.taconame
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Taco import TacoCommand

                newCommand = TacoCommand(cmdName, cmd, **attributesDict)
            except BaseException:
                logging.getLogger().exception(
                    '%s: could not add command "%s" (hint: check command attributes)',
                    self.name(),
                    cmdName,
                )
        elif cmdType.lower() == "tango":
            if "tangoname" not in attributesDict:
                try:
                    attributesDict["tangoname"] = self.tangoname
                except AttributeError:
                    pass
            try:
                from HardwareRepository.Command.Tango import TangoCommand

                newCommand = TangoCommand(cmdName, cmd, **attributesDict)
            except ConnectionError:
                logging.getLogger().error(
                    "%s: could not connect to device server %s (hint: is it running ?)",
                    self.name(),
                    attributesDict["tangoname"],
                )
                raise ConnectionError
            except BaseException:
                logging.getLogger().exception(
                    '%s: could not add command "%s" (hint: check command attributes)',
                    self.name(),
                    cmdName,
                )

        elif cmdType.lower() == "exporter":
            if "exporter_address" not in attributesDict:
                try:
                    attributesDict["exporter_address"] = self.exporter_address
                except AttributeError:
                    pass
            host, port = attributesDict["exporter_address"].split(":")

            try:
                attributesDict["address"] = host
                attributesDict["port"] = int(port)
                del attributesDict["exporter_address"]

                from HardwareRepository.Command.Exporter import ExporterCommand

                newCommand = ExporterCommand(cmdName, cmd, **attributesDict)
            except BaseException:
                logging.getLogger().exception(
                    "%s: cannot add command %s (hint: check attributes)",
                    self.name(),
                    cmdName,
                )
        elif cmdType.lower() == "epics":
            try:
                from HardwareRepository.Command.Epics import EpicsCommand

                newCommand = EpicsCommand(cmdName, cmd, **attributesDict)
            except BaseException:
                logging.getLogger().exception(
                    "%s: cannot add EPICS channel %s (hint: check PV name)",
                    self.name(),
                    cmdName,
                )

        elif cmdType.lower() == "sardana":

            doorname = None
            taurusname = None
            cmdtype = None
            door_first = False
            tango_first = False

            if "doorname" not in attributesDict:
                try:
                    attributesDict["doorname"] = self.doorname
                    doorname = self.doorname
                except AttributeError:
                    pass
            else:
                door_first = True
                doorname = attributesDict["doorname"]

            if "taurusname" not in attributesDict:
                try:
                    attributesDict["taurusname"] = self.taurusname
                    taurusname = self.taurusname
                except AttributeError:
                    pass
            else:
                tango_first = True
                taurusname = attributesDict["taurusname"]

            if "cmdtype" in attributesDict:
                cmdtype = attributesDict["cmdtype"]

            # guess what kind of command to create
            if cmdtype is None:
                if taurusname is not None and doorname is None:
                    cmdtype = "command"
                elif doorname is not None and taurusname is None:
                    cmdtype = "macro"
                elif doorname is not None and taurusname is not None:
                    if door_first:
                        cmdtype = "macro"
                    elif tango_first:
                        cmdtype = "command"
                    else:
                        cmdtype = "macro"
                else:
                    logging.getLogger().error(
                        "%s: incomplete sardana command declaration. ignored",
                        self.name(),
                    )

            from HardwareRepository.Command.Sardana import SardanaCommand, SardanaMacro

            if cmdtype == "macro" and doorname is not None:
                try:
                    newCommand = SardanaMacro(cmdName, cmd, **attributesDict)
                except ConnectionError:
                    logging.getLogger().error(
                        "%s: could not connect to sardana door %s (hint: is it running ?)",
                        self.name(),
                        attributesDict["doorname"],
                    )
                    raise ConnectionError
                except BaseException:
                    logging.getLogger().exception(
                        '%s: could not add command "%s" (hint: check command attributes)',
                        self.name(),
                        cmdName,
                    )
            elif cmdtype == "command" and taurusname is not None:
                try:
                    newCommand = SardanaCommand(cmdName, cmd, **attributesDict)
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
                        cmdName,
                    )
            else:
                logging.getLogger().error(
                    "%s: incomplete sardana command declaration. ignored", self.name()
                )

        elif cmdType.lower() == "pool":
            if "tangoname" not in attributesDict:
                try:
                    attributesDict["tangoname"] = self.tangoname
                except AttributeError:
                    pass
            try:
                from HardwareRepository.Command.Pool import PoolCommand

                newCommand = PoolCommand(cmdName, cmd, **attributesDict)
            except ConnectionError:
                logging.getLogger().error(
                    "%s: could not connect to device server %s (hint: is it running ?)",
                    self.name(),
                    attributesDict["tangoname"],
                )
                raise ConnectionError
            except BaseException:
                logging.getLogger().exception(
                    '%s: could not add command "%s" (hint: check command attributes)',
                    self.name(),
                    cmdName,
                )
        elif cmdType.lower() == "tine":
            if "tinename" not in attributesDict:
                try:
                    attributesDict["tinename"] = self.tinename
                except AttributeError:
                    pass

            try:
                from HardwareRepository.Command.Tine import TineCommand

                newCommand = TineCommand(cmdName, cmd, **attributesDict)
            except BaseException:
                logging.getLogger().exception(
                    '%s: could not add command "%s" (hint: check command attributes)',
                    self.name(),
                    cmdName,
                )

        elif cmdType.lower() == "mockup":
            try:
                from HardwareRepository.Command.Mockup import MockupCommand

                newCommand = MockupCommand(cmdName, cmd, **attributesDict)
            except BaseException:
                logging.getLogger().exception(
                    '%s: could not add command "%s" (hint: check command attributes)',
                    self.name(),
                    cmdName,
                )

        if newCommand is not None:
            self.__commands[cmdName] = newCommand

            if not isinstance(arg1, dict):
                i = 1
                for arg in arg1.getObjects("argument"):
                    onchange = arg.getProperty("onchange")
                    if onchange is not None:
                        onchange = (onchange, weakref.ref(self))
                    valuefrom = arg.getProperty("valuefrom")
                    if valuefrom is not None:
                        valuefrom = (valuefrom, weakref.ref(self))

                    try:
                        comboitems = arg["type"]["item"]
                    except IndexError:
                        try:
                            newCommand.addArgument(
                                arg.getProperty("name"),
                                arg.type,
                                onchange=onchange,
                                valuefrom=valuefrom,
                            )
                        except AttributeError:
                            logging.getLogger().error(
                                '%s, command "%s": could not add argument %d, missing type or name',
                                self.name(),
                                cmdName,
                                i,
                            )
                            continue
                    else:
                        if isinstance(comboitems, list):
                            combo_items = []
                            for item in comboitems:
                                name = item.getProperty("name")
                                value = item.getProperty("value")
                                if name is None or value is None:
                                    logging.getLogger().error(
                                        "%s, command '%s': could not add argument %d, missing combo item name or value",
                                        self.name(),
                                        cmdName,
                                        i,
                                    )
                                    continue
                                else:
                                    combo_items.append((name, value))
                        else:
                            name = comboitems.getProperty("name")
                            value = comboitems.getProperty("value")
                            if name is None or value is None:
                                combo_items = ((name, value),)
                            else:
                                logging.getLogger().error(
                                    "%s, command '%s': could not add argument %d, missing combo item name or value",
                                    self.name(),
                                    cmdName,
                                    i,
                                )
                                continue

                        newCommand.addArgument(
                            arg.getProperty("name"),
                            "combo",
                            combo_items,
                            onchange,
                            valuefrom,
                        )

                    i += 1

            return newCommand

    def _add_channels_and_commands(self):
        [self.add_channel(*args) for args in self.__channelsToAdd]
        [self.add_command(*args) for args in self.__commandsToAdd]
        self.__channelsToAdd = []
        self.__commandsToAdd = []

    def execute_command(self, command_name, *args, **kwargs):
        if command_name in self.__commands:
            return self.__commands[command_name](*args, **kwargs)
        else:
            raise AttributeError
