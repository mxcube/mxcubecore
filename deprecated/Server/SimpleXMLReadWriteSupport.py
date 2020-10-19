import sys
import io
from xml.sax.saxutils import XMLGenerator
from xml.sax import make_parser
from xml.sax import SAXParseException
from xml.sax.xmlreader import AttributesImpl
from xml.sax.handler import ContentHandler

_parser = make_parser()

NOTMATCH, MAYMATCH, MATCH = (0, 1, 2)


def testPath(pathParts, queryPathParts, attrs):
    """Given two paths, return True if the query path matches the current path, False otherwise"""
    if isinstance(pathParts, type("")):
        pathParts = pathParts.split("/")

    if isinstance(queryPathParts, type("")):
        queryPathParts = queryPathParts.split("/")

    nPathParts = len(pathParts)
    match = False
    mayMatch = True

    if nPathParts == len(queryPathParts):
        match = True

        for i in range(nPathParts):
            queryPathPart = queryPathParts[i]
            pathPart = pathParts[i]

            if queryPathPart == pathPart or queryPathPart == "*":
                continue
            else:
                j = queryPathPart.rfind("[")
                k = pathPart.rfind("[")

                if j < 0:
                    #
                    # query path part as no index specification ;
                    # does the current path part without index specification match ?
                    #
                    if queryPathPart != pathPart[:k]:
                        match = False
                        break
                else:
                    if queryPathPart[:j] == pathPart[:k] or queryPathPart[:j] == "*":
                        if queryPathPart[j + 1 : -1] == pathPart[k + 1 : -1]:
                            continue
                        else:
                            #
                            # does the query path have an attribute specifier ?
                            #
                            if queryPathPart[j + 1] == "@":
                                #
                                # now check if attribute matches
                                #
                                attributePart = queryPathPart[j + 2 : -1]
                                k = attributePart.find("=")
                                if k >= 0:
                                    queryAttribute = attributePart[:k]
                                    queryAttributeValue = attributePart[k + 1 :]
                                    queryAttribute.strip()
                                    queryAttributeValue.strip()

                                    if (
                                        queryAttribute in attrs
                                        and attrs[queryAttribute] == queryAttributeValue
                                    ):
                                        continue
                                    else:
                                        match = False
                                        break
                                else:
                                    if attributePart not in attrs:
                                        match = False
                                        break
                            else:
                                match = False
                                break
                    else:
                        match = False
                        break

    return match


def read(inputFile, path):
    if isinstance(inputFile, type("")):
        #
        # open input file
        #
        inputFile = open(inputFile, "r")

    curHandler = XMLReadingHandler(path)
    _parser.setContentHandler(curHandler)

    inputFile.seek(0)  # move to the beginning of the file

    _parser.parse(inputFile)

    return curHandler.get_value()


class XMLReadingHandler(ContentHandler):
    def __init__(self, path):
        ContentHandler.__init__(self)

        self.queryPathParts = path.split("/")
        self.path = ""
        self.previous_path = ""
        self.elementName = None
        self.value = []
        self.childDepth = 0

        if self.queryPathParts[-1][0] == "@":
            # we want to read an attribute
            self.queryAttribute = self.queryPathParts[-1][1:]

            del self.queryPathParts[-1]
        else:
            self.queryAttribute = None

    def startElement(self, name, attrs):
        #
        # determine path to the new object
        #
        self.path += "/" + str(name) + "[%d]"
        i = self.previous_path.rfind("[")

        if i >= 0 and self.path[:-4] == self.previous_path[:i]:
            objectIndex = int(self.previous_path[i + 1 : -1]) + 1
        else:
            objectIndex = 1  # XPath indexes begin at 1

        self.path %= objectIndex

        if self.elementName is None:
            if testPath(self.path, self.queryPathParts, attrs):
                if self.queryAttribute is not None:
                    if self.queryAttribute in attrs:
                        self.value.append(
                            {"__value__": str(attrs[self.queryAttribute])}
                        )
                else:
                    self.childDepth = 0
                    self.elementName = name

                    # append new node to value
                    self.value.append(
                        {"__value__": "", "__path__": self.path, "__children__": {}}
                    )

                    for key, value in list(attrs.items()):
                        # add attributes
                        self.value[-1][str(key)] = str(value)
        else:
            self.childDepth += 1

    def characters(self, content):
        if self.elementName is not None and self.childDepth == 0:
            self.value[-1]["__value__"] += str(content)

    def endElement(self, name):
        if self.elementName is not None and self.childDepth == 1:
            # add children
            self.value[-1]["__children__"][self.path] = str(name)

        if self.elementName == name and self.childDepth == 0:
            self.elementName = None

        self.childDepth -= 1
        self.previous_path = self.path
        self.path = self.path[
            : self.path.rfind("/")
        ]  # remove last added name and suffix

    def get_value(self):
        return self.value


