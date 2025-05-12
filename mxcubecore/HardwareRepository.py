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

"""Gives access to the Hardware Objects contained in the Hardware Repository database

The Hardware Repository database is a set of XML files describing devices, equipments
and procedures on a beamline. Each XML file represent a Hardware Object.
The Hardware Repository module provides access to these Hardware Objects, and manages
connections to the Control Software (Spec or Taco Device Servers).
"""

from __future__ import (
    absolute_import,
    print_function,
)

import importlib
import logging
import os
import sys
import time
import traceback
import weakref
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Optional,
    Union,
)
from warnings import warn

from ruamel.yaml import YAML

from mxcubecore import (
    BaseHardwareObjects,
    HardwareObjectFileParser,
)
from mxcubecore.dispatcher import dispatcher
from mxcubecore.protocols_config import setup_commands_channels
from mxcubecore.utils.conversion import (
    make_table,
    string_types,
)

if TYPE_CHECKING:
    from mxcubecore.BaseHardwareObjects import HardwareObject

# If you want to write out copies of the file, use typ="rt" instead
# pure=True uses yaml version 1.2, with fewer gotchas for strange type conversions
yaml = YAML(typ="safe", pure=True)
# The following are not needed for load, but define the default style.
yaml.default_flow_style = False
yaml.indent(mapping=2, sequence=4, offset=2)


__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


_instance = None
TIMERS = []

beamline = None
BEAMLINE_CONFIG_FILE = "beamline_config.yml"


def load_from_yaml(
    configuration_file,
    role,
    yaml_export_directory: Optional[Path] = None,
    _container=None,
    _table=None,
):
    """

    Args:
        configuration_file (str):
        role (str): Role name of configured object, used as its name
        _container (ConfiguredObject): Container object for recursive loading
        _table Optional[List]: Internal, collecting summary output

    Returns:

    """
    global beamline

    column_names = ("role", "Class", "file", "Time (ms)", "Comment")
    if _table is None:
        # This is the topmopst call
        _table = []

    start_time = time.time()
    msg0 = ""
    result = None
    class_name = "None"

    # Get full path for configuration file
    if _instance is None:
        raise RuntimeError("HardwareRepository has not been initialised")
    configuration_path = _instance.find_in_repository(configuration_file)
    if configuration_path is None:
        msg0 = "File not found"

    if not msg0:
        # Load the configuration file
        with open(configuration_path, "r") as fp0:
            configuration = yaml.load(fp0)
        class_import = configuration.pop("class", None)
        if not class_import:
            if _container:
                msg0 = "No 'class' tag"
            else:
                # at top level we want to get the actual error
                raise ValueError("%s file lacks  'class' tag" % configuration_file)

    if not msg0:
        module_name, class_name = class_import.rsplit(".", 1)
        # For "a.b.c" equivalent to absolute import of "from a.b import c"
        try:
            cls = getattr(importlib.import_module(module_name), class_name)
        except Exception as ex:
            if _container:
                msg0 = "Error importing class"
                class_name = class_import
                print(
                    "Encountered Exception (continuing):\n%s" % traceback.format_exc()
                )
            else:
                # at top level we want to get the actual error
                raise

    if not msg0:
        try:
            # instantiate object
            result = cls(name=role)
            result._hwobj_container = _container
        except Exception:
            if _container:
                msg0 = "Error instantiating %s" % cls.__name__
                print(
                    "Encountered Exception (continuing):\n%s" % traceback.format_exc()
                )
            else:
                # at top level we want to get the actual error
                raise

    if _container is None:
        # We are loading the beamline object into HardwareRepository
        # and want the link to be set before _init or content loading
        beamline = result

    if not msg0:
        try:
            config = configuration.pop("configuration", {})
            # Set configuration with non-object properties.
            result._config = result.HOConfig(**config)

            # Initialise object
            result._init()
        except Exception:
            if _container:
                msg0 = "Error in %s._init()" % cls.__name__
            else:
                # at top level we want to get the actual error
                raise

    if not msg0:
        # Recursively load contained objects (of any type that the system can support)
        objects = configuration.pop("objects", {})

        setup_commands_channels(result, configuration)

        if _container is None:
            load_time = 1000 * (time.time() - start_time)
            msg1 = "Start loading contents:"
            _table.append(
                (role, class_name, configuration_file, "%.1d" % load_time, msg1)
            )
            msg0 = "Done loading contents"

        for role1, config_file in objects.items():
            fname, fext = os.path.splitext(config_file)
            if fext in (".yaml", ".yml"):
                fname = f"/{fname}"

                hwobj = load_from_yaml(
                    config_file,
                    role=role1,
                    yaml_export_directory=yaml_export_directory,
                    _container=result,
                    _table=_table,
                )
                if hwobj:
                    # only add if we successfully loaded the object
                    _instance.hardware_objects[fname] = hwobj

            elif fext == ".xml":
                msg1 = ""
                time0 = time.time()
                class_name1 = "None"
                try:
                    hwobj = _instance.get_hardware_object(fname)
                    if hwobj is None:
                        msg1 = "No object loaded"
                    else:
                        class_name1 = hwobj.__class__.__name__
                        _attach_xml_objects(yaml_export_directory, result, hwobj, role1)
                except Exception as ex:
                    msg1 = "Loading error (%s)" % str(ex)
                load_time = 1000 * (time.time() - time0)
                _table.append(
                    (role1, class_name1, config_file, "%.1d" % load_time, msg1)
                )
    if not msg0:
        if _container:
            if not hasattr(_container, role):
                warn(
                    f"load_from_yaml Class {_container.__class__.__name__} has no attribute {role}",
                    stacklevel=2,
                )
            _container._hwobj_by_role[role] = result
        try:
            # Initialise object
            result.init()
        except Exception:
            if _container:
                msg0 = "Error in %s.init()" % cls.__name__
            else:
                # at top level we want to get the actual error
                raise

    load_time = 1000 * (time.time() - start_time)
    _table.append((role, class_name, configuration_file, "%.1d" % load_time, msg0))

    if _container is None:
        print(make_table(column_names, _table))
    elif yaml_export_directory and result:
        _export_draft_config_file(yaml_export_directory, result)

    return result


