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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import

import typing
import ast
import enum
import copy
import logging
from gevent import event, Timeout
import pydantic
from typing import (
    TYPE_CHECKING,
    Callable,
    Iterator,
    Union,
    Any,
    Generator,
    List,
    Dict,
    Tuple,
    Type,
    Optional,
)
from typing_extensions import Self, Literal
from warnings import warn

from mxcubecore.dispatcher import dispatcher
from mxcubecore.CommandContainer import CommandContainer

if TYPE_CHECKING:
    from logging import Logger
    from pydantic import BaseModel
    from .CommandContainer import CommandObject

__copyright__ = """ Copyright © 2010-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


@enum.unique
class HardwareObjectState(enum.Enum):
    """Enumeration of common states, shared between all HardwareObjects"""

    UNKNOWN = 0
    WARNING = 1
    BUSY = 2
    READY = 3
    FAULT = 4
    OFF = 5


class DefaultSpecificState(enum.Enum):
    """Placeholder enumeration for HardwareObject-specific states"""

    UNKNOWN = "UNKNOWN"


class ConfiguredObject:
    """Superclass for classes that take configuration from YAML files"""

    # class HOConfig(pydantic.BaseModel):
    #     model_config = pydantic.ConfigDict(extra="allow")

    class HOConfig:
        """Temporary replacement for Pydantic class

        Required during transition, as long as we do nto have teh fields defined"""

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def model_dump(self):
            return copy.deepcopy(self.__dict__)

    def __init__(
        self, name: str, hwobj_container: Optional["ConfiguredObject"] = None
    ) -> None:
        """
        Args:
            name (str): Equal to role name relative to hwobj_container (if applicable)
        """

        self._name = name
        self._config: Optional["ConfiguredObject.HOConfig"] = None
        self._hwobj_container: Optional[ConfiguredObject] = hwobj_container
        self._roles = []

    def __getattr__(self, attr):
        return getattr(self.__dict__["_config"], attr)

    @property
    def name(self):
        """HWOBJ name - Equal to role name relative to hwobj_container (if applicable)"""
        return self._name

    @property
    def id(self):
        """dot-separated role names defining path from beamline object to here

        NB beamline.id == ''"""
        if self._hwobj_container:
            names = []
            obj = self
            while obj._hwobj_container:
                names.append(obj.name)
                obj = obj._hwobj_container
            return ".".join(reversed(names))
        else:
            return ""

    @property
    def config(self):
        """Pydantic object with conifigured parameters, incl. contained HardwareObjects"""
        return self._config

    @property
    def hwobj_container(self):
        """HardwareObject contaiing this one - None for Beamline"""
        return self._hwobj_container

    def get_by_id(self, _id: str) -> "ConfiguredObject":
        result = self
        for name in _id.split("."):
            result = getattr(result, name)
            if result is None:
                break
        #
        return result

    @property
    def objects_by_role(self) -> Dict[str, Union[Self, None]]:
        """All contained Objects mapped by role (in specification order).

        Includes objects defined in subclasses.

        Returns:
            OrderedDict[str, Union[Self, None]]: Contained objects mapped by role.
        """
        result = {}
        for tag in self._roles:
            if hasattr(self, tag):
                result[tag] = getattr(self, tag)
            else:
                raise ValueError(
                    "%s object has no attribute %s" % (self.__class__.__name__, tag)
                )
        #
        return result

    def get_properties(self) -> Dict[str, Any]:
        """Get configured properties (not roles)"""
        if self._config is not None:
            return self._config.model_dump()
        elif isinstance(self, HardwareObjectNode):
            # NBNB TEMPORARY for transition to yaml configuration only
            return HardwareObjectNode.get_properties(self)

    def get_property(self, name: str, default_value: Optional[Any] = None) -> Any:
        """Get property value .

        Args:
            name (str): Name
            default_value (Optional[Any], optional): Default value. Defaults to None.

        Returns:
            Any: Property value.
        """
        if self._config is not None:
            if hasattr(self._config, name):
                return getattr(self._config, name)
            else:
                return default_value
        elif isinstance(self, HardwareObjectNode):
            # NBNB TEMPORARY for transition to yaml configuration only
            return HardwareObjectNode.get_property(self, name, default_value)

    def get_roles(self) -> List[str]:
        """Get hardware object roles.

        Returns:
            List[str]: List of hardware object roles.
        """
        return list(self._roles)

    def print_log(
        self,
        log_type: str = "HWR",
        level: str = "debug",
        msg: str = "",
    ) -> None:
        """Print message to logger.

        Args:
            log_type (str, optional): Logger type. Defaults to "HWR".
            level (str, optional): Logger level. Defaults to "debug".
            msg (str, optional): Message to log. Defaults to "".
        """
        if hasattr(logging.getLogger(log_type), level):
            getattr(logging.getLogger(log_type), level)(msg)


class PropertySet(dict):
    """Property Set"""

    def __init__(self) -> None:
        super().__init__()

        self.__properties_changed: Dict[str, Any] = {}
        self.__properties_path: Dict[str, Any] = {}

    def set_property_path(self, name: str, path: Union[str, Any]) -> None:
        """Set Property Path.

        Args:
            name (str): Name.
            path (Union[str, Any]): Path.
        """
        name = str(name)
        self.__properties_path[name] = path

    def get_properties_path(self) -> Iterator[tuple]:
        """Get Property Paths.

        Returns:
            Iterator[tuple]: Iterator for property paths.
        """
        return iter(self.__properties_path.items())

    def __setitem__(self, name: Union[str, Any], value: Union[str, Any]) -> None:
        name = str(name)

        if name in self and str(value) != str(self[name]):
            self.__properties_changed[name] = str(value)

        super().__setitem__(str(name), value)

    def get_changes(self) -> Generator[tuple, None, None]:
        """Get property changes since the last time checked.

        Yields:
            Generator[tuple, None, None]: Property changes.
        """
        for property_name, value in self.__properties_changed.items():
            yield (self.__properties_path[property_name], value)

        self.__properties_changed = {}  # reset changes at commit


class HardwareObjectNode:
    """Hardware Object Node"""

    user_file_directory: str

    def __init__(self, node_name: str) -> None:
        """
        Args:
            node_name (str): Node name.
        """
        self.__dict__["_property_set"] = PropertySet()
        self._property_set: PropertySet
        self.__objects_names: List[Union[str, None]] = []
        self.__objects: List[List[Union["HardwareObject", None]]] = []
        self._objects_by_role: Dict[str, "HardwareObject"] = {}
        self._path: str = ""
        self.__name: str = node_name
        self.__references: List[Tuple[str, str, str, int, int, int]] = []
        self._xml_path: Union[str, None] = None

    @staticmethod
    def set_user_file_directory(user_file_directory: str) -> None:
        """Set user file directory.

        Args:
            user_file_directory (str): User file directory path.
        """
        HardwareObjectNode.user_file_directory = user_file_directory

    @property
    def load_name(self) -> str:
        """Get node name.

        Returns:
            str: Name.
        """
        return self.__name

    def set_path(self, path: str) -> None:
        """Set the 'path' of the Hardware Object in the XML file describing it
        (the path follows the XPath syntax)

        Args:
            path (str): String representing the path of the Hardware Object in its file
        """

        # NB For use ONLY in loading xml-configured objects

        self._path = path

    def __iter__(self) -> Generator[Union["HardwareObject", None], None, None]:
        warn("%s.__iter__ is Deprecated. Avoid" % self.__class__.__name__)
        for i in range(len(self.__objects_names)):
            for object in self.__objects[i]:
                yield object

    def __len__(self) -> int:
        warn("%s.__len__ is Deprecated. Avoid" % self.__class__.__name__)
        return sum(map(len, self.__objects))

    def __setattr__(self, attr: str, value: Any) -> None:
        try:
            config = self.__dict__.get("_config")
            if attr not in self.__dict__ and config and attr in config.model_dump():
                warn("%s.__setattr__ is Deprecated. Avoid" % self.__class__.__name__)
                self._set_property(attr, value)
            else:
                self.__dict__[attr] = value
        except AttributeError:
            self.__dict__[attr] = value

    def __getitem__(
        self,
        key: Union[str, int],
    ) -> Union["HardwareObject", List[Union["HardwareObject", None]], None]:
        warn("%s.__getitem__ is Deprecated. Avoid" % self.__class__.__name__)
        if isinstance(key, str):
            object_name = key

            try:
                index = self.__objects_names.index(object_name)
            except Exception:
                raise KeyError
            else:
                obj = self.__objects[index]
                if len(obj) == 1:
                    return obj[0]
                else:
                    return obj
        elif isinstance(key, int):
            index = key

            if index < len(self.__objects_names):
                obj = self.__objects[index]
                if len(obj) == 1:
                    return obj[0]
                else:
                    return obj
            else:
                raise IndexError
        else:
            raise TypeError

    def add_reference(
        self,
        name: str,
        reference: str,
        role: Union[str, None] = None,
    ) -> None:
        """Add hardware object reference.

        Args:
            name (str): Name.
            reference (str): Xpath reference.
            role (Union[str, None], optional): Role. Defaults to None.
        """

        role = str(role).lower()

        try:
            index = self.__objects_names.index(name)
        except ValueError:
            objects_names_index = len(self.__objects_names)
            self.__objects_names.append(None)
            objects_index = len(self.__objects)
            self.__objects.append(None)
            objects_index2 = -1
        else:
            objects_names_index = -1
            objects_index = index
            objects_index2 = len(self.__objects[index])
            self.__objects[index].append(None)

        self.__references.append(
            (reference, name, role, objects_names_index, objects_index, objects_index2)
        )

    def resolve_references(self) -> None:
        """Resolve hardware objects from defined references."""
        # NB Must be here - importing at top level leads to circular imports
        from .HardwareRepository import get_hardware_repository

        # NB For use ONLY in loading xml-configured objects

        while len(self.__references) > 0:
            (
                reference,
                name,
                role,
                objects_names_index,
                objects_index,
                objects_index2,
            ) = self.__references.pop()

            hw_object = get_hardware_repository().get_hardware_object(reference)
            warn(
                "Deprecated: Hardware object '{}' with role '{}' is a reference".format(
                    name, role
                )
            )

            if hw_object is not None:
                self._objects_by_role[role] = hw_object
                hw_object.__role = role

                if objects_names_index >= 0:
                    self.__objects_names[objects_names_index] = role
                    self.__objects[objects_index] = [hw_object]
                else:
                    self.__objects[objects_index][objects_index2] = hw_object
            else:
                if objects_names_index >= 0:
                    del self.__objects_names[objects_names_index]
                    del self.__objects[objects_index]
                else:
                    del self.__objects[objects_index][objects_index2]
                    if len(self.__objects[objects_index]) == 0:
                        del self.__objects[objects_index]

        for hw_object in self:
            hw_object.resolve_references()

    def _add_object(
        self,
        name: str,
        hw_object: Union["HardwareObject", None],
        role: Optional[str] = None,
    ) -> None:
        """Add hardware object mapped by name.

        Args:
            name (str): Name.
            hw_object (Union[HardwareObject, None]): Hardware object.
            role (Optional[str], optional): Role. Defaults to None.
        """

        # NB For use ONLY in loading xml-configured objects

        if hw_object is None:
            return None
        elif role is not None:
            role = str(role).lower()
            self._objects_by_role[role] = hw_object
            hw_object.__role = role

        try:
            index = self.__objects_names.index(name)
        except ValueError:
            self.__objects_names.append(name)
            self.__objects.append([hw_object])
        else:
            self.__objects[index].append(hw_object)

    #

    def _get_objects(
        self,
        object_name: str,
    ) -> Generator[Union["HardwareObject", None], None, None]:
        """Get hardware objects by name.

        Args:
            object_name (str): Name.

        Yields:
            Union[HardwareObject, None]: Hardware object.
        """

        # NB For use ONLY in loading xml-configured objects

        try:
            index = self.__objects_names.index(object_name)
        except ValueError:
            pass
        else:
            for obj in self.__objects[index]:
                yield obj

    def get_object_by_role(self, role: str) -> Union["HardwareObject", None]:
        """Get hardware object by role.

        Args:
            role (str): Role.

        Returns:
            Union[HardwareObject, None]: Hardware object.
        """
        warn(
            "%s.get_object_by_role is deprecated. Use get_property instead"
            % self.__class__.__name__
        )
        role = str(role).lower()
        objects = [self]

        for curr in objects:
            result = curr._objects_by_role.get(role)
            if result is None:
                objects.extend(obj for obj in curr if obj)

            else:
                return result

    def _objects_names(self) -> List[Union[str, None]]:
        """Return hardware object names.

        Returns:
            List[Union[str, None]]: List of hardware object names.
        """
        return self.__objects_names[:]

    def _set_property(self, name: str, value: Any) -> None:
        """Set property value.

        Args:
            name (str): Name.
            value (Any): Value.
        """

        # NB For use ONLY in loading xml-configured objects

        name = str(name)
        value = str(value)

        if value == "None":
            value = None
        else:
            #
            # try to convert buffer to the appropriate type
            #
            try:
                value = int(value)
            except Exception:
                try:
                    value = float(value)
                except Exception:
                    if value == "True":
                        value = True
                    elif value == "False":
                        value = False

        self._property_set[name] = value
        self._property_set.set_property_path(name, self._path + "/" + str(name))

    def get_property(self, name: str, default_value: Optional[Any] = None) -> Any:
        """Get property value.

        Args:
            name (str): Name
            default_value (Optional[Any], optional): Default value. Defaults to None.

        Returns:
            Any: Property value.
        """
        return self._property_set.get(str(name), default_value)

    def get_properties(self) -> PropertySet:
        """Get properties - for XML-config implementation loading only

        Returns:
            PropertySet: Properties.
        """

        # NB For use ONLY in loading xml-configured objects

        return self._property_set


class HardwareObjectMixin(CommandContainer):
    """Functionality for either xml- or yaml-configured HardwareObjects

    Signals emited:

        - stateChanged

        - specificStateChanged
    """

    #: enum.Enum: General states, shared between all HardwareObjects. Do *not* overridde
    STATES = HardwareObjectState

    #: enum.Enum: Placeholder for HardwareObject-specific states. To be overridden
    SPECIFIC_STATES = DefaultSpecificState

    def __init__(self) -> None:
        CommandContainer.__init__(self)

        # Container for connections to HardwareObject
        self.connect_dict: Dict[str, Dict[str, Any]] = {}
        # event to handle waiting for object to be ready
        self._ready_event: event.Event = event.Event()
        # Internal general state attribute, used to check for state changes
        self._state: Union[HardwareObjectState, None] = None
        # Internal object-specific state attribute, used to check for state changes
        self._specific_state: Union[Any, None] = None

        # Dictionary on the form:
        # key: The exporterd member function name
        # value: The arguments of the exported member
        self._exports: Dict[str, Any] = {}

        # Dictionary containing list Pydantic models for each of the exported member
        # functions arguemnts. The key is the member name and the value a list of the
        # pydantic models.
        self._pydantic_models: Dict[str, Type["BaseModel"]] = {}

        # Dictionary on the form:
        # key: The exporterd member function name
        # value: dictionary on the form {signautre: [<arguments>] schema:<JSONSchema>}
        self._exported_attributes: Dict[str, Any] = {}

        # List of member names (methods) to be exported (Set at configuration stage)
        self._exports_config_list = []

        self.log: "Logger" = logging.getLogger("HWR").getChild(self.__class__.__name__)
        self.user_log: "Logger" = logging.getLogger("user_log_level")

    def __bool__(self) -> Literal[True]:
        return True

    def __nonzero__(self) -> Literal[True]:
        return True

    def _init(self) -> None:
        """'protected' post-initialization method. Override as needed.

        For ConfiguredObjects called before loading contained objects
        """
        self.update_state(self.STATES.UNKNOWN)

    def init(self) -> None:
        """'public' post-initialization method. Override as needed.

        For ConfiguredObjects called after loading contained objects.
        """
        self._exports_config_list.extend(
            ast.literal_eval(self.get_property("exports", "[]").strip())
        )
        self._exports = dict.fromkeys(self._exports_config_list, {})

        # Add methods that are exported programatically
        for attr_name in dir(self):
            _attr = getattr(self, attr_name)

            if getattr(_attr, "__exported__", False):
                self._exports[attr_name] = []

        if self._exports:
            self._get_type_annotations()

    def _get_type_annotations(self) -> None:
        """Retrieve typehints and create pydantic models for each argument."""
        _models = {}

        for attr_name, _ in self._exports.items():
            self._exported_attributes[attr_name] = {}
            self._exports[attr_name] = []
            self._pydantic_models[attr_name] = {}
            fdict = {}

            try:
                _attr = getattr(self, attr_name)
            except AttributeError:
                logging.getLogger("HWR").error(
                    f"{attr_name} configured as exported for {self.name} but not implemented"
                )
                continue

            for _n, _t in typing.get_type_hints(_attr).items():
                # Skipp return typehint
                if _n != "return":
                    self._exports[attr_name].append(_n)
                    fdict[_n] = (_t, pydantic.Field(alias=_n))

            _models[attr_name] = (
                pydantic.create_model(attr_name, **fdict),
                pydantic.Field(alias=attr_name),
            )

            self._pydantic_models[attr_name] = _models[attr_name][0]
            self._exported_attributes[attr_name]["display"] = True
            self._exported_attributes[attr_name]["signature"] = self._exports[attr_name]
            self._exported_attributes[attr_name]["schema"] = self._pydantic_models[
                attr_name
            ].schema_json()

        model = pydantic.create_model(self.__class__.__name__, **_models)
        self._pydantic_models["all"] = model

    def execute_exported_command(self, cmd_name: str, args: Dict[str, Any]) -> Any:
        """Execute exported command.

        Args:
            cmd_name (str): Command name.
            args (Dict[str, Any]): Command arguments.

        Returns:
            Any: Command execution output.
        """
        if cmd_name in self._exports.keys():
            cmd = getattr(self, cmd_name)
        else:
            self.log.info(
                f"Command {cmd_name} not exported, check type hints and configuration file"
            )

        return cmd(**args)

    @property
    def pydantic_model(self) -> Dict[str, Type["BaseModel"]]:
        """Get object Pydantic models.

        Returns:
            Dict[str, Type[BaseModel]]: Pydantic models for object.
        """
        return self._pydantic_models

    @property
    def exported_attributes(self) -> Dict[str, Any]:
        """Get exported attributes.

        Returns:
            Dict[str, Any]: Dictionary containing the method signature and JSONSchema.
            Follows the format;
            ```python
            {
                "schema": <JSONSchema string>,
                "signaure": <list of argument names>,
            }
            ```
        """
        return self._exported_attributes

    def abort(self) -> None:
        """Immediately terminate HardwareObject action.

        Should not happen in state READY.
        """
        if self.get_state() is self.STATES.READY:
            return

        # When overriding put active code here

    def stop(self) -> None:
        """Gentler (?) alternative to abort.

        Override as necessary to implement.
        """
        self.abort()

    def get_state(self) -> HardwareObjectState:
        """Getter for state attribute.

        Implementations must query the hardware directly, to ensure current results.

        Returns:
            HardwareObjectState: Current state.
        """
        return self._state

    def get_specific_state(self) -> Union[Any, None]:
        """Getter for specific_state attribute. Override if needed.

        Returns:
            Union[Any, None]: Specific state enum or None.
        """
        return self._specific_state

    def wait_ready(self, timeout: Optional[float] = None) -> None:
        """Wait timeout seconds till object is ready.

        If timeout is None: wait forever.

        Args:
            timeout (Optional[float], optional): Timeout (seconds). Defaults to None.
        """
        with Timeout(timeout, RuntimeError("Timeout waiting for status ready")):
            self._ready_event.wait(timeout=timeout)

    def is_ready(self) -> bool:
        """Convenience function: Check if the object state is READY.

        The same effect could be achieved with
        ```python
        self.get_state() == self.STATES.READY
        ```

        Returns:
            bool: True if ready, otherwise False.
        """
        return self._ready_event.is_set()

    def update_state(self, state: Optional[HardwareObjectState] = None) -> None:
        """Update self._state, and emit signal stateChanged if the state has changed.

        Args:
            state (Optional[HardwareObjectState], optional): State. Defaults to None.

        Raises:
            ValueError: If state specified is invalid.
        """
        if state is None:
            state = self.get_state()

        is_set = self._ready_event.is_set()

        if state == self.STATES.READY:
            if not is_set:
                self._ready_event.set()
        elif not isinstance(state, self.STATES):
            raise ValueError("Attempt to update to illegal state: %s" % state)
        elif is_set:
            self._ready_event.clear()

        if state != self._state:
            self._state = state
            self.emit("stateChanged", (self._state,))

    def update_specific_state(self, state: Optional[Any] = None) -> None:
        """Update self._specific_state, and emit specificStateChanged if appropriate.

        Args:
            state (Optional[Any], optional): Specific state - the enumeration will be
            specific for each HardwareObject class. Defaults to None.

        Raises:
            ValueError: If state specified is invalid.
        """
        if state is None:
            state = self.get_specific_state()
        if state != self._specific_state:
            if not isinstance(state, self.SPECIFIC_STATES):
                raise ValueError(
                    "Attempt to update to illegal specific state: %s" % state
                )

            self._specific_state = state
            self.emit("specificStateChanged", (state,))

    def re_emit_values(self) -> None:
        """Update values for all internal attributes

        Should be expanded in subclasse with more updatable attributes
        (e.g. value, limits)
        """
        self.update_state()
        self.update_specific_state()

    def force_emit_signals(self) -> None:
        """Emits all hardware object signals

        The method is called from the gui via beamline object to ensure that bricks have values
        after the initialization.
        Problem arrise when a hardware object is used by several bricks.
        If first brick connects to some signal emited by a brick then
        other bricks connecting to the same signal will not receive the
        values on the startup.
        The easiest solution is to call force_emit_signals method directly
        after the initialization of the beamline object
        """
        pass

    # Moved from HardwareObjectNode
    def clear_gevent(self) -> None:
        """Clear gevent tasks, called when disconnecting a HardwareObject.

        Override in subclasses as needed.
        """
        self.update_state(self.STATES.UNKNOWN)

    # Signal handling functions:
    def emit(self, signal: Union[str, object, Any], *args) -> None:
        """Emit signal. Accepts both multiple args and a single tuple of args.

        TODO: This function would be unnecessary if all callers used
        ```python
        dispatcher.send(signal, self, *argtuple)
        ```

        Args:
            signal (Union[str, object, Any]): In practice a string, or dispatcher.
            *args (tuple): Arguments sent with signal.
        """

        signal = str(signal)

        if len(args) == 1:
            if isinstance(args[0], tuple):
                args = args[0]
        dispatcher.send(signal, self, *args)

    def connect(
        self,
        sender: Union[str, object, Any],
        signal: Union[str, Any],
        slot: Optional[Callable] = None,
    ) -> None:
        """Connect a signal sent by self to a slot.

        The functions provides syntactic sugar ; Instead of
        ```python
        self.connect(self, "signal", slot)
        ```
        it is possible to do
        ```python
        self.connect("signal", slot)
        ```

        TODO: This would be much nicer if refactored as
        ```python
        def connect(self, signal, slot, sender=None)
        ```

        Args:
            sender (Union[str, object, Any]): If a string, interprted as the signal.
            signal (Union[str, Any]): In practice a string, or dispatcher.
            Any if sender is a string interpreted as the slot.
            slot (Optional[Callable], optional): In practice a functon or method.
            Defaults to None.

        Raises:
            ValueError: If slot is None and "sender" parameter is not a string.
        """

        if slot is None:
            if isinstance(sender, str):
                slot = signal
                signal = sender
                sender = self
            else:
                raise ValueError("invalid slot (None)")

        signal = str(signal)

        dispatcher.connect(slot, signal, sender)

        self.connect_dict[sender] = {"signal": signal, "slot": slot}

        if hasattr(sender, "connect_notify"):
            sender.connect_notify(signal)

    def disconnect(
        self,
        sender: Union[str, object, Any],
        signal: Union[str, Any],
        slot: Optional[Callable] = None,
    ) -> None:
        """Disconnect a signal sent by self to a slot.

        The functions provides syntactic sugar ; Instead of
        ```python
        self.connect(self, "signal", slot)
        ```
        it is possible to do
        ```python
        self.connect("signal", slot)
        ```

        TODO: This would be much nicer if refactored as
        ```python
        def disconnect(self, signal, slot, sender=None): ...
        ```

        Args:
            sender (Union[str, object, Any]): If a string, interprted as the signal.
            signal (Union[str, Any]): In practice a string, or dispatcher.
            Any if sender is a string interpreted as the slot.
            slot (Optional[Callable], optional): In practice a functon or method.
            Defaults to None.

        Raises:
            ValueError: If slot is None and "sender" parameter is not a string.
        """
        if slot is None:
            if isinstance(sender, str):
                slot = signal
                signal = sender
                sender = self
            else:
                raise ValueError("invalid slot (None)")

        signal = str(signal)

        dispatcher.disconnect(slot, signal, sender)

        if hasattr(sender, "disconnect_notify"):
            sender.disconnect_notify(signal)

    # def connect_notify(self, signal):
    #     pass
    #
    # def disconnect_notify(self, signal):
    #     pass


class HardwareObject(ConfiguredObject, HardwareObjectNode, HardwareObjectMixin):
    """Xml-configured hardware object"""

    def __init__(self, rootName: str) -> None:
        """
        Args:
            rootName (str): Name.
        """
        ConfiguredObject.__init__(self, rootName)
        HardwareObjectNode.__init__(self, rootName)
        HardwareObjectMixin.__init__(self)

    def __getstate__(self) -> str:

        # NBNB Needs updating

        return self.load_name

    def __setstate__(self, name: str) -> None:
        # NB Must be here - importing at top level leads to circular imports
        from .HardwareRepository import get_hardware_repository

        # NBNB Needs updating

        obj = get_hardware_repository().get_hardware_object(name)
        self.__dict__.update(obj.__dict__)

    def __getattr__(self, attr: str) -> Union["CommandObject", Any]:
        if attr.startswith("__"):
            raise AttributeError(attr)

        try:
            return CommandContainer.__getattr__(self, attr)
        except AttributeError:
            try:
                return super().__getattr__(attr)
            except AttributeError:
                raise AttributeError(attr)

    def commit_changes(self) -> None:
        """Commit last changes back to configuration."""

        # NB Must be here - importing at top level leads to circular imports
        from .HardwareRepository import get_hardware_repository

        def get_changes(node: Self) -> Union[list, List[tuple], Any]:
            updates = list(node._property_set.get_changes())
            if node:
                for subnode in node:
                    updates += get_changes(subnode)

            if isinstance(node, HardwareObject):
                if updates:
                    get_hardware_repository().update(node.load_name, updates)
                return []
            else:
                return updates

        get_changes(self)

    def rewrite_xml(self, xml: Union[bytes, Any]) -> None:
        """Rewrite XML conifguration file.

        Args:
            xml (Union[bytes, Any]): XML source to write to file.
        """

        # NB Must be here - importing at top level leads to circular imports
        from .HardwareRepository import get_hardware_repository

        get_hardware_repository().rewrite_xml(self.load_name, xml)

    def xml_source(self) -> Union[str, Any]:
        """Get XML configuration source.

        Returns:
            Union[str, Any]: XML source.
        """

        # NB Must be here - importing at top level leads to circular imports
        from .HardwareRepository import get_hardware_repository

        return get_hardware_repository().xml_source[self.load_name]


HardwareObjectYaml = HardwareObject

# class HardwareObjectYaml(ConfiguredObject, HardwareObjectMixin):
#     """Yaml-configured hardware object.
#
#     For use when we move confiugration out of xml and into yaml.
#
#     The class is needed only to provide a single superclass
#     that combines ConfiguredObject and HardwareObjectMixin"""
#
#     def __init__(self, name: str) -> None:
#         """
#         Args:
#             name (str): Name.
#         """
#         ConfiguredObject.__init__(self, name)
#         HardwareObjectMixin.__init__(self)


