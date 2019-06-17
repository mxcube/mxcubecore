"""Gives access to the Hardware Objects contained in the Hardware Repository database

The Hardware Repository database is a set of XML files describing devices, equipments
and procedures on a beamline. Each XML file represent a Hardware Object.
The Hardware Repository module provides access to these Hardware Objects, and manages
connections to the Control Software (Spec or Taco Device Servers).
"""
from __future__ import print_function, absolute_import

import logging
import gevent
import weakref
import sys
import os
import time
import gevent.monkey
from datetime import datetime

from . import BaseHardwareObjects
from . import HardwareObjectFileParser
from . import Beamline

from HardwareRepository.dispatcher import dispatcher
from HardwareRepository.ConvertUtils import string_types

__author__ = "Matias Guijarro"
__version__ = 1.3

_hwr_instance = None
_hwr_path = None
_timers = []

beamline = None

def init_beamline():
    global _hwr_instance
    global beamline

    _hwr_instance = getHardwareRepository(_hwr_path)
    beamline = Beamline.Beamline(_hwr_path, _hwr_instance)

    return beamline

def get_beamline_instance():
    return beamline

def addHardwareObjectsDirs(hoDirs):
    if isinstance(hoDirs, list):
        newHoDirs = list(filter(os.path.isdir, list(map(os.path.abspath, hoDirs))))

        for newHoDir in reversed(newHoDirs):
            if newHoDir not in sys.path:
                sys.path.insert(0, newHoDir)


def setUserFileDirectory(user_file_directory):
    BaseHardwareObjects.HardwareObjectNode.setUserFileDirectory(user_file_directory)


def setHardwareRepositoryServer(hwrserver):
    global _hwr_path

    xml_dirs_list = [os.path.abspath(x) for x in hwrserver.split(os.path.pathsep)]
    xml_dirs_list = [x for x in xml_dirs_list if os.path.exists(x)]

    if xml_dirs_list:
        _hwr_path = xml_dirs_list
    else:
        _hwr_path = hwrserver


def getHardwareRepository(xml_dir=None):
    """
    Get the HardwareRepository (singleton) instance, instantiates it if necessary.

    Args:
        xml_dir (str): Path to XML configuration files for HardwareObject's

    Returns:
        HardwareRepository: The Singleton instance of HardwareRepository
                            (in reality __HardwareRepositoryClient)
    """
    global _hwr_instance

    if _hwr_instance is None:
        if _hwr_path is None:
            if xml_dir is None:
                # Default to environment variable
                xml_dir = os.path.abspath(os.environ["XML_FILES_PATH"])

            setHardwareRepositoryServer(xml_dir)

        _hwr_instance = __HardwareRepositoryClient(_hwr_path)

    return _hwr_instance


