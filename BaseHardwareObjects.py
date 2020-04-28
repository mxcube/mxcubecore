from __future__ import absolute_import

import abc
import enum
from collections import OrderedDict
import logging
from gevent import event, Timeout

from HardwareRepository.dispatcher import dispatcher
from HardwareRepository.CommandContainer import CommandContainer
from HardwareRepository.ConvertUtils import string_types


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
        #
        return result


class PropertySet(dict):
    def __init__(self):
        dict.__init__(self)

        self.__propertiesChanged = {}
        self.__propertiesPath = {}

    def setPropertyPath(self, name, path):
        name = str(name)
        self.__propertiesPath[name] = path

    def getPropertiesPath(self):
        return iter(self.__propertiesPath.items())

    def __setitem__(self, name, value):
        name = str(name)

        if name in self and str(value) != str(self[name]):
            self.__propertiesChanged[name] = str(value)

        dict.__setitem__(self, str(name), value)

    def getChanges(self):
        for propertyName, value in self.__propertiesChanged.items():
            yield (self.__propertiesPath[propertyName], value)

        self.__propertiesChanged = {}  # reset changes at commit


class HardwareObjectNode(object):
    def __init__(self, nodeName):
        """Constructor"""
        self.__dict__["_propertySet"] = PropertySet()
        self.__objectsNames = []
        self.__objects = []
        self._objectsByRole = {}
        self._path = ""
        self.__name = nodeName
        self.__references = []

    @staticmethod
    def setUserFileDirectory(user_file_directory):
        HardwareObjectNode.user_file_directory = user_file_directory

    def name(self):
        return self.__name

    def setName(self, name):
        self.__name = name

    def getRoles(self):
        return list(self._objectsByRole.keys())

    def setPath(self, path):
        """Set the 'path' of the Hardware Object in the XML file describing it
        (the path follows the XPath syntax)

        Parameters :
          path -- string representing the path of the Hardware Object in its file"""
        self._path = path

    def __iter__(self):
        for i in range(len(self.__objectsNames)):
            for object in self.__objects[i]:
                yield object

    def __len__(self):
        return sum(map(len, self.__objects))

    def __getattr__(self, attr):
        if attr.startswith("__"):
            raise AttributeError(attr)

        try:
            return self.__dict__["_propertySet"][attr]
        except KeyError:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        try:
            if attr not in self.__dict__ and attr in self._propertySet:
                self.setProperty(attr, value)
            else:
                self.__dict__[attr] = value
        except AttributeError:
            self.__dict__[attr] = value

    def __getitem__(self, key):
        if isinstance(key, string_types):
            objectName = key

            try:
                i = self.__objectsNames.index(objectName)
            except BaseException:
                raise KeyError
            else:
                obj = self.__objects[i]
                if len(obj) == 1:
                    return obj[0]
                else:
                    return obj
        elif isinstance(key, int):
            i = key

            if i < len(self.__objectsNames):
                obj = self.__objects[i]
                if len(obj) == 1:
                    return obj[0]
                else:
                    return obj
            else:
                raise IndexError
        else:
            raise TypeError

    def addReference(self, name, reference, role=None):
        role = str(role).lower()

        try:
            i = self.__objectsNames.index(name)
        except ValueError:
            objectsNamesIndex = len(self.__objectsNames)
            self.__objectsNames.append(None)
            objectsIndex = len(self.__objects)
            self.__objects.append(None)
            objectsIndex2 = -1
        else:
            objectsNamesIndex = -1
            objectsIndex = i
            objectsIndex2 = len(self.__objects[i])
            self.__objects[i].append(None)

        self.__references.append(
            (reference, name, role, objectsNamesIndex, objectsIndex, objectsIndex2)
        )

    def resolveReferences(self):
        # NB Must be here - importing at top level leads to circular imports
        from .HardwareRepository import getHardwareRepository

        while len(self.__references) > 0:
            reference, name, role, objectsNamesIndex, objectsIndex, objectsIndex2 = (
                self.__references.pop()
            )

            hw_object = getHardwareRepository().getHardwareObject(reference)

            if hw_object is not None:
                self._objectsByRole[role] = hw_object
                hw_object.__role = role

                if objectsNamesIndex >= 0:
                    self.__objectsNames[objectsNamesIndex] = role
                    self.__objects[objectsIndex] = [hw_object]
                else:
                    self.__objects[objectsIndex][objectsIndex2] = hw_object
            else:
                if objectsNamesIndex >= 0:
                    del self.__objectsNames[objectsNamesIndex]
                    del self.__objects[objectsIndex]
                else:
                    del self.__objects[objectsIndex][objectsIndex2]
                    if len(self.objects[objectsIndex]) == 0:
                        del self.objects[objectsIndex]

        for hw_object in self:
            hw_object.resolveReferences()

    def addObject(self, name, hw_object, role=None):
        if hw_object is None:
            return
        elif role is not None:
            role = str(role).lower()
            self._objectsByRole[role] = hw_object
            hw_object.__role = role

        try:
            i = self.__objectsNames.index(name)
        except ValueError:
            self.__objectsNames.append(name)
            self.__objects.append([hw_object])
        else:
            self.__objects[i].append(hw_object)

    def hasObject(self, objectName):
        return objectName in self.__objectsNames

    def getObjects(self, objectName):
        try:
            i = self.__objectsNames.index(objectName)
        except ValueError:
            pass
        else:
            for obj in self.__objects[i]:
                yield obj

    def getObjectByRole(self, role):
        object = None
        obj = self
        objects = []
        role = str(role).lower()

        while True:
            if role in obj._objectsByRole:
                return obj._objectsByRole[role]

            for object in obj:
                objects.append(object)

            try:
                obj = objects.pop()
            except IndexError:
                break
            else:
                object = obj.getObjectByRole(role)
                if object is not None:
                    return object

                if len(objects) > 0:
                    obj = objects.pop()
                else:
                    break

    def objectsNames(self):
        return self.__objectsNames[:]

    def setProperty(self, name, value):
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
            except BaseException:
                try:
                    value = float(value)
                except BaseException:
                    if value == "True":
                        value = True
                    elif value == "False":
                        value = False

        self._propertySet[name] = value
        self._propertySet.setPropertyPath(name, self._path + "/" + str(name))

    def getProperty(self, name, default_value=None):
        return self._propertySet.get(str(name), default_value)

    def getProperties(self):
        return self._propertySet

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

    def update_values(self):
        """Update values for all internal attributes

        The method is called from Qt bricks to ensure that bricks have values
        after the initialization.
        Problem arrise when a hardware object is used by several bricks.
        If first brick connects to some signal emited by a brick then
        other bricks connecting to the same signal will not receive the
        values on the startup.
        The easiest solution is to call update_values method directly
        after getHardwareObject and connect.

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

        if hasattr(sender, "connectNotify"):
            sender.connectNotify(signal)

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

        if hasattr(sender, "disconnectNotify"):
            sender.disconnectNotify(signal)

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
        from .HardwareRepository import getHardwareRepository

        obj = getHardwareRepository().getHardwareObject(name)
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

        from .HardwareRepository import getHardwareRepository

        def get_changes(node):
            updates = list(node._propertySet.getChanges())
            if node:
                for subnode in node:
                    updates += get_changes(subnode)

            if isinstance(node, HardwareObject):
                if updates:
                    getHardwareRepository().update(node.name(), updates)
                return []
            else:
                return updates

        get_changes(self)

    def rewrite_xml(self, xml):
        """Rewrite XML conifguration file

        NB Must be here - importing at top level leads to circular imports"""
        from .HardwareRepository import getHardwareRepository

        getHardwareRepository().rewrite_xml(self.name(), xml)

    def xml_source(self):
        """Get XML configuration source

        NB Must be here - importing at top level leads to circular imports"""
        from .HardwareRepository import getHardwareRepository

        return getHardwareRepository().xml_source[self.name()]


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
        uname = self.getProperty("username")
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

    def setIsReady(self, ready):
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
        uname = self.getProperty("username")
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

    def getDevices(self):
        devices = []

        for item in dir(self):
            if isinstance(item, Device):
                devices.append(item)
            elif isinstance(item, DeviceContainer):
                devices += item.getDevices()

        return devices

    def getDevice(self, deviceName):
        devices = self.getDevices()

        for device in devices:
            if str(device.name()) == deviceName:
                return device

    def getDeviceByRole(self, role):
        # TODO This gives a pylint error, since getObjectByRoleis not in a superclass
        # it is available in the subclases that use this, but fixing this
        # would make more sense in connection with a general refactoring of
        # Device / DeciveContainer/Equipment
        item = self.getObjectByRole(role)

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
        for device in self.getDevices():
            self.connect(device, "deviceReady", self.__deviceReady)
            self.connect(device, "deviceNotReady", self.__deviceNotReady)

        self.__deviceReady()

    def __deviceReady(self):
        ready = True
        for device in self.getDevices():
            ready = ready and device.is_ready()
            if not ready:
                break

        if self.__ready != ready:
            self.__ready = ready

            if self.is_ready():
                self.emit("equipmentReady")
            else:
                self.emit("equipmentNotReady")

    def __deviceNotReady(self):
        if self.__ready:
            self.__ready = False
            self.emit("equipmentNotReady")

    def is_ready(self):
        return self.is_valid() and self.__ready

    def is_valid(self):
        return True

    def userName(self):
        uname = self.getProperty("username")
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
    the respective methods' implementation will depend very much
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