class Procedure(HardwareObject):
    """Procedure"""

    def __init__(self, name: str) -> None:
        """
        Args:
            name (str): Name.
        """
        HardwareObject.__init__(self, name)

    def userName(self) -> str:
        """Get procedure user name.

        Returns:
            str: Username.
        """
        uname = self.get_property("username")
        if uname is None:
            return str(self.name())
        else:
            return uname

    def GUI(self, parent: Any) -> None:
        pass


class Device(HardwareObject):
    """Old superclass for devices

    Signals:

        - "deviceReady"

        - "deviceNotReady"

    NB Deprecated - should be replaced by AbstractActuator"""

    (NOTREADY, READY) = (0, 1)  # device states

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.state = Device.NOTREADY

    def set_is_ready(self, ready):
        if ready and self.state == Device.NOTREADY:
            self.state = Device.READY
            self.emit("deviceReady")
        elif not ready and self.state == Device.READY:
            self.state = Device.NOTREADY
            self.emit("deviceNotReady")

    def is_ready(self):
        return self.state == Device.READY

    def userName(self):
        # TODO standardise on 'username' or 'user_name' globaly
        uname = self.get_property("username")
        if uname is None:
            return str(self.name())
        else:
            return uname


class DeviceContainer:
    """Device ocntainer class - old style

    NB Deprecated. Once DeviceContainerNode is removed,
    this clould be merged into Equipment"""

    def __init__(self):
        pass

    def get_devices(self):
        devices = []

        for item in dir(self):
            if isinstance(item, Device):
                devices.append(item)
            elif isinstance(item, DeviceContainer):
                devices += item.get_devices()

        return devices

    def get_device(self, device_name):
        devices = self.get_devices()

        for device in devices:
            if str(device.name()) == device_name:
                return device

    def get_device_by_role(self, role):
        # TODO This gives a pylint error, since get_object_by_roleis not in a superclass
        # it is available in the subclases that use this, but fixing this
        # would make more sense in connection with a general refactoring of
        # Device / DeciveContainer/Equipment
        item = self.get_object_by_role(role)

        if isinstance(item, Device):
            return item

    def clear_gevent(self):
        pass


