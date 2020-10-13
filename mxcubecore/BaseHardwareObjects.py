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

import enum
from collections import OrderedDict
import logging
from gevent import event, Timeout

from HardwareRepository.dispatcher import dispatcher
from HardwareRepository.CommandContainer import CommandContainer
from HardwareRepository.ConvertUtils import string_types


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
    """Placeholder enumeration for HardwareObject-specific states
    """

    UNKNOWN = "UNKNOWN"


class ConfiguredObject(object):
    """Superclass for classes that take configuration from YAML files"""

    # Roles of defined objects and the category they belong to
    # NB the double underscore is deliberate - attribute must be hidden from subclasses
    __content_roles = []

    # Procedure names - placeholder.
    # Will be replaced by a set in any subclasses that can contain procedures
    # Note that _procedure_names may *not* be set if it is already set in a superclass
    _procedure_names = None

    def __init__(self, name):

        self.name = name

        self._objects = OrderedDict((role, None) for role in self.all_roles)

    def _init(self):
        """Object initialisation - executed *before* loading contents"""
        pass

    def init(self):
        """Object initialisation - executed *after* loading contents"""
        pass

    def replace_object(self, role, new_object):
        """Replace already defined Object with a new one - for runtime use

        Args:
            role (text_str): Role name of contained Object
            new_object (Optional[ConfiguredObject]): New contained Object
        """
        if role in self._objects:
            self._objects[role] = new_object
        else:
            raise ValueError("Unknown contained Object role: %s" % role)

    # NB this function must be re-implemented in nested subclasses
    @property
    def all_roles(self):
        """Tuple of all content object roles, indefinition and loading order

        Returns:
            tuple[text_str, ...]
        """
        return tuple(self.__content_roles)

    @property
    def all_objects_by_role(self):
        """All contained Objects mapped by role (in specification order).

            Includes objects defined in subclasses.

        Returns:
            OrderedDict[text_str, ConfiguredObject]:

        """
        return self._objects.copy()

    @property
    def procedures(self):
        """Procedures attached to this object  mapped by name (in specification order).

        Returns:
            OrderedDict[text_str, ConfiguredObject]:

        """
        procedure_names = self.__class__._procedure_names
        result = OrderedDict()
        if procedure_names:
            for name in procedure_names:
                procedure = getattr(self, name)
                if procedure is not None:
                    result[name] = procedure

        return result


class PropertySet(dict):
    def __init__(self):
        dict.__init__(self)

        self.__properties_changed = {}
        self.__properties_path = {}

    def set_property_path(self, name, path):
        name = str(name)
        self.__properties_path[name] = path

    def get_properties_path(self):
        return iter(self.__properties_path.items())

    def __setitem__(self, name, value):
        name = str(name)

        if name in self and str(value) != str(self[name]):
            self.__properties_changed[name] = str(value)

        dict.__setitem__(self, str(name), value)

    def get_changes(self):
        for property_name, value in self.__properties_changed.items():
            yield (self.__properties_path[property_name], value)

        self.__properties_changed = {}  # reset changes at commit


class HardwareObjectNode(object):
    
    def __init__(self, node_name):
        """Constructor"""
        self.__dict__["_property_set"] = PropertySet()
        self.__objects_names = []
        self.__objects = []
        self._objects_by_role = {}
        self._path = ""
        self.__name = node_name
        self.__references = []

    @staticmethod
    def set_user_file_directory(user_file_directory):
        HardwareObjectNode.user_file_directory = user_file_directory

    def name(self):
        return self.__name

    def set_name(self, name):
        self.__name = name

    def get_roles(self):
        return list(self._objects_by_role.keys())

    def set_path(self, path):
        """Set the 'path' of the Hardware Object in the XML file describing it
        (the path follows the XPath syntax)

        Parameters :
          path -- string representing the path of the Hardware Object in its file"""
        self._path = path

    def __iter__(self):
        for i in range(len(self.__objects_names)):
            for object in self.__objects[i]:
                yield object

    def __len__(self):
        return sum(map(len, self.__objects))

    def __getattr__(self, attr):
        if attr.startswith("__"):
            raise AttributeError(attr)

        try:
            return self.__dict__["_property_set"][attr]
        except KeyError:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        try:
            if attr not in self.__dict__ and attr in self._property_set:
                self.set_property(attr, value)
            else:
                self.__dict__[attr] = value
        except AttributeError:
            self.__dict__[attr] = value

    def __getitem__(self, key):
        if isinstance(key, string_types):
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

    def add_reference(self, name, reference, role=None):
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

    def resolve_references(self):
        # NB Must be here - importing at top level leads to circular imports
        from .HardwareRepository import get_hardware_repository

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
                    if len(self.objects[objects_index]) == 0:
                        del self.objects[objects_index]

        for hw_object in self:
            hw_object.resolve_references()

    def add_object(self, name, hw_object, role=None):
        if hw_object is None:
            return
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

    def has_object(self, object_name):
        return object_name in self.__objects_names

    def get_objects(self, object_name):
        try:
            index = self.__objects_names.index(object_name)
        except ValueError:
            pass
        else:
            for obj in self.__objects[index]:
                yield obj

    def get_object_by_role(self, role):
        object = None
        obj = self
        objects = []
        role = str(role).lower()

        while True:
            if role in obj._objects_by_role:
                return obj._objects_by_role[role]

            for object in obj:
                objects.append(object)

            try:
                obj = objects.pop()
            except IndexError:
                break
            else:
                object = obj.get_object_by_role(role)
                if object is not None:
                    return object

                if len(objects) > 0:
                    obj = objects.pop()
                else:
                    break

    def objects_names(self):
        return self.__objects_names[:]

    def set_property(self, name, value):
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

    def get_property(self, name, default_value=None):
        return self._property_set.get(str(name), default_value)

    def get_properties(self):
        return self._property_set

    def print_log(self, log_type="HWR", level="debug", msg=""):
        if hasattr(logging.getLogger(log_type), level):
            getattr(logging.getLogger(log_type), level)(msg)