def _export_draft_config_file(dest_dir: Path, hwobj):
    def write_yaml(data, file_name: str):
        dest_dir.mkdir(parents=True, exist_ok=True)
        yaml.dump(data, Path(dest_dir, file_name))

    result = {
        "class": "%s.%s" % (hwobj.__class__.__module__, hwobj.__class__.__name__),
    }
    objects_by_role = hwobj.objects_by_role
    if objects_by_role:
        objects = result["objects"] = {}
        for role, obj in objects_by_role.items():
            try:
                objects[role] = "%s.yaml" % obj.id
            except Exception:
                logging.getLogger("HWR").exception("")

    config = result["configuration"] = {}
    for tag, val in hwobj.config.model_dump().items():
        if tag not in objects_by_role:
            config[tag] = val  # noqa: PERF403

    write_yaml(result, "%s.yaml" % hwobj.id)


def _attach_xml_objects(yaml_export_directory: Optional[Path], container, hwobj, role):
    """Recursively attach XML-configured object to container as role

    NBNB guard against duplicate objects"""

    hwobj._hwobj_container = container
    hwobj._name = role
    container._hwobj_by_role[role] = hwobj

    objects_by_role = hwobj._objects_by_role
    for role2, hwobj2 in objects_by_role.items():
        _attach_xml_objects(yaml_export_directory, hwobj, hwobj2, role2)

    if yaml_export_directory and hwobj:
        _export_draft_config_file(yaml_export_directory, hwobj)


def _convert_xml_property(hwobj):
    """Convert complex xml-configured object"""
    result = {}
    result.update(hwobj.get_properties())
    for tag in hwobj._objects_names():
        # NB this does NOT allow having HardwareObjects inside complex properties
        objs = list(hwobj._get_objects(tag))
        result[tag] = [_convert_xml_property(obj) for obj in objs]
    #
    return result


def _create_config_for_xml_hwobj(hwobj: BaseHardwareObjects.HardwareObjectNode):
    """
    Populate hwobj._config attribute for an HWOBJ loaded with XML configure file.

    This allows to access HWOBJ configuration uniformly for both YAML and XML
    configured objects, using its 'config' attribute.
    """
    hwobj._config = hwobj.HOConfig(**hwobj.get_properties())

    objects_by_role = hwobj._objects_by_role
    for tag in hwobj._objects_names():
        if tag not in objects_by_role:
            # Complex object, not contained hwobj
            objs = [_convert_xml_property(obj) for obj in hwobj._get_objects(tag)]
            if len(objs) == 1:
                setattr(hwobj.config, tag, objs[0])
            else:
                setattr(hwobj.config, tag, objs)


