import types
import socket
import os
import stat
import xml.sax
from xml.sax import SAXParseException
from xml.sax.xmlreader import AttributesImpl
from xml.sax.handler import ContentHandler

from SpecClient_gevent import SpecServer
from SpecClient_gevent import SpecMessage
import Daemonize
import SimpleXMLReadWriteSupport


class XMLNodesWithRolesReadingHandler(ContentHandler):
    def __init__(self):
        ContentHandler.__init__(self)

        self.path = ""
        self.previousPath = ""
        self.elementName = None
        self.value = {}
        self.currentValue = None
        self.childDepth = 0

    def startElement(self, name, attrs):
        #
        # determine path to the new object
        #
        self.path += "/" + str(name) + "[%d]"
        i = self.previousPath.rfind("[")

        if i >= 0 and self.path[:-4] == self.previousPath[:i]:
            objectIndex = int(self.previousPath[i + 1 : -1]) + 1
        else:
            objectIndex = 1  # XPath indexes begin at 1

        self.path %= objectIndex

        if self.elementName is None:
            if "role" in list(attrs.keys()):
                self.childDepth = 0
                self.elementName = name

                # append new node to value
                self.currentValue = {
                    "__value__": "",
                    "__path__": self.path,
                    "__children__": "",
                }
                self.value[str(attrs["role"])] = self.currentValue

                for key, value in list(attrs.items()):
                    # add attributes
                    self.currentValue[str(key)] = str(value)
        else:
            self.childDepth += 1

    def characters(self, content):
        if self.elementName is not None and self.childDepth == 0:
            self.currentValue["__value__"] += str(content)

    def endElement(self, name):
        if self.elementName is not None and self.childDepth == 1:
            # add children
            self.currentValue["__children__"] += self.path + ":" + str(name) + " "

        if self.elementName == name and self.childDepth == 0:
            self.elementName = None

        self.childDepth -= 1
        self.previousPath = self.path
        self.path = self.path[
            : self.path.rfind("/")
        ]  # remove last added name and suffix

    def getValue(self):
        for val in self.value.values():
            val["__children__"].strip()

        return self.value


class XMLPropertiesReadingHandler(ContentHandler):
    def __init__(self, queryPath="/*"):
        ContentHandler.__init__(self)

        self.path = ""
        self.previousPath = ""
        self.queryPath = queryPath + "/*"
        self.properties = {}
        self.getProperty = False
        self.propertyName = ""
        self.propertyValue = ""

    def startElement(self, name, attrs):
        #
        # determine path to the new object
        #
        self.path += "/" + str(name) + "[%d]"
        i = self.previousPath.rfind("[")

        if i >= 0 and self.path[:-4] == self.previousPath[:i]:
            objectIndex = int(self.previousPath[i + 1 : -1]) + 1
        else:
            objectIndex = 1  # XPath indexes begin at 1

        self.path %= objectIndex

        if SimpleXMLReadWriteSupport.testPath(self.path, self.queryPath, attrs):
            self.getProperty = True
            self.propertyName = str(name)
            self.propertyValue = ""
        else:
            self.getProperty = False

    def characters(self, content):
        if self.getProperty:
            self.propertyValue += str(content)

    def endElement(self, name):
        if self.getProperty:
            self.getProperty = False
            self.properties[self.propertyName] = {
                "__value__": self.propertyValue,
                "__path__": self.path,
            }

        self.previousPath = self.path
        self.path = self.path[
            : self.path.rfind("/")
        ]  # remove last added name and suffix

    def getValue(self):
        return self.properties


class XMLReferencesReadingHandler(ContentHandler):
    def __init__(self):
        ContentHandler.__init__(self)

        self.references = []

    def startElement(self, name, attrs):
        reference = (
            ("hwrid" in attrs and attrs["hwrid"])
            or ("href" in attrs and attrs["href"])
            or ""
        )

        if len(reference) > 0:
            self.references.append(str(reference))


