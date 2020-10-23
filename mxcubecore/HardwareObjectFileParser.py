import logging
import xml.sax
from xml.sax.handler import ContentHandler

from HardwareRepository import BaseHardwareObjects

currentXML = None

try:
    newObjectsClasses = {
        "equipment": BaseHardwareObjects.Equipment,
        "device": BaseHardwareObjects.Device,
        "procedure": BaseHardwareObjects.Procedure,
    }
except AttributeError:
    pass


def parse(filename, name):
    curHandler = HardwareObjectHandler(name)

    global currentXML
    try:
        f = open(filename)
        currentXML = f.read()
    except Exception:
        currentXML = None

    xml.sax.parse(filename, curHandler)

    return curHandler.getHardwareObject()


def parseString(XMLHardwareObject, name):
    global currentXML
    currentXML = XMLHardwareObject
    curHandler = HardwareObjectHandler(name)
    # LNLS
    # python2.7
    # xml.sax.parseString(XMLHardwareObject, curHandler)
    # python3.4
    xml.sax.parseString(str.encode(XMLHardwareObject), curHandler)
    return curHandler.getHardwareObject()


def loadModule(hardwareObjectName):
    return __import__(hardwareObjectName, globals(), locals(), [""])


def instanciateClass(moduleName, className, objectName):
    module = loadModule(moduleName)
    if module is None:
        return
    else:
        try:
            classObj = getattr(module, className)
        except AttributeError:
            logging.getLogger("HWR").error(
                "No class %s in module %s", className, moduleName
            )
        else:
            # check the XML
            if module.__doc__ is not None and currentXML is not None:
                i = module.__doc__.find("template:")

                if i >= 0:
                    XMLTemplate = module.__doc__[i + 10 :]

                    xmlStructureRetriever = XMLStructureRetriever()
                    xml.sax.parseString(currentXML, xmlStructureRetriever)
                    currentStructure = xmlStructureRetriever.getStructure()
                    xmlStructureRetriever = XMLStructureRetriever()
                    xml.sax.parseString(XMLTemplate, xmlStructureRetriever)
                    templateStructure = xmlStructureRetriever.getStructure()

                    if not templateStructure == currentStructure:
                        logging.getLogger("HWR").error(
                            "%s: XML file does not match the %s class template"
                            % (objectName, className)
                        )
                        return
            try:
                newInstance = classObj(objectName)
            except Exception:
                logging.getLogger("HWR").exception(
                    "Cannot instanciate class %s", className
                )
            else:
                return newInstance