def update(inputFile, path, value, outputFile=None):
    if isinstance(inputFile, type("")):
        #
        # open input file
        #
        inputFile = open(inputFile, "r")

    curHandler = XMLUpdateHandler(path, value)
    _parser.setContentHandler(curHandler)
    inputFile.seek(0)  # move to the beginning of the file

    _parser.parse(inputFile)

    if outputFile is None:
        outputFile = sys.stdout
    else:
        if isinstance(outputFile, type("")):
            outputFile = open(outputFile, "w")
        else:
            outputFile.flush()
            outputFile.seek(0)
            outputFile.truncate(0)

    outputFile.write(curHandler.getBuffer())
    outputFile.flush()


def batchUpdate(inputFile, paths, values, outputFile=None):
    if isinstance(inputFile, type("")):
        #
        # open input file
        #
        inputFile = open(inputFile, "r")

    if type(paths) != type(values) != type([]):
        raise TypeError

    curHandler = XMLBatchUpdateHandler(paths, values)
    _parser.setContentHandler(curHandler)
    inputFile.seek(0)

    _parser.parse(inputFile)

    if outputFile is None:
        outputFile = sys.stdout
    else:
        if isinstance(outputFile, type("")):
            outputFile = open(outputFile, "w")
        else:
            outputFile.flush()
            outputFile.seek(0)
            outputFile.truncate(0)

    outputFile.write(curHandler.getBuffer())
    outputFile.flush()


def remove(inputFile, path, outputFile=None):
    if isinstance(inputFile, type("")):
        #
        # open input file
        #
        inputFile = open(inputFile, "r")

    curHandler = XMLRemoveHandler(path)
    _parser.setContentHandler(curHandler)
    inputFile.seek(0)

    _parser.parse(inputFile)

    if outputFile is None:
        outputFile = sys.stdout
    else:
        if isinstance(outputFile, type("")):
            outputFile = open(outputFile, "w")
        else:
            outputFile.flush()
            outputFile.seek(0)
            outputFile.truncate(0)
    outputFile.write(curHandler.getBuffer())
    outputFile.flush()


class XMLModifier(XMLGenerator):
    def __init__(self):
        self.__buffer = io.StringIO()

        XMLGenerator.__init__(self, self.__buffer)

    def getBuffer(self):
        return self.__buffer.get_value()


class XMLUpdateHandler(XMLModifier):
    def __init__(self, path, newValue):
        XMLModifier.__init__(self)

        self.path = ""
        self.previous_path = ""
        self.modifiedContent = None
        self.queryPathParts = path.split("/")
        self.updatedValue = str(newValue)

        if self.queryPathParts[-1][0] == "@":
            # we want to update an attribute
            self.queryAttribute = self.queryPathParts[-1][1:]

            del self.queryPathParts[-1]
        else:
            self.queryAttribute = None

    def startElement(self, name, attrs):
        #
        # determine path to the new element
        #
        self.path += "/" + str(name) + "[%d]"
        i = self.previous_path.rfind("[")

        if i >= 0 and self.path[:-4] == self.previous_path[:i]:
            elementIndex = int(self.previous_path[i + 1 : -1]) + 1
        else:
            elementIndex = 1  # XPath indexes begin at 1

        self.path %= elementIndex
        pathParts = self.path.split("/")

        if testPath(pathParts, self.queryPathParts, attrs):
            if self.queryAttribute is None:
                self.modifiedContent = self.updatedValue
            else:
                new_attrs = {}
                for key, value in list(attrs.items()):
                    new_attrs[key] = value
                new_attrs[self.queryAttribute] = self.updatedValue

                attrs = AttributesImpl(new_attrs)

        XMLModifier.startElement(self, name, attrs)

    def characters(self, content):
        if self.modifiedContent is not None:
            XMLModifier.characters(self, self.modifiedContent)
            self.modifiedContent = None
        else:
            XMLModifier.characters(self, content)

    def endElement(self, name):
        if self.modifiedContent is not None:
            XMLModifier.characters(self, self.modifiedContent)
            self.modifiedContent = None

        XMLModifier.endElement(self, name)

        self.previous_path = self.path
        self.path = self.path[
            : self.path.rfind("/")
        ]  # remove last added name and suffix