class __HardwareRepositoryClient:
    """Hardware Repository class

    Warning -- should not be instanciated directly ; call the module's level getHardwareRepository() function instead
    """

    def __init__(self, serverAddress):
        """Constructor

        serverAddress needs to be the HWR server address (host:port) or
        a list of paths where to find XML files locally (when server is not in use)
        """
        self.serverAddress = serverAddress
        self.requiredHardwareObjects = {}
        self.xml_source = {}
        self.__connected = False
        self.server = None
        self.hwobj_info_list = []
        self.invalidHardwareObjects = None
        self.hardwareObjects = None

    def connect(self):
        if self.__connected:
            return
        self.invalidHardwareObjects = set()
        self.hardwareObjects = weakref.WeakValueDictionary()
        self.__connected = True

    def findInRepository(self, relative_path):
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

            for xml_files_path in self.serverAddress:
                file_path = os.path.join(xml_files_path, relative_path)
                if os.path.exists(file_path):
                    return os.path.abspath(file_path)
            #
            return

    def require(self, mnemonicsList):
        """Download a list of Hardware Objects in one go"""
        self.requiredHardwareObjects = {}

        if not self.server:
            return

        try:
            t0 = time.time()
            mnemonics = ",".join([repr(mne) for mne in mnemonicsList])
            if len(mnemonics) > 0:
                self.requiredHardwareObjects = SpecWaitObject.waitReply(
                    self.server,
                    "send_msg_cmd_with_return",
                    ("xml_getall(%s)" % mnemonics,),
                    timeout=3,
                )
                logging.getLogger("HWR").debug(
                    "Getting %s hardware objects took %s ms."
                    % (len(self.requiredHardwareObjects), (time.time() - t0) * 1000)
                )
        except SpecClientError.SpecClientTimeoutError:
            logging.getLogger("HWR").error("Timeout loading Hardware Objects")
        except BaseException:
            logging.getLogger("HWR").exception(
                "Could not execute 'require' on Hardware Repository server"
            )

    def loadHardwareObject(self, hwobj_name=""):
        """
        Load a Hardware Object

        :param hwobj_name:  string name of the Hardware Object to load, for example '/motors/m0'
        :return: the loaded Hardware Object, or None if it fails
        """

        comment = ""
        class_name = ""
        hwobj_instance = None

        if self.server:
            if self.server.isSpecConnected():
                try:
                    if hwobj_name in self.requiredHardwareObjects:
                        reply_dict = self.requiredHardwareObjects[hwobj_name]
                    else:
                        reply_dict = SpecWaitObject.waitReply(
                            self.server,
                            "send_msg_chan_read",
                            ('xml_get("%s")' % hwobj_name,),
                            timeout=3,
                        )
                except BaseException:
                    logging.getLogger("HWR").exception(
                        'Could not load Hardware Object "%s"' % hwobj_name
                    )
                else:
                    try:
                        # TODO Both variables not used: remove?
                        xml_data = reply_dict["xmldata"]
                        mtime = int(reply_dict["mtime"])
                    except KeyError:
                        logging.getLogger("HWR").error(
                            "Cannot load Hardware Object %s: file does not exist."
                            % hwobj_name
                        )
                        return
            else:
                logging.getLogger("HWR").error(
                    'Cannot load Hardware Object "%s" : not connected to server.'
                    % hwobj_name
                )
        else:
            xml_data = ""
            for xml_files_path in self.serverAddress:
                file_name = (
                    hwobj_name[1:] if hwobj_name.startswith(os.path.sep) else hwobj_name
                )
                file_path = (
                    os.path.join(xml_files_path, file_name) + os.path.extsep + "xml"
                )
                if os.path.exists(file_path):
                    try:
                        xml_data = open(file_path, "r").read()
                    except BaseException:
                        pass
                    break

        start_time = datetime.now()

        if len(xml_data) > 0:
            try:
                hwobj_instance = self.parseXML(xml_data, hwobj_name)
                if isinstance(hwobj_instance, string_types):
                    return self.loadHardwareObject(hwobj_instance)
            except BaseException:
                comment = "Cannot parse xml"
                logging.getLogger("HWR").exception(
                    "Cannot parse XML file for Hardware Object %s", hwobj_name
                )
            else:
                if hwobj_instance is not None:
                    self.xml_source[hwobj_name] = xml_data
                    dispatcher.send("hardwareObjectLoaded", hwobj_name, self)

                    def hardwareObjectDeleted(name=hwobj_instance.name()):
                        logging.getLogger("HWR").debug(
                            "%s Hardware Object has been deleted from Hardware Repository",
                            name,
                        )
                        del self.hardwareObjects[name]

                    hwobj_instance.resolveReferences()

                    try:
                        hwobj_instance._addChannelsAndCommands()
                    except BaseException:
                        logging.getLogger("HWR").exception(
                            "Error while adding commands and/or channels to Hardware Object %s",
                            hwobj_name,
                        )
                        comment = "Failed to add all commands and/or channels"

                    try:
                        hwobj_instance._init()
                        hwobj_instance.init()
                        class_name = str(hwobj_instance.__module__)
                    except BaseException:
                        logging.getLogger("HWR").exception(
                            'Cannot initialize Hardware Object "%s"', hwobj_name
                        )
                        self.invalidHardwareObjects.add(hwobj_instance.name())
                        hwobj_instance = None
                        comment = "Failed to init class"
                    else:
                        if hwobj_instance.name() in self.invalidHardwareObjects:
                            self.invalidHardwareObjects.remove(hwobj_instance.name())

                        self.hardwareObjects[hwobj_instance.name()] = hwobj_instance
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

    def discardHardwareObject(self, hoName):
        """Remove a Hardware Object from the Hardware Repository

        Parameters :
          hoName -- the name of the Hardware Object to remove

        Emitted signals :
          hardwareObjectDiscarded (<object name>) -- emitted when the object has been removed
        """
        try:
            del self.hardwareObjects[hoName]
        except KeyError:
            pass
        try:
            self.invalidHardwareObjects.remove(hoName)
        except BaseException:
            pass
        try:
            del self.requiredHardwareObjects[hoName]
        except KeyError:
            pass

        dispatcher.send("hardwareObjectDiscarded", hoName, self)

    def parseXML(self, XMLString, hoName):
        """Load a Hardware Object from its XML string representation

        Parameters :
          XMLString -- the XML string
          hoName -- the name of the Hardware Object to load (i.e. '/motors/m0')

        Return :
          the Hardware Object, or None if it fails
        """
        try:
            ho = HardwareObjectFileParser.parseString(XMLString, hoName)
        except BaseException:
            logging.getLogger("HWR").exception(
                "Cannot parse Hardware Repository file %s", hoName
            )
        else:
            return ho

    def update(self, name, updatesList):
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
        if item == "equipments":
            return self.getEquipments()
        elif item == "procedures":
            return self.getProcedures()
        elif item == "devices":
            return self.getDevices()
        else:
            return self.getHardwareObject(item)

        raise KeyError

    def getHardwareRepositoryPath(self):
        if self.server:
            return ""
        else:
            path = self.serverAddress[0]
            return os.path.abspath(path)

    def getHardwareRepositoryFiles(self, startdir="/"):
        # TODO: when server is not used
        if not self.server:
            return

        try:
            completeFilesList = SpecWaitObject.waitReply(
                self.server, "send_msg_chan_read", ("readDirectory()",), timeout=3
            )
        except BaseException:
            logging.getLogger("HWR").error(
                "Cannot retrieve Hardware Repository files list"
            )
        else:
            if "__error__" in completeFilesList:
                logging.getLogger("HWR").error(
                    "Error while doing Hardware Repository files list"
                )
                return
            else:
                for name, filename in completeFilesList.items():
                    if name.startswith(startdir):
                        yield (name, filename)

    def getEquipments(self):
        """Return the list of the currently loaded Equipments Hardware Objects"""
        list = []

        for hoName in self.hardwareObjects:
            if self.isEquipment(hoName):
                list.append(self.hardwareObjects[hoName])

        return list

    def getProcedures(self):
        """Return the list of the currently loaded Procedures Hardware Objects"""
        list = []

        for hoName in self.hardwareObjects:
            if self.isProcedure(hoName):
                list.append(self.hardwareObjects[hoName])

        return list

    def getDevices(self):
        """Return the list of the currently loaded Devices Hardware Objects"""
        list = []

        for hoName in self.hardwareObjects:
            if self.isDevice(hoName):
                list.append(self.hardwareObjects[hoName])

        return list

    def getHardwareObject(self, objectName):
        """Return a Hardware Object given its name

        If the object is not in the Hardware Repository, try to load it.

        Parameters :
          objectName -- the name of the Hardware Object

        Return :
          the required Hardware Object
        """

        if not objectName:
            return None

        if not objectName.startswith("/"):
            objectName = "/" + objectName

        try:
            if objectName:
                if objectName in self.invalidHardwareObjects:
                    return None

                if objectName in self.hardwareObjects:
                    ho = self.hardwareObjects[objectName]
                else:
                    ho = self.loadHardwareObject(objectName)
                return ho
        except TypeError as err:
            logging.getLogger("HWR").exception(
                "could not get Hardware Object %s", objectName
            )

    def getEquipment(self, equipmentName):
        """Return an Equipment given its name (see getHardwareObject())"""
        return self.getHardwareObject(equipmentName)

    def getDevice(self, deviceName):
        """Return a Device given its name (see getHardwareObject())"""
        return self.getHardwareObject(deviceName)

    def getProcedure(self, procedureName):
        """Return a Procedure given its name (see getHardwareObject())"""
        return self.getHardwareObject(procedureName)

    def getConnection(self, connectionName):
        """Return the Connection object for a Spec connection, given its name

        Parameters :
          connectionName -- a Spec version name ('host:port' string)

        Return :
          the corresponding SpecConnection object
        """
        connectionsManager = SpecConnectionsManager.SpecConnectionsManager()

        return connectionsManager.getConnection(connectionName)

    def isDevice(self, name):
        """Check if a Hardware Object is a Device

        Parameters :
          name -- name of the Hardware Object to test

        Return :
          True if the Hardware Object is a Device, False otherwise
        """
        try:
            return isinstance(self.hardwareObjects[name], BaseHardwareObjects.Device)
        except BaseException:
            return False

    def isProcedure(self, name):
        """Check if a Hardware Object is a Procedure

        Parameters :
          name -- name of the Hardware Object to test

        Return :
          True if the Hardware Object is a Procedure, False otherwise
        """
        try:
            return isinstance(self.hardwareObjects[name], BaseHardwareObjects.Procedure)
        except BaseException:
            return False

    def isEquipment(self, name):
        """Check if a Hardware Object is an Equipment

        Parameters :
          name -- name of the Hardware Object to test

        Return :
          True if the Hardware Object is an Equipment, False otherwise
        """
        try:
            return isinstance(self.hardwareObjects[name], BaseHardwareObjects.Equipment)
        except BaseException:
            return False

    def hasHardwareObject(self, name):
        """Check if the Hardware Repository contains an object

        Parameters :
          name -- name of the Hardware Object

        Return :
          True if the Hardware Object is loaded in the Hardware Repository, False otherwise
        """
        return name in self.hardwareObjects

    def getInfo(self, name):
        """Return a dictionary with information about the specified Hardware Object

        Parameters :
          name -- name of the Hardware Object

        Return :
          a dictionary containing information about the Hardware Object
        """
        try:
            ho = self.hardwareObjects[name]
        except KeyError:
            return {}
        else:
            ho_class = ho.__class__.__name__

            d = {
                "class": ho_class,
                "python module": sys.modules[ho.__module__].__file__,
            }

            if hasattr(ho, "isReady"):
                d["is ready ?"] = str(ho.isReady())

            if hasattr(ho, "getCommands"):
                # hardware object is a command container
                d["commands"] = {}

                for cmd in ho.getCommands():
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
                        dd = {"type": "taco", "device": cmd.deviceName}

                        try:
                            dd["imported ?"] = cmd.device.imported and "yes" or "no"
                        except BaseException:
                            dd["imported ?"] = "no, invalid Taco device"

                        dd["device method"] = str(cmd.command)

                        d["commands"][cmd.userName()] = dd
                    elif cmd.__class__.__name__ == "TangoCommand":
                        d["commands"][cmd.userName()] = {
                            "type": "tango",
                            "device": cmd.deviceName,
                            "imported ?": cmd.device is not None
                            and "yes"
                            or "no, invalid Tango device",
                            "device method": str(cmd.command),
                        }

                d["channels"] = {}

                for chan in ho.getChannels():
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
                            "device": chan.deviceName,
                            "imported ?": chan.device is not None
                            and "yes"
                            or "no, invalid Tango device or attribute name",
                            "attribute": str(chan.attributeName),
                        }

            if "SpecMotorA" in [klass.__name__ for klass in ho.__class__.__bases__]:
                d["spec version"] = ho.specVersion
                d["motor mnemonic"] = ho.specName
                try:
                    d["connected ?"] = ho.connection.isSpecConnected() and "yes" or "no"
                except BaseException:
                    d["connected ?"] = "no"

            if isinstance(ho, BaseHardwareObjects.DeviceContainer):
                d["children"] = {}

                for ho in ho.getDevices():
                    try:
                        d["children"][ho.name()] = self.getInfo(ho.name())
                    except Exception:
                        continue

            return d

    def endPolling(self):
        """Stop all pollers

        Warning : should not be used directly (finalization purposes only)
        """
        return

    def close(self):
        """'close' the Hardware Repository

        Discards all Hardware Objects
        """
        self.endPolling()

        self.hardwareObjects = weakref.WeakValueDictionary()

    def timerEvent(self, t_ev):
        try:
            global _timers

            func_ref = _timers[t_ev.timerId()]
            func = func_ref()

            if func is None:
                #self.killTimer(t_ev.timerId())
                del _timers[t_ev.timerId()]
            else:
                try:
                    func()
                except BaseException:
                    logging.getLogger("HWR").exception(
                        "an error occured while calling timer function"
                    )
        except BaseException:
            logging.getLogger("HWR").exception("an error occured inside the timerEvent")

    def printReport(self):
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

    def reloadHardwareObjects(self):
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

        import reimport

        modified_modules = reimport.modified()
        for hwr_obj in self.hardwareObjects:
            for item in modified_modules:
                if self.hardwareObjects[hwr_obj].__module__ == item:
                    try:
                        connections = self.hardwareObjects[hwr_obj].connect_dict
                        for sender in connections:
                            self.hardwareObjects[hwr_obj].disconnect(
                                sender,
                                connections[sender]["signal"],
                                connections[sender]["slot"],
                            )
                        logging.getLogger("HWR").debug(
                            "HardwareRepository: %s disconnected from GUI" % item
                        )
                        self.hardwareObjects[hwr_obj].clear_gevent()
                    except BaseException:
                        logging.getLogger("HWR").exception(
                            "HardwareRepository: Unable to disconnect hwobj %s" % item
                        )
                        continue

                    try:
                        __import__(item, globals(), locals(), [], -1)
                        reimport.reimport(item)
                        logging.getLogger("HWR").debug(
                            "HardwareRepository: %s reloaded" % item
                        )
                    except BaseException:
                        logging.getLogger("HWR").exception(
                            "HardwareRepository: Unable to reload module %s" % item
                        )

                    try:
                        for sender in connections:
                            self.hardwareObjects[hwr_obj].connect(
                                sender,
                                connections[sender]["signal"],
                                connections[sender]["slot"],
                            )
                        logging.getLogger("HWR").debug(
                            "HardwareRepository: %s connected to GUI" % item
                        )
                    except BaseException:
                        logging.getLogger("HWR").exception(
                            "HardwareRepository: Unable to connect hwobj %s" % item
                        )
                    try:
                        self.hardwareObjects[hwr_obj].init()
                        self.hardwareObjects[hwr_obj].update_values()
                        logging.getLogger("HWR").debug(
                            "HardwareRepository: %s initialized and updated" % item
                        )
                    except BaseException:
                        logging.getLogger("HWR").exception(
                            "HardwareRepository: Unable to initialize hwobj %s" % item
                        )