def add_hardware_objects_dirs(ho_dirs):
    """Adds directories with xml/yaml config files

    Args:
        ho_dirs ([type]): [description]
    """
    if isinstance(ho_dirs, list):
        new_ho_dirs = list(filter(os.path.isdir, list(map(os.path.abspath, ho_dirs))))

        for new_ho_dir in reversed(new_ho_dirs):
            if new_ho_dir not in sys.path:
                sys.path.insert(0, new_ho_dir)


#
#
def set_user_file_directory(user_file_directory):
    """Sets user file directory.

    Args:
        user_file_directory (str): absolute path to user file directory
    """
    BaseHardwareObjects.HardwareObjectNode.set_user_file_directory(user_file_directory)


def init_hardware_repository(
    configuration_path: str,
    yaml_export_directory: Optional[Path] = None,
):
    """Initialise hardware repository - must be run at program start

    Args:
        configuration_path (str): PATHSEP-separated string of directories
        giving configuration file lookup path
        yaml_export_directory: if specified, loaded hardware objects configuration
        will be written to this directory, as YAML files

    Returns:

    """
    global _instance
    global beamline

    if _instance is not None or beamline is not None:
        raise RuntimeError(
            "init_hardware_repository called on already initialised repository"
        )
    if not configuration_path:
        logging.getLogger("HWR").error(
            "Unable to initialize hardware repository. No configuration path passed."
        )
        return

    # If configuration_path is a string of combined paths, split it up
    lookup_path = [
        os.path.abspath(os.path.expanduser(x))
        for x in configuration_path.split(os.path.pathsep)
    ]
    lookup_path = [x for x in lookup_path if os.path.exists(x)]
    if lookup_path:
        configuration_path = lookup_path

    logging.getLogger("HWR").info("Hardware repository: %s", configuration_path)
    _instance = __HardwareRepositoryClient(configuration_path)
    _instance.connect()
    beamline = load_from_yaml(
        BEAMLINE_CONFIG_FILE,
        role="beamline",
        yaml_export_directory=yaml_export_directory,
    )


def uninit_hardware_repository():
    global _instance, beamline
    _instance = None
    beamline = None


def get_hardware_repository():
    """
    Get the HardwareRepository (singleton) instance,

    Returns:
        HardwareRepository: The Singleton instance of HardwareRepository
                            (in reality __HardwareRepositoryClient)
    """

    if _instance is None:
        raise RuntimeError("The HardwareRepository has not been initialised")

    return _instance