class SpecServerConnection(SpecServer.BaseSpecRequestHandler):
    def __init__(self, *args):
        SpecServer.BaseSpecRequestHandler.__init__(self, *args)

        self.updateRegistered = False

    def dispatchIncomingMessage(self, m):
        if m.cmd == SpecMessage.CHAN_READ:
            # temporary code (workaround for a Spec client bug)
            self.executeCommandAndReply(
                replyID=m.sn, cmd=m.name
            )  # for CHAN_READ m.data==m.name
        elif m.cmd == SpecMessage.CMD_WITH_RETURN:
            self.executeCommandAndReply(replyID=m.sn, cmd=m.data)
        elif m.cmd == SpecMessage.FUNC_WITH_RETURN:
            print(m, m.data)
            self.executeCommandAndReply(replyID=m.sn, cmd=m.data)
        elif m.cmd == SpecMessage.REGISTER:
            if m.name == "update":
                print("update channel registered !")
                self.updateRegistered = True
        else:
            return False
        return True

    def xml_read(self, hardwareObjectName, path):
        if self.server.hardwareRepositoryDirectory is not None:
            filename = os.path.normpath(
                self.server.hardwareRepositoryDirectory + hardwareObjectName + ".xml"
            )

            if os.path.exists(filename):
                try:
                    ret = SimpleXMLReadWriteSupport.read(filename, path)
                except SAXParseException as msg:
                    return {
                        "__error__": "Could not parse hardware object file %s : %s"
                        % (hardwareObjectName, msg)
                    }
                except Exception:
                    return {
                        "__error__": "Could not read hardware object %s"
                        % hardwareObjectName
                    }

                #
                # format return value for Spec
                #
                spec_ret = {}
                for i in range(len(ret)):
                    dict = {}
                    dict.update(ret[i])

                    tmp = ""
                    if "__children__" in dict:
                        for childpath, childname in list(dict["__children__"].items()):
                            tmp += childname + ":" + childpath + " "
                        tmp.strip()
                        dict["__children__"] = tmp

                    spec_ret[i] = dict

                if len(spec_ret) > 0:
                    return spec_ret
                else:
                    return {"__error__": "No match."}
            else:
                return {"__error__": "%s does not exist." % hardwareObjectName}
        else:
            return {"__error__": "No server."}

    def xml_readNodesWithRoles(self, hardwareObjectName):
        if self.server.hardwareRepositoryDirectory is not None:
            filename = os.path.normpath(
                self.server.hardwareRepositoryDirectory + hardwareObjectName + ".xml"
            )

            if os.path.exists(filename):
                curHandler = XMLNodesWithRolesReadingHandler()

                try:
                    xml.sax.parse(filename, curHandler)
                except SAXParseException as msg:
                    return {"__error__": "Could not parse the XML file %s" % filename}
                else:
                    ret = curHandler.getValue()

                    if len(ret) > 0:
                        return ret
                    else:
                        return {"__error__": "No match."}
            else:
                return {"__error__": "%s does not exist." % hardwareObjectName}
        else:
            return {"__error__": "No server."}

    def xml_readProperties(self, hardwareObjectName, path=None):
        if self.server.hardwareRepositoryDirectory is not None:
            filename = os.path.normpath(
                self.server.hardwareRepositoryDirectory + hardwareObjectName + ".xml"
            )

            if os.path.exists(filename):
                if path is not None:
                    curHandler = XMLPropertiesReadingHandler(path)
                else:
                    curHandler = XMLPropertiesReadingHandler()

                try:
                    xml.sax.parse(filename, curHandler)
                except SAXParseException as msg:
                    return {"__error__": "Could not parse the XML file %s" % filename}
                else:
                    ret = curHandler.getValue()

                    if len(ret) > 0:
                        return ret
                    else:
                        return {"__error__": "No match."}
            else:
                return {"__error__": "%s does not exist." % hardwareObjectName}
        else:
            return {"__error__": "No server."}

    def xml_writefile(self, hardwareObjectName, xml):
        if self.server.hardwareRepositoryDirectory is not None:
            filename = os.path.normpath(
                self.server.hardwareRepositoryDirectory + hardwareObjectName + ".xml"
            )

            if os.path.exists(filename):
                try:
                    f = open(filename, "r")
                    old_contents = f.read()
                    f.close()

                    bak_filename = os.path.splitext(filename)[0] + ".bak"
                    f = open(bak_filename, "w")
                    f.write(old_contents)
                    f.close()

                    f = open(filename, "w")
                    f.write(xml)
                    f.close()
                except Exception:
                    return {"__error__": "%s update failed" % hardwareObjectName}
                else:
                    self.server.broadcast_update_event(hardwareObjectName)
            else:
                return {"__error__": "%s does not exist." % hardwareObjectName}
        else:
            return {"__error__": "No server."}

    def xml_write(self, hardwareObjectName, path, value):
        if self.server.hardwareRepositoryDirectory is not None:
            filename = os.path.normpath(
                self.server.hardwareRepositoryDirectory + hardwareObjectName + ".xml"
            )

            if os.path.exists(filename):
                try:
                    return SimpleXMLReadWriteSupport.update(
                        filename, path, value, filename
                    )
                except SAXParseException as msg:
                    return {
                        "__error__": "Could not parse hardware object file %s : %s"
                        % (hardwareObjectName, msg)
                    }
                except Exception:
                    return {
                        "__error__": "Could not update hardware object %s"
                        % hardwareObjectName
                    }
                else:
                    self.server.broadcast_update_event(hardwareObjectName)
            else:
                return {"__error__": "%s does not exist." % hardwareObjectName}
        else:
            return {"__error__": "No server."}

    def xml_multiwrite(self, hardwareObjectName, str_updateList):
        if self.server.hardwareRepositoryDirectory is not None:
            filename = os.path.normpath(
                self.server.hardwareRepositoryDirectory + hardwareObjectName + ".xml"
            )

            if os.path.exists(filename):
                try:
                    pathvalueList = eval(str_updateList)
                except Exception:
                    return {"__error__": "Bad update list format."}

                if type(pathvalueList) in (list, tuple):
                    paths = []
                    values = []
                    for path, value in pathvalueList:
                        paths.append(path)
                        values.append(value)

                    try:
                        SimpleXMLReadWriteSupport.batchUpdate(
                            filename, paths, values, filename
                        )
                    except SAXParseException as msg:
                        return {
                            "__error__": "Could not parse hardware object file %s : %s"
                            % (hardwareObjectName, msg)
                        }
                    except Exception:
                        return {
                            "__error__": "Could not update hardware object %s"
                            % hardwareObjectName
                        }
                    else:
                        self.server.broadcast_update_event(hardwareObjectName)
                        return {}
                else:
                    return {"__error__": "Could not eval. update list"}
            else:
                return {"__error__": "%s does not exist." % hardwareObjectName}
        else:
            return {"__error__": "No server."}

    def xml_view(self, hardwareObjectName):
        if self.server.hardwareRepositoryDirectory is not None:
            filename = os.path.normpath(
                self.server.hardwareRepositoryDirectory + hardwareObjectName + ".xml"
            )

            #
            # load file
            #
            try:
                f = open(filename)
                return f.read()
            except Exception:
                return ""
        else:
            return ""  # { '__error__': 'No server.' }

    def xml_viewList(self, hardwareObjectNames):
        hoNamesList = hardwareObjectNames.split()
        data = {}

        for hoName in hoNamesList:
            data[hoName] = self.xml_view(hoName)

        # print 'returning %d objects' % len(data)
        return data

    def xml_get(self, hardwareObjectName, old_mtime=-1):
        if self.server.hardwareRepositoryDirectory is not None:
            filename = os.path.normpath(
                self.server.hardwareRepositoryDirectory + hardwareObjectName + ".xml"
            )

            try:
                file_stats = os.stat(filename)
            except OSError as err:
                return {"xmldata": ""}
            else:
                mtime = file_stats[stat.ST_MTIME]
                if mtime > old_mtime:
                    return {
                        "xmldata": self.xml_view(hardwareObjectName),
                        "mtime": mtime,
                    }
                return {"xmldata": "", "mtime": mtime}
        else:
            return {"xmldata": ""}

    def xml_getall(self, *hoNames):  # hardwareObjectName):
        hardwareObjectsDict = {}

        for hoName in hoNames:
            hoDict = self.xml_get(hoName)
            hardwareObjectsDict[hoName] = hoDict

            if self.server.hardwareRepositoryDirectory is not None:
                filename = os.path.normpath(
                    self.server.hardwareRepositoryDirectory + hoName + ".xml"
                )

                if os.path.exists(filename):
                    curHandler = XMLReferencesReadingHandler()

                    try:
                        xml.sax.parse(filename, curHandler)
                    except SAXParseException:
                        pass
                    else:
                        for ref in curHandler.references:
                            hoDict = self.xml_get(ref)

                            if len(hoDict) > 0:
                                hardwareObjectsDict[ref] = hoDict

        return hardwareObjectsDict


