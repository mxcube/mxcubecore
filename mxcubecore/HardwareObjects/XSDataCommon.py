#!/usr/bin/env python

#
# Generated Tue Jun 21 10:50::49 2011 by EDGenerateDS.
#

import sys
from xml.dom import (
    Node,
    minidom,
)

#
# Support/utility functions.
#

# Compabiltity between Python 2 and 3:
if sys.version.startswith("3"):
    unicode = str
    from io import StringIO
else:
    from StringIO import StringIO


def showIndent(outfile, level):
    for idx in range(level):
        outfile.write(unicode("    "))


def checkType(_strClassName, _strMethodName, _value, _strExpectedType):
    if _strExpectedType not in ["float", "double", "string", "boolean", "integer"]:
        if _value is not None:
            if _value.__class__.__name__ != _strExpectedType:
                strMessage = "ERROR! %s.%s argument is not %s but %s" % (
                    _strClassName,
                    _strMethodName,
                    _strExpectedType,
                    _value.__class__.__name__,
                )
                print(strMessage)
                # raise Exception(strMessage)


# 	elif _value is None:
# 		strMessage = "ERROR! %s.%s argument which should be %s is None" % (_strClassName, _strMethodName, _strExpectedType)
# 		print(strMessage)
# 		#raise Exception(strMessage)


def warnEmptyAttribute(_strName, _strTypeName):
    pass
    # if not _strTypeName in ["float", "double", "string", "boolean", "integer"]:
    # 		print("Warning! Non-optional attribute %s of type %s is None!" % (_strName, _strTypeName))


class MixedContainer(object):
    # Constants for category:
    CategoryNone = 0
    CategoryText = 1
    CategorySimple = 2
    CategoryComplex = 3
    # Constants for content_type:
    TypeNone = 0
    TypeText = 1
    TypeString = 2
    TypeInteger = 3
    TypeFloat = 4
    TypeDecimal = 5
    TypeDouble = 6
    TypeBoolean = 7

    def __init__(self, category, content_type, name, value):
        self.category = category
        self.content_type = content_type
        self.name = name
        self.value = value

    def getCategory(self):
        return self.category

    def getContenttype(self, content_type):
        return self.content_type

    def getValue(self):
        return self.value

    def getName(self):
        return self.name

    def export(self, outfile, level, name):
        if self.category == MixedContainer.CategoryText:
            outfile.write(self.value)
        elif self.category == MixedContainer.CategorySimple:
            self.exportSimple(outfile, level, name)
        else:  # category == MixedContainer.CategoryComplex
            self.value.export(outfile, level, name)

    def exportSimple(self, outfile, level, name):
        if self.content_type == MixedContainer.TypeString:
            outfile.write(unicode("<%s>%s</%s>" % (self.name, self.value, self.name)))
        elif (
            self.content_type == MixedContainer.TypeInteger
            or self.content_type == MixedContainer.TypeBoolean
        ):
            outfile.write(unicode("<%s>%d</%s>" % (self.name, self.value, self.name)))
        elif (
            self.content_type == MixedContainer.TypeFloat
            or self.content_type == MixedContainer.TypeDecimal
        ):
            outfile.write(unicode("<%s>%f</%s>" % (self.name, self.value, self.name)))
        elif self.content_type == MixedContainer.TypeDouble:
            outfile.write(unicode("<%s>%g</%s>" % (self.name, self.value, self.name)))


#
# Data representation classes.
#