class HardwareObjectMixin(CommandContainer):
    """ Functionality for either xml- or yaml-configured HardwareObjects

    Signals emited:

        - stateChanged

        - specificStateChanged"""

    #: enum.Enum: General states, shared between all HardwareObjects. Do *not* overridde
    STATES = HardwareObjectState

    #: enum.Enum: Placeholder for HardwareObject-specific states. To be overridden
    SPECIFIC_STATES = DefaultSpecificState

    def __init__(self):
        CommandContainer.__init__(self)

        # Container for connections to HardwareObject
        self.connect_dict = {}
        # event to handle waiting for object to be ready
        self._ready_event = event.Event()
        # Internal general state attribute, used to check for state changes
        self._state = None
        # Internal object-specific state attribute, used to check for state changes
        self._specific_state = None

    def __bool__(self):
        return True

    def __nonzero__(self):
        return True

    def _init(self):
        """'protected' post-initialization method. Override as needed

        For ConfiguredObjects called before loading contained objects"""
        self.update_state(self.STATES.UNKNOWN)

    def init(self):
        """"'public' post-initialization method. Override as needed

        For ConfiguredObjects called after loading contained objects"""
        pass

    def abort(self):
        """Immediately terminate HardwareObject action

        Should not happen in state READY"""
        if self.get_state() is self.STATES.READY:
            return

        # When overriding put active code here

    def stop(self):
        """Gentler (?) alternative to abort

        Override as necessary to implement"""
        self.abort()

    def get_state(self):
        """ Getter for state attribute

        Implementations must query the hardware directly, to ensure current results

        Returns:
            HardwareObjectState
        """
        return self._state

    def get_specific_state(self):
        """ Getter for specific_state attribute. Override if needed.

        Returns:
            HardwareObjectSpecificState or None
        """
        return self._specific_state

    def wait_ready(self, timeout=None):
        """Wait timeout seconds till object is ready.

        if timeout is None: wait forever.

        Args:
            timeout (s):

        Returns:
        """
        with Timeout(timeout, RuntimeError("Timeout waiting for status ready")):
            self._ready_event.wait(timeout=timeout)

    def is_ready(self):
        """Convenience function: Check if the object state is READY.

        The same effect could be achieved with 'self.get_state() == self.STATES.READY'

        Returns:
            (bool): True if ready, otherwise False.
        """
        return self._ready_event.is_set()

    def update_state(self, state=None):
        """Update self._state, and emit signal stateChanged if the state has changed

        Args:
            state (enum 'HardwareObjectState'): state
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

    def update_specific_state(self, state=None):
        """Update self._specific_state, and emit specificStateChanged if appropriate

        Args:
            state (enum.Enum): specific state - the enumeration will be sepcific for
            each HardwareObject class
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

    def re_emit_values(self):
        """Update values for all internal attributes

        The method is called from Qt bricks to ensure that bricks have values
        after the initialization.
        Problem arrise when a hardware object is used by several bricks.
        If first brick connects to some signal emited by a brick then
        other bricks connecting to the same signal will not receive the
        values on the startup.
        The easiest solution is to call re_emit_values method directly
        after get_hardware_object and connect.

        Should be expanded in subclasse with more updatable attributes
        (e.g. value, limits)
        """
        self.update_state()
        self.update_specific_state()

    # Moved from HardwareObjectNode
    def clear_gevent(self):
        """Clear gevent tasks, called when disconnecting a HardwareObject.

        Override in subclasses as needed.

        """
        self.update_state(self.STATES.UNKNOWN)

    # Signal handling functions:
    def emit(self, signal, *args):
        """Emit signal. Accepts both multiple args and a single tuple of args.

        TODO This function would be unnecessary if all callers used
        dispatcher.send(signal, self, *argtuple)

        Args:
            signal (hashable object): Signal. In practice a string, or dispatcher.Any
            *args (tuple): Arguments sent with signal"""

        signal = str(signal)

        if len(args) == 1:
            if isinstance(args[0], tuple):
                args = args[0]
        dispatcher.send(signal, self, *args)

    def connect(self, sender, signal, slot=None):
        """Connect a signal sent by self to a slot

        The functions provides syntactic sugar ; Instead of
        self.connect(self, "signal", slot)
        it is possible to do
        self.connect("signal", slot)

        TODO this would be much nicer if refactored as

            def connect(self, signal, slot, sender=None)

        Args:
            sender (object): If a string, interprted as the signal
            signal (Hashable object): In practice a string, or dispatcher.Any
                if sender is a string interpreted as the slot
            slot (Callable object): In practice a functon or method
        """

        if slot is None:
            if isinstance(sender, string_types):
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

    def disconnect(self, sender, signal, slot=None):
        """Disconnect a signal sent by self to a slot

        The functions provides syntactic sugar ; Instead of
        self.connect(self, "signal", slot)
        it is possible to do
        self.connect("signal", slot)

        TODO this would be much nicer if refactored as

            def disconnect(self, signal, slot, sender=None)

        Args:
            sender (object): If a string, interprted as the signal
            signal (Hashable object): In practice a string, or dispatcher.Any
            if sender is a string interpreted as the slot
            slot (Callable object): In practice a functon or method
        """
        if slot is None:
            if isinstance(sender, string_types):
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