class HardwareRepositorySpecServer(SpecServer.SpecServer):
    def __init__(self, *args):
        SpecServer.SpecServer.__init__(self, handler=SpecServerConnection, *args)

        self.hardwareRepositoryDirectory = None

    def broadcast_update_event(self, updatedHardwareObject):
        for client in self.clients:
            if client.updateRegistered:
                client.send_msg_event("update", updatedHardwareObject)

    def setDirectory(self, dir):
        if os.path.exists(dir):
            self.hardwareRepositoryDirectory = dir
        else:
            self.hardwareRepositoryDirectory = None

    def readDirectory(self):
        """Walk through the Hardware Repository directories, and retrieve the XML files found

          Return :
          the dictionary of all the XML files found. Keys are the corresponding Hardware Object names.
          """
        if self.hardwareRepositoryDirectory is not None:
            baseDir = self.hardwareRepositoryDirectory
            hardwareObjectFilenames = {}

            for dirpath, dirnames, filenames in os.walk(baseDir):
                prefix = dirpath[len(baseDir) :]

                for file in filenames:
                    if file.endswith(".xml"):
                        shortName = ".".join(file.split(os.extsep)[:-1])
                        hoName = os.path.join(prefix, shortName)
                        if hoName[0] != os.sep:
                            hoName = os.sep + hoName
                        hardwareObjectFilenames[hoName] = os.path.join(dirpath, file)

            return hardwareObjectFilenames
        else:
            return {"__error__": "No Hardware Repository directory."}
