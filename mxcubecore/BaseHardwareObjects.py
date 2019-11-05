from __future__ import absolute_import

import logging
from collections import OrderedDict

from HardwareRepository.dispatcher import dispatcher
from HardwareRepository.CommandContainer import CommandContainer
from HardwareRepository.ConvertUtils import string_types


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

        Returns:

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
        procedure_names = self.__class__._procedure_names
        result = {}
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


class HardwareObjectNode:
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

    def update_values(self):
        """Method called from Qt bricks to ensure that bricks have values
           after the initialization.
           Problem arrise when a hardware object is used by several bricks.
           If first brick connects to some signal emited by a brick then
           other bricks connecting to the same signal will no receive the
           values on the startup.
           The easiest solution is to call update_values method directly
           after getHardwareObject and connect.

           Normaly this method would emit all values
        """
        return

    def clear_gevent(self):
        pass

    def print_log(self, log_type="HWR", level="debug", msg=""):
        if hasattr(logging.getLogger(log_type), level):
            getattr(logging.getLogger(log_type), level)(msg)


class HardwareObjectMixin(HardwareObjectNode, CommandContainer):
    """HardwareObject functionality, for either xml- or yaml-configured subclasses"""
    def __init__(self, rootName):
        HardwareObjectNode.__init__(self, rootName)
        CommandContainer.__init__(self)
        self.connect_dict = {}

    def _init(self):
        # 'protected' post-initialization method
        pass

    def init(self):
        # 'public' post-initialization method
        pass

    def __getstate__(self):
        return self.name()

    def __setstate__(self, name):
        # NB Must be here - importing at top level leads to circular imports
        from .HardwareRepository import getHardwareRepository

        o = getHardwareRepository().getHardwareObject(name)
        self.__dict__.update(o.__dict__)

    def __bool__(self):
        return True

    def __nonzero__(self):
        return True

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

    def emit(self, signal, *args):

        signal = str(signal)

        if len(args) == 1:
            if isinstance(args[0], tuple):
                args = args[0]
        dispatcher.send(signal, self, *args)

    def connect(self, sender, signal, slot=None):
        if slot is None:
            # if type(sender) == bytes:
            if isinstance(sender, string_types):
                # provides syntactic sugar ; for
                # self.connect(self, "signal", slot)
                # it is possible to do
                # self.connect("signal", slot)
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
        if slot is None:
            # TODO 2to3
            # if type(sender) == bytes:
            if isinstance(sender, string_types):
                # provides syntactic sugar ; for
                # self.connect(self, "signal", slot)
                # it is possible to do
                # self.connect("signal", slot)
                slot = signal
                signal = sender
                sender = self
            else:
                raise ValueError("invalid slot (None)")

        signal = str(signal)

        dispatcher.disconnect(slot, signal, sender)

        if hasattr(sender, "disconnectNotify"):
            sender.disconnectNotify(signal)

    def connectNotify(self, signal):
        pass

    def disconnectNotify(self, signal):
        pass

    def commitChanges(self):
        """Commit last changes"""
        # NB Must be here - importing at top level leads to circular imports
        from .HardwareRepository import getHardwareRepository

        def getChanges(node):
            updates = list(node._propertySet.getChanges())
            if len(node) > 0:
                for n in node:
                    updates += getChanges(n)

            if isinstance(node, HardwareObject):
                if len(updates) > 0:
                    getHardwareRepository().update(node.name(), updates)
                return []
            else:
                return updates

        getChanges(self)

    def rewrite_xml(self, xml):
        """Rewrite XML file"""
        # NB Must be here - importing at top level leads to circular imports
        from .HardwareRepository import getHardwareRepository

        getHardwareRepository().rewrite_xml(self.name(), xml)

    def xml_source(self):
        """Get XML source code"""
        # NB Must be here - importing at top level leads to circular imports
        from .HardwareRepository import getHardwareRepository

        return getHardwareRepository().xml_source[self.name()]

class HardwareObject(HardwareObjectMixin, HardwareObjectNode, CommandContainer):
    """Xml-configured hardware object"""
    pass

class HardwareObjectYaml(HardwareObjectMixin, ConfiguredObject, CommandContainer):
    """Yaml-configured hardware object"""
    pass

class Procedure(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

    def addCommand(self, *args, **kwargs):
        return HardwareObject.addCommand(self, *args, **kwargs)

    def userName(self):
        uname = self.getProperty("username")
        if uname is None:
            return str(self.name())
        else:
            return uname

    def GUI(self, parent):
        pass


class Device(HardwareObject):
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

    def isReady(self):
        return self.state == Device.READY

    def is_ready(self):
        return self.isReady()

    def userName(self):
        uname = self.getProperty("username")
        if uname is None:
            return str(self.name())
        else:
            return uname


class DeviceContainer:
    def __init__(self):
        pass

    def getDevices(self):
        devices = []

        for item in dir(self):
            if isinstance(item, Device):
                devices.append(object)
            elif isinstance(item, DeviceContainer):
                devices += item.getDevices()

        return devices

    def getDevice(self, deviceName):
        devices = self.getDevices()

        for device in devices:
            if str(device.name()) == deviceName:
                return device

    def getDeviceByRole(self, role):
        item = self.getObjectByRole(role)

        if isinstance(item, Device):
            return item


class DeviceContainerNode(HardwareObjectNode, DeviceContainer):
    pass


class Equipment(HardwareObject, DeviceContainer):
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
            ready = ready and device.isReady()
            if not ready:
                break

        if self.__ready != ready:
            self.__ready = ready

            if self.isReady():
                self.emit("equipmentReady")
            else:
                self.emit("equipmentNotReady")

    def __deviceNotReady(self):
        if self.__ready:
            self.__ready = False
            self.emit("equipmentNotReady")

    def isReady(self):
        return self.isValid() and self.__ready

    def is_ready(self):
        return self.isReady()

    def isValid(self):
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