class HardwareObjectHandler(ContentHandler):
    def __init__(self, name):
        ContentHandler.__init__(self)

        self.name = name
        self.classError = False
        self.objects = []
        self.reference = ""
        self.property = ""
        self.elementIsAReference = False
        self.elementRole = None
        self.buffer = ""
        self.path = ""
        self.previousPath = ""
        self.hwr_import_reference = None

    def getHardwareObject(self):
        if self.hwr_import_reference is not None:
            return self.hwr_import_reference
        elif len(self.objects) == 1:
            return self.objects[0]

    def startElement(self, name, attrs):
        if self.classError:
            return

        self.buffer = ""

        if len(self.objects) == 0:
            objectName = self.name
        else:
            objectName = name

        assert not self.elementIsAReference

        self.elementRole = None
        self.property = ""
        self.command = {}
        self.channel = {}

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

        _attrs = attrs
        attrs = {}

        for k in list(_attrs.keys()):
            v = str(_attrs[k])

            if v == "None":
                attrs[str(k)] = None
            else:
                try:
                    attrs[str(k)] = int(v)
                except Exception:
                    try:
                        attrs[str(k)] = float(v)
                    except Exception:
                        if v == "False":
                            attrs[str(k)] = False
                        elif v == "True":
                            attrs[str(k)] = True
                        else:
                            attrs[str(k)] = v
        if name == "hwr_import":
            self.hwr_import_reference = attrs["href"]

        if "role" in attrs:
            self.elementRole = attrs["role"]
        if name == "device":
            # maybe we have to add the DeviceContainer mix-in class to each node of
            # the Hardware Object hierarchy
            i = len(self.objects) - 1
            while i >= 0 and not isinstance(
                self.objects[i], BaseHardwareObjects.DeviceContainer
            ):
                # newClass = new.classobj("toto", (self.objects[i].__class__,) + self.objects[i].__class__.__bases__ + (BaseHardwareObjects.DeviceContainer, ), {})
                # TODO replace deprecated DeviceContainerNode with a different class
                self.objects[i].__class__ = BaseHardwareObjects.DeviceContainerNode
                i -= 1

        #
        # is element a reference to another hardware object ?
        #
        ref = "hwrid" in attrs and attrs["hwrid"] or "href" in attrs and attrs["href"]
        if ref:
            self.elementIsAReference = True
            self.reference = str(ref)

            if self.reference.startswith("../"):
                self.reference = "/".join(
                    self.name.split("/")[:-1] + [self.reference[3:]]
                )
            elif self.reference.startswith("./"):
                self.reference = "/".join(
                    self.name.split("/")[:-1] + [self.reference[2:]]
                )
            return

        if name in newObjectsClasses:
            if "class" in attrs:
                moduleName = str(attrs["class"])
                className = moduleName.split(".")[-1]

                newObject = instanciateClass(moduleName, className, objectName)

                if newObject is None:
                    self.classError = True
                    return
                else:
                    newObject.setPath(self.path)
                    self.objects.append(newObject)
            else:
                newObjectClass = newObjectsClasses[name]
                newObject = newObjectClass(objectName)
                newObject.setPath(self.path)

                self.objects.append(newObject)
        elif name == "command":
            if "name" in attrs and "type" in attrs:
                # short command notation
                self.command.update(attrs)
            else:
                # long command notation (allow arguments)
                self.objects.append(BaseHardwareObjects.HardwareObjectNode(objectName))
        elif name == "channel":
            if "name" in attrs and "type" in attrs:
                self.channel.update(attrs)
        else:
            if len(self.objects) == 0:
                if "class" in attrs:
                    moduleName = str(attrs["class"])
                    className = moduleName.split(".")[-1]

                    newObject = instanciateClass(moduleName, className, objectName)

                    if newObject is None:
                        self.classError = True
                        return
                else:
                    newObject = BaseHardwareObjects.HardwareObject(objectName)

                newObject.setPath(self.path)
                self.objects.append(newObject)
                """
                # maybe we can create a HardwareObject ? be strict for the moment...
                logging.getLogger("HWR").error("%s: unknown Hardware Object type (should be one of %s)", objectName, str(newObjectsClasses.keys()))
                self.classError = True
                return
                """
            else:
                newObject = BaseHardwareObjects.HardwareObjectNode(objectName)
                newObject.setPath(self.path)
                self.objects.append(newObject)

                self.property = name  # element is supposed to be a Property

    def characters(self, content):
        if self.classError:
            return

        self.buffer += str(content)

    def endElement(self, name):
        if self.classError:
            return

        name = str(name)

        if self.elementIsAReference:
            if len(self.objects) > 0:
                self.objects[0].addReference(
                    name, self.reference, role=self.elementRole
                )
        else:
            try:
                if name == "command":
                    if len(self.command) > 0:
                        if len(self.objects) > 0:
                            self.objects[-1].add_command(
                                self.command, self.buffer, addNow=False
                            )
                    else:
                        if len(self.objects) > 1:
                            self.objects[-2].add_command(
                                self.objects.pop(), addNow=False
                            )
                elif name == "channel":
                    if len(self.channel) > 0:
                        if len(self.objects) > 0:
                            self.objects[-1].add_channel(
                                self.channel, self.buffer, addNow=False
                            )
                elif name == self.property:
                    del self.objects[-1]  # remove empty object
                    self.objects[-1].setProperty(name, self.buffer)
                else:
                    if len(self.objects) == 1:
                        return

                    if len(self.objects) > 1:
                        self.objects[-2].addObject(
                            name, self.objects[-1], role=self.elementRole
                        )
                    if len(self.objects) > 0:
                        del self.objects[-1]
            except Exception:
                logging.getLogger("HWR").exception(
                    "%s: error while creating Hardware Object from XML file", self.name
                )

        self.elementIsAReference = False
        self.elementRole = None
        self.buffer = ""
        self.previousPath = self.path
        self.path = self.path[
            : self.path.rfind("/")
        ]  # remove last added name and suffix


class XMLStructure:
    def __init__(self):
        self.xmlpaths = set()
        self.attributes = {}

    def add(self, xmlpath, attributesSet):
        self.xmlpaths.add(xmlpath)

        if len(attributesSet) > 0:
            self.attributes[xmlpath] = attributesSet

    def __eq__(self, s):
        if self.xmlpaths.issubset(s.xmlpaths):
            for xmlpath, attributeSet in self.attributes.items():
                try:
                    attributeSet2 = s.attributes[xmlpath]
                except KeyError:
                    return False
                else:
                    if not attributeSet.issubset(attributeSet2):
                        return False

            return True
        else:
            return False


class XMLStructureRetriever(ContentHandler):
    def __init__(self):
        ContentHandler.__init__(self)

        self.path = ""
        self.previousPath = ""
        self.currentAttributes = set()
        self.structure = XMLStructure()

    def getStructure(self):
        return self.structure

    def startElement(self, name, attrs):
        self.path += "/" + str(name) + "[%d]"
        i = self.previousPath.rfind("[")

        if i >= 0 and self.path[:-4] == self.previousPath[:i]:
            index = int(self.previousPath[i + 1 : -1]) + 1
        else:
            index = 1  # XPath indexes begin at 1

        self.path %= index

        for attr, value in list(attrs.items()):
            if str(attr) == "hwrid":
                attr = "href"

            self.currentAttributes.add("%s=%s" % (str(attr), str(value)))

    def endElement(self, name):
        self.structure.add(self.path, self.currentAttributes)

        self.previousPath = self.path
        self.path = self.path[: self.path.rfind("/")]