class XMLBatchUpdateHandler(XMLModifier):
    def __init__(self, paths, values):
        XMLModifier.__init__(self)

        self.path = ""
        self.previous_path = ""
        self.modifiedContent = None
        self.queryPathsParts = []
        self.queryAttribute = []

        for path in paths:
            self.queryPathsParts.append(path.split("/"))
            if self.queryPathsParts[-1][-1][0] == "@":
                self.queryAttribute.append(self.queryPathsParts[-1][-1][1:])
                del self.queryPathsParts[-1][-1]
            else:
                self.queryAttribute.append(None)

        self.updatedValues = []
        for value in values:
            self.updatedValues.append(str(value))

    def startElement(self, name, attrs):
        #
        # determine path to the new element
        #
        self.path += "/" + str(name) + "[%d]"
        i = self.previous_path.rfind("[")

        if i >= 0 and self.path[:-4] == self.previous_path[:i]:
            elementIndex = int(self.previous_path[i + 1 : -1]) + 1
        else:
            elementIndex = 1  # XPath indexes begin at 1

        self.path %= elementIndex
        pathParts = self.path.split("/")
        i = 0

        for queryPathParts in self.queryPathsParts:
            if testPath(pathParts, queryPathParts, attrs):
                if self.queryAttribute[i] is None:
                    self.modifiedContent = self.updatedValues[i]
                else:
                    new_attrs = {}
                    for key, value in list(attrs.items()):
                        new_attrs[key] = value
                    new_attrs[self.queryAttribute[i]] = self.updatedValues[i]

                    attrs = AttributesImpl(new_attrs)
            i += 1

        XMLModifier.startElement(self, name, attrs)

    def characters(self, content):
        if self.modifiedContent is not None:
            XMLModifier.characters(self, self.modifiedContent)
            self.modifiedContent = None
        else:
            XMLModifier.characters(self, content)

    def endElement(self, name):
        if self.modifiedContent is not None:
            XMLModifier.characters(self, self.modifiedContent)
            self.modifiedContent = None

        XMLModifier.endElement(self, name)

        self.previous_path = self.path
        self.path = self.path[
            : self.path.rfind("/")
        ]  # remove last added name and suffix


class XMLRemoveHandler(XMLModifier):
    def __init__(self, path):
        XMLModifier.__init__(self)

        self.path = ""
        self.previous_path = ""
        self.skip = False
        self.skipElementPath = None
        self.queryPathParts = path.split("/")

        if self.queryPathParts[-1][0] == "@":
            # we want to remove an attribute
            self.queryAttribute = self.queryPathParts[-1][1:]

            del self.queryPathParts[-1]
        else:
            self.queryAttribute = None

    def startElement(self, name, attrs):
        #
        # determine path to the new element
        #
        self.path += "/" + str(name) + "[%d]"
        i = self.previous_path.rfind("[")

        if i >= 0 and self.path[:-4] == self.previous_path[:i]:
            elementIndex = int(self.previous_path[i + 1 : -1]) + 1
        else:
            elementIndex = 1  # XPath indexes begin at 1

        self.path %= elementIndex

        if self.skip:
            return

        pathParts = self.path.split("/")
        if testPath(pathParts, self.queryPathParts, attrs):
            if self.queryAttribute is None:
                self.skip = True
                self.skipElementPath = self.path
                return
            else:
                if self.queryAttribute in attrs:
                    new_attrs = {}
                    for key, value in list(attrs.items()):
                        new_attrs[key] = value
                    del new_attrs[self.queryAttribute]

                    attrs = AttributesImpl(new_attrs)

        XMLModifier.startElement(self, name, attrs)

    def characters(self, content):
        if not self.skip:
            XMLModifier.characters(self, content)

    def endElement(self, name):
        if self.skip:
            if self.skipElementPath == self.path:
                self.skip = False
                self.skipElementPath = None
        else:
            XMLModifier.endElement(self, name)

        self.previous_path = self.path
        self.path = self.path[
            : self.path.rfind("/")
        ]  # remove last added name and suffix