class XSConfiguration(object):
    def __init__(self, XSPluginList=None):
        checkType(
            "XSConfiguration",
            "Constructor of XSConfiguration",
            XSPluginList,
            "XSPluginList",
        )
        self.__XSPluginList = XSPluginList

    def getXSPluginList(self):
        return self.__XSPluginList

    def setXSPluginList(self, XSPluginList):
        checkType("XSConfiguration", "setXSPluginList", XSPluginList, "XSPluginList")
        self.__XSPluginList = XSPluginList

    def delXSPluginList(self):
        self.__XSPluginList = None

    # Properties
    XSPluginList = property(
        getXSPluginList, setXSPluginList, delXSPluginList, "Property for XSPluginList"
    )

    def export(self, outfile, level, name_="XSConfiguration"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSConfiguration"):
        if self.__XSPluginList is not None:
            self.XSPluginList.export(outfile, level, name_="XSPluginList")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "XSPluginList":
            obj_ = XSPluginList()
            obj_.build(child_)
            self.setXSPluginList(obj_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSConfiguration")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSConfiguration")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSConfiguration is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSConfiguration.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSConfiguration()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSConfiguration")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSConfiguration()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSConfiguration


class XSData(object):
    def __init__(self):
        pass

    def export(self, outfile, level, name_="XSData"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSData"):
        pass

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        pass

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSData")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSData")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSData is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSData.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSData()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSData")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSData()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSData


class XSDataDisplacement(object):
    """These simple objects that use built-in types are basically aimed to be used by the rest of the data model objects."""

    def __init__(self, value=None, unit=None, error=None):
        checkType(
            "XSDataDisplacement",
            "Constructor of XSDataDisplacement",
            error,
            "XSDataDouble",
        )
        self.__error = error
        checkType(
            "XSDataDisplacement",
            "Constructor of XSDataDisplacement",
            unit,
            "XSDataString",
        )
        self.__unit = unit
        checkType(
            "XSDataDisplacement", "Constructor of XSDataDisplacement", value, "double"
        )
        self.__value = value

    def getError(self):
        return self.__error

    def setError(self, error):
        checkType("XSDataDisplacement", "setError", error, "XSDataDouble")
        self.__error = error

    def delError(self):
        self.__error = None

    # Properties
    error = property(getError, setError, delError, "Property for error")

    def getUnit(self):
        return self.__unit

    def setUnit(self, unit):
        checkType("XSDataDisplacement", "setUnit", unit, "XSDataString")
        self.__unit = unit

    def delUnit(self):
        self.__unit = None

    # Properties
    unit = property(getUnit, setUnit, delUnit, "Property for unit")

    def getValue(self):
        return self.__value

    def setValue(self, value):
        checkType("XSDataDisplacement", "setValue", value, "double")
        self.__value = value

    def delValue(self):
        self.__value = None

    # Properties
    value = property(getValue, setValue, delValue, "Property for value")

    def export(self, outfile, level, name_="XSDataDisplacement"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataDisplacement"):
        if self.__error is not None:
            self.error.export(outfile, level, name_="error")
        if self.__unit is not None:
            self.unit.export(outfile, level, name_="unit")
        if self.__value is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<value>%e</value>\n" % self.__value))
        else:
            warnEmptyAttribute("value", "double")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "error":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setError(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "unit":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setUnit(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "value":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__value = fval_

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataDisplacement")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataDisplacement")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataDisplacement is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataDisplacement.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataDisplacement()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataDisplacement")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataDisplacement()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataDisplacement


class XSDataExecutionInfo(object):
    """This class contains details of the execution of a particular plugin."""

    def __init__(
        self,
        workingDirectory=None,
        systeminfo=None,
        startOfExecution=None,
        pluginName=None,
        executionTime=None,
        configuration=None,
        baseDirectory=None,
    ):
        checkType(
            "XSDataExecutionInfo",
            "Constructor of XSDataExecutionInfo",
            baseDirectory,
            "XSDataFile",
        )
        self.__baseDirectory = baseDirectory
        checkType(
            "XSDataExecutionInfo",
            "Constructor of XSDataExecutionInfo",
            configuration,
            "XSConfiguration",
        )
        self.__configuration = configuration
        checkType(
            "XSDataExecutionInfo",
            "Constructor of XSDataExecutionInfo",
            executionTime,
            "XSDataTime",
        )
        self.__executionTime = executionTime
        checkType(
            "XSDataExecutionInfo",
            "Constructor of XSDataExecutionInfo",
            pluginName,
            "XSDataString",
        )
        self.__pluginName = pluginName
        checkType(
            "XSDataExecutionInfo",
            "Constructor of XSDataExecutionInfo",
            startOfExecution,
            "XSDataDate",
        )
        self.__startOfExecution = startOfExecution
        checkType(
            "XSDataExecutionInfo",
            "Constructor of XSDataExecutionInfo",
            systeminfo,
            "XSDataSysteminfo",
        )
        self.__systeminfo = systeminfo
        checkType(
            "XSDataExecutionInfo",
            "Constructor of XSDataExecutionInfo",
            workingDirectory,
            "XSDataFile",
        )
        self.__workingDirectory = workingDirectory

    def getBaseDirectory(self):
        return self.__baseDirectory

    def setBaseDirectory(self, baseDirectory):
        checkType(
            "XSDataExecutionInfo", "setBaseDirectory", baseDirectory, "XSDataFile"
        )
        self.__baseDirectory = baseDirectory

    def delBaseDirectory(self):
        self.__baseDirectory = None

    # Properties
    baseDirectory = property(
        getBaseDirectory,
        setBaseDirectory,
        delBaseDirectory,
        "Property for baseDirectory",
    )

    def getConfiguration(self):
        return self.__configuration

    def setConfiguration(self, configuration):
        checkType(
            "XSDataExecutionInfo", "setConfiguration", configuration, "XSConfiguration"
        )
        self.__configuration = configuration

    def delConfiguration(self):
        self.__configuration = None

    # Properties
    configuration = property(
        getConfiguration,
        setConfiguration,
        delConfiguration,
        "Property for configuration",
    )

    def getExecutionTime(self):
        return self.__executionTime

    def setExecutionTime(self, executionTime):
        checkType(
            "XSDataExecutionInfo", "setExecutionTime", executionTime, "XSDataTime"
        )
        self.__executionTime = executionTime

    def delExecutionTime(self):
        self.__executionTime = None

    # Properties
    executionTime = property(
        getExecutionTime,
        setExecutionTime,
        delExecutionTime,
        "Property for executionTime",
    )

    def getPluginName(self):
        return self.__pluginName

    def setPluginName(self, pluginName):
        checkType("XSDataExecutionInfo", "setPluginName", pluginName, "XSDataString")
        self.__pluginName = pluginName

    def delPluginName(self):
        self.__pluginName = None

    # Properties
    pluginName = property(
        getPluginName, setPluginName, delPluginName, "Property for pluginName"
    )

    def getStartOfExecution(self):
        return self.__startOfExecution

    def setStartOfExecution(self, startOfExecution):
        checkType(
            "XSDataExecutionInfo", "setStartOfExecution", startOfExecution, "XSDataDate"
        )
        self.__startOfExecution = startOfExecution

    def delStartOfExecution(self):
        self.__startOfExecution = None

    # Properties
    startOfExecution = property(
        getStartOfExecution,
        setStartOfExecution,
        delStartOfExecution,
        "Property for startOfExecution",
    )

    def getSysteminfo(self):
        return self.__systeminfo

    def setSysteminfo(self, systeminfo):
        checkType(
            "XSDataExecutionInfo", "setSysteminfo", systeminfo, "XSDataSysteminfo"
        )
        self.__systeminfo = systeminfo

    def delSysteminfo(self):
        self.__systeminfo = None

    # Properties
    systeminfo = property(
        getSysteminfo, setSysteminfo, delSysteminfo, "Property for systeminfo"
    )

    def getWorkingDirectory(self):
        return self.__workingDirectory

    def setWorkingDirectory(self, workingDirectory):
        checkType(
            "XSDataExecutionInfo", "setWorkingDirectory", workingDirectory, "XSDataFile"
        )
        self.__workingDirectory = workingDirectory

    def delWorkingDirectory(self):
        self.__workingDirectory = None

    # Properties
    workingDirectory = property(
        getWorkingDirectory,
        setWorkingDirectory,
        delWorkingDirectory,
        "Property for workingDirectory",
    )

    def export(self, outfile, level, name_="XSDataExecutionInfo"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataExecutionInfo"):
        if self.__baseDirectory is not None:
            self.baseDirectory.export(outfile, level, name_="baseDirectory")
        else:
            warnEmptyAttribute("baseDirectory", "XSDataFile")
        if self.__configuration is not None:
            self.configuration.export(outfile, level, name_="configuration")
        else:
            warnEmptyAttribute("configuration", "XSConfiguration")
        if self.__executionTime is not None:
            self.executionTime.export(outfile, level, name_="executionTime")
        else:
            warnEmptyAttribute("executionTime", "XSDataTime")
        if self.__pluginName is not None:
            self.pluginName.export(outfile, level, name_="pluginName")
        else:
            warnEmptyAttribute("pluginName", "XSDataString")
        if self.__startOfExecution is not None:
            self.startOfExecution.export(outfile, level, name_="startOfExecution")
        else:
            warnEmptyAttribute("startOfExecution", "XSDataDate")
        if self.__systeminfo is not None:
            self.systeminfo.export(outfile, level, name_="systeminfo")
        else:
            warnEmptyAttribute("systeminfo", "XSDataSysteminfo")
        if self.__workingDirectory is not None:
            self.workingDirectory.export(outfile, level, name_="workingDirectory")
        else:
            warnEmptyAttribute("workingDirectory", "XSDataFile")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "baseDirectory":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setBaseDirectory(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "configuration":
            obj_ = XSConfiguration()
            obj_.build(child_)
            self.setConfiguration(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "executionTime":
            obj_ = XSDataTime()
            obj_.build(child_)
            self.setExecutionTime(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "pluginName":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setPluginName(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "startOfExecution":
            obj_ = XSDataDate()
            obj_.build(child_)
            self.setStartOfExecution(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "systeminfo":
            obj_ = XSDataSysteminfo()
            obj_.build(child_)
            self.setSysteminfo(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "workingDirectory":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setWorkingDirectory(obj_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataExecutionInfo")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataExecutionInfo")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataExecutionInfo is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataExecutionInfo.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataExecutionInfo()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataExecutionInfo")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataExecutionInfo()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataExecutionInfo


class XSDataKeyValuePair(object):
    def __init__(self, value=None, key=None):
        checkType(
            "XSDataKeyValuePair",
            "Constructor of XSDataKeyValuePair",
            key,
            "XSDataString",
        )
        self.__key = key
        checkType(
            "XSDataKeyValuePair",
            "Constructor of XSDataKeyValuePair",
            value,
            "XSDataString",
        )
        self.__value = value

    def getKey(self):
        return self.__key

    def setKey(self, key):
        checkType("XSDataKeyValuePair", "setKey", key, "XSDataString")
        self.__key = key

    def delKey(self):
        self.__key = None

    # Properties
    key = property(getKey, setKey, delKey, "Property for key")

    def getValue(self):
        return self.__value

    def setValue(self, value):
        checkType("XSDataKeyValuePair", "setValue", value, "XSDataString")
        self.__value = value

    def delValue(self):
        self.__value = None

    # Properties
    value = property(getValue, setValue, delValue, "Property for value")

    def export(self, outfile, level, name_="XSDataKeyValuePair"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataKeyValuePair"):
        if self.__key is not None:
            self.key.export(outfile, level, name_="key")
        else:
            warnEmptyAttribute("key", "XSDataString")
        if self.__value is not None:
            self.value.export(outfile, level, name_="value")
        else:
            warnEmptyAttribute("value", "XSDataString")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "key":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setKey(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "value":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setValue(obj_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataKeyValuePair")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataKeyValuePair")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataKeyValuePair is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataKeyValuePair.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataKeyValuePair()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataKeyValuePair")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataKeyValuePair()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataKeyValuePair


class XSDataDictionary(object):
    def __init__(self, keyValuePair=None):
        if keyValuePair is None:
            self.__keyValuePair = []
        else:
            checkType(
                "XSDataDictionary",
                "Constructor of XSDataDictionary",
                keyValuePair,
                "list",
            )
            self.__keyValuePair = keyValuePair

    def getKeyValuePair(self):
        return self.__keyValuePair

    def setKeyValuePair(self, keyValuePair):
        checkType("XSDataDictionary", "setKeyValuePair", keyValuePair, "list")
        self.__keyValuePair = keyValuePair

    def delKeyValuePair(self):
        self.__keyValuePair = None

    # Properties
    keyValuePair = property(
        getKeyValuePair, setKeyValuePair, delKeyValuePair, "Property for keyValuePair"
    )

    def addKeyValuePair(self, value):
        checkType("XSDataDictionary", "setKeyValuePair", value, "XSDataKeyValuePair")
        self.__keyValuePair.append(value)

    def insertKeyValuePair(self, index, value):
        checkType("XSDataDictionary", "setKeyValuePair", value, "XSDataKeyValuePair")
        self.__keyValuePair[index] = value

    def export(self, outfile, level, name_="XSDataDictionary"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataDictionary"):
        for keyValuePair_ in self.getKeyValuePair():
            keyValuePair_.export(outfile, level, name_="keyValuePair")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "keyValuePair":
            obj_ = XSDataKeyValuePair()
            obj_.build(child_)
            self.keyValuePair.append(obj_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataDictionary")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataDictionary")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataDictionary is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataDictionary.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataDictionary()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataDictionary")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataDictionary()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataDictionary


class XSOptionItem(object):
    def __init__(self, name=None, enabled=None):
        checkType("XSOptionItem", "Constructor of XSOptionItem", enabled, "boolean")
        self.__enabled = enabled
        checkType("XSOptionItem", "Constructor of XSOptionItem", name, "string")
        self.__name = name

    def getEnabled(self):
        return self.__enabled

    def setEnabled(self, enabled):
        checkType("XSOptionItem", "setEnabled", enabled, "boolean")
        self.__enabled = enabled

    def delEnabled(self):
        self.__enabled = None

    # Properties
    enabled = property(getEnabled, setEnabled, delEnabled, "Property for enabled")

    def getName(self):
        return self.__name

    def setName(self, name):
        checkType("XSOptionItem", "setName", name, "string")
        self.__name = name

    def delName(self):
        self.__name = None

    # Properties
    name = property(getName, setName, delName, "Property for name")

    def export(self, outfile, level, name_="XSOptionItem"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSOptionItem"):
        if self.__enabled is not None:
            showIndent(outfile, level)
            if self.__enabled:
                outfile.write(unicode("<enabled>true</enabled>\n"))
            else:
                outfile.write(unicode("<enabled>false</enabled>\n"))
        else:
            warnEmptyAttribute("enabled", "boolean")
        if self.__name is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<name>%s</name>\n" % self.__name))
        else:
            warnEmptyAttribute("name", "string")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "enabled":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                if sval_ in ("True", "true", "1"):
                    ival_ = True
                elif sval_ in ("False", "false", "0"):
                    ival_ = False
                else:
                    raise ValueError("requires boolean -- %s" % child_.toxml())
                self.__enabled = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "name":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self.__name = value_

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSOptionItem")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSOptionItem")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSOptionItem is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSOptionItem.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSOptionItem()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSOptionItem")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSOptionItem()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSOptionItem


class XSOptionList(object):
    def __init__(self, XSOptionItem=None):
        if XSOptionItem is None:
            self.__XSOptionItem = []
        else:
            checkType(
                "XSOptionList", "Constructor of XSOptionList", XSOptionItem, "list"
            )
            self.__XSOptionItem = XSOptionItem

    def getXSOptionItem(self):
        return self.__XSOptionItem

    def setXSOptionItem(self, XSOptionItem):
        checkType("XSOptionList", "setXSOptionItem", XSOptionItem, "list")
        self.__XSOptionItem = XSOptionItem

    def delXSOptionItem(self):
        self.__XSOptionItem = None

    # Properties
    XSOptionItem = property(
        getXSOptionItem, setXSOptionItem, delXSOptionItem, "Property for XSOptionItem"
    )

    def addXSOptionItem(self, value):
        checkType("XSOptionList", "setXSOptionItem", value, "XSOptionItem")
        self.__XSOptionItem.append(value)

    def insertXSOptionItem(self, index, value):
        checkType("XSOptionList", "setXSOptionItem", value, "XSOptionItem")
        self.__XSOptionItem[index] = value

    def export(self, outfile, level, name_="XSOptionList"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSOptionList"):
        for XSOptionItem_ in self.getXSOptionItem():
            XSOptionItem_.export(outfile, level, name_="XSOptionItem")
        if self.getXSOptionItem() == []:
            warnEmptyAttribute("XSOptionItem", "XSOptionItem")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "XSOptionItem":
            obj_ = XSOptionItem()
            obj_.build(child_)
            self.XSOptionItem.append(obj_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSOptionList")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSOptionList")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSOptionList is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSOptionList.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSOptionList()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSOptionList")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSOptionList()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSOptionList


class XSParamItem(object):
    def __init__(self, value=None, name=None):
        checkType("XSParamItem", "Constructor of XSParamItem", name, "string")
        self.__name = name
        checkType("XSParamItem", "Constructor of XSParamItem", value, "string")
        self.__value = value

    def getName(self):
        return self.__name

    def setName(self, name):
        checkType("XSParamItem", "setName", name, "string")
        self.__name = name

    def delName(self):
        self.__name = None

    # Properties
    name = property(getName, setName, delName, "Property for name")

    def getValue(self):
        return self.__value

    def setValue(self, value):
        checkType("XSParamItem", "setValue", value, "string")
        self.__value = value

    def delValue(self):
        self.__value = None

    # Properties
    value = property(getValue, setValue, delValue, "Property for value")

    def export(self, outfile, level, name_="XSParamItem"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSParamItem"):
        if self.__name is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<name>%s</name>\n" % self.__name))
        else:
            warnEmptyAttribute("name", "string")
        if self.__value is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<value>%s</value>\n" % self.__value))
        else:
            warnEmptyAttribute("value", "string")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "name":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self.__name = value_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "value":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self.__value = value_

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSParamItem")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSParamItem")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSParamItem is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSParamItem.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSParamItem()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSParamItem")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSParamItem()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSParamItem


class XSParamList(object):
    def __init__(self, XSParamItem=None):
        if XSParamItem is None:
            self.__XSParamItem = []
        else:
            checkType("XSParamList", "Constructor of XSParamList", XSParamItem, "list")
            self.__XSParamItem = XSParamItem

    def getXSParamItem(self):
        return self.__XSParamItem

    def setXSParamItem(self, XSParamItem):
        checkType("XSParamList", "setXSParamItem", XSParamItem, "list")
        self.__XSParamItem = XSParamItem

    def delXSParamItem(self):
        self.__XSParamItem = None

    # Properties
    XSParamItem = property(
        getXSParamItem, setXSParamItem, delXSParamItem, "Property for XSParamItem"
    )

    def addXSParamItem(self, value):
        checkType("XSParamList", "setXSParamItem", value, "XSParamItem")
        self.__XSParamItem.append(value)

    def insertXSParamItem(self, index, value):
        checkType("XSParamList", "setXSParamItem", value, "XSParamItem")
        self.__XSParamItem[index] = value

    def export(self, outfile, level, name_="XSParamList"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSParamList"):
        for XSParamItem_ in self.getXSParamItem():
            XSParamItem_.export(outfile, level, name_="XSParamItem")
        if self.getXSParamItem() == []:
            warnEmptyAttribute("XSParamItem", "XSParamItem")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "XSParamItem":
            obj_ = XSParamItem()
            obj_.build(child_)
            self.XSParamItem.append(obj_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSParamList")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSParamList")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSParamList is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSParamList.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSParamList()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSParamList")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSParamList()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSParamList


class XSPluginItem(object):
    def __init__(self, name=None, XSParamList=None, XSOptionList=None):
        checkType(
            "XSPluginItem", "Constructor of XSPluginItem", XSOptionList, "XSOptionList"
        )
        self.__XSOptionList = XSOptionList
        checkType(
            "XSPluginItem", "Constructor of XSPluginItem", XSParamList, "XSParamList"
        )
        self.__XSParamList = XSParamList
        checkType("XSPluginItem", "Constructor of XSPluginItem", name, "string")
        self.__name = name

    def getXSOptionList(self):
        return self.__XSOptionList

    def setXSOptionList(self, XSOptionList):
        checkType("XSPluginItem", "setXSOptionList", XSOptionList, "XSOptionList")
        self.__XSOptionList = XSOptionList

    def delXSOptionList(self):
        self.__XSOptionList = None

    # Properties
    XSOptionList = property(
        getXSOptionList, setXSOptionList, delXSOptionList, "Property for XSOptionList"
    )

    def getXSParamList(self):
        return self.__XSParamList

    def setXSParamList(self, XSParamList):
        checkType("XSPluginItem", "setXSParamList", XSParamList, "XSParamList")
        self.__XSParamList = XSParamList

    def delXSParamList(self):
        self.__XSParamList = None

    # Properties
    XSParamList = property(
        getXSParamList, setXSParamList, delXSParamList, "Property for XSParamList"
    )

    def getName(self):
        return self.__name

    def setName(self, name):
        checkType("XSPluginItem", "setName", name, "string")
        self.__name = name

    def delName(self):
        self.__name = None

    # Properties
    name = property(getName, setName, delName, "Property for name")

    def export(self, outfile, level, name_="XSPluginItem"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSPluginItem"):
        if self.__XSOptionList is not None:
            self.XSOptionList.export(outfile, level, name_="XSOptionList")
        if self.__XSParamList is not None:
            self.XSParamList.export(outfile, level, name_="XSParamList")
        if self.__name is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<name>%s</name>\n" % self.__name))
        else:
            warnEmptyAttribute("name", "string")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "XSOptionList":
            obj_ = XSOptionList()
            obj_.build(child_)
            self.setXSOptionList(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "XSParamList":
            obj_ = XSParamList()
            obj_.build(child_)
            self.setXSParamList(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "name":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self.__name = value_

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSPluginItem")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSPluginItem")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSPluginItem is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSPluginItem.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSPluginItem()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSPluginItem")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSPluginItem()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSPluginItem


class XSPluginList(object):
    def __init__(self, XSPluginItem=None):
        if XSPluginItem is None:
            self.__XSPluginItem = []
        else:
            checkType(
                "XSPluginList", "Constructor of XSPluginList", XSPluginItem, "list"
            )
            self.__XSPluginItem = XSPluginItem

    def getXSPluginItem(self):
        return self.__XSPluginItem

    def setXSPluginItem(self, XSPluginItem):
        checkType("XSPluginList", "setXSPluginItem", XSPluginItem, "list")
        self.__XSPluginItem = XSPluginItem

    def delXSPluginItem(self):
        self.__XSPluginItem = None

    # Properties
    XSPluginItem = property(
        getXSPluginItem, setXSPluginItem, delXSPluginItem, "Property for XSPluginItem"
    )

    def addXSPluginItem(self, value):
        checkType("XSPluginList", "setXSPluginItem", value, "XSPluginItem")
        self.__XSPluginItem.append(value)

    def insertXSPluginItem(self, index, value):
        checkType("XSPluginList", "setXSPluginItem", value, "XSPluginItem")
        self.__XSPluginItem[index] = value

    def export(self, outfile, level, name_="XSPluginList"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSPluginList"):
        for XSPluginItem_ in self.getXSPluginItem():
            XSPluginItem_.export(outfile, level, name_="XSPluginItem")
        if self.getXSPluginItem() == []:
            warnEmptyAttribute("XSPluginItem", "XSPluginItem")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "XSPluginItem":
            obj_ = XSPluginItem()
            obj_.build(child_)
            self.XSPluginItem.append(obj_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSPluginList")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSPluginList")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSPluginList is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSPluginList.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSPluginList()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSPluginList")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSPluginList()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSPluginList


class XSDataAngle(XSDataDisplacement):
    def __init__(self, value=None, unit=None, error=None):
        XSDataDisplacement.__init__(self, value, unit, error)

    def export(self, outfile, level, name_="XSDataAngle"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataAngle"):
        XSDataDisplacement.exportChildren(self, outfile, level, name_)

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        XSDataDisplacement.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataAngle")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataAngle")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataAngle is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataAngle.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataAngle()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataAngle")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataAngle()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataAngle


class XSDataArray(XSData):
    """md5 checksum has to be calculated on the decoded data, not the encoded one. Default encoding is "base64" default byte order is "little-endian" (intel) not "big-endian" (java)"""

    def __init__(
        self, size=None, shape=None, md5sum=None, dtype=None, data=None, coding=None
    ):
        XSData.__init__(self)
        checkType("XSDataArray", "Constructor of XSDataArray", coding, "XSDataString")
        self.__coding = coding
        checkType("XSDataArray", "Constructor of XSDataArray", data, "string")
        self.__data = data
        checkType("XSDataArray", "Constructor of XSDataArray", dtype, "string")
        self.__dtype = dtype
        checkType("XSDataArray", "Constructor of XSDataArray", md5sum, "XSDataString")
        self.__md5sum = md5sum
        if shape is None:
            self.__shape = []
        else:
            checkType("XSDataArray", "Constructor of XSDataArray", shape, "list")
            self.__shape = shape
        checkType("XSDataArray", "Constructor of XSDataArray", size, "integer")
        self.__size = size

    def getCoding(self):
        return self.__coding

    def setCoding(self, coding):
        checkType("XSDataArray", "setCoding", coding, "XSDataString")
        self.__coding = coding

    def delCoding(self):
        self.__coding = None

    # Properties
    coding = property(getCoding, setCoding, delCoding, "Property for coding")

    def getData(self):
        return self.__data

    def setData(self, data):
        checkType("XSDataArray", "setData", data, "string")
        self.__data = data

    def delData(self):
        self.__data = None

    # Properties
    data = property(getData, setData, delData, "Property for data")

    def getDtype(self):
        return self.__dtype

    def setDtype(self, dtype):
        checkType("XSDataArray", "setDtype", dtype, "string")
        self.__dtype = dtype

    def delDtype(self):
        self.__dtype = None

    # Properties
    dtype = property(getDtype, setDtype, delDtype, "Property for dtype")

    def getMd5sum(self):
        return self.__md5sum

    def setMd5sum(self, md5sum):
        checkType("XSDataArray", "setMd5sum", md5sum, "XSDataString")
        self.__md5sum = md5sum

    def delMd5sum(self):
        self.__md5sum = None

    # Properties
    md5sum = property(getMd5sum, setMd5sum, delMd5sum, "Property for md5sum")

    def getShape(self):
        return self.__shape

    def setShape(self, shape):
        checkType("XSDataArray", "setShape", shape, "list")
        self.__shape = shape

    def delShape(self):
        self.__shape = None

    # Properties
    shape = property(getShape, setShape, delShape, "Property for shape")

    def addShape(self, value):
        checkType("XSDataArray", "setShape", value, "integer")
        self.__shape.append(value)

    def insertShape(self, index, value):
        checkType("XSDataArray", "setShape", value, "integer")
        self.__shape[index] = value

    def getSize(self):
        return self.__size

    def setSize(self, size):
        checkType("XSDataArray", "setSize", size, "integer")
        self.__size = size

    def delSize(self):
        self.__size = None

    # Properties
    size = property(getSize, setSize, delSize, "Property for size")

    def export(self, outfile, level, name_="XSDataArray"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataArray"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__coding is not None:
            self.coding.export(outfile, level, name_="coding")
        if self.__data is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<data>%s</data>\n" % self.__data))
        else:
            warnEmptyAttribute("data", "string")
        if self.__dtype is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<dtype>%s</dtype>\n" % self.__dtype))
        else:
            warnEmptyAttribute("dtype", "string")
        if self.__md5sum is not None:
            self.md5sum.export(outfile, level, name_="md5sum")
        for shape_ in self.getShape():
            showIndent(outfile, level)
            outfile.write(unicode("<shape>%d</shape>\n" % shape_))
        if self.getShape() == []:
            warnEmptyAttribute("shape", "integer")
        if self.__size is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<size>%d</size>\n" % self.__size))
        else:
            warnEmptyAttribute("size", "integer")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "coding":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setCoding(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "data":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self.__data = value_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "dtype":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self.__dtype = value_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "md5sum":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setMd5sum(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "shape":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__shape.append(ival_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "size":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__size = ival_
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataArray")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataArray")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataArray is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataArray.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataArray()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataArray")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataArray()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataArray


class XSDataBoolean(XSData):
    """These simple objects that use built-in types are basically aimed to be used by the rest of the data model objects."""

    def __init__(self, value=None):
        XSData.__init__(self)
        checkType("XSDataBoolean", "Constructor of XSDataBoolean", value, "boolean")
        self.__value = value

    def getValue(self):
        return self.__value

    def setValue(self, value):
        checkType("XSDataBoolean", "setValue", value, "boolean")
        self.__value = value

    def delValue(self):
        self.__value = None

    # Properties
    value = property(getValue, setValue, delValue, "Property for value")

    def export(self, outfile, level, name_="XSDataBoolean"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataBoolean"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__value is not None:
            showIndent(outfile, level)
            if self.__value:
                outfile.write(unicode("<value>true</value>\n"))
            else:
                outfile.write(unicode("<value>false</value>\n"))
        else:
            warnEmptyAttribute("value", "boolean")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "value":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                if sval_ in ("True", "true", "1"):
                    ival_ = True
                elif sval_ in ("False", "false", "0"):
                    ival_ = False
                else:
                    raise ValueError("requires boolean -- %s" % child_.toxml())
                self.__value = ival_
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataBoolean")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataBoolean")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataBoolean is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataBoolean.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataBoolean()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataBoolean")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataBoolean()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataBoolean


class XSDataDouble(XSData):
    """These simple objects that use built-in types are basically aimed to be used by the rest of the data model objects."""

    def __init__(self, value=None):
        XSData.__init__(self)
        checkType("XSDataDouble", "Constructor of XSDataDouble", value, "double")
        self.__value = value

    def getValue(self):
        return self.__value

    def setValue(self, value):
        checkType("XSDataDouble", "setValue", value, "double")
        self.__value = value

    def delValue(self):
        self.__value = None

    # Properties
    value = property(getValue, setValue, delValue, "Property for value")

    def export(self, outfile, level, name_="XSDataDouble"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataDouble"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__value is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<value>%e</value>\n" % self.__value))
        else:
            warnEmptyAttribute("value", "double")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "value":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__value = fval_
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataDouble")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataDouble")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataDouble is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataDouble.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataDouble()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataDouble")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataDouble()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataDouble


class XSDataFile(XSData):
    """These objects use the simple objects described above to create useful structures for the rest for the data model."""

    def __init__(self, path=None):
        XSData.__init__(self)
        checkType("XSDataFile", "Constructor of XSDataFile", path, "XSDataString")
        self.__path = path

    def getPath(self):
        return self.__path

    def setPath(self, path):
        checkType("XSDataFile", "setPath", path, "XSDataString")
        self.__path = path

    def delPath(self):
        self.__path = None

    # Properties
    path = property(getPath, setPath, delPath, "Property for path")

    def export(self, outfile, level, name_="XSDataFile"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataFile"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__path is not None:
            self.path.export(outfile, level, name_="path")
        else:
            warnEmptyAttribute("path", "XSDataString")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "path":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setPath(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataFile")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataFile")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataFile is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataFile.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataFile()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataFile")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataFile()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataFile


class XSDataFloat(XSData):
    """These simple objects that use built-in types are basically aimed to be used by the rest of the data model objects."""

    def __init__(self, value=None):
        XSData.__init__(self)
        checkType("XSDataFloat", "Constructor of XSDataFloat", value, "double")
        self.__value = value

    def getValue(self):
        return self.__value

    def setValue(self, value):
        checkType("XSDataFloat", "setValue", value, "double")
        self.__value = value

    def delValue(self):
        self.__value = None

    # Properties
    value = property(getValue, setValue, delValue, "Property for value")

    def export(self, outfile, level, name_="XSDataFloat"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataFloat"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__value is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<value>%e</value>\n" % self.__value))
        else:
            warnEmptyAttribute("value", "double")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "value":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__value = fval_
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataFloat")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataFloat")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataFloat is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataFloat.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataFloat()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataFloat")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataFloat()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataFloat


class XSDataInput(XSData):
    """All plugin input and result classes should be derived from these two classes."""

    def __init__(self, configuration=None):
        XSData.__init__(self)
        checkType(
            "XSDataInput",
            "Constructor of XSDataInput",
            configuration,
            "XSConfiguration",
        )
        self.__configuration = configuration

    def getConfiguration(self):
        return self.__configuration

    def setConfiguration(self, configuration):
        checkType("XSDataInput", "setConfiguration", configuration, "XSConfiguration")
        self.__configuration = configuration

    def delConfiguration(self):
        self.__configuration = None

    # Properties
    configuration = property(
        getConfiguration,
        setConfiguration,
        delConfiguration,
        "Property for configuration",
    )

    def export(self, outfile, level, name_="XSDataInput"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataInput"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__configuration is not None:
            self.configuration.export(outfile, level, name_="configuration")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "configuration":
            obj_ = XSConfiguration()
            obj_.build(child_)
            self.setConfiguration(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataInput")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataInput")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataInput is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataInput.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInput()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataInput")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInput()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataInput


class XSDataInteger(XSData):
    """These simple objects that use built-in types are basically aimed to be used by the rest of the data model objects."""

    def __init__(self, value=None):
        XSData.__init__(self)
        checkType("XSDataInteger", "Constructor of XSDataInteger", value, "integer")
        self.__value = value

    def getValue(self):
        return self.__value

    def setValue(self, value):
        checkType("XSDataInteger", "setValue", value, "integer")
        self.__value = value

    def delValue(self):
        self.__value = None

    # Properties
    value = property(getValue, setValue, delValue, "Property for value")

    def export(self, outfile, level, name_="XSDataInteger"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataInteger"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__value is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<value>%d</value>\n" % self.__value))
        else:
            warnEmptyAttribute("value", "integer")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "value":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__value = ival_
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataInteger")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataInteger")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataInteger is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataInteger.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInteger()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataInteger")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInteger()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataInteger


class XSDataLinearDisplacement(XSDataDisplacement):
    def __init__(self, value=None, unit=None, error=None):
        XSDataDisplacement.__init__(self, value, unit, error)

    def export(self, outfile, level, name_="XSDataLinearDisplacement"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataLinearDisplacement"):
        XSDataDisplacement.exportChildren(self, outfile, level, name_)

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        XSDataDisplacement.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataLinearDisplacement")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataLinearDisplacement")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataLinearDisplacement is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataLinearDisplacement.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataLinearDisplacement()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataLinearDisplacement")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataLinearDisplacement()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataLinearDisplacement


class XSDataMatrixDouble(XSData):
    """These are compound object used for linear algebra operations."""

    def __init__(
        self,
        m33=None,
        m32=None,
        m31=None,
        m23=None,
        m22=None,
        m21=None,
        m13=None,
        m12=None,
        m11=None,
    ):
        XSData.__init__(self)
        checkType(
            "XSDataMatrixDouble", "Constructor of XSDataMatrixDouble", m11, "double"
        )
        self.__m11 = m11
        checkType(
            "XSDataMatrixDouble", "Constructor of XSDataMatrixDouble", m12, "double"
        )
        self.__m12 = m12
        checkType(
            "XSDataMatrixDouble", "Constructor of XSDataMatrixDouble", m13, "double"
        )
        self.__m13 = m13
        checkType(
            "XSDataMatrixDouble", "Constructor of XSDataMatrixDouble", m21, "double"
        )
        self.__m21 = m21
        checkType(
            "XSDataMatrixDouble", "Constructor of XSDataMatrixDouble", m22, "double"
        )
        self.__m22 = m22
        checkType(
            "XSDataMatrixDouble", "Constructor of XSDataMatrixDouble", m23, "double"
        )
        self.__m23 = m23
        checkType(
            "XSDataMatrixDouble", "Constructor of XSDataMatrixDouble", m31, "double"
        )
        self.__m31 = m31
        checkType(
            "XSDataMatrixDouble", "Constructor of XSDataMatrixDouble", m32, "double"
        )
        self.__m32 = m32
        checkType(
            "XSDataMatrixDouble", "Constructor of XSDataMatrixDouble", m33, "double"
        )
        self.__m33 = m33

    def getM11(self):
        return self.__m11

    def setM11(self, m11):
        checkType("XSDataMatrixDouble", "setM11", m11, "double")
        self.__m11 = m11

    def delM11(self):
        self.__m11 = None

    # Properties
    m11 = property(getM11, setM11, delM11, "Property for m11")

    def getM12(self):
        return self.__m12

    def setM12(self, m12):
        checkType("XSDataMatrixDouble", "setM12", m12, "double")
        self.__m12 = m12

    def delM12(self):
        self.__m12 = None

    # Properties
    m12 = property(getM12, setM12, delM12, "Property for m12")

    def getM13(self):
        return self.__m13

    def setM13(self, m13):
        checkType("XSDataMatrixDouble", "setM13", m13, "double")
        self.__m13 = m13

    def delM13(self):
        self.__m13 = None

    # Properties
    m13 = property(getM13, setM13, delM13, "Property for m13")

    def getM21(self):
        return self.__m21

    def setM21(self, m21):
        checkType("XSDataMatrixDouble", "setM21", m21, "double")
        self.__m21 = m21

    def delM21(self):
        self.__m21 = None

    # Properties
    m21 = property(getM21, setM21, delM21, "Property for m21")

    def getM22(self):
        return self.__m22

    def setM22(self, m22):
        checkType("XSDataMatrixDouble", "setM22", m22, "double")
        self.__m22 = m22

    def delM22(self):
        self.__m22 = None

    # Properties
    m22 = property(getM22, setM22, delM22, "Property for m22")

    def getM23(self):
        return self.__m23

    def setM23(self, m23):
        checkType("XSDataMatrixDouble", "setM23", m23, "double")
        self.__m23 = m23

    def delM23(self):
        self.__m23 = None

    # Properties
    m23 = property(getM23, setM23, delM23, "Property for m23")

    def getM31(self):
        return self.__m31

    def setM31(self, m31):
        checkType("XSDataMatrixDouble", "setM31", m31, "double")
        self.__m31 = m31

    def delM31(self):
        self.__m31 = None

    # Properties
    m31 = property(getM31, setM31, delM31, "Property for m31")

    def getM32(self):
        return self.__m32

    def setM32(self, m32):
        checkType("XSDataMatrixDouble", "setM32", m32, "double")
        self.__m32 = m32

    def delM32(self):
        self.__m32 = None

    # Properties
    m32 = property(getM32, setM32, delM32, "Property for m32")

    def getM33(self):
        return self.__m33

    def setM33(self, m33):
        checkType("XSDataMatrixDouble", "setM33", m33, "double")
        self.__m33 = m33

    def delM33(self):
        self.__m33 = None

    # Properties
    m33 = property(getM33, setM33, delM33, "Property for m33")

    def export(self, outfile, level, name_="XSDataMatrixDouble"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataMatrixDouble"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__m11 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m11>%e</m11>\n" % self.__m11))
        else:
            warnEmptyAttribute("m11", "double")
        if self.__m12 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m12>%e</m12>\n" % self.__m12))
        else:
            warnEmptyAttribute("m12", "double")
        if self.__m13 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m13>%e</m13>\n" % self.__m13))
        else:
            warnEmptyAttribute("m13", "double")
        if self.__m21 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m21>%e</m21>\n" % self.__m21))
        else:
            warnEmptyAttribute("m21", "double")
        if self.__m22 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m22>%e</m22>\n" % self.__m22))
        else:
            warnEmptyAttribute("m22", "double")
        if self.__m23 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m23>%e</m23>\n" % self.__m23))
        else:
            warnEmptyAttribute("m23", "double")
        if self.__m31 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m31>%e</m31>\n" % self.__m31))
        else:
            warnEmptyAttribute("m31", "double")
        if self.__m32 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m32>%e</m32>\n" % self.__m32))
        else:
            warnEmptyAttribute("m32", "double")
        if self.__m33 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m33>%e</m33>\n" % self.__m33))
        else:
            warnEmptyAttribute("m33", "double")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m11":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__m11 = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m12":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__m12 = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m13":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__m13 = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m21":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__m21 = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m22":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__m22 = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m23":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__m23 = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m31":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__m31 = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m32":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__m32 = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m33":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__m33 = fval_
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataMatrixDouble")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataMatrixDouble")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataMatrixDouble is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataMatrixDouble.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataMatrixDouble()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataMatrixDouble")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataMatrixDouble()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataMatrixDouble


class XSDataMatrixInteger(XSData):
    """These are compound object used for linear algebra operations."""

    def __init__(
        self,
        m33=None,
        m32=None,
        m31=None,
        m23=None,
        m22=None,
        m21=None,
        m13=None,
        m12=None,
        m11=None,
    ):
        XSData.__init__(self)
        checkType(
            "XSDataMatrixInteger", "Constructor of XSDataMatrixInteger", m11, "integer"
        )
        self.__m11 = m11
        checkType(
            "XSDataMatrixInteger", "Constructor of XSDataMatrixInteger", m12, "integer"
        )
        self.__m12 = m12
        checkType(
            "XSDataMatrixInteger", "Constructor of XSDataMatrixInteger", m13, "integer"
        )
        self.__m13 = m13
        checkType(
            "XSDataMatrixInteger", "Constructor of XSDataMatrixInteger", m21, "integer"
        )
        self.__m21 = m21
        checkType(
            "XSDataMatrixInteger", "Constructor of XSDataMatrixInteger", m22, "integer"
        )
        self.__m22 = m22
        checkType(
            "XSDataMatrixInteger", "Constructor of XSDataMatrixInteger", m23, "integer"
        )
        self.__m23 = m23
        checkType(
            "XSDataMatrixInteger", "Constructor of XSDataMatrixInteger", m31, "integer"
        )
        self.__m31 = m31
        checkType(
            "XSDataMatrixInteger", "Constructor of XSDataMatrixInteger", m32, "integer"
        )
        self.__m32 = m32
        checkType(
            "XSDataMatrixInteger", "Constructor of XSDataMatrixInteger", m33, "integer"
        )
        self.__m33 = m33

    def getM11(self):
        return self.__m11

    def setM11(self, m11):
        checkType("XSDataMatrixInteger", "setM11", m11, "integer")
        self.__m11 = m11

    def delM11(self):
        self.__m11 = None

    # Properties
    m11 = property(getM11, setM11, delM11, "Property for m11")

    def getM12(self):
        return self.__m12

    def setM12(self, m12):
        checkType("XSDataMatrixInteger", "setM12", m12, "integer")
        self.__m12 = m12

    def delM12(self):
        self.__m12 = None

    # Properties
    m12 = property(getM12, setM12, delM12, "Property for m12")

    def getM13(self):
        return self.__m13

    def setM13(self, m13):
        checkType("XSDataMatrixInteger", "setM13", m13, "integer")
        self.__m13 = m13

    def delM13(self):
        self.__m13 = None

    # Properties
    m13 = property(getM13, setM13, delM13, "Property for m13")

    def getM21(self):
        return self.__m21

    def setM21(self, m21):
        checkType("XSDataMatrixInteger", "setM21", m21, "integer")
        self.__m21 = m21

    def delM21(self):
        self.__m21 = None

    # Properties
    m21 = property(getM21, setM21, delM21, "Property for m21")

    def getM22(self):
        return self.__m22

    def setM22(self, m22):
        checkType("XSDataMatrixInteger", "setM22", m22, "integer")
        self.__m22 = m22

    def delM22(self):
        self.__m22 = None

    # Properties
    m22 = property(getM22, setM22, delM22, "Property for m22")

    def getM23(self):
        return self.__m23

    def setM23(self, m23):
        checkType("XSDataMatrixInteger", "setM23", m23, "integer")
        self.__m23 = m23

    def delM23(self):
        self.__m23 = None

    # Properties
    m23 = property(getM23, setM23, delM23, "Property for m23")

    def getM31(self):
        return self.__m31

    def setM31(self, m31):
        checkType("XSDataMatrixInteger", "setM31", m31, "integer")
        self.__m31 = m31

    def delM31(self):
        self.__m31 = None

    # Properties
    m31 = property(getM31, setM31, delM31, "Property for m31")

    def getM32(self):
        return self.__m32

    def setM32(self, m32):
        checkType("XSDataMatrixInteger", "setM32", m32, "integer")
        self.__m32 = m32

    def delM32(self):
        self.__m32 = None

    # Properties
    m32 = property(getM32, setM32, delM32, "Property for m32")

    def getM33(self):
        return self.__m33

    def setM33(self, m33):
        checkType("XSDataMatrixInteger", "setM33", m33, "integer")
        self.__m33 = m33

    def delM33(self):
        self.__m33 = None

    # Properties
    m33 = property(getM33, setM33, delM33, "Property for m33")

    def export(self, outfile, level, name_="XSDataMatrixInteger"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataMatrixInteger"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__m11 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m11>%d</m11>\n" % self.__m11))
        else:
            warnEmptyAttribute("m11", "integer")
        if self.__m12 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m12>%d</m12>\n" % self.__m12))
        else:
            warnEmptyAttribute("m12", "integer")
        if self.__m13 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m13>%d</m13>\n" % self.__m13))
        else:
            warnEmptyAttribute("m13", "integer")
        if self.__m21 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m21>%d</m21>\n" % self.__m21))
        else:
            warnEmptyAttribute("m21", "integer")
        if self.__m22 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m22>%d</m22>\n" % self.__m22))
        else:
            warnEmptyAttribute("m22", "integer")
        if self.__m23 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m23>%d</m23>\n" % self.__m23))
        else:
            warnEmptyAttribute("m23", "integer")
        if self.__m31 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m31>%d</m31>\n" % self.__m31))
        else:
            warnEmptyAttribute("m31", "integer")
        if self.__m32 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m32>%d</m32>\n" % self.__m32))
        else:
            warnEmptyAttribute("m32", "integer")
        if self.__m33 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<m33>%d</m33>\n" % self.__m33))
        else:
            warnEmptyAttribute("m33", "integer")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m11":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__m11 = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m12":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__m12 = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m13":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__m13 = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m21":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__m21 = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m22":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__m22 = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m23":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__m23 = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m31":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__m31 = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m32":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__m32 = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "m33":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__m33 = ival_
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataMatrixInteger")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataMatrixInteger")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataMatrixInteger is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataMatrixInteger.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataMatrixInteger()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataMatrixInteger")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataMatrixInteger()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataMatrixInteger


class XSDataString(XSData):
    """These simple objects that use built-in types are basically aimed to be used by the rest of the data model objects."""

    def __init__(self, value=None):
        XSData.__init__(self)
        checkType("XSDataString", "Constructor of XSDataString", value, "string")
        self.__value = value

    def getValue(self):
        return self.__value

    def setValue(self, value):
        checkType("XSDataString", "setValue", value, "string")
        self.__value = value

    def delValue(self):
        self.__value = None

    # Properties
    value = property(getValue, setValue, delValue, "Property for value")

    def export(self, outfile, level, name_="XSDataString"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataString"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__value is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<value>%s</value>\n" % self.__value))
        else:
            warnEmptyAttribute("value", "string")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "value":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self.__value = value_
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataString")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataString")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataString is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataString.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataString()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataString")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataString()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataString


class XSDataMessage(XSData):
    """This message class is used (amongst other messages) for warning and error messages."""

    def __init__(self, type=None, text=None, level=None, debuginfo=None):
        XSData.__init__(self)
        checkType(
            "XSDataMessage", "Constructor of XSDataMessage", debuginfo, "XSDataString"
        )
        self.__debuginfo = debuginfo
        checkType(
            "XSDataMessage", "Constructor of XSDataMessage", level, "XSDataString"
        )
        self.__level = level
        checkType("XSDataMessage", "Constructor of XSDataMessage", text, "XSDataString")
        self.__text = text
        checkType("XSDataMessage", "Constructor of XSDataMessage", type, "XSDataString")
        self.__type = type

    def getDebuginfo(self):
        return self.__debuginfo

    def setDebuginfo(self, debuginfo):
        checkType("XSDataMessage", "setDebuginfo", debuginfo, "XSDataString")
        self.__debuginfo = debuginfo

    def delDebuginfo(self):
        self.__debuginfo = None

    # Properties
    debuginfo = property(
        getDebuginfo, setDebuginfo, delDebuginfo, "Property for debuginfo"
    )

    def getLevel(self):
        return self.__level

    def setLevel(self, level):
        checkType("XSDataMessage", "setLevel", level, "XSDataString")
        self.__level = level

    def delLevel(self):
        self.__level = None

    # Properties
    level = property(getLevel, setLevel, delLevel, "Property for level")

    def getText(self):
        return self.__text

    def setText(self, text):
        checkType("XSDataMessage", "setText", text, "XSDataString")
        self.__text = text

    def delText(self):
        self.__text = None

    # Properties
    text = property(getText, setText, delText, "Property for text")

    def getType(self):
        return self.__type

    def setType(self, type):
        checkType("XSDataMessage", "setType", type, "XSDataString")
        self.__type = type

    def delType(self):
        self.__type = None

    # Properties
    type = property(getType, setType, delType, "Property for type")

    def export(self, outfile, level, name_="XSDataMessage"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataMessage"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__debuginfo is not None:
            self.debuginfo.export(outfile, level, name_="debuginfo")
        else:
            warnEmptyAttribute("debuginfo", "XSDataString")
        if self.__level is not None:
            self.level.export(outfile, level, name_="level")
        else:
            warnEmptyAttribute("level", "XSDataString")
        if self.__text is not None:
            self.text.export(outfile, level, name_="text")
        else:
            warnEmptyAttribute("text", "XSDataString")
        if self.__type is not None:
            self.type.export(outfile, level, name_="type")
        else:
            warnEmptyAttribute("type", "XSDataString")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "debuginfo":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setDebuginfo(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "level":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setLevel(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "text":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setText(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "type":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setType(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataMessage")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataMessage")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataMessage is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataMessage.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataMessage()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataMessage")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataMessage()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataMessage


class XSDataStatus(XSData):
    """This class contains all data related to the execution of a plugin."""

    def __init__(
        self, message=None, isSuccess=None, executiveSummary=None, executionInfo=None
    ):
        XSData.__init__(self)
        checkType(
            "XSDataStatus",
            "Constructor of XSDataStatus",
            executionInfo,
            "XSDataExecutionInfo",
        )
        self.__executionInfo = executionInfo
        checkType(
            "XSDataStatus",
            "Constructor of XSDataStatus",
            executiveSummary,
            "XSDataString",
        )
        self.__executiveSummary = executiveSummary
        checkType(
            "XSDataStatus", "Constructor of XSDataStatus", isSuccess, "XSDataBoolean"
        )
        self.__isSuccess = isSuccess
        checkType(
            "XSDataStatus", "Constructor of XSDataStatus", message, "XSDataMessage"
        )
        self.__message = message

    def getExecutionInfo(self):
        return self.__executionInfo

    def setExecutionInfo(self, executionInfo):
        checkType(
            "XSDataStatus", "setExecutionInfo", executionInfo, "XSDataExecutionInfo"
        )
        self.__executionInfo = executionInfo

    def delExecutionInfo(self):
        self.__executionInfo = None

    # Properties
    executionInfo = property(
        getExecutionInfo,
        setExecutionInfo,
        delExecutionInfo,
        "Property for executionInfo",
    )

    def getExecutiveSummary(self):
        return self.__executiveSummary

    def setExecutiveSummary(self, executiveSummary):
        checkType(
            "XSDataStatus", "setExecutiveSummary", executiveSummary, "XSDataString"
        )
        self.__executiveSummary = executiveSummary

    def delExecutiveSummary(self):
        self.__executiveSummary = None

    # Properties
    executiveSummary = property(
        getExecutiveSummary,
        setExecutiveSummary,
        delExecutiveSummary,
        "Property for executiveSummary",
    )

    def getIsSuccess(self):
        return self.__isSuccess

    def setIsSuccess(self, isSuccess):
        checkType("XSDataStatus", "setIsSuccess", isSuccess, "XSDataBoolean")
        self.__isSuccess = isSuccess

    def delIsSuccess(self):
        self.__isSuccess = None

    # Properties
    isSuccess = property(
        getIsSuccess, setIsSuccess, delIsSuccess, "Property for isSuccess"
    )

    def getMessage(self):
        return self.__message

    def setMessage(self, message):
        checkType("XSDataStatus", "setMessage", message, "XSDataMessage")
        self.__message = message

    def delMessage(self):
        self.__message = None

    # Properties
    message = property(getMessage, setMessage, delMessage, "Property for message")

    def export(self, outfile, level, name_="XSDataStatus"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataStatus"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__executionInfo is not None:
            self.executionInfo.export(outfile, level, name_="executionInfo")
        if self.__executiveSummary is not None:
            self.executiveSummary.export(outfile, level, name_="executiveSummary")
        if self.__isSuccess is not None:
            self.isSuccess.export(outfile, level, name_="isSuccess")
        else:
            warnEmptyAttribute("isSuccess", "XSDataBoolean")
        if self.__message is not None:
            self.message.export(outfile, level, name_="message")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "executionInfo":
            obj_ = XSDataExecutionInfo()
            obj_.build(child_)
            self.setExecutionInfo(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "executiveSummary":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setExecutiveSummary(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "isSuccess":
            obj_ = XSDataBoolean()
            obj_.build(child_)
            self.setIsSuccess(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "message":
            obj_ = XSDataMessage()
            obj_.build(child_)
            self.setMessage(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataStatus")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataStatus")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataStatus is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataStatus.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataStatus()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataStatus")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataStatus()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataStatus


class XSDataResult(XSData):
    """All plugin input and result classes should be derived from these two classes."""

    def __init__(self, status=None):
        XSData.__init__(self)
        checkType("XSDataResult", "Constructor of XSDataResult", status, "XSDataStatus")
        self.__status = status

    def getStatus(self):
        return self.__status

    def setStatus(self, status):
        checkType("XSDataResult", "setStatus", status, "XSDataStatus")
        self.__status = status

    def delStatus(self):
        self.__status = None

    # Properties
    status = property(getStatus, setStatus, delStatus, "Property for status")

    def export(self, outfile, level, name_="XSDataResult"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataResult"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__status is not None:
            self.status.export(outfile, level, name_="status")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "status":
            obj_ = XSDataStatus()
            obj_.build(child_)
            self.setStatus(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataResult")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataResult")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataResult is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataResult.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResult()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataResult")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResult()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataResult


class XSDataRotation(XSData):
    """These are compound object used for linear algebra operations."""

    def __init__(self, q3=None, q2=None, q1=None, q0=None):
        XSData.__init__(self)
        checkType("XSDataRotation", "Constructor of XSDataRotation", q0, "double")
        self.__q0 = q0
        checkType("XSDataRotation", "Constructor of XSDataRotation", q1, "double")
        self.__q1 = q1
        checkType("XSDataRotation", "Constructor of XSDataRotation", q2, "double")
        self.__q2 = q2
        checkType("XSDataRotation", "Constructor of XSDataRotation", q3, "double")
        self.__q3 = q3

    def getQ0(self):
        return self.__q0

    def setQ0(self, q0):
        checkType("XSDataRotation", "setQ0", q0, "double")
        self.__q0 = q0

    def delQ0(self):
        self.__q0 = None

    # Properties
    q0 = property(getQ0, setQ0, delQ0, "Property for q0")

    def getQ1(self):
        return self.__q1

    def setQ1(self, q1):
        checkType("XSDataRotation", "setQ1", q1, "double")
        self.__q1 = q1

    def delQ1(self):
        self.__q1 = None

    # Properties
    q1 = property(getQ1, setQ1, delQ1, "Property for q1")

    def getQ2(self):
        return self.__q2

    def setQ2(self, q2):
        checkType("XSDataRotation", "setQ2", q2, "double")
        self.__q2 = q2

    def delQ2(self):
        self.__q2 = None

    # Properties
    q2 = property(getQ2, setQ2, delQ2, "Property for q2")

    def getQ3(self):
        return self.__q3

    def setQ3(self, q3):
        checkType("XSDataRotation", "setQ3", q3, "double")
        self.__q3 = q3

    def delQ3(self):
        self.__q3 = None

    # Properties
    q3 = property(getQ3, setQ3, delQ3, "Property for q3")

    def export(self, outfile, level, name_="XSDataRotation"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataRotation"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__q0 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<q0>%e</q0>\n" % self.__q0))
        else:
            warnEmptyAttribute("q0", "double")
        if self.__q1 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<q1>%e</q1>\n" % self.__q1))
        else:
            warnEmptyAttribute("q1", "double")
        if self.__q2 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<q2>%e</q2>\n" % self.__q2))
        else:
            warnEmptyAttribute("q2", "double")
        if self.__q3 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<q3>%e</q3>\n" % self.__q3))
        else:
            warnEmptyAttribute("q3", "double")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "q0":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__q0 = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "q1":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__q1 = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "q2":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__q2 = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "q3":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__q3 = fval_
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataRotation")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataRotation")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataRotation is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataRotation.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataRotation()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataRotation")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataRotation()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataRotation


class XSDataSize(XSData):
    """These objects use the simple objects described above to create useful structures for the rest for the data model."""

    def __init__(self, z=None, y=None, x=None):
        XSData.__init__(self)
        checkType("XSDataSize", "Constructor of XSDataSize", x, "XSDataLength")
        self.__x = x
        checkType("XSDataSize", "Constructor of XSDataSize", y, "XSDataLength")
        self.__y = y
        checkType("XSDataSize", "Constructor of XSDataSize", z, "XSDataLength")
        self.__z = z

    def getX(self):
        return self.__x

    def setX(self, x):
        checkType("XSDataSize", "setX", x, "XSDataLength")
        self.__x = x

    def delX(self):
        self.__x = None

    # Properties
    x = property(getX, setX, delX, "Property for x")

    def getY(self):
        return self.__y

    def setY(self, y):
        checkType("XSDataSize", "setY", y, "XSDataLength")
        self.__y = y

    def delY(self):
        self.__y = None

    # Properties
    y = property(getY, setY, delY, "Property for y")

    def getZ(self):
        return self.__z

    def setZ(self, z):
        checkType("XSDataSize", "setZ", z, "XSDataLength")
        self.__z = z

    def delZ(self):
        self.__z = None

    # Properties
    z = property(getZ, setZ, delZ, "Property for z")

    def export(self, outfile, level, name_="XSDataSize"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataSize"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__x is not None:
            self.x.export(outfile, level, name_="x")
        else:
            warnEmptyAttribute("x", "XSDataLength")
        if self.__y is not None:
            self.y.export(outfile, level, name_="y")
        else:
            warnEmptyAttribute("y", "XSDataLength")
        if self.__z is not None:
            self.z.export(outfile, level, name_="z")
        else:
            warnEmptyAttribute("z", "XSDataLength")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "x":
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setX(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "y":
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setY(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "z":
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setZ(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataSize")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataSize")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataSize is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataSize.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataSize()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataSize")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataSize()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataSize


class XSDataSysteminfo(XSData):
    """This class contains information about the system executing the plugin."""

    def __init__(
        self,
        virtualMachine=None,
        userName=None,
        operatingSystemType=None,
        operatingSystem=None,
        hostName=None,
        hostIP=None,
        compiler=None,
    ):
        XSData.__init__(self)
        checkType(
            "XSDataSysteminfo",
            "Constructor of XSDataSysteminfo",
            compiler,
            "XSDataString",
        )
        self.__compiler = compiler
        checkType(
            "XSDataSysteminfo",
            "Constructor of XSDataSysteminfo",
            hostIP,
            "XSDataString",
        )
        self.__hostIP = hostIP
        checkType(
            "XSDataSysteminfo",
            "Constructor of XSDataSysteminfo",
            hostName,
            "XSDataString",
        )
        self.__hostName = hostName
        checkType(
            "XSDataSysteminfo",
            "Constructor of XSDataSysteminfo",
            operatingSystem,
            "XSDataString",
        )
        self.__operatingSystem = operatingSystem
        checkType(
            "XSDataSysteminfo",
            "Constructor of XSDataSysteminfo",
            operatingSystemType,
            "XSDataString",
        )
        self.__operatingSystemType = operatingSystemType
        checkType(
            "XSDataSysteminfo",
            "Constructor of XSDataSysteminfo",
            userName,
            "XSDataString",
        )
        self.__userName = userName
        checkType(
            "XSDataSysteminfo",
            "Constructor of XSDataSysteminfo",
            virtualMachine,
            "XSDataString",
        )
        self.__virtualMachine = virtualMachine

    def getCompiler(self):
        return self.__compiler

    def setCompiler(self, compiler):
        checkType("XSDataSysteminfo", "setCompiler", compiler, "XSDataString")
        self.__compiler = compiler

    def delCompiler(self):
        self.__compiler = None

    # Properties
    compiler = property(getCompiler, setCompiler, delCompiler, "Property for compiler")

    def getHostIP(self):
        return self.__hostIP

    def setHostIP(self, hostIP):
        checkType("XSDataSysteminfo", "setHostIP", hostIP, "XSDataString")
        self.__hostIP = hostIP

    def delHostIP(self):
        self.__hostIP = None

    # Properties
    hostIP = property(getHostIP, setHostIP, delHostIP, "Property for hostIP")

    def getHostName(self):
        return self.__hostName

    def setHostName(self, hostName):
        checkType("XSDataSysteminfo", "setHostName", hostName, "XSDataString")
        self.__hostName = hostName

    def delHostName(self):
        self.__hostName = None

    # Properties
    hostName = property(getHostName, setHostName, delHostName, "Property for hostName")

    def getOperatingSystem(self):
        return self.__operatingSystem

    def setOperatingSystem(self, operatingSystem):
        checkType(
            "XSDataSysteminfo", "setOperatingSystem", operatingSystem, "XSDataString"
        )
        self.__operatingSystem = operatingSystem

    def delOperatingSystem(self):
        self.__operatingSystem = None

    # Properties
    operatingSystem = property(
        getOperatingSystem,
        setOperatingSystem,
        delOperatingSystem,
        "Property for operatingSystem",
    )

    def getOperatingSystemType(self):
        return self.__operatingSystemType

    def setOperatingSystemType(self, operatingSystemType):
        checkType(
            "XSDataSysteminfo",
            "setOperatingSystemType",
            operatingSystemType,
            "XSDataString",
        )
        self.__operatingSystemType = operatingSystemType

    def delOperatingSystemType(self):
        self.__operatingSystemType = None

    # Properties
    operatingSystemType = property(
        getOperatingSystemType,
        setOperatingSystemType,
        delOperatingSystemType,
        "Property for operatingSystemType",
    )

    def getUserName(self):
        return self.__userName

    def setUserName(self, userName):
        checkType("XSDataSysteminfo", "setUserName", userName, "XSDataString")
        self.__userName = userName

    def delUserName(self):
        self.__userName = None

    # Properties
    userName = property(getUserName, setUserName, delUserName, "Property for userName")

    def getVirtualMachine(self):
        return self.__virtualMachine

    def setVirtualMachine(self, virtualMachine):
        checkType(
            "XSDataSysteminfo", "setVirtualMachine", virtualMachine, "XSDataString"
        )
        self.__virtualMachine = virtualMachine

    def delVirtualMachine(self):
        self.__virtualMachine = None

    # Properties
    virtualMachine = property(
        getVirtualMachine,
        setVirtualMachine,
        delVirtualMachine,
        "Property for virtualMachine",
    )

    def export(self, outfile, level, name_="XSDataSysteminfo"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataSysteminfo"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__compiler is not None:
            self.compiler.export(outfile, level, name_="compiler")
        else:
            warnEmptyAttribute("compiler", "XSDataString")
        if self.__hostIP is not None:
            self.hostIP.export(outfile, level, name_="hostIP")
        else:
            warnEmptyAttribute("hostIP", "XSDataString")
        if self.__hostName is not None:
            self.hostName.export(outfile, level, name_="hostName")
        else:
            warnEmptyAttribute("hostName", "XSDataString")
        if self.__operatingSystem is not None:
            self.operatingSystem.export(outfile, level, name_="operatingSystem")
        else:
            warnEmptyAttribute("operatingSystem", "XSDataString")
        if self.__operatingSystemType is not None:
            self.operatingSystemType.export(outfile, level, name_="operatingSystemType")
        else:
            warnEmptyAttribute("operatingSystemType", "XSDataString")
        if self.__userName is not None:
            self.userName.export(outfile, level, name_="userName")
        else:
            warnEmptyAttribute("userName", "XSDataString")
        if self.__virtualMachine is not None:
            self.virtualMachine.export(outfile, level, name_="virtualMachine")
        else:
            warnEmptyAttribute("virtualMachine", "XSDataString")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "compiler":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setCompiler(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "hostIP":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setHostIP(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "hostName":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setHostName(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "operatingSystem":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setOperatingSystem(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "operatingSystemType"
        ):
            obj_ = XSDataString()
            obj_.build(child_)
            self.setOperatingSystemType(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "userName":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setUserName(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "virtualMachine":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setVirtualMachine(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataSysteminfo")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataSysteminfo")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataSysteminfo is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataSysteminfo.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataSysteminfo()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataSysteminfo")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataSysteminfo()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataSysteminfo


class XSDataVectorDouble(XSData):
    """These are compound object used for linear algebra operations."""

    def __init__(self, v3=None, v2=None, v1=None):
        XSData.__init__(self)
        checkType(
            "XSDataVectorDouble", "Constructor of XSDataVectorDouble", v1, "double"
        )
        self.__v1 = v1
        checkType(
            "XSDataVectorDouble", "Constructor of XSDataVectorDouble", v2, "double"
        )
        self.__v2 = v2
        checkType(
            "XSDataVectorDouble", "Constructor of XSDataVectorDouble", v3, "double"
        )
        self.__v3 = v3

    def getV1(self):
        return self.__v1

    def setV1(self, v1):
        checkType("XSDataVectorDouble", "setV1", v1, "double")
        self.__v1 = v1

    def delV1(self):
        self.__v1 = None

    # Properties
    v1 = property(getV1, setV1, delV1, "Property for v1")

    def getV2(self):
        return self.__v2

    def setV2(self, v2):
        checkType("XSDataVectorDouble", "setV2", v2, "double")
        self.__v2 = v2

    def delV2(self):
        self.__v2 = None

    # Properties
    v2 = property(getV2, setV2, delV2, "Property for v2")

    def getV3(self):
        return self.__v3

    def setV3(self, v3):
        checkType("XSDataVectorDouble", "setV3", v3, "double")
        self.__v3 = v3

    def delV3(self):
        self.__v3 = None

    # Properties
    v3 = property(getV3, setV3, delV3, "Property for v3")

    def export(self, outfile, level, name_="XSDataVectorDouble"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataVectorDouble"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__v1 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<v1>%e</v1>\n" % self.__v1))
        else:
            warnEmptyAttribute("v1", "double")
        if self.__v2 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<v2>%e</v2>\n" % self.__v2))
        else:
            warnEmptyAttribute("v2", "double")
        if self.__v3 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<v3>%e</v3>\n" % self.__v3))
        else:
            warnEmptyAttribute("v3", "double")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "v1":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__v1 = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "v2":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__v2 = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "v3":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self.__v3 = fval_
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataVectorDouble")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataVectorDouble")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataVectorDouble is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataVectorDouble.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataVectorDouble()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataVectorDouble")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataVectorDouble()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataVectorDouble


class XSDataVectorInteger(XSData):
    """These are compound object used for linear algebra operations."""

    def __init__(self, v3=None, v2=None, v1=None):
        XSData.__init__(self)
        checkType(
            "XSDataVectorInteger", "Constructor of XSDataVectorInteger", v1, "integer"
        )
        self.__v1 = v1
        checkType(
            "XSDataVectorInteger", "Constructor of XSDataVectorInteger", v2, "integer"
        )
        self.__v2 = v2
        checkType(
            "XSDataVectorInteger", "Constructor of XSDataVectorInteger", v3, "integer"
        )
        self.__v3 = v3

    def getV1(self):
        return self.__v1

    def setV1(self, v1):
        checkType("XSDataVectorInteger", "setV1", v1, "integer")
        self.__v1 = v1

    def delV1(self):
        self.__v1 = None

    # Properties
    v1 = property(getV1, setV1, delV1, "Property for v1")

    def getV2(self):
        return self.__v2

    def setV2(self, v2):
        checkType("XSDataVectorInteger", "setV2", v2, "integer")
        self.__v2 = v2

    def delV2(self):
        self.__v2 = None

    # Properties
    v2 = property(getV2, setV2, delV2, "Property for v2")

    def getV3(self):
        return self.__v3

    def setV3(self, v3):
        checkType("XSDataVectorInteger", "setV3", v3, "integer")
        self.__v3 = v3

    def delV3(self):
        self.__v3 = None

    # Properties
    v3 = property(getV3, setV3, delV3, "Property for v3")

    def export(self, outfile, level, name_="XSDataVectorInteger"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataVectorInteger"):
        XSData.exportChildren(self, outfile, level, name_)
        if self.__v1 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<v1>%d</v1>\n" % self.__v1))
        else:
            warnEmptyAttribute("v1", "integer")
        if self.__v2 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<v2>%d</v2>\n" % self.__v2))
        else:
            warnEmptyAttribute("v2", "integer")
        if self.__v3 is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<v3>%d</v3>\n" % self.__v3))
        else:
            warnEmptyAttribute("v3", "integer")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "v1":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__v1 = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "v2":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__v2 = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "v3":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self.__v3 = ival_
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataVectorInteger")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataVectorInteger")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataVectorInteger is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataVectorInteger.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataVectorInteger()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataVectorInteger")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataVectorInteger()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataVectorInteger


class XSDataDate(XSDataString):
    """These simple objects that use built-in types are basically aimed to be used by the rest of the data model objects."""

    def __init__(self, value=None):
        XSDataString.__init__(self, value)

    def export(self, outfile, level, name_="XSDataDate"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataDate"):
        XSDataString.exportChildren(self, outfile, level, name_)

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        XSDataString.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataDate")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataDate")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataDate is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataDate.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataDate()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataDate")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataDate()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataDate


class XSDataDoubleWithUnit(XSDataDouble):
    def __init__(self, value=None, unit=None, error=None):
        XSDataDouble.__init__(self, value)
        checkType(
            "XSDataDoubleWithUnit",
            "Constructor of XSDataDoubleWithUnit",
            error,
            "XSDataDouble",
        )
        self.__error = error
        checkType(
            "XSDataDoubleWithUnit",
            "Constructor of XSDataDoubleWithUnit",
            unit,
            "XSDataString",
        )
        self.__unit = unit

    def getError(self):
        return self.__error

    def setError(self, error):
        checkType("XSDataDoubleWithUnit", "setError", error, "XSDataDouble")
        self.__error = error

    def delError(self):
        self.__error = None

    # Properties
    error = property(getError, setError, delError, "Property for error")

    def getUnit(self):
        return self.__unit

    def setUnit(self, unit):
        checkType("XSDataDoubleWithUnit", "setUnit", unit, "XSDataString")
        self.__unit = unit

    def delUnit(self):
        self.__unit = None

    # Properties
    unit = property(getUnit, setUnit, delUnit, "Property for unit")

    def export(self, outfile, level, name_="XSDataDoubleWithUnit"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataDoubleWithUnit"):
        XSDataDouble.exportChildren(self, outfile, level, name_)
        if self.__error is not None:
            self.error.export(outfile, level, name_="error")
        if self.__unit is not None:
            self.unit.export(outfile, level, name_="unit")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "error":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setError(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "unit":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setUnit(obj_)
        XSDataDouble.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataDoubleWithUnit")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataDoubleWithUnit")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataDoubleWithUnit is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataDoubleWithUnit.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataDoubleWithUnit()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataDoubleWithUnit")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataDoubleWithUnit()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataDoubleWithUnit


class XSDataImage(XSDataFile):
    """These objects use the simple objects described above to create useful structures for the rest for the data model."""

    def __init__(self, path=None, number=None, date=None):
        XSDataFile.__init__(self, path)
        checkType("XSDataImage", "Constructor of XSDataImage", date, "XSDataString")
        self.__date = date
        checkType("XSDataImage", "Constructor of XSDataImage", number, "XSDataInteger")
        self.__number = number

    def getDate(self):
        return self.__date

    def setDate(self, date):
        checkType("XSDataImage", "setDate", date, "XSDataString")
        self.__date = date

    def delDate(self):
        self.__date = None

    # Properties
    date = property(getDate, setDate, delDate, "Property for date")

    def getNumber(self):
        return self.__number

    def setNumber(self, number):
        checkType("XSDataImage", "setNumber", number, "XSDataInteger")
        self.__number = number

    def delNumber(self):
        self.__number = None

    # Properties
    number = property(getNumber, setNumber, delNumber, "Property for number")

    def export(self, outfile, level, name_="XSDataImage"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataImage"):
        XSDataFile.exportChildren(self, outfile, level, name_)
        if self.__date is not None:
            self.date.export(outfile, level, name_="date")
        if self.__number is not None:
            self.number.export(outfile, level, name_="number")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "date":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setDate(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "number":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumber(obj_)
        XSDataFile.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataImage")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataImage")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataImage is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataImage.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataImage()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataImage")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataImage()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataImage


class XSDataMatrix(XSDataMatrixDouble):
    """XSDataMatrix is deprecated and should be replaced with XSDataMatrixDouble."""

    def __init__(
        self,
        m33=None,
        m32=None,
        m31=None,
        m23=None,
        m22=None,
        m21=None,
        m13=None,
        m12=None,
        m11=None,
    ):
        XSDataMatrixDouble.__init__(self, m33, m32, m31, m23, m22, m21, m13, m12, m11)

    def export(self, outfile, level, name_="XSDataMatrix"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataMatrix"):
        XSDataMatrixDouble.exportChildren(self, outfile, level, name_)

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        XSDataMatrixDouble.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataMatrix")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataMatrix")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataMatrix is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataMatrix.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataMatrix()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataMatrix")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataMatrix()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataMatrix


class XSDataUnitVector(XSDataVectorDouble):
    """<<Invariant>>
    {abs(v1**2.0 + v3**2.0-1.0) < epsilon}"""

    def __init__(self, v3=None, v2=None, v1=None):
        XSDataVectorDouble.__init__(self, v3, v2, v1)

    def export(self, outfile, level, name_="XSDataUnitVector"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataUnitVector"):
        XSDataVectorDouble.exportChildren(self, outfile, level, name_)

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        XSDataVectorDouble.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataUnitVector")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataUnitVector")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataUnitVector is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataUnitVector.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataUnitVector()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataUnitVector")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataUnitVector()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataUnitVector


class XSDataAbsorbedDoseRate(XSDataDoubleWithUnit):
    """These simple objects that use built-in types are basically aimed to be used by the rest of the data model objects."""

    def __init__(self, value=None, unit=None, error=None):
        XSDataDoubleWithUnit.__init__(self, value, unit, error)

    def export(self, outfile, level, name_="XSDataAbsorbedDoseRate"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataAbsorbedDoseRate"):
        XSDataDoubleWithUnit.exportChildren(self, outfile, level, name_)

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        XSDataDoubleWithUnit.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataAbsorbedDoseRate")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataAbsorbedDoseRate")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataAbsorbedDoseRate is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataAbsorbedDoseRate.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataAbsorbedDoseRate()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataAbsorbedDoseRate")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataAbsorbedDoseRate()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataAbsorbedDoseRate


class XSDataAngularSpeed(XSDataDoubleWithUnit):
    """These simple objects that use built-in types are basically aimed to be used by the rest of the data model objects."""

    def __init__(self, value=None, unit=None, error=None):
        XSDataDoubleWithUnit.__init__(self, value, unit, error)

    def export(self, outfile, level, name_="XSDataAngularSpeed"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataAngularSpeed"):
        XSDataDoubleWithUnit.exportChildren(self, outfile, level, name_)

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        XSDataDoubleWithUnit.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataAngularSpeed")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataAngularSpeed")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataAngularSpeed is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataAngularSpeed.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataAngularSpeed()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataAngularSpeed")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataAngularSpeed()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataAngularSpeed


class XSDataFlux(XSDataDoubleWithUnit):
    """These simple objects that use built-in types are basically aimed to be used by the rest of the data model objects."""

    def __init__(self, value=None, unit=None, error=None):
        XSDataDoubleWithUnit.__init__(self, value, unit, error)

    def export(self, outfile, level, name_="XSDataFlux"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataFlux"):
        XSDataDoubleWithUnit.exportChildren(self, outfile, level, name_)

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        XSDataDoubleWithUnit.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataFlux")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataFlux")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataFlux is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataFlux.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataFlux()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataFlux")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataFlux()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataFlux


class XSDataLength(XSDataDoubleWithUnit):
    """These simple objects that use built-in types are basically aimed to be used by the rest of the data model objects."""

    def __init__(self, value=None, unit=None, error=None):
        XSDataDoubleWithUnit.__init__(self, value, unit, error)

    def export(self, outfile, level, name_="XSDataLength"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataLength"):
        XSDataDoubleWithUnit.exportChildren(self, outfile, level, name_)

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        XSDataDoubleWithUnit.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataLength")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataLength")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataLength is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataLength.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataLength()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataLength")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataLength()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataLength


class XSDataSpeed(XSDataDoubleWithUnit):
    """These simple objects that use built-in types are basically aimed to be used by the rest of the data model objects."""

    def __init__(self, value=None, unit=None, error=None):
        XSDataDoubleWithUnit.__init__(self, value, unit, error)

    def export(self, outfile, level, name_="XSDataSpeed"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataSpeed"):
        XSDataDoubleWithUnit.exportChildren(self, outfile, level, name_)

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        XSDataDoubleWithUnit.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataSpeed")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataSpeed")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataSpeed is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataSpeed.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataSpeed()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataSpeed")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataSpeed()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataSpeed


class XSDataTime(XSDataDoubleWithUnit):
    """These simple objects that use built-in types are basically aimed to be used by the rest of the data model objects."""

    def __init__(self, value=None, unit=None, error=None):
        XSDataDoubleWithUnit.__init__(self, value, unit, error)

    def export(self, outfile, level, name_="XSDataTime"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataTime"):
        XSDataDoubleWithUnit.exportChildren(self, outfile, level, name_)

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        XSDataDoubleWithUnit.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataTime")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataTime")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataTime is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataTime.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataTime()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataTime")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataTime()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataTime


class XSDataWavelength(XSDataDoubleWithUnit):
    """These simple objects that use built-in types are basically aimed to be used by the rest of the data model objects."""

    def __init__(self, value=None, unit=None, error=None):
        XSDataDoubleWithUnit.__init__(self, value, unit, error)

    def export(self, outfile, level, name_="XSDataWavelength"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataWavelength"):
        XSDataDoubleWithUnit.exportChildren(self, outfile, level, name_)

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        XSDataDoubleWithUnit.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataWavelength")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataWavelength")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataWavelength is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataWavelength.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataWavelength()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataWavelength")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataWavelength()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataWavelength


# End of data representation classes.