class __HardwareRepositoryClient:
    """Hardware Repository class

    Warning -- should not be instantiated directly ;
    call the module's level get_hardware_repository() function instead
    """

    def __init__(self, server_address):
        """Constructor

        server_address needs to be the HWR server address (host:port) or
        a list of paths where to find XML files locally (when server is not in use)
        """
        self.server_address = server_address
        self.required_hardware_objects = {}
        self.xml_source = {}
        self.__connected = False
        self.server = None
        self.hwobj_info_list = []
        self.invalid_hardware_objects = None
        self.hardware_objects = None

    def connect(self):
        if self.__connected:
            return
        try:
            self.invalid_hardware_objects = set()
            self.hardware_objects = weakref.WeakValueDictionary()

            self.server = None
        finally:
            self.__connected = True

    def find_in_repository(self, relative_path):
        """Finds absolute path of a file or directory matching relativePath
        in one of the hardwareRepository directories

        Will work for any file or directory, but intended for configuration
        files that do NOT match the standard XML file system"""

        if self.server:
            logging.getLogger("HWR").error(
                "Cannot find file in repository - server is in use"
            )
            return
        else:
            if relative_path.startswith(os.path.sep):
                relative_path = relative_path[1:]

            for xml_files_path in self.server_address:
                file_path = os.path.join(xml_files_path, relative_path)
                if os.path.exists(file_path):
                    return os.path.abspath(file_path)
            #
            return

    def require(self, mnemonics_list):
        """Download a list of Hardware Objects in one go"""
        self.required_hardware_objects = {}

        if not self.server:
            return

        try:
            t0 = time.time()
            mnemonics = ",".join([repr(mne) for mne in mnemonics_list])
        except Exception:
            logging.getLogger("HWR").exception(
                "Could not execute 'require' on Hardware Repository server"
            )

    def _load_hardware_object(self, hwobj_name=""):
        """
        Load a Hardware Object. Do NOT use externally,
        as this will mess up object tracking, signals, etc.

        :param hwobj_name:  string name of the Hardware Object to load, e.g. /motors/m0
        :return: the loaded Hardware Object, or None if it fails
        """

        comment = ""
        class_name = ""
        hwobj_instance = None
        xml_data = ""

        for xml_files_path in self.server_address:
            file_name = (
                hwobj_name[1:] if hwobj_name.startswith(os.path.sep) else hwobj_name
            )
            file_path = os.path.join(xml_files_path, file_name) + os.path.extsep + "xml"
            if os.path.exists(file_path):
                try:
                    xml_data = open(file_path, "r").read()
                except Exception:
                    pass
                break

        start_time = datetime.now()

        if xml_data:
            try:
                hwobj_instance = self.parse_xml(xml_data, hwobj_name)
                if isinstance(hwobj_instance, string_types):
                    # We have redirection to another file
                    # Enter in dictionaries also under original names
                    result = self._load_hardware_object(hwobj_instance)
                    if hwobj_name in self.invalid_hardware_objects:
                        self.invalid_hardware_objects.remove(hwobj_name)
                    self.hardware_objects[hwobj_name] = result
                    return result
            except Exception:
                comment = "Cannot parse xml"
                logging.getLogger("HWR").exception(
                    "Cannot parse XML file for Hardware Object %s", hwobj_name
                )
            else:
                if hwobj_instance is not None:
                    self.xml_source[hwobj_name] = xml_data

                    dispatcher.send("hardwareObjectLoaded", hwobj_name, self)

                    def hardwareObjectDeleted(name=hwobj_instance.name):
                        logging.getLogger("HWR").debug(
                            "%s Hardware Object has been deleted from Hardware Repository",
                            name,
                        )
                        del self.hardware_objects[name]

                    hwobj_instance.resolve_references()

                    try:
                        hwobj_instance._add_channels_and_commands()
                    except Exception:
                        logging.getLogger("HWR").exception(
                            "Error while adding commands and/or channels to Hardware Object %s",
                            hwobj_name,
                        )
                        comment = "Failed to add all commands and/or channels"

                    try:
                        _create_config_for_xml_hwobj(hwobj_instance)
                        hwobj_instance._init()
                        hwobj_instance.init()
                        class_name = str(hwobj_instance.__module__)
                    except Exception:
                        logging.getLogger("HWR").exception(
                            'Cannot initialize Hardware Object "%s"', hwobj_name
                        )
                        self.invalid_hardware_objects.add(hwobj_instance.name)
                        hwobj_instance = None
                        comment = "Failed to init class"
                    else:
                        if hwobj_instance.load_name in self.invalid_hardware_objects:
                            self.invalid_hardware_objects.remove(hwobj_instance.name)

                        self.hardware_objects[hwobj_instance.load_name] = hwobj_instance
                else:
                    logging.getLogger("HWR").error(
                        "Failed to load Hardware object %s", hwobj_name
                    )
                    comment = "Loading failed"
        else:
            logging.getLogger("HWR").error(
                'Cannot load Hardware Object "%s" : file not found.', hwobj_name
            )

        end_time = datetime.now()
        time_delta = end_time - start_time

        self.hwobj_info_list.append(
            (
                hwobj_name,
                class_name,
                "%d ms" % (time_delta.microseconds / 1000),
                comment,
            )
        )

        return hwobj_instance

    def discard_hardware_object(self, ho_name):
        """Remove a Hardware Object from the Hardware Repository

        Parameters :
          ho_name -- the name of the Hardware Object to remove

        Emitted signals :
          hardwareObjectDiscarded (<object name>) -- emitted when the object has been removed
        """
        try:
            del self.hardware_objects[ho_name]
        except KeyError:
            pass
        try:
            self.invalid_hardware_objects.remove(ho_name)
        except Exception:
            pass
        try:
            del self.required_hardware_objects[ho_name]
        except KeyError:
            pass

        dispatcher.send("hardwareObjectDiscarded", ho_name, self)

    def parse_xml(self, xml_string, ho_name):
        """Load a Hardware Object from its XML string representation

        Parameters :
          xml_string -- the XML string
          ho_name -- the name of the Hardware Object to load (i.e. '/motors/m0')

        Return :
          the Hardware Object, or None if it fails
        """
        try:
            hardware_obj = HardwareObjectFileParser.parse_string(xml_string, ho_name)
        except Exception:
            logging.getLogger("HWR").exception(
                "Cannot parse Hardware Repository file %s", ho_name
            )
        else:
            return hardware_obj

    def update(self, name, updatesList):
        """[summary]

        Args:
            name ([type]): [description]
            updatesList ([type]): [description]
        """
        # TODO: update without HWR server
        if self.server is not None and self.server.isSpecConnected():
            self.server.send_msg_cmd_with_return(
                'xml_multiwrite("%s", "%s")' % (name, str(updatesList))
            )
        else:
            logging.getLogger("HWR").error(
                "Cannot update Hardware Object %s : not connected to server", name
            )

    def rewrite_xml(self, name, xml):
        """[summary]

        Args:
            name ([type]): [description]
            xml ([type]): [description]
        """
        # TODO: rewrite without HWR server
        if self.server is not None and self.server.isSpecConnected():
            self.server.send_msg_cmd_with_return(
                'xml_writefile("%s", %s)' % (name, repr(xml))
            )
            self.xml_source[name] = xml
        else:
            logging.getLogger("HWR").error(
                "Cannot update Hardware Object %s : not connected to server", name
            )

    def __getitem__(self, item):
        """[summary]

        Args:
            item ([type]): [description]

        Raises:
            KeyError: [description]

        Returns:
            [type]: [description]
        """
        if item == "equipments":
            return self.get_equipments()
        elif item == "procedures":
            return self.get_procedures()
        elif item == "devices":
            return self.get_devices()
        else:
            return self.get_hardware_object(item)

        raise KeyError

    def get_equipments(self):
        """Return the list of the currently loaded Equipments Hardware Objects"""
        eq_list = []

        for ho_name in self.hardware_objects:
            if self.is_equipment(ho_name):
                eq_list.append(self.hardware_objects[ho_name])

        return eq_list

    def get_procedures(self):
        """Return the list of the currently loaded Procedures Hardware Objects"""
        result = []

        for ho_name in self.hardware_objects:
            if self.is_procedure(ho_name):
                result.append(self.hardware_objects[ho_name])

        return result

    def get_devices(self):
        """Return the list of the currently loaded Devices Hardware Objects"""
        result = []

        for ho_name in self.hardware_objects:
            if self.is_device(ho_name):
                result.append(self.hardware_objects[ho_name])

        return result

    def get_hardware_object(self, object_name: str) -> Union["HardwareObject", None]:
        """Return a Hardware Object given its name.

        If the object is not in the Hardware Repository, try to load it.

        Args:
            object_name (str): The name of the Hardware Object

        Returns:
            Union[HardwareObject, None]: The required Hardware Object
        """

        if not object_name:
            return None

        if not object_name.startswith("/"):
            object_name = "/" + object_name

        try:
            if object_name:
                if object_name in self.invalid_hardware_objects:
                    return None

                if object_name in self.hardware_objects:
                    hardware_obj = self.hardware_objects[object_name]
                else:
                    hardware_obj = self._load_hardware_object(object_name)
                return hardware_obj
        except TypeError as err:
            logging.getLogger("HWR").exception(
                "could not get Hardware Object %s", object_name
            )

    def get_equipment(self, equipment_name):
        """Return an Equipment given its name (see get_hardware_object())"""
        return self.get_hardware_object(equipment_name)

    def get_device(self, device_name):
        """Return a Device given its name (see get_hardware_object())"""
        return self.get_hardware_object(device_name)

    def get_procedure(self, procedure_name):
        """Return a Procedure given its name (see get_hardware_object())"""
        return self.get_hardware_object(procedure_name)

    def is_device(self, name):
        """Check if a Hardware Object is a Device

        Parameters :
          name -- name of the Hardware Object to test

        Return :
          True if the Hardware Object is a Device, False otherwise
        """
        try:
            return isinstance(self.hardware_objects[name], BaseHardwareObjects.Device)
        except Exception:
            return False

    def is_procedure(self, name):
        """Check if a Hardware Object is a Procedure

        Parameters :
          name -- name of the Hardware Object to test

        Return :
          True if the Hardware Object is a Procedure, False otherwise
        """
        try:
            return isinstance(
                self.hardware_objects[name], BaseHardwareObjects.Procedure
            )
        except Exception:
            return False

    def is_equipment(self, name):
        """Check if a Hardware Object is an Equipment

        Parameters :
          name -- name of the Hardware Object to test

        Return :
          True if the Hardware Object is an Equipment, False otherwise
        """
        try:
            return isinstance(
                self.hardware_objects[name], BaseHardwareObjects.Equipment
            )
        except Exception:
            return False

    def has_hardware_object(self, name):
        """Check if the Hardware Repository contains an object

        Parameters :
          name -- name of the Hardware Object

        Return :
          True if HardwareObject is loaded in the Hardware Repository, False otherwise
        """
        return name in self.hardware_objects

    def get_info(self, name):
        """Return a dictionary with information about the specified Hardware Object

        Parameters :
          name -- name of the Hardware Object

        Return :
          a dictionary containing information about the Hardware Object
        """
        try:
            hardware_obj = self.hardware_objects[name]
        except KeyError:
            return {}
        else:
            hardware_obj_class = hardware_obj.__class__.__name__

            d = {
                "class": hardware_obj_class,
                "python module": sys.modules[hardware_obj.__module__].__file__,
            }

            if hasattr(hardware_obj, "is_ready"):
                d["is ready ?"] = str(hardware_obj.is_ready())

            if hasattr(hardware_obj, "get_commands"):
                # hardware object is a command container
                d["commands"] = {}

                for cmd in hardware_obj.get_commands():
                    if cmd.__class__.__name__ == "SpecCommand":
                        d["commands"][cmd.userName()] = {
                            "type": "spec",
                            "version": "%s:%s"
                            % (
                                cmd.connection.host,
                                cmd.connection.port or cmd.connection.scanname,
                            ),
                            "connected ?": cmd.isSpecConnected() and "yes" or "no",
                            "macro or function": str(cmd.command),
                        }
                    elif cmd.__class__.__name__ == "TacoCommand":
                        dd = {"type": "taco", "device": cmd.device_name}

                        try:
                            dd["imported ?"] = "yes" if cmd.device.imported else "no"
                        except Exception:
                            dd["imported ?"] = "no, invalid Taco device"

                        dd["device method"] = str(cmd.command)

                        d["commands"][cmd.userName()] = dd
                    elif cmd.__class__.__name__ == "TangoCommand":
                        d["commands"][cmd.userName()] = {
                            "type": "tango",
                            "device": cmd.device_name,
                            "imported ?": (
                                "no, invalid Tango device"
                                if cmd.device is None
                                else "yes"
                            ),
                            "device method": str(cmd.command),
                        }

                d["channels"] = {}

                for chan in hardware_obj.get_channels():
                    if chan.__class__.__name__ == "SpecChannel":
                        d["channels"][chan.userName()] = {
                            "type": "spec",
                            "version": "%s:%s"
                            % (
                                chan.connection.host,
                                chan.connection.port or chan.connection.scanname,
                            ),
                            "connected ?": chan.isSpecConnected() and "yes" or "no",
                            "variable": str(chan.varName),
                        }
                    elif chan.__class__.__name__ == "TangoChannel":
                        d["channels"][chan.userName()] = {
                            "type": "tango",
                            "device": chan.device_name,
                            "imported ?": chan.device is not None
                            and "yes"
                            or "no, invalid Tango device or attribute name",
                            "attribute": str(chan.attribute_name),
                        }

            if "SpecMotorA" in [
                klass.__name__ for klass in hardware_obj.__class__.__bases__
            ]:
                d["spec version"] = hardware_obj.specVersion
                d["motor mnemonic"] = hardware_obj.specName
                try:
                    d["connected ?"] = (
                        "yes" if hardware_obj.connection.isSpecConnected() else "no"
                    )
                except Exception:
                    d["connected ?"] = "no"

            if isinstance(hardware_obj, BaseHardwareObjects.DeviceContainer):
                d["children"] = {}

                for ho in hardware_obj.get_devices():
                    try:
                        d["children"][ho.load_name] = self.get_info(ho.load_name)
                    except Exception:
                        continue

            return d

    def end_polling(self):
        """Stop all pollers

        Warning : should not be used directly (finalization purposes only)
        """
        return

    def close(self):
        """'close' the Hardware Repository

        Discards all Hardware Objects
        """
        self.end_polling()

        self.hardware_objects = weakref.WeakValueDictionary()

    def timerEvent(self, t_ev):
        try:
            global TIMERS

            func_ref = TIMERS[t_ev.timerId()]
            func = func_ref()

            if func is None:
                # self.killTimer(t_ev.timerId())
                del TIMERS[t_ev.timerId()]
            else:
                try:
                    func()
                except Exception:
                    logging.getLogger("HWR").exception(
                        "an error occured while calling timer function"
                    )
        except Exception:
            logging.getLogger("HWR").exception("an error occured inside the timerEvent")

    def print_report(self):
        longest_cols = [
            (max([len(str(row[i])) for row in self.hwobj_info_list]) + 3)
            for i in range(len(self.hwobj_info_list[0]))
        ]
        row_format = "| ".join(
            ["{:<" + str(longest_col) + "}" for longest_col in longest_cols]
        )

        print("+", "=" * sum(longest_cols), "+")
        print("| %s" % row_format.format(*("xml", "Class", "Load time", "Comment")))
        print("+", "=" * sum(longest_cols), "+")

        for row in sorted(self.hwobj_info_list):
            print("| %s" % row_format.format(*row))
        print("+", "=" * sum(longest_cols), "+")

    def reload_hardware_objects(self):
        """
        Reloads all modified modules.
        Package reimport is used to detect modified modules.
        Hardware objects that correspond to these modules:
        1. are disconnected from gui
        2. imported in this module with __import__ and reimport is called
        3. connected back to the gui channels
        """
        # NOTE
        # reimport is supported for python 2.x and not by python 3.x
        # if needed a similar package for 3x could be used. In this case
        # code depends on a platform: platform.python_version()[0] > 2 ...

        # NB reload_hardware_objects does NOT work with beamline_opbject
        # and other yaml configs

        import reimport

        modified_modules = reimport.modified()
        for hwr_obj in self.hardware_objects:
            for item in modified_modules:
                if self.hardware_objects[hwr_obj].__module__ == item:
                    try:
                        connections = self.hardware_objects[hwr_obj].connect_dict
                        for sender in connections:
                            self.hardware_objects[hwr_obj].disconnect(
                                sender,
                                connections[sender]["signal"],
                                connections[sender]["slot"],
                            )
                        logging.getLogger("HWR").debug(
                            "HardwareRepository: %s disconnected from GUI", item
                        )
                        self.hardware_objects[hwr_obj].clear_gevent()
                    except Exception:
                        logging.getLogger("HWR").exception(
                            "HardwareRepository: Unable to disconnect hwobj %s", item
                        )
                        continue

                    try:
                        __import__(item, globals(), locals(), [], -1)
                        reimport.reimport(item)
                        logging.getLogger("HWR").debug(
                            "HardwareRepository: %s reloaded", item
                        )
                    except Exception:
                        logging.getLogger("HWR").exception(
                            "HardwareRepository: Unable to reload module %s", item
                        )

                    try:
                        for sender in connections:
                            self.hardware_objects[hwr_obj].connect(
                                sender,
                                connections[sender]["signal"],
                                connections[sender]["slot"],
                            )
                        logging.getLogger("HWR").debug(
                            "HardwareRepository: %s connected to GUI", item
                        )
                    except Exception:
                        logging.getLogger("HWR").exception(
                            "HardwareRepository: Unable to connect hwobj %s", item
                        )
                    try:
                        self.hardware_objects[hwr_obj].init()
                        self.hardware_objects[hwr_obj].re_emit_values()
                        logging.getLogger("HWR").debug(
                            "HardwareRepository: %s initialized and updated", item
                        )
                    except Exception:
                        logging.getLogger("HWR").exception(
                            "HardwareRepository: Unable to initialize hwobj %s", item
                        )
