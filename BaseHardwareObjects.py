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


from __future__ import absolute_import

import logging

from warnings import warn

from HardwareRepository.dispatcher import dispatcher
from HardwareRepository.CommandContainer import CommandContainer
from HardwareRepository.ConvertUtils import string_types


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


class HardwareObjectNode:
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
    def setUserFileDirectory(user_file_directory):
        HardwareObjectNode.user_file_directory = user_file_directory

    def name(self):
        return self.__name

    def setName(self, name):
        self.__name = name

    def getRoles(self):
        return list(self._objects_by_role.keys())

    def setPath(self, path):
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
                self.setProperty(attr, value)
            else:
                self.__dict__[attr] = value
        except AttributeError:
            self.__dict__[attr] = value

    def __getitem__(self, key):
        if isinstance(key, string_types):
            objectName = key

            try:
                i = self.__objects_names.index(objectName)
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

            if i < len(self.__objects_names):
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
            i = self.__objects_names.index(name)
        except ValueError:
            objects_names_index = len(self.__objects_names)
            self.__objects_names.append(None)
            objects_index = len(self.__objects)
            self.__objects.append(None)
            objects_index_2 = -1
        else:
            objects_names_index = -1
            objects_index = i
            objects_index_2 = len(self.__objects[i])
            self.__objects[i].append(None)

        self.__references.append(
            (reference, name, role, objects_names_index, objects_index, objects_index_2)
        )

    def resolveReferences(self):
        # NB Must be here - importing at top level leads to circular imports
        from .HardwareRepository import getHardwareRepository
        while len(self.__references) > 0:
            reference, name, role, objects_names_index, objects_index, objects_index_2 = (
                self.__references.pop()
            )

            hw_object = getHardwareRepository().getHardwareObject(
                reference
            )

            if hw_object is not None:
                self._objects_by_role[role] = hw_object
                hw_object.__role = role

                if objects_names_index >= 0:
                    self.__objects_names[objects_names_index] = role
                    self.__objects[objects_index] = [hw_object]
                else:
                    self.__objects[objects_index][objects_index_2] = hw_object
            else:
                if objects_names_index >= 0:
                    del self.__objects_names[objects_names_index]
                    del self.__objects[objects_index]
                else:
                    del self.__objects[objects_index][objects_index_2]
                    if not self.objects[objects_index]:
                        del self.objects[objects_index]

        for hw_object in self:
            hw_object.resolveReferences()

    def addObject(self, name, hw_object, role=None):
        if hw_object is None:
            return
        elif role is not None:
            role = str(role).lower()
            self._objects_by_role[role] = hw_object
            hw_object.__role = role

        try:
            i = self.__objects_names.index(name)
        except ValueError:
            self.__objects_names.append(name)
            self.__objects.append([hw_object])
        else:
            self.__objects[i].append(hw_object)

    def hasObject(self, objectName):
        return objectName in self.__objects_names

    def getObjects(self, objectName):
        try:
            i = self.__objects_names.index(objectName)
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
            if role in obj._objects_by_role:
                return obj._objects_by_role[role]

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

                if objects:
                    obj = objects.pop()
                else:
                    break

    def objectsNames(self):
        return self.__objects_names[:]

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

        self._property_set[name] = value
        self._property_set.set_property_path(name, self._path + "/" + str(name))

    def getProperty(self, name, default_value=None):
        return self._property_set.get(str(name), default_value)

    def getProperties(self):
        return self._property_set

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


class HardwareObject(HardwareObjectNode, CommandContainer):
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

    def connect_notify(self, signal):
        pass

    def connectNotify(self, signal):
        logging.getLogger("HWR").warning("DeprecationWarning: connectNotify is deprecated. Use connect_notify instead")
        warn("connectNotify is deprecated. Use connect_notify instead", DeprecationWarning)

        self.connect_notify(signal)

    def disconnect_notify(self, signal):
        pass
        
    def disconnectNotify(self, signal):
        logging.getLogger("HWR").warning("DeprecationWarning: disconnectNotify is deprecated. Use disconnect_notify instead")
        warn("disconnectNotify is deprecated. Use disconnect_notify instead", DeprecationWarning)

        self.disconnect_notify(signal)

    def commitChanges(self):
        """Commit last changes"""
        # NB Must be here - importing at top level leads to circular imports
        from .HardwareRepository import getHardwareRepository

        def get_changes(node):
            updates = list(node._property_set.get_changes())
            if len(node) > 0:
                for n in node:
                    updates += get_changes(n)

            if isinstance(node, HardwareObject):
                if len(updates) > 0:
                    getHardwareRepository().update(node.name(), updates)
                return []
            else:
                return updates

        get_changes(self)

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


class Device(HardwareObject):
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

    def setIsReady(self, ready):
        logging.getLogger("HWR").warning("DeprecationWarning: setIsReady is deprecated. Use set_is_ready instead")
        warn("setIsReady is deprecated. Use set_is_ready instead", DeprecationWarning)
        self.set_is_ready(ready)

    def isReady(self):
        logging.getLogger("HWR").warning("DeprecationWarning: isReady is deprecated. Use is_ready instead")
        warn("isReady is deprecated. Use is_ready instead", DeprecationWarning)
        return self.is_ready()

    def is_ready(self):
        return self.state == Device.READY

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

    def isReady(self):
        logging.getLogger("HWR").warning("DeprecationWarning: isReady is deprecated. Use is_ready instead")
        warn("isReady is deprecated. Use is_ready instead", DeprecationWarning)
        return self.is_ready()

    def is_ready(self):
        return self.isValid() and self.__ready

    def is_valid(self):
        return True

    def isValid(self):
        logging.getLogger("HWR").warning("DeprecationWarning: isValid is deprecated. Use is_valid instead")
        warn("isValid is deprecated. Use is_valid instead", DeprecationWarning)
        return self.is_valid()

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