class HardwareObject(HardwareObjectNode, HardwareObjectMixin):
    """Xml-configured hardware object"""

    def __init__(self, rootName):
        HardwareObjectNode.__init__(self, rootName)
        HardwareObjectMixin.__init__(self)
        self.log = logging.getLogger("HWR").getChild(self.__class__.__name__)
        self.user_log = logging.getLogger("user_log_level")

    def __getstate__(self):
        return self.name()

    def __setstate__(self, name):
        # NB Must be here - importing at top level leads to circular imports
        from .HardwareRepository import get_hardware_repository

        obj = get_hardware_repository().get_hardware_object(name)
        self.__dict__.update(obj.__dict__)

    def __getattr__(self, attr):
        if attr.startswith("__"):
            raise AttributeError(attr)

        try:
            return CommandContainer.__getattr__(self, attr)
        except AttributeError:
            try:
                return HardwareObjectNode.__getattr__(self, attr)
            except AttributeError:
                raise AttributeError(attr)

    def commit_changes(self):
        """Commit last changes back to configuration

        NB Must be here - importing at top level leads to circular imports
        """

        from .HardwareRepository import get_hardware_repository

        def get_changes(node):
            updates = list(node._property_set.get_changes())
            if node:
                for subnode in node:
                    updates += get_changes(subnode)

            if isinstance(node, HardwareObject):
                if updates:
                    get_hardware_repository().update(node.name(), updates)
                return []
            else:
                return updates

        get_changes(self)

    def rewrite_xml(self, xml):
        """Rewrite XML conifguration file

        NB Must be here - importing at top level leads to circular imports"""
        from .HardwareRepository import get_hardware_repository

        get_hardware_repository().rewrite_xml(self.name(), xml)

    def xml_source(self):
        """Get XML configuration source

        NB Must be here - importing at top level leads to circular imports"""
        from .HardwareRepository import get_hardware_repository

        return get_hardware_repository().xml_source[self.name()]


class HardwareObjectYaml(ConfiguredObject, HardwareObjectMixin):
    """Yaml-configured hardware object.

    For use when we move confiugration out of xml and into yaml.

    The class is needed only to provide a single superclass
    that combines ConfiguredObject and HardwareObjectMixin"""

    pass


class Procedure(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

    def userName(self):
        uname = self.get_property("username")
        if uname is None:
            return str(self.name())
        else:
            return uname

    def GUI(self, parent):
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

    pass


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