class DeviceContainerNode(HardwareObjectNode, DeviceContainer):
    """Class serves solely to provide a single supercalss
    combining HardwareObjectNode and DeviceContaine

    TODO.This class is Deprecated.

    it is only used once,
    in HardwareObjectFileParser.HardwareObjectHandler.startElement
    And that use looks like it could be replaced by something else"""


class Equipment(HardwareObject, DeviceContainer):
    """Equipment class -old style

    Signals:

        - equipmentReady"

        - "equipmentNotReady"

    NB This class needs refactoring. Since many (soon: all??) contained
     objects are no longer of class Device, the code in here is unlikely to work."""

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        DeviceContainer.__init__(self)

        self.__ready = None

    def _init(self):
        for device in self.get_devices():
            self.connect(device, "deviceReady", self.__device_ready)
            self.connect(device, "deviceNotReady", self.__device_not_ready)

        self.__device_ready()

    def __device_ready(self):
        ready = True
        for device in self.get_devices():
            ready = ready and device.is_ready()
            if not ready:
                break

        if self.__ready != ready:
            self.__ready = ready

            if self.is_ready():
                self.emit("equipmentReady")
            else:
                self.emit("equipmentNotReady")

    def __device_not_ready(self):
        if self.__ready:
            self.__ready = False
            self.emit("equipmentNotReady")

    def is_ready(self):
        return self.is_valid() and self.__ready

    def is_valid(self):
        return True

    def userName(self):
        uname = self.get_property("username")
        if uname is None:
            return str(self.name())
        else:
            return uname


class Null:
    """
    This class ignores all parameters passed when constructing or
    calling instances and traps all attribute and method requests.
    Instances of it always (and reliably) do 'nothing'.

    The code might benefit from implementing some further special
    Python methods depending on the context in which its instances
    are used. Especially when comparing and coercing Null objects
    the respective methods' iimplementation will depend very much
    on the environment and, hence, these special methods are not
    provided here.
    """

    def __init__(self, *args, **kwargs):
        "Ignore parameters."
        return None

    def __call__(self, *args, **kwargs):
        "Ignore method calls."
        return self

    def __bool__(self):
        return 0

    def __getattr__(self, mname):
        "Ignore attribute requests."
        return self

    def __setattr__(self, name, value):
        "Ignore attribute setting."
        return self

    def __delattr__(self, name):
        "Ignore deleting attributes."
        return self

    def __repr__(self):
        "Return a string representation."
        return "<Null>"

    def __str__(self):
        "Convert to a string and return it."
        return "Null"
