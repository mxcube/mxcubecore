#!/usr/bin/env python

#
# Generated Fri Feb 15 02:34::39 2013 by EDGenerateDS.
#

from XSDataCommon import XSDataAngle
from XSDataCommon import XSDataWavelength
from XSDataCommon import XSDataTime
from XSDataCommon import XSDataLength
from XSDataCommon import XSDataFlux
from XSDataCommon import XSDataAngularSpeed
from XSDataCommon import XSDataAbsorbedDoseRate
from XSDataCommon import XSDataImage
from XSDataCommon import XSDataVectorDouble
from XSDataCommon import XSDataString
from XSDataCommon import XSDataSize
from XSDataCommon import XSDataResult
from XSDataCommon import XSDataMatrixDouble
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataInput
from XSDataCommon import XSDataFloat
from XSDataCommon import XSDataFile
from XSDataCommon import XSDataDouble
from XSDataCommon import XSDataBoolean
from XSDataCommon import XSData
import os
import sys
from xml.dom import minidom
from xml.dom import Node


strEdnaHome = os.environ.get("EDNA_HOME", None)

dictLocation = {
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
}

try:
    from XSDataCommon import XSData
    from XSDataCommon import XSDataBoolean
    from XSDataCommon import XSDataDouble
    from XSDataCommon import XSDataFile
    from XSDataCommon import XSDataFloat
    from XSDataCommon import XSDataInput
    from XSDataCommon import XSDataInteger
    from XSDataCommon import XSDataMatrixDouble
    from XSDataCommon import XSDataResult
    from XSDataCommon import XSDataSize
    from XSDataCommon import XSDataString
    from XSDataCommon import XSDataVectorDouble
    from XSDataCommon import XSDataImage
    from XSDataCommon import XSDataAbsorbedDoseRate
    from XSDataCommon import XSDataAngularSpeed
    from XSDataCommon import XSDataFlux
    from XSDataCommon import XSDataLength
    from XSDataCommon import XSDataTime
    from XSDataCommon import XSDataWavelength
    from XSDataCommon import XSDataAngle
except ImportError as error:
    if strEdnaHome is not None:
        for strXsdName in dictLocation:
            strXsdModule = strXsdName + ".py"
            strRootdir = os.path.dirname(
                os.path.abspath(os.path.join(strEdnaHome, dictLocation[strXsdName]))
            )
            for strRoot, listDirs, listFiles in os.walk(strRootdir):
                if strXsdModule in listFiles:
                    sys.path.append(strRoot)
    else:
        raise error


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


def warnEmptyAttribute(_strName, _strTypeName):
    pass
    # if not _strTypeName in ["float", "double", "string", "boolean", "integer"]:
    #    print("Warning! Non-optional attribute %s of type %s is None!" % (_strName, _strTypeName))


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


class XSDataStatisticsIntegrationAverageAndNumberOfReflections(object):
    def __init__(
        self,
        numberOfReflections=None,
        averageSigma=None,
        averageIntensity=None,
        averageIOverSigma=None,
    ):
        if averageIOverSigma is None:
            self._averageIOverSigma = None
        elif averageIOverSigma.__class__.__name__ == "XSDataDouble":
            self._averageIOverSigma = averageIOverSigma
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationAverageAndNumberOfReflections constructor argument 'averageIOverSigma' is not XSDataDouble but %s"
                % self._averageIOverSigma.__class__.__name__
            )
            raise BaseException(strMessage)
        if averageIntensity is None:
            self._averageIntensity = None
        elif averageIntensity.__class__.__name__ == "XSDataDouble":
            self._averageIntensity = averageIntensity
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationAverageAndNumberOfReflections constructor argument 'averageIntensity' is not XSDataDouble but %s"
                % self._averageIntensity.__class__.__name__
            )
            raise BaseException(strMessage)
        if averageSigma is None:
            self._averageSigma = None
        elif averageSigma.__class__.__name__ == "XSDataDouble":
            self._averageSigma = averageSigma
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationAverageAndNumberOfReflections constructor argument 'averageSigma' is not XSDataDouble but %s"
                % self._averageSigma.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberOfReflections is None:
            self._numberOfReflections = None
        elif numberOfReflections.__class__.__name__ == "XSDataInteger":
            self._numberOfReflections = numberOfReflections
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationAverageAndNumberOfReflections constructor argument 'numberOfReflections' is not XSDataInteger but %s"
                % self._numberOfReflections.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'averageIOverSigma' attribute
    def getAverageIOverSigma(self):
        return self._averageIOverSigma

    def setAverageIOverSigma(self, averageIOverSigma):
        if averageIOverSigma is None:
            self._averageIOverSigma = None
        elif averageIOverSigma.__class__.__name__ == "XSDataDouble":
            self._averageIOverSigma = averageIOverSigma
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationAverageAndNumberOfReflections.setAverageIOverSigma argument is not XSDataDouble but %s"
                % averageIOverSigma.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAverageIOverSigma(self):
        self._averageIOverSigma = None

    averageIOverSigma = property(
        getAverageIOverSigma,
        setAverageIOverSigma,
        delAverageIOverSigma,
        "Property for averageIOverSigma",
    )
    # Methods and properties for the 'averageIntensity' attribute

    def getAverageIntensity(self):
        return self._averageIntensity

    def setAverageIntensity(self, averageIntensity):
        if averageIntensity is None:
            self._averageIntensity = None
        elif averageIntensity.__class__.__name__ == "XSDataDouble":
            self._averageIntensity = averageIntensity
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationAverageAndNumberOfReflections.setAverageIntensity argument is not XSDataDouble but %s"
                % averageIntensity.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAverageIntensity(self):
        self._averageIntensity = None

    averageIntensity = property(
        getAverageIntensity,
        setAverageIntensity,
        delAverageIntensity,
        "Property for averageIntensity",
    )
    # Methods and properties for the 'averageSigma' attribute

    def getAverageSigma(self):
        return self._averageSigma

    def setAverageSigma(self, averageSigma):
        if averageSigma is None:
            self._averageSigma = None
        elif averageSigma.__class__.__name__ == "XSDataDouble":
            self._averageSigma = averageSigma
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationAverageAndNumberOfReflections.setAverageSigma argument is not XSDataDouble but %s"
                % averageSigma.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAverageSigma(self):
        self._averageSigma = None

    averageSigma = property(
        getAverageSigma, setAverageSigma, delAverageSigma, "Property for averageSigma"
    )
    # Methods and properties for the 'numberOfReflections' attribute

    def getNumberOfReflections(self):
        return self._numberOfReflections

    def setNumberOfReflections(self, numberOfReflections):
        if numberOfReflections is None:
            self._numberOfReflections = None
        elif numberOfReflections.__class__.__name__ == "XSDataInteger":
            self._numberOfReflections = numberOfReflections
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationAverageAndNumberOfReflections.setNumberOfReflections argument is not XSDataInteger but %s"
                % numberOfReflections.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberOfReflections(self):
        self._numberOfReflections = None

    numberOfReflections = property(
        getNumberOfReflections,
        setNumberOfReflections,
        delNumberOfReflections,
        "Property for numberOfReflections",
    )

    def export(
        self,
        outfile,
        level,
        name_="XSDataStatisticsIntegrationAverageAndNumberOfReflections",
    ):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(
        self,
        outfile,
        level,
        name_="XSDataStatisticsIntegrationAverageAndNumberOfReflections",
    ):
        if self._averageIOverSigma is not None:
            self.averageIOverSigma.export(outfile, level, name_="averageIOverSigma")
        else:
            warnEmptyAttribute("averageIOverSigma", "XSDataDouble")
        if self._averageIntensity is not None:
            self.averageIntensity.export(outfile, level, name_="averageIntensity")
        else:
            warnEmptyAttribute("averageIntensity", "XSDataDouble")
        if self._averageSigma is not None:
            self.averageSigma.export(outfile, level, name_="averageSigma")
        else:
            warnEmptyAttribute("averageSigma", "XSDataDouble")
        if self._numberOfReflections is not None:
            self.numberOfReflections.export(outfile, level, name_="numberOfReflections")
        else:
            warnEmptyAttribute("numberOfReflections", "XSDataInteger")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "averageIOverSigma":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setAverageIOverSigma(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "averageIntensity":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setAverageIntensity(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "averageSigma":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setAverageSigma(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "numberOfReflections"
        ):
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumberOfReflections(obj_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(
            oStreamString,
            0,
            name_="XSDataStatisticsIntegrationAverageAndNumberOfReflections",
        )
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(
            outfile, 0, name_="XSDataStatisticsIntegrationAverageAndNumberOfReflections"
        )
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataStatisticsIntegrationAverageAndNumberOfReflections is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataStatisticsIntegrationAverageAndNumberOfReflections.parseString(
            self.marshal()
        )

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataStatisticsIntegrationAverageAndNumberOfReflections()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(
            oStreamString,
            0,
            name_="XSDataStatisticsIntegrationAverageAndNumberOfReflections",
        )
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataStatisticsIntegrationAverageAndNumberOfReflections()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataStatisticsIntegrationAverageAndNumberOfReflections


class XSDataAtom(XSData):
    """This object describes a single atom content (of type 'symbol' i.e 'S') that could be either expressed in concentration if dilute in a solvent (mM) or in number in a structure"""

    def __init__(self, symbol=None, numberOf=None, concentration=None):
        XSData.__init__(self)
        if concentration is None:
            self._concentration = None
        elif concentration.__class__.__name__ == "XSDataDouble":
            self._concentration = concentration
        else:
            strMessage = (
                "ERROR! XSDataAtom constructor argument 'concentration' is not XSDataDouble but %s"
                % self._concentration.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberOf is None:
            self._numberOf = None
        elif numberOf.__class__.__name__ == "XSDataDouble":
            self._numberOf = numberOf
        else:
            strMessage = (
                "ERROR! XSDataAtom constructor argument 'numberOf' is not XSDataDouble but %s"
                % self._numberOf.__class__.__name__
            )
            raise BaseException(strMessage)
        if symbol is None:
            self._symbol = None
        elif symbol.__class__.__name__ == "XSDataString":
            self._symbol = symbol
        else:
            strMessage = (
                "ERROR! XSDataAtom constructor argument 'symbol' is not XSDataString but %s"
                % self._symbol.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'concentration' attribute
    def getConcentration(self):
        return self._concentration

    def setConcentration(self, concentration):
        if concentration is None:
            self._concentration = None
        elif concentration.__class__.__name__ == "XSDataDouble":
            self._concentration = concentration
        else:
            strMessage = (
                "ERROR! XSDataAtom.setConcentration argument is not XSDataDouble but %s"
                % concentration.__class__.__name__
            )
            raise BaseException(strMessage)

    def delConcentration(self):
        self._concentration = None

    concentration = property(
        getConcentration,
        setConcentration,
        delConcentration,
        "Property for concentration",
    )
    # Methods and properties for the 'numberOf' attribute

    def getNumberOf(self):
        return self._numberOf

    def setNumberOf(self, numberOf):
        if numberOf is None:
            self._numberOf = None
        elif numberOf.__class__.__name__ == "XSDataDouble":
            self._numberOf = numberOf
        else:
            strMessage = (
                "ERROR! XSDataAtom.setNumberOf argument is not XSDataDouble but %s"
                % numberOf.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberOf(self):
        self._numberOf = None

    numberOf = property(getNumberOf, setNumberOf, delNumberOf, "Property for numberOf")
    # Methods and properties for the 'symbol' attribute

    def getSymbol(self):
        return self._symbol

    def setSymbol(self, symbol):
        if symbol is None:
            self._symbol = None
        elif symbol.__class__.__name__ == "XSDataString":
            self._symbol = symbol
        else:
            strMessage = (
                "ERROR! XSDataAtom.setSymbol argument is not XSDataString but %s"
                % symbol.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSymbol(self):
        self._symbol = None

    symbol = property(getSymbol, setSymbol, delSymbol, "Property for symbol")

    def export(self, outfile, level, name_="XSDataAtom"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataAtom"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._concentration is not None:
            self.concentration.export(outfile, level, name_="concentration")
        if self._numberOf is not None:
            self.numberOf.export(outfile, level, name_="numberOf")
        if self._symbol is not None:
            self.symbol.export(outfile, level, name_="symbol")
        else:
            warnEmptyAttribute("symbol", "XSDataString")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "concentration":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setConcentration(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "numberOf":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setNumberOf(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "symbol":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setSymbol(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataAtom")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataAtom")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataAtom is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataAtom.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataAtom()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataAtom")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataAtom()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataAtom


class XSDataAtomicComposition(XSData):
    def __init__(self, atom=None):
        XSData.__init__(self)
        if atom is None:
            self._atom = []
        elif atom.__class__.__name__ == "list":
            self._atom = atom
        else:
            strMessage = (
                "ERROR! XSDataAtomicComposition constructor argument 'atom' is not list but %s"
                % self._atom.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'atom' attribute
    def getAtom(self):
        return self._atom

    def setAtom(self, atom):
        if atom is None:
            self._atom = []
        elif atom.__class__.__name__ == "list":
            self._atom = atom
        else:
            strMessage = (
                "ERROR! XSDataAtomicComposition.setAtom argument is not list but %s"
                % atom.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAtom(self):
        self._atom = None

    atom = property(getAtom, setAtom, delAtom, "Property for atom")

    def addAtom(self, value):
        if value is None:
            strMessage = "ERROR! XSDataAtomicComposition.addAtom argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataAtom":
            self._atom.append(value)
        else:
            strMessage = (
                "ERROR! XSDataAtomicComposition.addAtom argument is not XSDataAtom but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertAtom(self, index, value):
        if index is None:
            strMessage = (
                "ERROR! XSDataAtomicComposition.insertAtom argument 'index' is None"
            )
            raise BaseException(strMessage)
        if value is None:
            strMessage = (
                "ERROR! XSDataAtomicComposition.insertAtom argument 'value' is None"
            )
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataAtom":
            self._atom[index] = value
        else:
            strMessage = (
                "ERROR! XSDataAtomicComposition.addAtom argument is not XSDataAtom but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def export(self, outfile, level, name_="XSDataAtomicComposition"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataAtomicComposition"):
        XSData.exportChildren(self, outfile, level, name_)
        for atom_ in self.getAtom():
            atom_.export(outfile, level, name_="atom")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "atom":
            obj_ = XSDataAtom()
            obj_.build(child_)
            self.atom.append(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataAtomicComposition")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataAtomicComposition")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataAtomicComposition is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataAtomicComposition.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataAtomicComposition()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataAtomicComposition")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataAtomicComposition()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataAtomicComposition


class XSDataBeam(XSData):
    """This object contains all the properties related to the beam:
- the exposure time (sec)
- the flux (photons/sec)
- The minimum exposure time permitted by hardware (sec)
- The size of the beam (mm x mm)
- The wavelength (a)
- Transmission in %"""

    def __init__(
        self,
        wavelength=None,
        transmission=None,
        size=None,
        minExposureTimePerImage=None,
        flux=None,
        exposureTime=None,
    ):
        XSData.__init__(self)
        if exposureTime is None:
            self._exposureTime = None
        elif exposureTime.__class__.__name__ == "XSDataTime":
            self._exposureTime = exposureTime
        else:
            strMessage = (
                "ERROR! XSDataBeam constructor argument 'exposureTime' is not XSDataTime but %s"
                % self._exposureTime.__class__.__name__
            )
            raise BaseException(strMessage)
        if flux is None:
            self._flux = None
        elif flux.__class__.__name__ == "XSDataFlux":
            self._flux = flux
        else:
            strMessage = (
                "ERROR! XSDataBeam constructor argument 'flux' is not XSDataFlux but %s"
                % self._flux.__class__.__name__
            )
            raise BaseException(strMessage)
        if minExposureTimePerImage is None:
            self._minExposureTimePerImage = None
        elif minExposureTimePerImage.__class__.__name__ == "XSDataTime":
            self._minExposureTimePerImage = minExposureTimePerImage
        else:
            strMessage = (
                "ERROR! XSDataBeam constructor argument 'minExposureTimePerImage' is not XSDataTime but %s"
                % self._minExposureTimePerImage.__class__.__name__
            )
            raise BaseException(strMessage)
        if size is None:
            self._size = None
        elif size.__class__.__name__ == "XSDataSize":
            self._size = size
        else:
            strMessage = (
                "ERROR! XSDataBeam constructor argument 'size' is not XSDataSize but %s"
                % self._size.__class__.__name__
            )
            raise BaseException(strMessage)
        if transmission is None:
            self._transmission = None
        elif transmission.__class__.__name__ == "XSDataDouble":
            self._transmission = transmission
        else:
            strMessage = (
                "ERROR! XSDataBeam constructor argument 'transmission' is not XSDataDouble but %s"
                % self._transmission.__class__.__name__
            )
            raise BaseException(strMessage)
        if wavelength is None:
            self._wavelength = None
        elif wavelength.__class__.__name__ == "XSDataWavelength":
            self._wavelength = wavelength
        else:
            strMessage = (
                "ERROR! XSDataBeam constructor argument 'wavelength' is not XSDataWavelength but %s"
                % self._wavelength.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'exposureTime' attribute
    def getExposureTime(self):
        return self._exposureTime

    def setExposureTime(self, exposureTime):
        if exposureTime is None:
            self._exposureTime = None
        elif exposureTime.__class__.__name__ == "XSDataTime":
            self._exposureTime = exposureTime
        else:
            strMessage = (
                "ERROR! XSDataBeam.setExposureTime argument is not XSDataTime but %s"
                % exposureTime.__class__.__name__
            )
            raise BaseException(strMessage)

    def delExposureTime(self):
        self._exposureTime = None

    exposureTime = property(
        getExposureTime, setExposureTime, delExposureTime, "Property for exposureTime"
    )
    # Methods and properties for the 'flux' attribute

    def getFlux(self):
        return self._flux

    def setFlux(self, flux):
        if flux is None:
            self._flux = None
        elif flux.__class__.__name__ == "XSDataFlux":
            self._flux = flux
        else:
            strMessage = (
                "ERROR! XSDataBeam.setFlux argument is not XSDataFlux but %s"
                % flux.__class__.__name__
            )
            raise BaseException(strMessage)

    def delFlux(self):
        self._flux = None

    flux = property(getFlux, setFlux, delFlux, "Property for flux")
    # Methods and properties for the 'minExposureTimePerImage' attribute

    def getMinExposureTimePerImage(self):
        return self._minExposureTimePerImage

    def setMinExposureTimePerImage(self, minExposureTimePerImage):
        if minExposureTimePerImage is None:
            self._minExposureTimePerImage = None
        elif minExposureTimePerImage.__class__.__name__ == "XSDataTime":
            self._minExposureTimePerImage = minExposureTimePerImage
        else:
            strMessage = (
                "ERROR! XSDataBeam.setMinExposureTimePerImage argument is not XSDataTime but %s"
                % minExposureTimePerImage.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMinExposureTimePerImage(self):
        self._minExposureTimePerImage = None

    minExposureTimePerImage = property(
        getMinExposureTimePerImage,
        setMinExposureTimePerImage,
        delMinExposureTimePerImage,
        "Property for minExposureTimePerImage",
    )
    # Methods and properties for the 'size' attribute

    def getSize(self):
        return self._size

    def setSize(self, size):
        if size is None:
            self._size = None
        elif size.__class__.__name__ == "XSDataSize":
            self._size = size
        else:
            strMessage = (
                "ERROR! XSDataBeam.setSize argument is not XSDataSize but %s"
                % size.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSize(self):
        self._size = None

    size = property(getSize, setSize, delSize, "Property for size")
    # Methods and properties for the 'transmission' attribute

    def getTransmission(self):
        return self._transmission

    def setTransmission(self, transmission):
        if transmission is None:
            self._transmission = None
        elif transmission.__class__.__name__ == "XSDataDouble":
            self._transmission = transmission
        else:
            strMessage = (
                "ERROR! XSDataBeam.setTransmission argument is not XSDataDouble but %s"
                % transmission.__class__.__name__
            )
            raise BaseException(strMessage)

    def delTransmission(self):
        self._transmission = None

    transmission = property(
        getTransmission, setTransmission, delTransmission, "Property for transmission"
    )
    # Methods and properties for the 'wavelength' attribute

    def getWavelength(self):
        return self._wavelength

    def setWavelength(self, wavelength):
        if wavelength is None:
            self._wavelength = None
        elif wavelength.__class__.__name__ == "XSDataWavelength":
            self._wavelength = wavelength
        else:
            strMessage = (
                "ERROR! XSDataBeam.setWavelength argument is not XSDataWavelength but %s"
                % wavelength.__class__.__name__
            )
            raise BaseException(strMessage)

    def delWavelength(self):
        self._wavelength = None

    wavelength = property(
        getWavelength, setWavelength, delWavelength, "Property for wavelength"
    )

    def export(self, outfile, level, name_="XSDataBeam"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataBeam"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._exposureTime is not None:
            self.exposureTime.export(outfile, level, name_="exposureTime")
        if self._flux is not None:
            self.flux.export(outfile, level, name_="flux")
        if self._minExposureTimePerImage is not None:
            self.minExposureTimePerImage.export(
                outfile, level, name_="minExposureTimePerImage"
            )
        if self._size is not None:
            self.size.export(outfile, level, name_="size")
        if self._transmission is not None:
            self.transmission.export(outfile, level, name_="transmission")
        if self._wavelength is not None:
            self.wavelength.export(outfile, level, name_="wavelength")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "exposureTime":
            obj_ = XSDataTime()
            obj_.build(child_)
            self.setExposureTime(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "flux":
            obj_ = XSDataFlux()
            obj_.build(child_)
            self.setFlux(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "minExposureTimePerImage"
        ):
            obj_ = XSDataTime()
            obj_.build(child_)
            self.setMinExposureTimePerImage(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "size":
            obj_ = XSDataSize()
            obj_.build(child_)
            self.setSize(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "transmission":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setTransmission(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "wavelength":
            obj_ = XSDataWavelength()
            obj_.build(child_)
            self.setWavelength(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataBeam")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataBeam")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataBeam is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataBeam.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataBeam()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataBeam")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataBeam()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataBeam


class XSDataCell(XSData):
    """Crystallographic properties"""

    def __init__(
        self,
        length_c=None,
        length_b=None,
        length_a=None,
        angle_gamma=None,
        angle_beta=None,
        angle_alpha=None,
    ):
        XSData.__init__(self)
        if angle_alpha is None:
            self._angle_alpha = None
        elif angle_alpha.__class__.__name__ == "XSDataAngle":
            self._angle_alpha = angle_alpha
        else:
            strMessage = (
                "ERROR! XSDataCell constructor argument 'angle_alpha' is not XSDataAngle but %s"
                % self._angle_alpha.__class__.__name__
            )
            raise BaseException(strMessage)
        if angle_beta is None:
            self._angle_beta = None
        elif angle_beta.__class__.__name__ == "XSDataAngle":
            self._angle_beta = angle_beta
        else:
            strMessage = (
                "ERROR! XSDataCell constructor argument 'angle_beta' is not XSDataAngle but %s"
                % self._angle_beta.__class__.__name__
            )
            raise BaseException(strMessage)
        if angle_gamma is None:
            self._angle_gamma = None
        elif angle_gamma.__class__.__name__ == "XSDataAngle":
            self._angle_gamma = angle_gamma
        else:
            strMessage = (
                "ERROR! XSDataCell constructor argument 'angle_gamma' is not XSDataAngle but %s"
                % self._angle_gamma.__class__.__name__
            )
            raise BaseException(strMessage)
        if length_a is None:
            self._length_a = None
        elif length_a.__class__.__name__ == "XSDataLength":
            self._length_a = length_a
        else:
            strMessage = (
                "ERROR! XSDataCell constructor argument 'length_a' is not XSDataLength but %s"
                % self._length_a.__class__.__name__
            )
            raise BaseException(strMessage)
        if length_b is None:
            self._length_b = None
        elif length_b.__class__.__name__ == "XSDataLength":
            self._length_b = length_b
        else:
            strMessage = (
                "ERROR! XSDataCell constructor argument 'length_b' is not XSDataLength but %s"
                % self._length_b.__class__.__name__
            )
            raise BaseException(strMessage)
        if length_c is None:
            self._length_c = None
        elif length_c.__class__.__name__ == "XSDataLength":
            self._length_c = length_c
        else:
            strMessage = (
                "ERROR! XSDataCell constructor argument 'length_c' is not XSDataLength but %s"
                % self._length_c.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'angle_alpha' attribute
    def getAngle_alpha(self):
        return self._angle_alpha

    def setAngle_alpha(self, angle_alpha):
        if angle_alpha is None:
            self._angle_alpha = None
        elif angle_alpha.__class__.__name__ == "XSDataAngle":
            self._angle_alpha = angle_alpha
        else:
            strMessage = (
                "ERROR! XSDataCell.setAngle_alpha argument is not XSDataAngle but %s"
                % angle_alpha.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAngle_alpha(self):
        self._angle_alpha = None

    angle_alpha = property(
        getAngle_alpha, setAngle_alpha, delAngle_alpha, "Property for angle_alpha"
    )
    # Methods and properties for the 'angle_beta' attribute

    def getAngle_beta(self):
        return self._angle_beta

    def setAngle_beta(self, angle_beta):
        if angle_beta is None:
            self._angle_beta = None
        elif angle_beta.__class__.__name__ == "XSDataAngle":
            self._angle_beta = angle_beta
        else:
            strMessage = (
                "ERROR! XSDataCell.setAngle_beta argument is not XSDataAngle but %s"
                % angle_beta.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAngle_beta(self):
        self._angle_beta = None

    angle_beta = property(
        getAngle_beta, setAngle_beta, delAngle_beta, "Property for angle_beta"
    )
    # Methods and properties for the 'angle_gamma' attribute

    def getAngle_gamma(self):
        return self._angle_gamma

    def setAngle_gamma(self, angle_gamma):
        if angle_gamma is None:
            self._angle_gamma = None
        elif angle_gamma.__class__.__name__ == "XSDataAngle":
            self._angle_gamma = angle_gamma
        else:
            strMessage = (
                "ERROR! XSDataCell.setAngle_gamma argument is not XSDataAngle but %s"
                % angle_gamma.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAngle_gamma(self):
        self._angle_gamma = None

    angle_gamma = property(
        getAngle_gamma, setAngle_gamma, delAngle_gamma, "Property for angle_gamma"
    )
    # Methods and properties for the 'length_a' attribute

    def getLength_a(self):
        return self._length_a

    def setLength_a(self, length_a):
        if length_a is None:
            self._length_a = None
        elif length_a.__class__.__name__ == "XSDataLength":
            self._length_a = length_a
        else:
            strMessage = (
                "ERROR! XSDataCell.setLength_a argument is not XSDataLength but %s"
                % length_a.__class__.__name__
            )
            raise BaseException(strMessage)

    def delLength_a(self):
        self._length_a = None

    length_a = property(getLength_a, setLength_a, delLength_a, "Property for length_a")
    # Methods and properties for the 'length_b' attribute

    def getLength_b(self):
        return self._length_b

    def setLength_b(self, length_b):
        if length_b is None:
            self._length_b = None
        elif length_b.__class__.__name__ == "XSDataLength":
            self._length_b = length_b
        else:
            strMessage = (
                "ERROR! XSDataCell.setLength_b argument is not XSDataLength but %s"
                % length_b.__class__.__name__
            )
            raise BaseException(strMessage)

    def delLength_b(self):
        self._length_b = None

    length_b = property(getLength_b, setLength_b, delLength_b, "Property for length_b")
    # Methods and properties for the 'length_c' attribute

    def getLength_c(self):
        return self._length_c

    def setLength_c(self, length_c):
        if length_c is None:
            self._length_c = None
        elif length_c.__class__.__name__ == "XSDataLength":
            self._length_c = length_c
        else:
            strMessage = (
                "ERROR! XSDataCell.setLength_c argument is not XSDataLength but %s"
                % length_c.__class__.__name__
            )
            raise BaseException(strMessage)

    def delLength_c(self):
        self._length_c = None

    length_c = property(getLength_c, setLength_c, delLength_c, "Property for length_c")

    def export(self, outfile, level, name_="XSDataCell"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataCell"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._angle_alpha is not None:
            self.angle_alpha.export(outfile, level, name_="angle_alpha")
        else:
            warnEmptyAttribute("angle_alpha", "XSDataAngle")
        if self._angle_beta is not None:
            self.angle_beta.export(outfile, level, name_="angle_beta")
        else:
            warnEmptyAttribute("angle_beta", "XSDataAngle")
        if self._angle_gamma is not None:
            self.angle_gamma.export(outfile, level, name_="angle_gamma")
        else:
            warnEmptyAttribute("angle_gamma", "XSDataAngle")
        if self._length_a is not None:
            self.length_a.export(outfile, level, name_="length_a")
        else:
            warnEmptyAttribute("length_a", "XSDataLength")
        if self._length_b is not None:
            self.length_b.export(outfile, level, name_="length_b")
        else:
            warnEmptyAttribute("length_b", "XSDataLength")
        if self._length_c is not None:
            self.length_c.export(outfile, level, name_="length_c")
        else:
            warnEmptyAttribute("length_c", "XSDataLength")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "angle_alpha":
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setAngle_alpha(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "angle_beta":
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setAngle_beta(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "angle_gamma":
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setAngle_gamma(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "length_a":
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setLength_a(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "length_b":
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setLength_b(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "length_c":
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setLength_c(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataCell")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataCell")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataCell is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataCell.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataCell()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataCell")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataCell()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataCell


class XSDataChain(XSData):
    """A polymer chain of type 'protein', 'dna' or 'rna' that contains monomers (which number is defined by numberOfMonomers) and a list of heavy atoms. The number of this is particular chain in the whole polymer is defined by numberOfCopies."""

    def __init__(
        self, type=None, numberOfMonomers=None, numberOfCopies=None, heavyAtoms=None
    ):
        XSData.__init__(self)
        if heavyAtoms is None:
            self._heavyAtoms = None
        elif heavyAtoms.__class__.__name__ == "XSDataAtomicComposition":
            self._heavyAtoms = heavyAtoms
        else:
            strMessage = (
                "ERROR! XSDataChain constructor argument 'heavyAtoms' is not XSDataAtomicComposition but %s"
                % self._heavyAtoms.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberOfCopies is None:
            self._numberOfCopies = None
        elif numberOfCopies.__class__.__name__ == "XSDataDouble":
            self._numberOfCopies = numberOfCopies
        else:
            strMessage = (
                "ERROR! XSDataChain constructor argument 'numberOfCopies' is not XSDataDouble but %s"
                % self._numberOfCopies.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberOfMonomers is None:
            self._numberOfMonomers = None
        elif numberOfMonomers.__class__.__name__ == "XSDataDouble":
            self._numberOfMonomers = numberOfMonomers
        else:
            strMessage = (
                "ERROR! XSDataChain constructor argument 'numberOfMonomers' is not XSDataDouble but %s"
                % self._numberOfMonomers.__class__.__name__
            )
            raise BaseException(strMessage)
        if type is None:
            self._type = None
        elif type.__class__.__name__ == "XSDataString":
            self._type = type
        else:
            strMessage = (
                "ERROR! XSDataChain constructor argument 'type' is not XSDataString but %s"
                % self._type.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'heavyAtoms' attribute
    def getHeavyAtoms(self):
        return self._heavyAtoms

    def setHeavyAtoms(self, heavyAtoms):
        if heavyAtoms is None:
            self._heavyAtoms = None
        elif heavyAtoms.__class__.__name__ == "XSDataAtomicComposition":
            self._heavyAtoms = heavyAtoms
        else:
            strMessage = (
                "ERROR! XSDataChain.setHeavyAtoms argument is not XSDataAtomicComposition but %s"
                % heavyAtoms.__class__.__name__
            )
            raise BaseException(strMessage)

    def delHeavyAtoms(self):
        self._heavyAtoms = None

    heavyAtoms = property(
        getHeavyAtoms, setHeavyAtoms, delHeavyAtoms, "Property for heavyAtoms"
    )
    # Methods and properties for the 'numberOfCopies' attribute

    def getNumberOfCopies(self):
        return self._numberOfCopies

    def setNumberOfCopies(self, numberOfCopies):
        if numberOfCopies is None:
            self._numberOfCopies = None
        elif numberOfCopies.__class__.__name__ == "XSDataDouble":
            self._numberOfCopies = numberOfCopies
        else:
            strMessage = (
                "ERROR! XSDataChain.setNumberOfCopies argument is not XSDataDouble but %s"
                % numberOfCopies.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberOfCopies(self):
        self._numberOfCopies = None

    numberOfCopies = property(
        getNumberOfCopies,
        setNumberOfCopies,
        delNumberOfCopies,
        "Property for numberOfCopies",
    )
    # Methods and properties for the 'numberOfMonomers' attribute

    def getNumberOfMonomers(self):
        return self._numberOfMonomers

    def setNumberOfMonomers(self, numberOfMonomers):
        if numberOfMonomers is None:
            self._numberOfMonomers = None
        elif numberOfMonomers.__class__.__name__ == "XSDataDouble":
            self._numberOfMonomers = numberOfMonomers
        else:
            strMessage = (
                "ERROR! XSDataChain.setNumberOfMonomers argument is not XSDataDouble but %s"
                % numberOfMonomers.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberOfMonomers(self):
        self._numberOfMonomers = None

    numberOfMonomers = property(
        getNumberOfMonomers,
        setNumberOfMonomers,
        delNumberOfMonomers,
        "Property for numberOfMonomers",
    )
    # Methods and properties for the 'type' attribute

    def getType(self):
        return self._type

    def setType(self, type):
        if type is None:
            self._type = None
        elif type.__class__.__name__ == "XSDataString":
            self._type = type
        else:
            strMessage = (
                "ERROR! XSDataChain.setType argument is not XSDataString but %s"
                % type.__class__.__name__
            )
            raise BaseException(strMessage)

    def delType(self):
        self._type = None

    type = property(getType, setType, delType, "Property for type")

    def export(self, outfile, level, name_="XSDataChain"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataChain"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._heavyAtoms is not None:
            self.heavyAtoms.export(outfile, level, name_="heavyAtoms")
        else:
            warnEmptyAttribute("heavyAtoms", "XSDataAtomicComposition")
        if self._numberOfCopies is not None:
            self.numberOfCopies.export(outfile, level, name_="numberOfCopies")
        else:
            warnEmptyAttribute("numberOfCopies", "XSDataDouble")
        if self._numberOfMonomers is not None:
            self.numberOfMonomers.export(outfile, level, name_="numberOfMonomers")
        else:
            warnEmptyAttribute("numberOfMonomers", "XSDataDouble")
        if self._type is not None:
            self.type.export(outfile, level, name_="type")
        else:
            warnEmptyAttribute("type", "XSDataString")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "heavyAtoms":
            obj_ = XSDataAtomicComposition()
            obj_.build(child_)
            self.setHeavyAtoms(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "numberOfCopies":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setNumberOfCopies(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "numberOfMonomers":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setNumberOfMonomers(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "type":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setType(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataChain")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataChain")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataChain is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataChain.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataChain()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataChain")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataChain()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataChain


class XSDataChemicalCompositionMM(XSData):
    """This is the composition of a crystal sample of a Macro Molecule (MM stand for Macro Molecule)"""

    def __init__(self, structure=None, solvent=None):
        XSData.__init__(self)
        if solvent is None:
            self._solvent = None
        elif solvent.__class__.__name__ == "XSDataSolvent":
            self._solvent = solvent
        else:
            strMessage = (
                "ERROR! XSDataChemicalCompositionMM constructor argument 'solvent' is not XSDataSolvent but %s"
                % self._solvent.__class__.__name__
            )
            raise BaseException(strMessage)
        if structure is None:
            self._structure = None
        elif structure.__class__.__name__ == "XSDataStructure":
            self._structure = structure
        else:
            strMessage = (
                "ERROR! XSDataChemicalCompositionMM constructor argument 'structure' is not XSDataStructure but %s"
                % self._structure.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'solvent' attribute
    def getSolvent(self):
        return self._solvent

    def setSolvent(self, solvent):
        if solvent is None:
            self._solvent = None
        elif solvent.__class__.__name__ == "XSDataSolvent":
            self._solvent = solvent
        else:
            strMessage = (
                "ERROR! XSDataChemicalCompositionMM.setSolvent argument is not XSDataSolvent but %s"
                % solvent.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSolvent(self):
        self._solvent = None

    solvent = property(getSolvent, setSolvent, delSolvent, "Property for solvent")
    # Methods and properties for the 'structure' attribute

    def getStructure(self):
        return self._structure

    def setStructure(self, structure):
        if structure is None:
            self._structure = None
        elif structure.__class__.__name__ == "XSDataStructure":
            self._structure = structure
        else:
            strMessage = (
                "ERROR! XSDataChemicalCompositionMM.setStructure argument is not XSDataStructure but %s"
                % structure.__class__.__name__
            )
            raise BaseException(strMessage)

    def delStructure(self):
        self._structure = None

    structure = property(
        getStructure, setStructure, delStructure, "Property for structure"
    )

    def export(self, outfile, level, name_="XSDataChemicalCompositionMM"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataChemicalCompositionMM"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._solvent is not None:
            self.solvent.export(outfile, level, name_="solvent")
        else:
            warnEmptyAttribute("solvent", "XSDataSolvent")
        if self._structure is not None:
            self.structure.export(outfile, level, name_="structure")
        else:
            warnEmptyAttribute("structure", "XSDataStructure")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "solvent":
            obj_ = XSDataSolvent()
            obj_.build(child_)
            self.setSolvent(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "structure":
            obj_ = XSDataStructure()
            obj_.build(child_)
            self.setStructure(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataChemicalCompositionMM")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataChemicalCompositionMM")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataChemicalCompositionMM is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataChemicalCompositionMM.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataChemicalCompositionMM()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataChemicalCompositionMM")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataChemicalCompositionMM()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataChemicalCompositionMM


class XSDataCollection(XSData):
    """The data collection carried out or to be carried out with a particular sample with specific user inputs defined by the diffraction plan."""

    def __init__(self, subWedge=None, sample=None, diffractionPlan=None):
        XSData.__init__(self)
        if diffractionPlan is None:
            self._diffractionPlan = None
        elif diffractionPlan.__class__.__name__ == "XSDataDiffractionPlan":
            self._diffractionPlan = diffractionPlan
        else:
            strMessage = (
                "ERROR! XSDataCollection constructor argument 'diffractionPlan' is not XSDataDiffractionPlan but %s"
                % self._diffractionPlan.__class__.__name__
            )
            raise BaseException(strMessage)
        if sample is None:
            self._sample = None
        elif sample.__class__.__name__ == "XSDataSampleCrystalMM":
            self._sample = sample
        else:
            strMessage = (
                "ERROR! XSDataCollection constructor argument 'sample' is not XSDataSampleCrystalMM but %s"
                % self._sample.__class__.__name__
            )
            raise BaseException(strMessage)
        if subWedge is None:
            self._subWedge = []
        elif subWedge.__class__.__name__ == "list":
            self._subWedge = subWedge
        else:
            strMessage = (
                "ERROR! XSDataCollection constructor argument 'subWedge' is not list but %s"
                % self._subWedge.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'diffractionPlan' attribute
    def getDiffractionPlan(self):
        return self._diffractionPlan

    def setDiffractionPlan(self, diffractionPlan):
        if diffractionPlan is None:
            self._diffractionPlan = None
        elif diffractionPlan.__class__.__name__ == "XSDataDiffractionPlan":
            self._diffractionPlan = diffractionPlan
        else:
            strMessage = (
                "ERROR! XSDataCollection.setDiffractionPlan argument is not XSDataDiffractionPlan but %s"
                % diffractionPlan.__class__.__name__
            )
            raise BaseException(strMessage)

    def delDiffractionPlan(self):
        self._diffractionPlan = None

    diffractionPlan = property(
        getDiffractionPlan,
        setDiffractionPlan,
        delDiffractionPlan,
        "Property for diffractionPlan",
    )
    # Methods and properties for the 'sample' attribute

    def getSample(self):
        return self._sample

    def setSample(self, sample):
        if sample is None:
            self._sample = None
        elif sample.__class__.__name__ == "XSDataSampleCrystalMM":
            self._sample = sample
        else:
            strMessage = (
                "ERROR! XSDataCollection.setSample argument is not XSDataSampleCrystalMM but %s"
                % sample.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSample(self):
        self._sample = None

    sample = property(getSample, setSample, delSample, "Property for sample")
    # Methods and properties for the 'subWedge' attribute

    def getSubWedge(self):
        return self._subWedge

    def setSubWedge(self, subWedge):
        if subWedge is None:
            self._subWedge = []
        elif subWedge.__class__.__name__ == "list":
            self._subWedge = subWedge
        else:
            strMessage = (
                "ERROR! XSDataCollection.setSubWedge argument is not list but %s"
                % subWedge.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSubWedge(self):
        self._subWedge = None

    subWedge = property(getSubWedge, setSubWedge, delSubWedge, "Property for subWedge")

    def addSubWedge(self, value):
        if value is None:
            strMessage = "ERROR! XSDataCollection.addSubWedge argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataSubWedge":
            self._subWedge.append(value)
        else:
            strMessage = (
                "ERROR! XSDataCollection.addSubWedge argument is not XSDataSubWedge but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertSubWedge(self, index, value):
        if index is None:
            strMessage = (
                "ERROR! XSDataCollection.insertSubWedge argument 'index' is None"
            )
            raise BaseException(strMessage)
        if value is None:
            strMessage = (
                "ERROR! XSDataCollection.insertSubWedge argument 'value' is None"
            )
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataSubWedge":
            self._subWedge[index] = value
        else:
            strMessage = (
                "ERROR! XSDataCollection.addSubWedge argument is not XSDataSubWedge but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def export(self, outfile, level, name_="XSDataCollection"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataCollection"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._diffractionPlan is not None:
            self.diffractionPlan.export(outfile, level, name_="diffractionPlan")
        if self._sample is not None:
            self.sample.export(outfile, level, name_="sample")
        for subWedge_ in self.getSubWedge():
            subWedge_.export(outfile, level, name_="subWedge")
        if self.getSubWedge() == []:
            warnEmptyAttribute("subWedge", "XSDataSubWedge")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "diffractionPlan":
            obj_ = XSDataDiffractionPlan()
            obj_.build(child_)
            self.setDiffractionPlan(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "sample":
            obj_ = XSDataSampleCrystalMM()
            obj_.build(child_)
            self.setSample(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "subWedge":
            obj_ = XSDataSubWedge()
            obj_.build(child_)
            self.subWedge.append(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataCollection")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataCollection")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataCollection is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataCollection.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataCollection()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataCollection")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataCollection()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataCollection


class XSDataDetector(XSData):
    """The properties of a detector. """

    def __init__(
        self,
        type=None,
        twoTheta=None,
        serialNumber=None,
        pixelSizeY=None,
        pixelSizeX=None,
        numberPixelY=None,
        numberPixelX=None,
        numberBytesInHeader=None,
        name=None,
        imageSaturation=None,
        gain=None,
        distance=None,
        dataType=None,
        byteOrder=None,
        bin=None,
        beamPositionY=None,
        beamPositionX=None,
    ):
        XSData.__init__(self)
        if beamPositionX is None:
            self._beamPositionX = None
        elif beamPositionX.__class__.__name__ == "XSDataLength":
            self._beamPositionX = beamPositionX
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'beamPositionX' is not XSDataLength but %s"
                % self._beamPositionX.__class__.__name__
            )
            raise BaseException(strMessage)
        if beamPositionY is None:
            self._beamPositionY = None
        elif beamPositionY.__class__.__name__ == "XSDataLength":
            self._beamPositionY = beamPositionY
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'beamPositionY' is not XSDataLength but %s"
                % self._beamPositionY.__class__.__name__
            )
            raise BaseException(strMessage)
        if bin is None:
            self._bin = None
        elif bin.__class__.__name__ == "XSDataString":
            self._bin = bin
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'bin' is not XSDataString but %s"
                % self._bin.__class__.__name__
            )
            raise BaseException(strMessage)
        if byteOrder is None:
            self._byteOrder = None
        elif byteOrder.__class__.__name__ == "XSDataString":
            self._byteOrder = byteOrder
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'byteOrder' is not XSDataString but %s"
                % self._byteOrder.__class__.__name__
            )
            raise BaseException(strMessage)
        if dataType is None:
            self._dataType = None
        elif dataType.__class__.__name__ == "XSDataString":
            self._dataType = dataType
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'dataType' is not XSDataString but %s"
                % self._dataType.__class__.__name__
            )
            raise BaseException(strMessage)
        if distance is None:
            self._distance = None
        elif distance.__class__.__name__ == "XSDataLength":
            self._distance = distance
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'distance' is not XSDataLength but %s"
                % self._distance.__class__.__name__
            )
            raise BaseException(strMessage)
        if gain is None:
            self._gain = None
        elif gain.__class__.__name__ == "XSDataFloat":
            self._gain = gain
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'gain' is not XSDataFloat but %s"
                % self._gain.__class__.__name__
            )
            raise BaseException(strMessage)
        if imageSaturation is None:
            self._imageSaturation = None
        elif imageSaturation.__class__.__name__ == "XSDataInteger":
            self._imageSaturation = imageSaturation
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'imageSaturation' is not XSDataInteger but %s"
                % self._imageSaturation.__class__.__name__
            )
            raise BaseException(strMessage)
        if name is None:
            self._name = None
        elif name.__class__.__name__ == "XSDataString":
            self._name = name
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'name' is not XSDataString but %s"
                % self._name.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberBytesInHeader is None:
            self._numberBytesInHeader = None
        elif numberBytesInHeader.__class__.__name__ == "XSDataInteger":
            self._numberBytesInHeader = numberBytesInHeader
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'numberBytesInHeader' is not XSDataInteger but %s"
                % self._numberBytesInHeader.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberPixelX is None:
            self._numberPixelX = None
        elif numberPixelX.__class__.__name__ == "XSDataInteger":
            self._numberPixelX = numberPixelX
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'numberPixelX' is not XSDataInteger but %s"
                % self._numberPixelX.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberPixelY is None:
            self._numberPixelY = None
        elif numberPixelY.__class__.__name__ == "XSDataInteger":
            self._numberPixelY = numberPixelY
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'numberPixelY' is not XSDataInteger but %s"
                % self._numberPixelY.__class__.__name__
            )
            raise BaseException(strMessage)
        if pixelSizeX is None:
            self._pixelSizeX = None
        elif pixelSizeX.__class__.__name__ == "XSDataLength":
            self._pixelSizeX = pixelSizeX
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'pixelSizeX' is not XSDataLength but %s"
                % self._pixelSizeX.__class__.__name__
            )
            raise BaseException(strMessage)
        if pixelSizeY is None:
            self._pixelSizeY = None
        elif pixelSizeY.__class__.__name__ == "XSDataLength":
            self._pixelSizeY = pixelSizeY
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'pixelSizeY' is not XSDataLength but %s"
                % self._pixelSizeY.__class__.__name__
            )
            raise BaseException(strMessage)
        if serialNumber is None:
            self._serialNumber = None
        elif serialNumber.__class__.__name__ == "XSDataString":
            self._serialNumber = serialNumber
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'serialNumber' is not XSDataString but %s"
                % self._serialNumber.__class__.__name__
            )
            raise BaseException(strMessage)
        if twoTheta is None:
            self._twoTheta = None
        elif twoTheta.__class__.__name__ == "XSDataAngle":
            self._twoTheta = twoTheta
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'twoTheta' is not XSDataAngle but %s"
                % self._twoTheta.__class__.__name__
            )
            raise BaseException(strMessage)
        if type is None:
            self._type = None
        elif type.__class__.__name__ == "XSDataString":
            self._type = type
        else:
            strMessage = (
                "ERROR! XSDataDetector constructor argument 'type' is not XSDataString but %s"
                % self._type.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'beamPositionX' attribute
    def getBeamPositionX(self):
        return self._beamPositionX

    def setBeamPositionX(self, beamPositionX):
        if beamPositionX is None:
            self._beamPositionX = None
        elif beamPositionX.__class__.__name__ == "XSDataLength":
            self._beamPositionX = beamPositionX
        else:
            strMessage = (
                "ERROR! XSDataDetector.setBeamPositionX argument is not XSDataLength but %s"
                % beamPositionX.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBeamPositionX(self):
        self._beamPositionX = None

    beamPositionX = property(
        getBeamPositionX,
        setBeamPositionX,
        delBeamPositionX,
        "Property for beamPositionX",
    )
    # Methods and properties for the 'beamPositionY' attribute

    def getBeamPositionY(self):
        return self._beamPositionY

    def setBeamPositionY(self, beamPositionY):
        if beamPositionY is None:
            self._beamPositionY = None
        elif beamPositionY.__class__.__name__ == "XSDataLength":
            self._beamPositionY = beamPositionY
        else:
            strMessage = (
                "ERROR! XSDataDetector.setBeamPositionY argument is not XSDataLength but %s"
                % beamPositionY.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBeamPositionY(self):
        self._beamPositionY = None

    beamPositionY = property(
        getBeamPositionY,
        setBeamPositionY,
        delBeamPositionY,
        "Property for beamPositionY",
    )
    # Methods and properties for the 'bin' attribute

    def getBin(self):
        return self._bin

    def setBin(self, bin):
        if bin is None:
            self._bin = None
        elif bin.__class__.__name__ == "XSDataString":
            self._bin = bin
        else:
            strMessage = (
                "ERROR! XSDataDetector.setBin argument is not XSDataString but %s"
                % bin.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBin(self):
        self._bin = None

    bin = property(getBin, setBin, delBin, "Property for bin")
    # Methods and properties for the 'byteOrder' attribute

    def getByteOrder(self):
        return self._byteOrder

    def setByteOrder(self, byteOrder):
        if byteOrder is None:
            self._byteOrder = None
        elif byteOrder.__class__.__name__ == "XSDataString":
            self._byteOrder = byteOrder
        else:
            strMessage = (
                "ERROR! XSDataDetector.setByteOrder argument is not XSDataString but %s"
                % byteOrder.__class__.__name__
            )
            raise BaseException(strMessage)

    def delByteOrder(self):
        self._byteOrder = None

    byteOrder = property(
        getByteOrder, setByteOrder, delByteOrder, "Property for byteOrder"
    )
    # Methods and properties for the 'dataType' attribute

    def getDataType(self):
        return self._dataType

    def setDataType(self, dataType):
        if dataType is None:
            self._dataType = None
        elif dataType.__class__.__name__ == "XSDataString":
            self._dataType = dataType
        else:
            strMessage = (
                "ERROR! XSDataDetector.setDataType argument is not XSDataString but %s"
                % dataType.__class__.__name__
            )
            raise BaseException(strMessage)

    def delDataType(self):
        self._dataType = None

    dataType = property(getDataType, setDataType, delDataType, "Property for dataType")
    # Methods and properties for the 'distance' attribute

    def getDistance(self):
        return self._distance

    def setDistance(self, distance):
        if distance is None:
            self._distance = None
        elif distance.__class__.__name__ == "XSDataLength":
            self._distance = distance
        else:
            strMessage = (
                "ERROR! XSDataDetector.setDistance argument is not XSDataLength but %s"
                % distance.__class__.__name__
            )
            raise BaseException(strMessage)

    def delDistance(self):
        self._distance = None

    distance = property(getDistance, setDistance, delDistance, "Property for distance")
    # Methods and properties for the 'gain' attribute

    def getGain(self):
        return self._gain

    def setGain(self, gain):
        if gain is None:
            self._gain = None
        elif gain.__class__.__name__ == "XSDataFloat":
            self._gain = gain
        else:
            strMessage = (
                "ERROR! XSDataDetector.setGain argument is not XSDataFloat but %s"
                % gain.__class__.__name__
            )
            raise BaseException(strMessage)

    def delGain(self):
        self._gain = None

    gain = property(getGain, setGain, delGain, "Property for gain")
    # Methods and properties for the 'imageSaturation' attribute

    def getImageSaturation(self):
        return self._imageSaturation

    def setImageSaturation(self, imageSaturation):
        if imageSaturation is None:
            self._imageSaturation = None
        elif imageSaturation.__class__.__name__ == "XSDataInteger":
            self._imageSaturation = imageSaturation
        else:
            strMessage = (
                "ERROR! XSDataDetector.setImageSaturation argument is not XSDataInteger but %s"
                % imageSaturation.__class__.__name__
            )
            raise BaseException(strMessage)

    def delImageSaturation(self):
        self._imageSaturation = None

    imageSaturation = property(
        getImageSaturation,
        setImageSaturation,
        delImageSaturation,
        "Property for imageSaturation",
    )
    # Methods and properties for the 'name' attribute

    def getName(self):
        return self._name

    def setName(self, name):
        if name is None:
            self._name = None
        elif name.__class__.__name__ == "XSDataString":
            self._name = name
        else:
            strMessage = (
                "ERROR! XSDataDetector.setName argument is not XSDataString but %s"
                % name.__class__.__name__
            )
            raise BaseException(strMessage)

    def delName(self):
        self._name = None

    name = property(getName, setName, delName, "Property for name")
    # Methods and properties for the 'numberBytesInHeader' attribute

    def getNumberBytesInHeader(self):
        return self._numberBytesInHeader

    def setNumberBytesInHeader(self, numberBytesInHeader):
        if numberBytesInHeader is None:
            self._numberBytesInHeader = None
        elif numberBytesInHeader.__class__.__name__ == "XSDataInteger":
            self._numberBytesInHeader = numberBytesInHeader
        else:
            strMessage = (
                "ERROR! XSDataDetector.setNumberBytesInHeader argument is not XSDataInteger but %s"
                % numberBytesInHeader.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberBytesInHeader(self):
        self._numberBytesInHeader = None

    numberBytesInHeader = property(
        getNumberBytesInHeader,
        setNumberBytesInHeader,
        delNumberBytesInHeader,
        "Property for numberBytesInHeader",
    )
    # Methods and properties for the 'numberPixelX' attribute

    def getNumberPixelX(self):
        return self._numberPixelX

    def setNumberPixelX(self, numberPixelX):
        if numberPixelX is None:
            self._numberPixelX = None
        elif numberPixelX.__class__.__name__ == "XSDataInteger":
            self._numberPixelX = numberPixelX
        else:
            strMessage = (
                "ERROR! XSDataDetector.setNumberPixelX argument is not XSDataInteger but %s"
                % numberPixelX.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberPixelX(self):
        self._numberPixelX = None

    numberPixelX = property(
        getNumberPixelX, setNumberPixelX, delNumberPixelX, "Property for numberPixelX"
    )
    # Methods and properties for the 'numberPixelY' attribute

    def getNumberPixelY(self):
        return self._numberPixelY

    def setNumberPixelY(self, numberPixelY):
        if numberPixelY is None:
            self._numberPixelY = None
        elif numberPixelY.__class__.__name__ == "XSDataInteger":
            self._numberPixelY = numberPixelY
        else:
            strMessage = (
                "ERROR! XSDataDetector.setNumberPixelY argument is not XSDataInteger but %s"
                % numberPixelY.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberPixelY(self):
        self._numberPixelY = None

    numberPixelY = property(
        getNumberPixelY, setNumberPixelY, delNumberPixelY, "Property for numberPixelY"
    )
    # Methods and properties for the 'pixelSizeX' attribute

    def getPixelSizeX(self):
        return self._pixelSizeX

    def setPixelSizeX(self, pixelSizeX):
        if pixelSizeX is None:
            self._pixelSizeX = None
        elif pixelSizeX.__class__.__name__ == "XSDataLength":
            self._pixelSizeX = pixelSizeX
        else:
            strMessage = (
                "ERROR! XSDataDetector.setPixelSizeX argument is not XSDataLength but %s"
                % pixelSizeX.__class__.__name__
            )
            raise BaseException(strMessage)

    def delPixelSizeX(self):
        self._pixelSizeX = None

    pixelSizeX = property(
        getPixelSizeX, setPixelSizeX, delPixelSizeX, "Property for pixelSizeX"
    )
    # Methods and properties for the 'pixelSizeY' attribute

    def getPixelSizeY(self):
        return self._pixelSizeY

    def setPixelSizeY(self, pixelSizeY):
        if pixelSizeY is None:
            self._pixelSizeY = None
        elif pixelSizeY.__class__.__name__ == "XSDataLength":
            self._pixelSizeY = pixelSizeY
        else:
            strMessage = (
                "ERROR! XSDataDetector.setPixelSizeY argument is not XSDataLength but %s"
                % pixelSizeY.__class__.__name__
            )
            raise BaseException(strMessage)

    def delPixelSizeY(self):
        self._pixelSizeY = None

    pixelSizeY = property(
        getPixelSizeY, setPixelSizeY, delPixelSizeY, "Property for pixelSizeY"
    )
    # Methods and properties for the 'serialNumber' attribute

    def getSerialNumber(self):
        return self._serialNumber

    def setSerialNumber(self, serialNumber):
        if serialNumber is None:
            self._serialNumber = None
        elif serialNumber.__class__.__name__ == "XSDataString":
            self._serialNumber = serialNumber
        else:
            strMessage = (
                "ERROR! XSDataDetector.setSerialNumber argument is not XSDataString but %s"
                % serialNumber.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSerialNumber(self):
        self._serialNumber = None

    serialNumber = property(
        getSerialNumber, setSerialNumber, delSerialNumber, "Property for serialNumber"
    )
    # Methods and properties for the 'twoTheta' attribute

    def getTwoTheta(self):
        return self._twoTheta

    def setTwoTheta(self, twoTheta):
        if twoTheta is None:
            self._twoTheta = None
        elif twoTheta.__class__.__name__ == "XSDataAngle":
            self._twoTheta = twoTheta
        else:
            strMessage = (
                "ERROR! XSDataDetector.setTwoTheta argument is not XSDataAngle but %s"
                % twoTheta.__class__.__name__
            )
            raise BaseException(strMessage)

    def delTwoTheta(self):
        self._twoTheta = None

    twoTheta = property(getTwoTheta, setTwoTheta, delTwoTheta, "Property for twoTheta")
    # Methods and properties for the 'type' attribute

    def getType(self):
        return self._type

    def setType(self, type):
        if type is None:
            self._type = None
        elif type.__class__.__name__ == "XSDataString":
            self._type = type
        else:
            strMessage = (
                "ERROR! XSDataDetector.setType argument is not XSDataString but %s"
                % type.__class__.__name__
            )
            raise BaseException(strMessage)

    def delType(self):
        self._type = None

    type = property(getType, setType, delType, "Property for type")

    def export(self, outfile, level, name_="XSDataDetector"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataDetector"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._beamPositionX is not None:
            self.beamPositionX.export(outfile, level, name_="beamPositionX")
        else:
            warnEmptyAttribute("beamPositionX", "XSDataLength")
        if self._beamPositionY is not None:
            self.beamPositionY.export(outfile, level, name_="beamPositionY")
        else:
            warnEmptyAttribute("beamPositionY", "XSDataLength")
        if self._bin is not None:
            self.bin.export(outfile, level, name_="bin")
        else:
            warnEmptyAttribute("bin", "XSDataString")
        if self._byteOrder is not None:
            self.byteOrder.export(outfile, level, name_="byteOrder")
        else:
            warnEmptyAttribute("byteOrder", "XSDataString")
        if self._dataType is not None:
            self.dataType.export(outfile, level, name_="dataType")
        else:
            warnEmptyAttribute("dataType", "XSDataString")
        if self._distance is not None:
            self.distance.export(outfile, level, name_="distance")
        else:
            warnEmptyAttribute("distance", "XSDataLength")
        if self._gain is not None:
            self.gain.export(outfile, level, name_="gain")
        if self._imageSaturation is not None:
            self.imageSaturation.export(outfile, level, name_="imageSaturation")
        else:
            warnEmptyAttribute("imageSaturation", "XSDataInteger")
        if self._name is not None:
            self.name.export(outfile, level, name_="name")
        else:
            warnEmptyAttribute("name", "XSDataString")
        if self._numberBytesInHeader is not None:
            self.numberBytesInHeader.export(outfile, level, name_="numberBytesInHeader")
        else:
            warnEmptyAttribute("numberBytesInHeader", "XSDataInteger")
        if self._numberPixelX is not None:
            self.numberPixelX.export(outfile, level, name_="numberPixelX")
        else:
            warnEmptyAttribute("numberPixelX", "XSDataInteger")
        if self._numberPixelY is not None:
            self.numberPixelY.export(outfile, level, name_="numberPixelY")
        else:
            warnEmptyAttribute("numberPixelY", "XSDataInteger")
        if self._pixelSizeX is not None:
            self.pixelSizeX.export(outfile, level, name_="pixelSizeX")
        else:
            warnEmptyAttribute("pixelSizeX", "XSDataLength")
        if self._pixelSizeY is not None:
            self.pixelSizeY.export(outfile, level, name_="pixelSizeY")
        else:
            warnEmptyAttribute("pixelSizeY", "XSDataLength")
        if self._serialNumber is not None:
            self.serialNumber.export(outfile, level, name_="serialNumber")
        else:
            warnEmptyAttribute("serialNumber", "XSDataString")
        if self._twoTheta is not None:
            self.twoTheta.export(outfile, level, name_="twoTheta")
        else:
            warnEmptyAttribute("twoTheta", "XSDataAngle")
        if self._type is not None:
            self.type.export(outfile, level, name_="type")
        else:
            warnEmptyAttribute("type", "XSDataString")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "beamPositionX":
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setBeamPositionX(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "beamPositionY":
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setBeamPositionY(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "bin":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setBin(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "byteOrder":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setByteOrder(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "dataType":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setDataType(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "distance":
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setDistance(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "gain":
            obj_ = XSDataFloat()
            obj_.build(child_)
            self.setGain(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "imageSaturation":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setImageSaturation(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "name":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setName(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "numberBytesInHeader"
        ):
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumberBytesInHeader(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "numberPixelX":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumberPixelX(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "numberPixelY":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumberPixelY(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "pixelSizeX":
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setPixelSizeX(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "pixelSizeY":
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setPixelSizeY(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "serialNumber":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setSerialNumber(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "twoTheta":
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setTwoTheta(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "type":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setType(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataDetector")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataDetector")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataDetector is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataDetector.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataDetector()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataDetector")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataDetector()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataDetector


class XSDataDiffractionPlan(XSData):
    """This object contains the main properties a user can parameterize for a crystal characterisation:

- the aimed* parameters are the parameters that a user would like to reach for a BEST run.
- the required* are not yet used (the idea is to warn the user if these parameters cannot be reached)
- complexity: BEST complexity input, can be either "none" (always single wedge strategy). "min" (few subwedges) or "full" (many subwedges).
- maxExposureTimePerDataCollection is the max total exposure time (shutter open, not including readout time) the crystal can be exposed to the X-ray beam.
- forcedSpaceGroup: option to force the space group of the indexing solution
- strategyOption: extra option for BEST for more advanced strategies like estimating the sensitivity to radiation damage
- anomalousData: Depreccated! Boolean value for enabling anomalous strategy. In the future the strategyOption should be used instead of anomalousData.
- estimateRadiationDamage: Boolean value for enabling or disabling the use of Raddose for estimation of radiation damage. If estimateRadiationDamage is enabled also the flux and beamsize must be provided.
- detectorDistanceMin and detectorDistanceMax: optimal input to BEST for limiting the calculated strategy resolution to be in the range of the detector displacements with respect to the sample.
- minTransmission: optional input for BEST
- kappaStrategyOption: optional input for kappa strategies
- numberOfPositions: optional input for BEST"""

    def __init__(
        self,
        userDefinedRotationStart=None,
        userDefinedRotationRange=None,
        strategyOption=None,
        requiredResolution=None,
        requiredMultiplicity=None,
        requiredCompleteness=None,
        numberOfPositions=None,
        minTransmission=None,
        minExposureTimePerImage=None,
        maxExposureTimePerDataCollection=None,
        kappaStrategyOption=None,
        goniostatMinOscillationWidth=None,
        goniostatMaxOscillationSpeed=None,
        forcedSpaceGroup=None,
        estimateRadiationDamage=None,
        detectorDistanceMin=None,
        detectorDistanceMax=None,
        complexity=None,
        anomalousData=None,
        aimedResolution=None,
        aimedMultiplicity=None,
        aimedIOverSigmaAtHighestResolution=None,
        aimedCompleteness=None,
    ):
        XSData.__init__(self)
        if aimedCompleteness is None:
            self._aimedCompleteness = None
        elif aimedCompleteness.__class__.__name__ == "XSDataDouble":
            self._aimedCompleteness = aimedCompleteness
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'aimedCompleteness' is not XSDataDouble but %s"
                % self._aimedCompleteness.__class__.__name__
            )
            raise BaseException(strMessage)
        if aimedIOverSigmaAtHighestResolution is None:
            self._aimedIOverSigmaAtHighestResolution = None
        elif aimedIOverSigmaAtHighestResolution.__class__.__name__ == "XSDataDouble":
            self._aimedIOverSigmaAtHighestResolution = (
                aimedIOverSigmaAtHighestResolution
            )
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'aimedIOverSigmaAtHighestResolution' is not XSDataDouble but %s"
                % self._aimedIOverSigmaAtHighestResolution.__class__.__name__
            )
            raise BaseException(strMessage)
        if aimedMultiplicity is None:
            self._aimedMultiplicity = None
        elif aimedMultiplicity.__class__.__name__ == "XSDataDouble":
            self._aimedMultiplicity = aimedMultiplicity
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'aimedMultiplicity' is not XSDataDouble but %s"
                % self._aimedMultiplicity.__class__.__name__
            )
            raise BaseException(strMessage)
        if aimedResolution is None:
            self._aimedResolution = None
        elif aimedResolution.__class__.__name__ == "XSDataDouble":
            self._aimedResolution = aimedResolution
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'aimedResolution' is not XSDataDouble but %s"
                % self._aimedResolution.__class__.__name__
            )
            raise BaseException(strMessage)
        if anomalousData is None:
            self._anomalousData = None
        elif anomalousData.__class__.__name__ == "XSDataBoolean":
            self._anomalousData = anomalousData
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'anomalousData' is not XSDataBoolean but %s"
                % self._anomalousData.__class__.__name__
            )
            raise BaseException(strMessage)
        if complexity is None:
            self._complexity = None
        elif complexity.__class__.__name__ == "XSDataString":
            self._complexity = complexity
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'complexity' is not XSDataString but %s"
                % self._complexity.__class__.__name__
            )
            raise BaseException(strMessage)
        if detectorDistanceMax is None:
            self._detectorDistanceMax = None
        elif detectorDistanceMax.__class__.__name__ == "XSDataLength":
            self._detectorDistanceMax = detectorDistanceMax
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'detectorDistanceMax' is not XSDataLength but %s"
                % self._detectorDistanceMax.__class__.__name__
            )
            raise BaseException(strMessage)
        if detectorDistanceMin is None:
            self._detectorDistanceMin = None
        elif detectorDistanceMin.__class__.__name__ == "XSDataLength":
            self._detectorDistanceMin = detectorDistanceMin
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'detectorDistanceMin' is not XSDataLength but %s"
                % self._detectorDistanceMin.__class__.__name__
            )
            raise BaseException(strMessage)
        if estimateRadiationDamage is None:
            self._estimateRadiationDamage = None
        elif estimateRadiationDamage.__class__.__name__ == "XSDataBoolean":
            self._estimateRadiationDamage = estimateRadiationDamage
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'estimateRadiationDamage' is not XSDataBoolean but %s"
                % self._estimateRadiationDamage.__class__.__name__
            )
            raise BaseException(strMessage)
        if forcedSpaceGroup is None:
            self._forcedSpaceGroup = None
        elif forcedSpaceGroup.__class__.__name__ == "XSDataString":
            self._forcedSpaceGroup = forcedSpaceGroup
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'forcedSpaceGroup' is not XSDataString but %s"
                % self._forcedSpaceGroup.__class__.__name__
            )
            raise BaseException(strMessage)
        if goniostatMaxOscillationSpeed is None:
            self._goniostatMaxOscillationSpeed = None
        elif goniostatMaxOscillationSpeed.__class__.__name__ == "XSDataAngularSpeed":
            self._goniostatMaxOscillationSpeed = goniostatMaxOscillationSpeed
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'goniostatMaxOscillationSpeed' is not XSDataAngularSpeed but %s"
                % self._goniostatMaxOscillationSpeed.__class__.__name__
            )
            raise BaseException(strMessage)
        if goniostatMinOscillationWidth is None:
            self._goniostatMinOscillationWidth = None
        elif goniostatMinOscillationWidth.__class__.__name__ == "XSDataAngle":
            self._goniostatMinOscillationWidth = goniostatMinOscillationWidth
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'goniostatMinOscillationWidth' is not XSDataAngle but %s"
                % self._goniostatMinOscillationWidth.__class__.__name__
            )
            raise BaseException(strMessage)
        if kappaStrategyOption is None:
            self._kappaStrategyOption = []
        elif kappaStrategyOption.__class__.__name__ == "list":
            self._kappaStrategyOption = kappaStrategyOption
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'kappaStrategyOption' is not list but %s"
                % self._kappaStrategyOption.__class__.__name__
            )
            raise BaseException(strMessage)
        if maxExposureTimePerDataCollection is None:
            self._maxExposureTimePerDataCollection = None
        elif maxExposureTimePerDataCollection.__class__.__name__ == "XSDataTime":
            self._maxExposureTimePerDataCollection = maxExposureTimePerDataCollection
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'maxExposureTimePerDataCollection' is not XSDataTime but %s"
                % self._maxExposureTimePerDataCollection.__class__.__name__
            )
            raise BaseException(strMessage)
        if minExposureTimePerImage is None:
            self._minExposureTimePerImage = None
        elif minExposureTimePerImage.__class__.__name__ == "XSDataTime":
            self._minExposureTimePerImage = minExposureTimePerImage
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'minExposureTimePerImage' is not XSDataTime but %s"
                % self._minExposureTimePerImage.__class__.__name__
            )
            raise BaseException(strMessage)
        if minTransmission is None:
            self._minTransmission = None
        elif minTransmission.__class__.__name__ == "XSDataDouble":
            self._minTransmission = minTransmission
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'minTransmission' is not XSDataDouble but %s"
                % self._minTransmission.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberOfPositions is None:
            self._numberOfPositions = None
        elif numberOfPositions.__class__.__name__ == "XSDataInteger":
            self._numberOfPositions = numberOfPositions
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'numberOfPositions' is not XSDataInteger but %s"
                % self._numberOfPositions.__class__.__name__
            )
            raise BaseException(strMessage)
        if requiredCompleteness is None:
            self._requiredCompleteness = None
        elif requiredCompleteness.__class__.__name__ == "XSDataDouble":
            self._requiredCompleteness = requiredCompleteness
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'requiredCompleteness' is not XSDataDouble but %s"
                % self._requiredCompleteness.__class__.__name__
            )
            raise BaseException(strMessage)
        if requiredMultiplicity is None:
            self._requiredMultiplicity = None
        elif requiredMultiplicity.__class__.__name__ == "XSDataDouble":
            self._requiredMultiplicity = requiredMultiplicity
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'requiredMultiplicity' is not XSDataDouble but %s"
                % self._requiredMultiplicity.__class__.__name__
            )
            raise BaseException(strMessage)
        if requiredResolution is None:
            self._requiredResolution = None
        elif requiredResolution.__class__.__name__ == "XSDataDouble":
            self._requiredResolution = requiredResolution
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'requiredResolution' is not XSDataDouble but %s"
                % self._requiredResolution.__class__.__name__
            )
            raise BaseException(strMessage)
        if strategyOption is None:
            self._strategyOption = None
        elif strategyOption.__class__.__name__ == "XSDataString":
            self._strategyOption = strategyOption
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'strategyOption' is not XSDataString but %s"
                % self._strategyOption.__class__.__name__
            )
            raise BaseException(strMessage)
        if userDefinedRotationRange is None:
            self._userDefinedRotationRange = None
        elif userDefinedRotationRange.__class__.__name__ == "XSDataAngle":
            self._userDefinedRotationRange = userDefinedRotationRange
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'userDefinedRotationRange' is not XSDataAngle but %s"
                % self._userDefinedRotationRange.__class__.__name__
            )
            raise BaseException(strMessage)
        if userDefinedRotationStart is None:
            self._userDefinedRotationStart = None
        elif userDefinedRotationStart.__class__.__name__ == "XSDataAngle":
            self._userDefinedRotationStart = userDefinedRotationStart
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan constructor argument 'userDefinedRotationStart' is not XSDataAngle but %s"
                % self._userDefinedRotationStart.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'aimedCompleteness' attribute
    def getAimedCompleteness(self):
        return self._aimedCompleteness

    def setAimedCompleteness(self, aimedCompleteness):
        if aimedCompleteness is None:
            self._aimedCompleteness = None
        elif aimedCompleteness.__class__.__name__ == "XSDataDouble":
            self._aimedCompleteness = aimedCompleteness
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setAimedCompleteness argument is not XSDataDouble but %s"
                % aimedCompleteness.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAimedCompleteness(self):
        self._aimedCompleteness = None

    aimedCompleteness = property(
        getAimedCompleteness,
        setAimedCompleteness,
        delAimedCompleteness,
        "Property for aimedCompleteness",
    )
    # Methods and properties for the 'aimedIOverSigmaAtHighestResolution' attribute

    def getAimedIOverSigmaAtHighestResolution(self):
        return self._aimedIOverSigmaAtHighestResolution

    def setAimedIOverSigmaAtHighestResolution(self, aimedIOverSigmaAtHighestResolution):
        if aimedIOverSigmaAtHighestResolution is None:
            self._aimedIOverSigmaAtHighestResolution = None
        elif aimedIOverSigmaAtHighestResolution.__class__.__name__ == "XSDataDouble":
            self._aimedIOverSigmaAtHighestResolution = (
                aimedIOverSigmaAtHighestResolution
            )
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setAimedIOverSigmaAtHighestResolution argument is not XSDataDouble but %s"
                % aimedIOverSigmaAtHighestResolution.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAimedIOverSigmaAtHighestResolution(self):
        self._aimedIOverSigmaAtHighestResolution = None

    aimedIOverSigmaAtHighestResolution = property(
        getAimedIOverSigmaAtHighestResolution,
        setAimedIOverSigmaAtHighestResolution,
        delAimedIOverSigmaAtHighestResolution,
        "Property for aimedIOverSigmaAtHighestResolution",
    )
    # Methods and properties for the 'aimedMultiplicity' attribute

    def getAimedMultiplicity(self):
        return self._aimedMultiplicity

    def setAimedMultiplicity(self, aimedMultiplicity):
        if aimedMultiplicity is None:
            self._aimedMultiplicity = None
        elif aimedMultiplicity.__class__.__name__ == "XSDataDouble":
            self._aimedMultiplicity = aimedMultiplicity
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setAimedMultiplicity argument is not XSDataDouble but %s"
                % aimedMultiplicity.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAimedMultiplicity(self):
        self._aimedMultiplicity = None

    aimedMultiplicity = property(
        getAimedMultiplicity,
        setAimedMultiplicity,
        delAimedMultiplicity,
        "Property for aimedMultiplicity",
    )
    # Methods and properties for the 'aimedResolution' attribute

    def getAimedResolution(self):
        return self._aimedResolution

    def setAimedResolution(self, aimedResolution):
        if aimedResolution is None:
            self._aimedResolution = None
        elif aimedResolution.__class__.__name__ == "XSDataDouble":
            self._aimedResolution = aimedResolution
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setAimedResolution argument is not XSDataDouble but %s"
                % aimedResolution.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAimedResolution(self):
        self._aimedResolution = None

    aimedResolution = property(
        getAimedResolution,
        setAimedResolution,
        delAimedResolution,
        "Property for aimedResolution",
    )
    # Methods and properties for the 'anomalousData' attribute

    def getAnomalousData(self):
        return self._anomalousData

    def setAnomalousData(self, anomalousData):
        if anomalousData is None:
            self._anomalousData = None
        elif anomalousData.__class__.__name__ == "XSDataBoolean":
            self._anomalousData = anomalousData
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setAnomalousData argument is not XSDataBoolean but %s"
                % anomalousData.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAnomalousData(self):
        self._anomalousData = None

    anomalousData = property(
        getAnomalousData,
        setAnomalousData,
        delAnomalousData,
        "Property for anomalousData",
    )
    # Methods and properties for the 'complexity' attribute

    def getComplexity(self):
        return self._complexity

    def setComplexity(self, complexity):
        if complexity is None:
            self._complexity = None
        elif complexity.__class__.__name__ == "XSDataString":
            self._complexity = complexity
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setComplexity argument is not XSDataString but %s"
                % complexity.__class__.__name__
            )
            raise BaseException(strMessage)

    def delComplexity(self):
        self._complexity = None

    complexity = property(
        getComplexity, setComplexity, delComplexity, "Property for complexity"
    )
    # Methods and properties for the 'detectorDistanceMax' attribute

    def getDetectorDistanceMax(self):
        return self._detectorDistanceMax

    def setDetectorDistanceMax(self, detectorDistanceMax):
        if detectorDistanceMax is None:
            self._detectorDistanceMax = None
        elif detectorDistanceMax.__class__.__name__ == "XSDataLength":
            self._detectorDistanceMax = detectorDistanceMax
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setDetectorDistanceMax argument is not XSDataLength but %s"
                % detectorDistanceMax.__class__.__name__
            )
            raise BaseException(strMessage)

    def delDetectorDistanceMax(self):
        self._detectorDistanceMax = None

    detectorDistanceMax = property(
        getDetectorDistanceMax,
        setDetectorDistanceMax,
        delDetectorDistanceMax,
        "Property for detectorDistanceMax",
    )
    # Methods and properties for the 'detectorDistanceMin' attribute

    def getDetectorDistanceMin(self):
        return self._detectorDistanceMin

    def setDetectorDistanceMin(self, detectorDistanceMin):
        if detectorDistanceMin is None:
            self._detectorDistanceMin = None
        elif detectorDistanceMin.__class__.__name__ == "XSDataLength":
            self._detectorDistanceMin = detectorDistanceMin
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setDetectorDistanceMin argument is not XSDataLength but %s"
                % detectorDistanceMin.__class__.__name__
            )
            raise BaseException(strMessage)

    def delDetectorDistanceMin(self):
        self._detectorDistanceMin = None

    detectorDistanceMin = property(
        getDetectorDistanceMin,
        setDetectorDistanceMin,
        delDetectorDistanceMin,
        "Property for detectorDistanceMin",
    )
    # Methods and properties for the 'estimateRadiationDamage' attribute

    def getEstimateRadiationDamage(self):
        return self._estimateRadiationDamage

    def setEstimateRadiationDamage(self, estimateRadiationDamage):
        if estimateRadiationDamage is None:
            self._estimateRadiationDamage = None
        elif estimateRadiationDamage.__class__.__name__ == "XSDataBoolean":
            self._estimateRadiationDamage = estimateRadiationDamage
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setEstimateRadiationDamage argument is not XSDataBoolean but %s"
                % estimateRadiationDamage.__class__.__name__
            )
            raise BaseException(strMessage)

    def delEstimateRadiationDamage(self):
        self._estimateRadiationDamage = None

    estimateRadiationDamage = property(
        getEstimateRadiationDamage,
        setEstimateRadiationDamage,
        delEstimateRadiationDamage,
        "Property for estimateRadiationDamage",
    )
    # Methods and properties for the 'forcedSpaceGroup' attribute

    def getForcedSpaceGroup(self):
        return self._forcedSpaceGroup

    def setForcedSpaceGroup(self, forcedSpaceGroup):
        if forcedSpaceGroup is None:
            self._forcedSpaceGroup = None
        elif forcedSpaceGroup.__class__.__name__ == "XSDataString":
            self._forcedSpaceGroup = forcedSpaceGroup
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setForcedSpaceGroup argument is not XSDataString but %s"
                % forcedSpaceGroup.__class__.__name__
            )
            raise BaseException(strMessage)

    def delForcedSpaceGroup(self):
        self._forcedSpaceGroup = None

    forcedSpaceGroup = property(
        getForcedSpaceGroup,
        setForcedSpaceGroup,
        delForcedSpaceGroup,
        "Property for forcedSpaceGroup",
    )
    # Methods and properties for the 'goniostatMaxOscillationSpeed' attribute

    def getGoniostatMaxOscillationSpeed(self):
        return self._goniostatMaxOscillationSpeed

    def setGoniostatMaxOscillationSpeed(self, goniostatMaxOscillationSpeed):
        if goniostatMaxOscillationSpeed is None:
            self._goniostatMaxOscillationSpeed = None
        elif goniostatMaxOscillationSpeed.__class__.__name__ == "XSDataAngularSpeed":
            self._goniostatMaxOscillationSpeed = goniostatMaxOscillationSpeed
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setGoniostatMaxOscillationSpeed argument is not XSDataAngularSpeed but %s"
                % goniostatMaxOscillationSpeed.__class__.__name__
            )
            raise BaseException(strMessage)

    def delGoniostatMaxOscillationSpeed(self):
        self._goniostatMaxOscillationSpeed = None

    goniostatMaxOscillationSpeed = property(
        getGoniostatMaxOscillationSpeed,
        setGoniostatMaxOscillationSpeed,
        delGoniostatMaxOscillationSpeed,
        "Property for goniostatMaxOscillationSpeed",
    )
    # Methods and properties for the 'goniostatMinOscillationWidth' attribute

    def getGoniostatMinOscillationWidth(self):
        return self._goniostatMinOscillationWidth

    def setGoniostatMinOscillationWidth(self, goniostatMinOscillationWidth):
        if goniostatMinOscillationWidth is None:
            self._goniostatMinOscillationWidth = None
        elif goniostatMinOscillationWidth.__class__.__name__ == "XSDataAngle":
            self._goniostatMinOscillationWidth = goniostatMinOscillationWidth
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setGoniostatMinOscillationWidth argument is not XSDataAngle but %s"
                % goniostatMinOscillationWidth.__class__.__name__
            )
            raise BaseException(strMessage)

    def delGoniostatMinOscillationWidth(self):
        self._goniostatMinOscillationWidth = None

    goniostatMinOscillationWidth = property(
        getGoniostatMinOscillationWidth,
        setGoniostatMinOscillationWidth,
        delGoniostatMinOscillationWidth,
        "Property for goniostatMinOscillationWidth",
    )
    # Methods and properties for the 'kappaStrategyOption' attribute

    def getKappaStrategyOption(self):
        return self._kappaStrategyOption

    def setKappaStrategyOption(self, kappaStrategyOption):
        if kappaStrategyOption is None:
            self._kappaStrategyOption = []
        elif kappaStrategyOption.__class__.__name__ == "list":
            self._kappaStrategyOption = kappaStrategyOption
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setKappaStrategyOption argument is not list but %s"
                % kappaStrategyOption.__class__.__name__
            )
            raise BaseException(strMessage)

    def delKappaStrategyOption(self):
        self._kappaStrategyOption = None

    kappaStrategyOption = property(
        getKappaStrategyOption,
        setKappaStrategyOption,
        delKappaStrategyOption,
        "Property for kappaStrategyOption",
    )

    def addKappaStrategyOption(self, value):
        if value is None:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.addKappaStrategyOption argument is None"
            )
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataString":
            self._kappaStrategyOption.append(value)
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.addKappaStrategyOption argument is not XSDataString but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertKappaStrategyOption(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataDiffractionPlan.insertKappaStrategyOption argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataDiffractionPlan.insertKappaStrategyOption argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataString":
            self._kappaStrategyOption[index] = value
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.addKappaStrategyOption argument is not XSDataString but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'maxExposureTimePerDataCollection' attribute
    def getMaxExposureTimePerDataCollection(self):
        return self._maxExposureTimePerDataCollection

    def setMaxExposureTimePerDataCollection(self, maxExposureTimePerDataCollection):
        if maxExposureTimePerDataCollection is None:
            self._maxExposureTimePerDataCollection = None
        elif maxExposureTimePerDataCollection.__class__.__name__ == "XSDataTime":
            self._maxExposureTimePerDataCollection = maxExposureTimePerDataCollection
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setMaxExposureTimePerDataCollection argument is not XSDataTime but %s"
                % maxExposureTimePerDataCollection.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMaxExposureTimePerDataCollection(self):
        self._maxExposureTimePerDataCollection = None

    maxExposureTimePerDataCollection = property(
        getMaxExposureTimePerDataCollection,
        setMaxExposureTimePerDataCollection,
        delMaxExposureTimePerDataCollection,
        "Property for maxExposureTimePerDataCollection",
    )
    # Methods and properties for the 'minExposureTimePerImage' attribute

    def getMinExposureTimePerImage(self):
        return self._minExposureTimePerImage

    def setMinExposureTimePerImage(self, minExposureTimePerImage):
        if minExposureTimePerImage is None:
            self._minExposureTimePerImage = None
        elif minExposureTimePerImage.__class__.__name__ == "XSDataTime":
            self._minExposureTimePerImage = minExposureTimePerImage
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setMinExposureTimePerImage argument is not XSDataTime but %s"
                % minExposureTimePerImage.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMinExposureTimePerImage(self):
        self._minExposureTimePerImage = None

    minExposureTimePerImage = property(
        getMinExposureTimePerImage,
        setMinExposureTimePerImage,
        delMinExposureTimePerImage,
        "Property for minExposureTimePerImage",
    )
    # Methods and properties for the 'minTransmission' attribute

    def getMinTransmission(self):
        return self._minTransmission

    def setMinTransmission(self, minTransmission):
        if minTransmission is None:
            self._minTransmission = None
        elif minTransmission.__class__.__name__ == "XSDataDouble":
            self._minTransmission = minTransmission
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setMinTransmission argument is not XSDataDouble but %s"
                % minTransmission.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMinTransmission(self):
        self._minTransmission = None

    minTransmission = property(
        getMinTransmission,
        setMinTransmission,
        delMinTransmission,
        "Property for minTransmission",
    )
    # Methods and properties for the 'numberOfPositions' attribute

    def getNumberOfPositions(self):
        return self._numberOfPositions

    def setNumberOfPositions(self, numberOfPositions):
        if numberOfPositions is None:
            self._numberOfPositions = None
        elif numberOfPositions.__class__.__name__ == "XSDataInteger":
            self._numberOfPositions = numberOfPositions
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setNumberOfPositions argument is not XSDataInteger but %s"
                % numberOfPositions.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberOfPositions(self):
        self._numberOfPositions = None

    numberOfPositions = property(
        getNumberOfPositions,
        setNumberOfPositions,
        delNumberOfPositions,
        "Property for numberOfPositions",
    )
    # Methods and properties for the 'requiredCompleteness' attribute

    def getRequiredCompleteness(self):
        return self._requiredCompleteness

    def setRequiredCompleteness(self, requiredCompleteness):
        if requiredCompleteness is None:
            self._requiredCompleteness = None
        elif requiredCompleteness.__class__.__name__ == "XSDataDouble":
            self._requiredCompleteness = requiredCompleteness
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setRequiredCompleteness argument is not XSDataDouble but %s"
                % requiredCompleteness.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRequiredCompleteness(self):
        self._requiredCompleteness = None

    requiredCompleteness = property(
        getRequiredCompleteness,
        setRequiredCompleteness,
        delRequiredCompleteness,
        "Property for requiredCompleteness",
    )
    # Methods and properties for the 'requiredMultiplicity' attribute

    def getRequiredMultiplicity(self):
        return self._requiredMultiplicity

    def setRequiredMultiplicity(self, requiredMultiplicity):
        if requiredMultiplicity is None:
            self._requiredMultiplicity = None
        elif requiredMultiplicity.__class__.__name__ == "XSDataDouble":
            self._requiredMultiplicity = requiredMultiplicity
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setRequiredMultiplicity argument is not XSDataDouble but %s"
                % requiredMultiplicity.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRequiredMultiplicity(self):
        self._requiredMultiplicity = None

    requiredMultiplicity = property(
        getRequiredMultiplicity,
        setRequiredMultiplicity,
        delRequiredMultiplicity,
        "Property for requiredMultiplicity",
    )
    # Methods and properties for the 'requiredResolution' attribute

    def getRequiredResolution(self):
        return self._requiredResolution

    def setRequiredResolution(self, requiredResolution):
        if requiredResolution is None:
            self._requiredResolution = None
        elif requiredResolution.__class__.__name__ == "XSDataDouble":
            self._requiredResolution = requiredResolution
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setRequiredResolution argument is not XSDataDouble but %s"
                % requiredResolution.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRequiredResolution(self):
        self._requiredResolution = None

    requiredResolution = property(
        getRequiredResolution,
        setRequiredResolution,
        delRequiredResolution,
        "Property for requiredResolution",
    )
    # Methods and properties for the 'strategyOption' attribute

    def getStrategyOption(self):
        return self._strategyOption

    def setStrategyOption(self, strategyOption):
        if strategyOption is None:
            self._strategyOption = None
        elif strategyOption.__class__.__name__ == "XSDataString":
            self._strategyOption = strategyOption
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setStrategyOption argument is not XSDataString but %s"
                % strategyOption.__class__.__name__
            )
            raise BaseException(strMessage)

    def delStrategyOption(self):
        self._strategyOption = None

    strategyOption = property(
        getStrategyOption,
        setStrategyOption,
        delStrategyOption,
        "Property for strategyOption",
    )
    # Methods and properties for the 'userDefinedRotationRange' attribute

    def getUserDefinedRotationRange(self):
        return self._userDefinedRotationRange

    def setUserDefinedRotationRange(self, userDefinedRotationRange):
        if userDefinedRotationRange is None:
            self._userDefinedRotationRange = None
        elif userDefinedRotationRange.__class__.__name__ == "XSDataAngle":
            self._userDefinedRotationRange = userDefinedRotationRange
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setUserDefinedRotationRange argument is not XSDataAngle but %s"
                % userDefinedRotationRange.__class__.__name__
            )
            raise BaseException(strMessage)

    def delUserDefinedRotationRange(self):
        self._userDefinedRotationRange = None

    userDefinedRotationRange = property(
        getUserDefinedRotationRange,
        setUserDefinedRotationRange,
        delUserDefinedRotationRange,
        "Property for userDefinedRotationRange",
    )
    # Methods and properties for the 'userDefinedRotationStart' attribute

    def getUserDefinedRotationStart(self):
        return self._userDefinedRotationStart

    def setUserDefinedRotationStart(self, userDefinedRotationStart):
        if userDefinedRotationStart is None:
            self._userDefinedRotationStart = None
        elif userDefinedRotationStart.__class__.__name__ == "XSDataAngle":
            self._userDefinedRotationStart = userDefinedRotationStart
        else:
            strMessage = (
                "ERROR! XSDataDiffractionPlan.setUserDefinedRotationStart argument is not XSDataAngle but %s"
                % userDefinedRotationStart.__class__.__name__
            )
            raise BaseException(strMessage)

    def delUserDefinedRotationStart(self):
        self._userDefinedRotationStart = None

    userDefinedRotationStart = property(
        getUserDefinedRotationStart,
        setUserDefinedRotationStart,
        delUserDefinedRotationStart,
        "Property for userDefinedRotationStart",
    )

    def export(self, outfile, level, name_="XSDataDiffractionPlan"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataDiffractionPlan"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._aimedCompleteness is not None:
            self.aimedCompleteness.export(outfile, level, name_="aimedCompleteness")
        if self._aimedIOverSigmaAtHighestResolution is not None:
            self.aimedIOverSigmaAtHighestResolution.export(
                outfile, level, name_="aimedIOverSigmaAtHighestResolution"
            )
        if self._aimedMultiplicity is not None:
            self.aimedMultiplicity.export(outfile, level, name_="aimedMultiplicity")
        if self._aimedResolution is not None:
            self.aimedResolution.export(outfile, level, name_="aimedResolution")
        if self._anomalousData is not None:
            self.anomalousData.export(outfile, level, name_="anomalousData")
        if self._complexity is not None:
            self.complexity.export(outfile, level, name_="complexity")
        if self._detectorDistanceMax is not None:
            self.detectorDistanceMax.export(outfile, level, name_="detectorDistanceMax")
        if self._detectorDistanceMin is not None:
            self.detectorDistanceMin.export(outfile, level, name_="detectorDistanceMin")
        if self._estimateRadiationDamage is not None:
            self.estimateRadiationDamage.export(
                outfile, level, name_="estimateRadiationDamage"
            )
        if self._forcedSpaceGroup is not None:
            self.forcedSpaceGroup.export(outfile, level, name_="forcedSpaceGroup")
        if self._goniostatMaxOscillationSpeed is not None:
            self.goniostatMaxOscillationSpeed.export(
                outfile, level, name_="goniostatMaxOscillationSpeed"
            )
        if self._goniostatMinOscillationWidth is not None:
            self.goniostatMinOscillationWidth.export(
                outfile, level, name_="goniostatMinOscillationWidth"
            )
        for kappaStrategyOption_ in self.getKappaStrategyOption():
            kappaStrategyOption_.export(outfile, level, name_="kappaStrategyOption")
        if self._maxExposureTimePerDataCollection is not None:
            self.maxExposureTimePerDataCollection.export(
                outfile, level, name_="maxExposureTimePerDataCollection"
            )
        if self._minExposureTimePerImage is not None:
            self.minExposureTimePerImage.export(
                outfile, level, name_="minExposureTimePerImage"
            )
        if self._minTransmission is not None:
            self.minTransmission.export(outfile, level, name_="minTransmission")
        if self._numberOfPositions is not None:
            self.numberOfPositions.export(outfile, level, name_="numberOfPositions")
        if self._requiredCompleteness is not None:
            self.requiredCompleteness.export(
                outfile, level, name_="requiredCompleteness"
            )
        if self._requiredMultiplicity is not None:
            self.requiredMultiplicity.export(
                outfile, level, name_="requiredMultiplicity"
            )
        if self._requiredResolution is not None:
            self.requiredResolution.export(outfile, level, name_="requiredResolution")
        if self._strategyOption is not None:
            self.strategyOption.export(outfile, level, name_="strategyOption")
        if self._userDefinedRotationRange is not None:
            self.userDefinedRotationRange.export(
                outfile, level, name_="userDefinedRotationRange"
            )
        if self._userDefinedRotationStart is not None:
            self.userDefinedRotationStart.export(
                outfile, level, name_="userDefinedRotationStart"
            )

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "aimedCompleteness":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setAimedCompleteness(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "aimedIOverSigmaAtHighestResolution"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setAimedIOverSigmaAtHighestResolution(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "aimedMultiplicity":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setAimedMultiplicity(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "aimedResolution":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setAimedResolution(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "anomalousData":
            obj_ = XSDataBoolean()
            obj_.build(child_)
            self.setAnomalousData(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "complexity":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setComplexity(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "detectorDistanceMax"
        ):
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setDetectorDistanceMax(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "detectorDistanceMin"
        ):
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setDetectorDistanceMin(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "estimateRadiationDamage"
        ):
            obj_ = XSDataBoolean()
            obj_.build(child_)
            self.setEstimateRadiationDamage(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "forcedSpaceGroup":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setForcedSpaceGroup(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "goniostatMaxOscillationSpeed"
        ):
            obj_ = XSDataAngularSpeed()
            obj_.build(child_)
            self.setGoniostatMaxOscillationSpeed(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "goniostatMinOscillationWidth"
        ):
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setGoniostatMinOscillationWidth(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "kappaStrategyOption"
        ):
            obj_ = XSDataString()
            obj_.build(child_)
            self.kappaStrategyOption.append(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "maxExposureTimePerDataCollection"
        ):
            obj_ = XSDataTime()
            obj_.build(child_)
            self.setMaxExposureTimePerDataCollection(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "minExposureTimePerImage"
        ):
            obj_ = XSDataTime()
            obj_.build(child_)
            self.setMinExposureTimePerImage(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "minTransmission":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setMinTransmission(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "numberOfPositions":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumberOfPositions(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "requiredCompleteness"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setRequiredCompleteness(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "requiredMultiplicity"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setRequiredMultiplicity(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "requiredResolution":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setRequiredResolution(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "strategyOption":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setStrategyOption(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "userDefinedRotationRange"
        ):
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setUserDefinedRotationRange(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "userDefinedRotationStart"
        ):
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setUserDefinedRotationStart(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataDiffractionPlan")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataDiffractionPlan")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataDiffractionPlan is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataDiffractionPlan.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataDiffractionPlan()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataDiffractionPlan")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataDiffractionPlan()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataDiffractionPlan


class XSDataGoniostat(XSData):
    """The properties of a goniostat:
- the maximal rotation speed permitted
- the minimal width for an oscillation width of subwedge
- the name of the rotation axis (typically phi)
- the rotation start angle
- the rotation end angle"""

    def __init__(
        self,
        samplePosition=None,
        rotationAxisStart=None,
        rotationAxisEnd=None,
        rotationAxis=None,
        overlap=None,
        oscillationWidth=None,
        minOscillationWidth=None,
        maxOscillationSpeed=None,
    ):
        XSData.__init__(self)
        if maxOscillationSpeed is None:
            self._maxOscillationSpeed = None
        elif maxOscillationSpeed.__class__.__name__ == "XSDataAngularSpeed":
            self._maxOscillationSpeed = maxOscillationSpeed
        else:
            strMessage = (
                "ERROR! XSDataGoniostat constructor argument 'maxOscillationSpeed' is not XSDataAngularSpeed but %s"
                % self._maxOscillationSpeed.__class__.__name__
            )
            raise BaseException(strMessage)
        if minOscillationWidth is None:
            self._minOscillationWidth = None
        elif minOscillationWidth.__class__.__name__ == "XSDataAngle":
            self._minOscillationWidth = minOscillationWidth
        else:
            strMessage = (
                "ERROR! XSDataGoniostat constructor argument 'minOscillationWidth' is not XSDataAngle but %s"
                % self._minOscillationWidth.__class__.__name__
            )
            raise BaseException(strMessage)
        if oscillationWidth is None:
            self._oscillationWidth = None
        elif oscillationWidth.__class__.__name__ == "XSDataAngle":
            self._oscillationWidth = oscillationWidth
        else:
            strMessage = (
                "ERROR! XSDataGoniostat constructor argument 'oscillationWidth' is not XSDataAngle but %s"
                % self._oscillationWidth.__class__.__name__
            )
            raise BaseException(strMessage)
        if overlap is None:
            self._overlap = None
        elif overlap.__class__.__name__ == "XSDataAngle":
            self._overlap = overlap
        else:
            strMessage = (
                "ERROR! XSDataGoniostat constructor argument 'overlap' is not XSDataAngle but %s"
                % self._overlap.__class__.__name__
            )
            raise BaseException(strMessage)
        if rotationAxis is None:
            self._rotationAxis = None
        elif rotationAxis.__class__.__name__ == "XSDataString":
            self._rotationAxis = rotationAxis
        else:
            strMessage = (
                "ERROR! XSDataGoniostat constructor argument 'rotationAxis' is not XSDataString but %s"
                % self._rotationAxis.__class__.__name__
            )
            raise BaseException(strMessage)
        if rotationAxisEnd is None:
            self._rotationAxisEnd = None
        elif rotationAxisEnd.__class__.__name__ == "XSDataAngle":
            self._rotationAxisEnd = rotationAxisEnd
        else:
            strMessage = (
                "ERROR! XSDataGoniostat constructor argument 'rotationAxisEnd' is not XSDataAngle but %s"
                % self._rotationAxisEnd.__class__.__name__
            )
            raise BaseException(strMessage)
        if rotationAxisStart is None:
            self._rotationAxisStart = None
        elif rotationAxisStart.__class__.__name__ == "XSDataAngle":
            self._rotationAxisStart = rotationAxisStart
        else:
            strMessage = (
                "ERROR! XSDataGoniostat constructor argument 'rotationAxisStart' is not XSDataAngle but %s"
                % self._rotationAxisStart.__class__.__name__
            )
            raise BaseException(strMessage)
        if samplePosition is None:
            self._samplePosition = None
        elif samplePosition.__class__.__name__ == "XSDataVectorDouble":
            self._samplePosition = samplePosition
        else:
            strMessage = (
                "ERROR! XSDataGoniostat constructor argument 'samplePosition' is not XSDataVectorDouble but %s"
                % self._samplePosition.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'maxOscillationSpeed' attribute
    def getMaxOscillationSpeed(self):
        return self._maxOscillationSpeed

    def setMaxOscillationSpeed(self, maxOscillationSpeed):
        if maxOscillationSpeed is None:
            self._maxOscillationSpeed = None
        elif maxOscillationSpeed.__class__.__name__ == "XSDataAngularSpeed":
            self._maxOscillationSpeed = maxOscillationSpeed
        else:
            strMessage = (
                "ERROR! XSDataGoniostat.setMaxOscillationSpeed argument is not XSDataAngularSpeed but %s"
                % maxOscillationSpeed.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMaxOscillationSpeed(self):
        self._maxOscillationSpeed = None

    maxOscillationSpeed = property(
        getMaxOscillationSpeed,
        setMaxOscillationSpeed,
        delMaxOscillationSpeed,
        "Property for maxOscillationSpeed",
    )
    # Methods and properties for the 'minOscillationWidth' attribute

    def getMinOscillationWidth(self):
        return self._minOscillationWidth

    def setMinOscillationWidth(self, minOscillationWidth):
        if minOscillationWidth is None:
            self._minOscillationWidth = None
        elif minOscillationWidth.__class__.__name__ == "XSDataAngle":
            self._minOscillationWidth = minOscillationWidth
        else:
            strMessage = (
                "ERROR! XSDataGoniostat.setMinOscillationWidth argument is not XSDataAngle but %s"
                % minOscillationWidth.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMinOscillationWidth(self):
        self._minOscillationWidth = None

    minOscillationWidth = property(
        getMinOscillationWidth,
        setMinOscillationWidth,
        delMinOscillationWidth,
        "Property for minOscillationWidth",
    )
    # Methods and properties for the 'oscillationWidth' attribute

    def getOscillationWidth(self):
        return self._oscillationWidth

    def setOscillationWidth(self, oscillationWidth):
        if oscillationWidth is None:
            self._oscillationWidth = None
        elif oscillationWidth.__class__.__name__ == "XSDataAngle":
            self._oscillationWidth = oscillationWidth
        else:
            strMessage = (
                "ERROR! XSDataGoniostat.setOscillationWidth argument is not XSDataAngle but %s"
                % oscillationWidth.__class__.__name__
            )
            raise BaseException(strMessage)

    def delOscillationWidth(self):
        self._oscillationWidth = None

    oscillationWidth = property(
        getOscillationWidth,
        setOscillationWidth,
        delOscillationWidth,
        "Property for oscillationWidth",
    )
    # Methods and properties for the 'overlap' attribute

    def getOverlap(self):
        return self._overlap

    def setOverlap(self, overlap):
        if overlap is None:
            self._overlap = None
        elif overlap.__class__.__name__ == "XSDataAngle":
            self._overlap = overlap
        else:
            strMessage = (
                "ERROR! XSDataGoniostat.setOverlap argument is not XSDataAngle but %s"
                % overlap.__class__.__name__
            )
            raise BaseException(strMessage)

    def delOverlap(self):
        self._overlap = None

    overlap = property(getOverlap, setOverlap, delOverlap, "Property for overlap")
    # Methods and properties for the 'rotationAxis' attribute

    def getRotationAxis(self):
        return self._rotationAxis

    def setRotationAxis(self, rotationAxis):
        if rotationAxis is None:
            self._rotationAxis = None
        elif rotationAxis.__class__.__name__ == "XSDataString":
            self._rotationAxis = rotationAxis
        else:
            strMessage = (
                "ERROR! XSDataGoniostat.setRotationAxis argument is not XSDataString but %s"
                % rotationAxis.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRotationAxis(self):
        self._rotationAxis = None

    rotationAxis = property(
        getRotationAxis, setRotationAxis, delRotationAxis, "Property for rotationAxis"
    )
    # Methods and properties for the 'rotationAxisEnd' attribute

    def getRotationAxisEnd(self):
        return self._rotationAxisEnd

    def setRotationAxisEnd(self, rotationAxisEnd):
        if rotationAxisEnd is None:
            self._rotationAxisEnd = None
        elif rotationAxisEnd.__class__.__name__ == "XSDataAngle":
            self._rotationAxisEnd = rotationAxisEnd
        else:
            strMessage = (
                "ERROR! XSDataGoniostat.setRotationAxisEnd argument is not XSDataAngle but %s"
                % rotationAxisEnd.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRotationAxisEnd(self):
        self._rotationAxisEnd = None

    rotationAxisEnd = property(
        getRotationAxisEnd,
        setRotationAxisEnd,
        delRotationAxisEnd,
        "Property for rotationAxisEnd",
    )
    # Methods and properties for the 'rotationAxisStart' attribute

    def getRotationAxisStart(self):
        return self._rotationAxisStart

    def setRotationAxisStart(self, rotationAxisStart):
        if rotationAxisStart is None:
            self._rotationAxisStart = None
        elif rotationAxisStart.__class__.__name__ == "XSDataAngle":
            self._rotationAxisStart = rotationAxisStart
        else:
            strMessage = (
                "ERROR! XSDataGoniostat.setRotationAxisStart argument is not XSDataAngle but %s"
                % rotationAxisStart.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRotationAxisStart(self):
        self._rotationAxisStart = None

    rotationAxisStart = property(
        getRotationAxisStart,
        setRotationAxisStart,
        delRotationAxisStart,
        "Property for rotationAxisStart",
    )
    # Methods and properties for the 'samplePosition' attribute

    def getSamplePosition(self):
        return self._samplePosition

    def setSamplePosition(self, samplePosition):
        if samplePosition is None:
            self._samplePosition = None
        elif samplePosition.__class__.__name__ == "XSDataVectorDouble":
            self._samplePosition = samplePosition
        else:
            strMessage = (
                "ERROR! XSDataGoniostat.setSamplePosition argument is not XSDataVectorDouble but %s"
                % samplePosition.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSamplePosition(self):
        self._samplePosition = None

    samplePosition = property(
        getSamplePosition,
        setSamplePosition,
        delSamplePosition,
        "Property for samplePosition",
    )

    def export(self, outfile, level, name_="XSDataGoniostat"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataGoniostat"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._maxOscillationSpeed is not None:
            self.maxOscillationSpeed.export(outfile, level, name_="maxOscillationSpeed")
        if self._minOscillationWidth is not None:
            self.minOscillationWidth.export(outfile, level, name_="minOscillationWidth")
        if self._oscillationWidth is not None:
            self.oscillationWidth.export(outfile, level, name_="oscillationWidth")
        else:
            warnEmptyAttribute("oscillationWidth", "XSDataAngle")
        if self._overlap is not None:
            self.overlap.export(outfile, level, name_="overlap")
        if self._rotationAxis is not None:
            self.rotationAxis.export(outfile, level, name_="rotationAxis")
        else:
            warnEmptyAttribute("rotationAxis", "XSDataString")
        if self._rotationAxisEnd is not None:
            self.rotationAxisEnd.export(outfile, level, name_="rotationAxisEnd")
        else:
            warnEmptyAttribute("rotationAxisEnd", "XSDataAngle")
        if self._rotationAxisStart is not None:
            self.rotationAxisStart.export(outfile, level, name_="rotationAxisStart")
        else:
            warnEmptyAttribute("rotationAxisStart", "XSDataAngle")
        if self._samplePosition is not None:
            self.samplePosition.export(outfile, level, name_="samplePosition")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "maxOscillationSpeed":
            obj_ = XSDataAngularSpeed()
            obj_.build(child_)
            self.setMaxOscillationSpeed(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "minOscillationWidth"
        ):
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setMinOscillationWidth(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "oscillationWidth":
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setOscillationWidth(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "overlap":
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setOverlap(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "rotationAxis":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setRotationAxis(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "rotationAxisEnd":
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setRotationAxisEnd(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "rotationAxisStart":
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setRotationAxisStart(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "samplePosition":
            obj_ = XSDataVectorDouble()
            obj_.build(child_)
            self.setSamplePosition(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataGoniostat")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataGoniostat")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataGoniostat is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataGoniostat.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataGoniostat()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataGoniostat")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataGoniostat()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataGoniostat


class XSDataExperimentalCondition(XSData):
    """This object encapsulates all the physical properties of an experiment instrumentation. i.e: Beam, detector, Goniostat."""

    def __init__(self, goniostat=None, detector=None, beam=None):
        XSData.__init__(self)
        if beam is None:
            self._beam = None
        elif beam.__class__.__name__ == "XSDataBeam":
            self._beam = beam
        else:
            strMessage = (
                "ERROR! XSDataExperimentalCondition constructor argument 'beam' is not XSDataBeam but %s"
                % self._beam.__class__.__name__
            )
            raise BaseException(strMessage)
        if detector is None:
            self._detector = None
        elif detector.__class__.__name__ == "XSDataDetector":
            self._detector = detector
        else:
            strMessage = (
                "ERROR! XSDataExperimentalCondition constructor argument 'detector' is not XSDataDetector but %s"
                % self._detector.__class__.__name__
            )
            raise BaseException(strMessage)
        if goniostat is None:
            self._goniostat = None
        elif goniostat.__class__.__name__ == "XSDataGoniostat":
            self._goniostat = goniostat
        else:
            strMessage = (
                "ERROR! XSDataExperimentalCondition constructor argument 'goniostat' is not XSDataGoniostat but %s"
                % self._goniostat.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'beam' attribute
    def getBeam(self):
        return self._beam

    def setBeam(self, beam):
        if beam is None:
            self._beam = None
        elif beam.__class__.__name__ == "XSDataBeam":
            self._beam = beam
        else:
            strMessage = (
                "ERROR! XSDataExperimentalCondition.setBeam argument is not XSDataBeam but %s"
                % beam.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBeam(self):
        self._beam = None

    beam = property(getBeam, setBeam, delBeam, "Property for beam")
    # Methods and properties for the 'detector' attribute

    def getDetector(self):
        return self._detector

    def setDetector(self, detector):
        if detector is None:
            self._detector = None
        elif detector.__class__.__name__ == "XSDataDetector":
            self._detector = detector
        else:
            strMessage = (
                "ERROR! XSDataExperimentalCondition.setDetector argument is not XSDataDetector but %s"
                % detector.__class__.__name__
            )
            raise BaseException(strMessage)

    def delDetector(self):
        self._detector = None

    detector = property(getDetector, setDetector, delDetector, "Property for detector")
    # Methods and properties for the 'goniostat' attribute

    def getGoniostat(self):
        return self._goniostat

    def setGoniostat(self, goniostat):
        if goniostat is None:
            self._goniostat = None
        elif goniostat.__class__.__name__ == "XSDataGoniostat":
            self._goniostat = goniostat
        else:
            strMessage = (
                "ERROR! XSDataExperimentalCondition.setGoniostat argument is not XSDataGoniostat but %s"
                % goniostat.__class__.__name__
            )
            raise BaseException(strMessage)

    def delGoniostat(self):
        self._goniostat = None

    goniostat = property(
        getGoniostat, setGoniostat, delGoniostat, "Property for goniostat"
    )

    def export(self, outfile, level, name_="XSDataExperimentalCondition"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataExperimentalCondition"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._beam is not None:
            self.beam.export(outfile, level, name_="beam")
        if self._detector is not None:
            self.detector.export(outfile, level, name_="detector")
        if self._goniostat is not None:
            self.goniostat.export(outfile, level, name_="goniostat")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "beam":
            obj_ = XSDataBeam()
            obj_.build(child_)
            self.setBeam(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "detector":
            obj_ = XSDataDetector()
            obj_.build(child_)
            self.setDetector(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "goniostat":
            obj_ = XSDataGoniostat()
            obj_.build(child_)
            self.setGoniostat(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataExperimentalCondition")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataExperimentalCondition")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataExperimentalCondition is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataExperimentalCondition.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataExperimentalCondition()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataExperimentalCondition")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataExperimentalCondition()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataExperimentalCondition


class XSDataImageQualityIndicators(XSData):
    def __init__(
        self,
        totalIntegratedSignal=None,
        spotTotal=None,
        signalRangeMin=None,
        signalRangeMax=None,
        signalRangeAverage=None,
        saturationRangeMin=None,
        saturationRangeMax=None,
        saturationRangeAverage=None,
        pctSaturationTop50Peaks=None,
        method2Res=None,
        method1Res=None,
        maxUnitCell=None,
        inResolutionOvrlSpots=None,
        inResTotal=None,
        image=None,
        iceRings=None,
        goodBraggCandidates=None,
        binPopCutOffMethod2Res=None,
    ):
        XSData.__init__(self)
        if binPopCutOffMethod2Res is None:
            self._binPopCutOffMethod2Res = None
        elif binPopCutOffMethod2Res.__class__.__name__ == "XSDataDouble":
            self._binPopCutOffMethod2Res = binPopCutOffMethod2Res
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'binPopCutOffMethod2Res' is not XSDataDouble but %s"
                % self._binPopCutOffMethod2Res.__class__.__name__
            )
            raise BaseException(strMessage)
        if goodBraggCandidates is None:
            self._goodBraggCandidates = None
        elif goodBraggCandidates.__class__.__name__ == "XSDataInteger":
            self._goodBraggCandidates = goodBraggCandidates
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'goodBraggCandidates' is not XSDataInteger but %s"
                % self._goodBraggCandidates.__class__.__name__
            )
            raise BaseException(strMessage)
        if iceRings is None:
            self._iceRings = None
        elif iceRings.__class__.__name__ == "XSDataInteger":
            self._iceRings = iceRings
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'iceRings' is not XSDataInteger but %s"
                % self._iceRings.__class__.__name__
            )
            raise BaseException(strMessage)
        if image is None:
            self._image = None
        elif image.__class__.__name__ == "XSDataImage":
            self._image = image
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'image' is not XSDataImage but %s"
                % self._image.__class__.__name__
            )
            raise BaseException(strMessage)
        if inResTotal is None:
            self._inResTotal = None
        elif inResTotal.__class__.__name__ == "XSDataInteger":
            self._inResTotal = inResTotal
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'inResTotal' is not XSDataInteger but %s"
                % self._inResTotal.__class__.__name__
            )
            raise BaseException(strMessage)
        if inResolutionOvrlSpots is None:
            self._inResolutionOvrlSpots = None
        elif inResolutionOvrlSpots.__class__.__name__ == "XSDataInteger":
            self._inResolutionOvrlSpots = inResolutionOvrlSpots
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'inResolutionOvrlSpots' is not XSDataInteger but %s"
                % self._inResolutionOvrlSpots.__class__.__name__
            )
            raise BaseException(strMessage)
        if maxUnitCell is None:
            self._maxUnitCell = None
        elif maxUnitCell.__class__.__name__ == "XSDataDouble":
            self._maxUnitCell = maxUnitCell
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'maxUnitCell' is not XSDataDouble but %s"
                % self._maxUnitCell.__class__.__name__
            )
            raise BaseException(strMessage)
        if method1Res is None:
            self._method1Res = None
        elif method1Res.__class__.__name__ == "XSDataDouble":
            self._method1Res = method1Res
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'method1Res' is not XSDataDouble but %s"
                % self._method1Res.__class__.__name__
            )
            raise BaseException(strMessage)
        if method2Res is None:
            self._method2Res = None
        elif method2Res.__class__.__name__ == "XSDataDouble":
            self._method2Res = method2Res
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'method2Res' is not XSDataDouble but %s"
                % self._method2Res.__class__.__name__
            )
            raise BaseException(strMessage)
        if pctSaturationTop50Peaks is None:
            self._pctSaturationTop50Peaks = None
        elif pctSaturationTop50Peaks.__class__.__name__ == "XSDataDouble":
            self._pctSaturationTop50Peaks = pctSaturationTop50Peaks
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'pctSaturationTop50Peaks' is not XSDataDouble but %s"
                % self._pctSaturationTop50Peaks.__class__.__name__
            )
            raise BaseException(strMessage)
        if saturationRangeAverage is None:
            self._saturationRangeAverage = None
        elif saturationRangeAverage.__class__.__name__ == "XSDataDouble":
            self._saturationRangeAverage = saturationRangeAverage
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'saturationRangeAverage' is not XSDataDouble but %s"
                % self._saturationRangeAverage.__class__.__name__
            )
            raise BaseException(strMessage)
        if saturationRangeMax is None:
            self._saturationRangeMax = None
        elif saturationRangeMax.__class__.__name__ == "XSDataDouble":
            self._saturationRangeMax = saturationRangeMax
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'saturationRangeMax' is not XSDataDouble but %s"
                % self._saturationRangeMax.__class__.__name__
            )
            raise BaseException(strMessage)
        if saturationRangeMin is None:
            self._saturationRangeMin = None
        elif saturationRangeMin.__class__.__name__ == "XSDataDouble":
            self._saturationRangeMin = saturationRangeMin
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'saturationRangeMin' is not XSDataDouble but %s"
                % self._saturationRangeMin.__class__.__name__
            )
            raise BaseException(strMessage)
        if signalRangeAverage is None:
            self._signalRangeAverage = None
        elif signalRangeAverage.__class__.__name__ == "XSDataDouble":
            self._signalRangeAverage = signalRangeAverage
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'signalRangeAverage' is not XSDataDouble but %s"
                % self._signalRangeAverage.__class__.__name__
            )
            raise BaseException(strMessage)
        if signalRangeMax is None:
            self._signalRangeMax = None
        elif signalRangeMax.__class__.__name__ == "XSDataDouble":
            self._signalRangeMax = signalRangeMax
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'signalRangeMax' is not XSDataDouble but %s"
                % self._signalRangeMax.__class__.__name__
            )
            raise BaseException(strMessage)
        if signalRangeMin is None:
            self._signalRangeMin = None
        elif signalRangeMin.__class__.__name__ == "XSDataDouble":
            self._signalRangeMin = signalRangeMin
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'signalRangeMin' is not XSDataDouble but %s"
                % self._signalRangeMin.__class__.__name__
            )
            raise BaseException(strMessage)
        if spotTotal is None:
            self._spotTotal = None
        elif spotTotal.__class__.__name__ == "XSDataInteger":
            self._spotTotal = spotTotal
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'spotTotal' is not XSDataInteger but %s"
                % self._spotTotal.__class__.__name__
            )
            raise BaseException(strMessage)
        if totalIntegratedSignal is None:
            self._totalIntegratedSignal = None
        elif totalIntegratedSignal.__class__.__name__ == "XSDataDouble":
            self._totalIntegratedSignal = totalIntegratedSignal
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators constructor argument 'totalIntegratedSignal' is not XSDataDouble but %s"
                % self._totalIntegratedSignal.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'binPopCutOffMethod2Res' attribute
    def getBinPopCutOffMethod2Res(self):
        return self._binPopCutOffMethod2Res

    def setBinPopCutOffMethod2Res(self, binPopCutOffMethod2Res):
        if binPopCutOffMethod2Res is None:
            self._binPopCutOffMethod2Res = None
        elif binPopCutOffMethod2Res.__class__.__name__ == "XSDataDouble":
            self._binPopCutOffMethod2Res = binPopCutOffMethod2Res
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setBinPopCutOffMethod2Res argument is not XSDataDouble but %s"
                % binPopCutOffMethod2Res.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBinPopCutOffMethod2Res(self):
        self._binPopCutOffMethod2Res = None

    binPopCutOffMethod2Res = property(
        getBinPopCutOffMethod2Res,
        setBinPopCutOffMethod2Res,
        delBinPopCutOffMethod2Res,
        "Property for binPopCutOffMethod2Res",
    )
    # Methods and properties for the 'goodBraggCandidates' attribute

    def getGoodBraggCandidates(self):
        return self._goodBraggCandidates

    def setGoodBraggCandidates(self, goodBraggCandidates):
        if goodBraggCandidates is None:
            self._goodBraggCandidates = None
        elif goodBraggCandidates.__class__.__name__ == "XSDataInteger":
            self._goodBraggCandidates = goodBraggCandidates
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setGoodBraggCandidates argument is not XSDataInteger but %s"
                % goodBraggCandidates.__class__.__name__
            )
            raise BaseException(strMessage)

    def delGoodBraggCandidates(self):
        self._goodBraggCandidates = None

    goodBraggCandidates = property(
        getGoodBraggCandidates,
        setGoodBraggCandidates,
        delGoodBraggCandidates,
        "Property for goodBraggCandidates",
    )
    # Methods and properties for the 'iceRings' attribute

    def getIceRings(self):
        return self._iceRings

    def setIceRings(self, iceRings):
        if iceRings is None:
            self._iceRings = None
        elif iceRings.__class__.__name__ == "XSDataInteger":
            self._iceRings = iceRings
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setIceRings argument is not XSDataInteger but %s"
                % iceRings.__class__.__name__
            )
            raise BaseException(strMessage)

    def delIceRings(self):
        self._iceRings = None

    iceRings = property(getIceRings, setIceRings, delIceRings, "Property for iceRings")
    # Methods and properties for the 'image' attribute

    def getImage(self):
        return self._image

    def setImage(self, image):
        if image is None:
            self._image = None
        elif image.__class__.__name__ == "XSDataImage":
            self._image = image
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setImage argument is not XSDataImage but %s"
                % image.__class__.__name__
            )
            raise BaseException(strMessage)

    def delImage(self):
        self._image = None

    image = property(getImage, setImage, delImage, "Property for image")
    # Methods and properties for the 'inResTotal' attribute

    def getInResTotal(self):
        return self._inResTotal

    def setInResTotal(self, inResTotal):
        if inResTotal is None:
            self._inResTotal = None
        elif inResTotal.__class__.__name__ == "XSDataInteger":
            self._inResTotal = inResTotal
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setInResTotal argument is not XSDataInteger but %s"
                % inResTotal.__class__.__name__
            )
            raise BaseException(strMessage)

    def delInResTotal(self):
        self._inResTotal = None

    inResTotal = property(
        getInResTotal, setInResTotal, delInResTotal, "Property for inResTotal"
    )
    # Methods and properties for the 'inResolutionOvrlSpots' attribute

    def getInResolutionOvrlSpots(self):
        return self._inResolutionOvrlSpots

    def setInResolutionOvrlSpots(self, inResolutionOvrlSpots):
        if inResolutionOvrlSpots is None:
            self._inResolutionOvrlSpots = None
        elif inResolutionOvrlSpots.__class__.__name__ == "XSDataInteger":
            self._inResolutionOvrlSpots = inResolutionOvrlSpots
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setInResolutionOvrlSpots argument is not XSDataInteger but %s"
                % inResolutionOvrlSpots.__class__.__name__
            )
            raise BaseException(strMessage)

    def delInResolutionOvrlSpots(self):
        self._inResolutionOvrlSpots = None

    inResolutionOvrlSpots = property(
        getInResolutionOvrlSpots,
        setInResolutionOvrlSpots,
        delInResolutionOvrlSpots,
        "Property for inResolutionOvrlSpots",
    )
    # Methods and properties for the 'maxUnitCell' attribute

    def getMaxUnitCell(self):
        return self._maxUnitCell

    def setMaxUnitCell(self, maxUnitCell):
        if maxUnitCell is None:
            self._maxUnitCell = None
        elif maxUnitCell.__class__.__name__ == "XSDataDouble":
            self._maxUnitCell = maxUnitCell
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setMaxUnitCell argument is not XSDataDouble but %s"
                % maxUnitCell.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMaxUnitCell(self):
        self._maxUnitCell = None

    maxUnitCell = property(
        getMaxUnitCell, setMaxUnitCell, delMaxUnitCell, "Property for maxUnitCell"
    )
    # Methods and properties for the 'method1Res' attribute

    def getMethod1Res(self):
        return self._method1Res

    def setMethod1Res(self, method1Res):
        if method1Res is None:
            self._method1Res = None
        elif method1Res.__class__.__name__ == "XSDataDouble":
            self._method1Res = method1Res
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setMethod1Res argument is not XSDataDouble but %s"
                % method1Res.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMethod1Res(self):
        self._method1Res = None

    method1Res = property(
        getMethod1Res, setMethod1Res, delMethod1Res, "Property for method1Res"
    )
    # Methods and properties for the 'method2Res' attribute

    def getMethod2Res(self):
        return self._method2Res

    def setMethod2Res(self, method2Res):
        if method2Res is None:
            self._method2Res = None
        elif method2Res.__class__.__name__ == "XSDataDouble":
            self._method2Res = method2Res
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setMethod2Res argument is not XSDataDouble but %s"
                % method2Res.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMethod2Res(self):
        self._method2Res = None

    method2Res = property(
        getMethod2Res, setMethod2Res, delMethod2Res, "Property for method2Res"
    )
    # Methods and properties for the 'pctSaturationTop50Peaks' attribute

    def getPctSaturationTop50Peaks(self):
        return self._pctSaturationTop50Peaks

    def setPctSaturationTop50Peaks(self, pctSaturationTop50Peaks):
        if pctSaturationTop50Peaks is None:
            self._pctSaturationTop50Peaks = None
        elif pctSaturationTop50Peaks.__class__.__name__ == "XSDataDouble":
            self._pctSaturationTop50Peaks = pctSaturationTop50Peaks
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setPctSaturationTop50Peaks argument is not XSDataDouble but %s"
                % pctSaturationTop50Peaks.__class__.__name__
            )
            raise BaseException(strMessage)

    def delPctSaturationTop50Peaks(self):
        self._pctSaturationTop50Peaks = None

    pctSaturationTop50Peaks = property(
        getPctSaturationTop50Peaks,
        setPctSaturationTop50Peaks,
        delPctSaturationTop50Peaks,
        "Property for pctSaturationTop50Peaks",
    )
    # Methods and properties for the 'saturationRangeAverage' attribute

    def getSaturationRangeAverage(self):
        return self._saturationRangeAverage

    def setSaturationRangeAverage(self, saturationRangeAverage):
        if saturationRangeAverage is None:
            self._saturationRangeAverage = None
        elif saturationRangeAverage.__class__.__name__ == "XSDataDouble":
            self._saturationRangeAverage = saturationRangeAverage
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setSaturationRangeAverage argument is not XSDataDouble but %s"
                % saturationRangeAverage.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSaturationRangeAverage(self):
        self._saturationRangeAverage = None

    saturationRangeAverage = property(
        getSaturationRangeAverage,
        setSaturationRangeAverage,
        delSaturationRangeAverage,
        "Property for saturationRangeAverage",
    )
    # Methods and properties for the 'saturationRangeMax' attribute

    def getSaturationRangeMax(self):
        return self._saturationRangeMax

    def setSaturationRangeMax(self, saturationRangeMax):
        if saturationRangeMax is None:
            self._saturationRangeMax = None
        elif saturationRangeMax.__class__.__name__ == "XSDataDouble":
            self._saturationRangeMax = saturationRangeMax
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setSaturationRangeMax argument is not XSDataDouble but %s"
                % saturationRangeMax.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSaturationRangeMax(self):
        self._saturationRangeMax = None

    saturationRangeMax = property(
        getSaturationRangeMax,
        setSaturationRangeMax,
        delSaturationRangeMax,
        "Property for saturationRangeMax",
    )
    # Methods and properties for the 'saturationRangeMin' attribute

    def getSaturationRangeMin(self):
        return self._saturationRangeMin

    def setSaturationRangeMin(self, saturationRangeMin):
        if saturationRangeMin is None:
            self._saturationRangeMin = None
        elif saturationRangeMin.__class__.__name__ == "XSDataDouble":
            self._saturationRangeMin = saturationRangeMin
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setSaturationRangeMin argument is not XSDataDouble but %s"
                % saturationRangeMin.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSaturationRangeMin(self):
        self._saturationRangeMin = None

    saturationRangeMin = property(
        getSaturationRangeMin,
        setSaturationRangeMin,
        delSaturationRangeMin,
        "Property for saturationRangeMin",
    )
    # Methods and properties for the 'signalRangeAverage' attribute

    def getSignalRangeAverage(self):
        return self._signalRangeAverage

    def setSignalRangeAverage(self, signalRangeAverage):
        if signalRangeAverage is None:
            self._signalRangeAverage = None
        elif signalRangeAverage.__class__.__name__ == "XSDataDouble":
            self._signalRangeAverage = signalRangeAverage
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setSignalRangeAverage argument is not XSDataDouble but %s"
                % signalRangeAverage.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSignalRangeAverage(self):
        self._signalRangeAverage = None

    signalRangeAverage = property(
        getSignalRangeAverage,
        setSignalRangeAverage,
        delSignalRangeAverage,
        "Property for signalRangeAverage",
    )
    # Methods and properties for the 'signalRangeMax' attribute

    def getSignalRangeMax(self):
        return self._signalRangeMax

    def setSignalRangeMax(self, signalRangeMax):
        if signalRangeMax is None:
            self._signalRangeMax = None
        elif signalRangeMax.__class__.__name__ == "XSDataDouble":
            self._signalRangeMax = signalRangeMax
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setSignalRangeMax argument is not XSDataDouble but %s"
                % signalRangeMax.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSignalRangeMax(self):
        self._signalRangeMax = None

    signalRangeMax = property(
        getSignalRangeMax,
        setSignalRangeMax,
        delSignalRangeMax,
        "Property for signalRangeMax",
    )
    # Methods and properties for the 'signalRangeMin' attribute

    def getSignalRangeMin(self):
        return self._signalRangeMin

    def setSignalRangeMin(self, signalRangeMin):
        if signalRangeMin is None:
            self._signalRangeMin = None
        elif signalRangeMin.__class__.__name__ == "XSDataDouble":
            self._signalRangeMin = signalRangeMin
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setSignalRangeMin argument is not XSDataDouble but %s"
                % signalRangeMin.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSignalRangeMin(self):
        self._signalRangeMin = None

    signalRangeMin = property(
        getSignalRangeMin,
        setSignalRangeMin,
        delSignalRangeMin,
        "Property for signalRangeMin",
    )
    # Methods and properties for the 'spotTotal' attribute

    def getSpotTotal(self):
        return self._spotTotal

    def setSpotTotal(self, spotTotal):
        if spotTotal is None:
            self._spotTotal = None
        elif spotTotal.__class__.__name__ == "XSDataInteger":
            self._spotTotal = spotTotal
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setSpotTotal argument is not XSDataInteger but %s"
                % spotTotal.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSpotTotal(self):
        self._spotTotal = None

    spotTotal = property(
        getSpotTotal, setSpotTotal, delSpotTotal, "Property for spotTotal"
    )
    # Methods and properties for the 'totalIntegratedSignal' attribute

    def getTotalIntegratedSignal(self):
        return self._totalIntegratedSignal

    def setTotalIntegratedSignal(self, totalIntegratedSignal):
        if totalIntegratedSignal is None:
            self._totalIntegratedSignal = None
        elif totalIntegratedSignal.__class__.__name__ == "XSDataDouble":
            self._totalIntegratedSignal = totalIntegratedSignal
        else:
            strMessage = (
                "ERROR! XSDataImageQualityIndicators.setTotalIntegratedSignal argument is not XSDataDouble but %s"
                % totalIntegratedSignal.__class__.__name__
            )
            raise BaseException(strMessage)

    def delTotalIntegratedSignal(self):
        self._totalIntegratedSignal = None

    totalIntegratedSignal = property(
        getTotalIntegratedSignal,
        setTotalIntegratedSignal,
        delTotalIntegratedSignal,
        "Property for totalIntegratedSignal",
    )

    def export(self, outfile, level, name_="XSDataImageQualityIndicators"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataImageQualityIndicators"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._binPopCutOffMethod2Res is not None:
            self.binPopCutOffMethod2Res.export(
                outfile, level, name_="binPopCutOffMethod2Res"
            )
        else:
            warnEmptyAttribute("binPopCutOffMethod2Res", "XSDataDouble")
        if self._goodBraggCandidates is not None:
            self.goodBraggCandidates.export(outfile, level, name_="goodBraggCandidates")
        else:
            warnEmptyAttribute("goodBraggCandidates", "XSDataInteger")
        if self._iceRings is not None:
            self.iceRings.export(outfile, level, name_="iceRings")
        else:
            warnEmptyAttribute("iceRings", "XSDataInteger")
        if self._image is not None:
            self.image.export(outfile, level, name_="image")
        else:
            warnEmptyAttribute("image", "XSDataImage")
        if self._inResTotal is not None:
            self.inResTotal.export(outfile, level, name_="inResTotal")
        else:
            warnEmptyAttribute("inResTotal", "XSDataInteger")
        if self._inResolutionOvrlSpots is not None:
            self.inResolutionOvrlSpots.export(
                outfile, level, name_="inResolutionOvrlSpots"
            )
        else:
            warnEmptyAttribute("inResolutionOvrlSpots", "XSDataInteger")
        if self._maxUnitCell is not None:
            self.maxUnitCell.export(outfile, level, name_="maxUnitCell")
        if self._method1Res is not None:
            self.method1Res.export(outfile, level, name_="method1Res")
        else:
            warnEmptyAttribute("method1Res", "XSDataDouble")
        if self._method2Res is not None:
            self.method2Res.export(outfile, level, name_="method2Res")
        if self._pctSaturationTop50Peaks is not None:
            self.pctSaturationTop50Peaks.export(
                outfile, level, name_="pctSaturationTop50Peaks"
            )
        if self._saturationRangeAverage is not None:
            self.saturationRangeAverage.export(
                outfile, level, name_="saturationRangeAverage"
            )
        if self._saturationRangeMax is not None:
            self.saturationRangeMax.export(outfile, level, name_="saturationRangeMax")
        if self._saturationRangeMin is not None:
            self.saturationRangeMin.export(outfile, level, name_="saturationRangeMin")
        if self._signalRangeAverage is not None:
            self.signalRangeAverage.export(outfile, level, name_="signalRangeAverage")
        if self._signalRangeMax is not None:
            self.signalRangeMax.export(outfile, level, name_="signalRangeMax")
        if self._signalRangeMin is not None:
            self.signalRangeMin.export(outfile, level, name_="signalRangeMin")
        if self._spotTotal is not None:
            self.spotTotal.export(outfile, level, name_="spotTotal")
        else:
            warnEmptyAttribute("spotTotal", "XSDataInteger")
        if self._totalIntegratedSignal is not None:
            self.totalIntegratedSignal.export(
                outfile, level, name_="totalIntegratedSignal"
            )

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "binPopCutOffMethod2Res"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setBinPopCutOffMethod2Res(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "goodBraggCandidates"
        ):
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setGoodBraggCandidates(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "iceRings":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setIceRings(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "image":
            obj_ = XSDataImage()
            obj_.build(child_)
            self.setImage(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "inResTotal":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setInResTotal(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "inResolutionOvrlSpots"
        ):
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setInResolutionOvrlSpots(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "maxUnitCell":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setMaxUnitCell(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "method1Res":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setMethod1Res(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "method2Res":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setMethod2Res(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "pctSaturationTop50Peaks"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setPctSaturationTop50Peaks(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "saturationRangeAverage"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setSaturationRangeAverage(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "saturationRangeMax":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setSaturationRangeMax(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "saturationRangeMin":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setSaturationRangeMin(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "signalRangeAverage":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setSignalRangeAverage(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "signalRangeMax":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setSignalRangeMax(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "signalRangeMin":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setSignalRangeMin(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "spotTotal":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setSpotTotal(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "totalIntegratedSignal"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setTotalIntegratedSignal(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataImageQualityIndicators")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataImageQualityIndicators")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataImageQualityIndicators is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataImageQualityIndicators.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataImageQualityIndicators()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataImageQualityIndicators")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataImageQualityIndicators()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataImageQualityIndicators


class XSDataIndexingSolution(XSData):
    def __init__(self, penalty=None, number=None, crystal=None):
        XSData.__init__(self)
        if crystal is None:
            self._crystal = None
        elif crystal.__class__.__name__ == "XSDataCrystal":
            self._crystal = crystal
        else:
            strMessage = (
                "ERROR! XSDataIndexingSolution constructor argument 'crystal' is not XSDataCrystal but %s"
                % self._crystal.__class__.__name__
            )
            raise BaseException(strMessage)
        if number is None:
            self._number = None
        elif number.__class__.__name__ == "XSDataInteger":
            self._number = number
        else:
            strMessage = (
                "ERROR! XSDataIndexingSolution constructor argument 'number' is not XSDataInteger but %s"
                % self._number.__class__.__name__
            )
            raise BaseException(strMessage)
        if penalty is None:
            self._penalty = None
        elif penalty.__class__.__name__ == "XSDataFloat":
            self._penalty = penalty
        else:
            strMessage = (
                "ERROR! XSDataIndexingSolution constructor argument 'penalty' is not XSDataFloat but %s"
                % self._penalty.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'crystal' attribute
    def getCrystal(self):
        return self._crystal

    def setCrystal(self, crystal):
        if crystal is None:
            self._crystal = None
        elif crystal.__class__.__name__ == "XSDataCrystal":
            self._crystal = crystal
        else:
            strMessage = (
                "ERROR! XSDataIndexingSolution.setCrystal argument is not XSDataCrystal but %s"
                % crystal.__class__.__name__
            )
            raise BaseException(strMessage)

    def delCrystal(self):
        self._crystal = None

    crystal = property(getCrystal, setCrystal, delCrystal, "Property for crystal")
    # Methods and properties for the 'number' attribute

    def getNumber(self):
        return self._number

    def setNumber(self, number):
        if number is None:
            self._number = None
        elif number.__class__.__name__ == "XSDataInteger":
            self._number = number
        else:
            strMessage = (
                "ERROR! XSDataIndexingSolution.setNumber argument is not XSDataInteger but %s"
                % number.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumber(self):
        self._number = None

    number = property(getNumber, setNumber, delNumber, "Property for number")
    # Methods and properties for the 'penalty' attribute

    def getPenalty(self):
        return self._penalty

    def setPenalty(self, penalty):
        if penalty is None:
            self._penalty = None
        elif penalty.__class__.__name__ == "XSDataFloat":
            self._penalty = penalty
        else:
            strMessage = (
                "ERROR! XSDataIndexingSolution.setPenalty argument is not XSDataFloat but %s"
                % penalty.__class__.__name__
            )
            raise BaseException(strMessage)

    def delPenalty(self):
        self._penalty = None

    penalty = property(getPenalty, setPenalty, delPenalty, "Property for penalty")

    def export(self, outfile, level, name_="XSDataIndexingSolution"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataIndexingSolution"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._crystal is not None:
            self.crystal.export(outfile, level, name_="crystal")
        else:
            warnEmptyAttribute("crystal", "XSDataCrystal")
        if self._number is not None:
            self.number.export(outfile, level, name_="number")
        else:
            warnEmptyAttribute("number", "XSDataInteger")
        if self._penalty is not None:
            self.penalty.export(outfile, level, name_="penalty")
        else:
            warnEmptyAttribute("penalty", "XSDataFloat")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "crystal":
            obj_ = XSDataCrystal()
            obj_.build(child_)
            self.setCrystal(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "number":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumber(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "penalty":
            obj_ = XSDataFloat()
            obj_.build(child_)
            self.setPenalty(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataIndexingSolution")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataIndexingSolution")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataIndexingSolution is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataIndexingSolution.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataIndexingSolution()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataIndexingSolution")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataIndexingSolution()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataIndexingSolution


class XSDataIntegrationSubWedgeResult(XSData):
    def __init__(
        self,
        subWedgeNumber=None,
        statisticsPerResolutionBin=None,
        statistics=None,
        integrationLogFile=None,
        generatedMTZFile=None,
        experimentalConditionRefined=None,
        bestfilePar=None,
        bestfileHKL=None,
        bestfileDat=None,
    ):
        XSData.__init__(self)
        if bestfileDat is None:
            self._bestfileDat = None
        elif bestfileDat.__class__.__name__ == "XSDataString":
            self._bestfileDat = bestfileDat
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult constructor argument 'bestfileDat' is not XSDataString but %s"
                % self._bestfileDat.__class__.__name__
            )
            raise BaseException(strMessage)
        if bestfileHKL is None:
            self._bestfileHKL = None
        elif bestfileHKL.__class__.__name__ == "XSDataString":
            self._bestfileHKL = bestfileHKL
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult constructor argument 'bestfileHKL' is not XSDataString but %s"
                % self._bestfileHKL.__class__.__name__
            )
            raise BaseException(strMessage)
        if bestfilePar is None:
            self._bestfilePar = None
        elif bestfilePar.__class__.__name__ == "XSDataString":
            self._bestfilePar = bestfilePar
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult constructor argument 'bestfilePar' is not XSDataString but %s"
                % self._bestfilePar.__class__.__name__
            )
            raise BaseException(strMessage)
        if experimentalConditionRefined is None:
            self._experimentalConditionRefined = None
        elif (
            experimentalConditionRefined.__class__.__name__
            == "XSDataExperimentalCondition"
        ):
            self._experimentalConditionRefined = experimentalConditionRefined
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult constructor argument 'experimentalConditionRefined' is not XSDataExperimentalCondition but %s"
                % self._experimentalConditionRefined.__class__.__name__
            )
            raise BaseException(strMessage)
        if generatedMTZFile is None:
            self._generatedMTZFile = None
        elif generatedMTZFile.__class__.__name__ == "XSDataFile":
            self._generatedMTZFile = generatedMTZFile
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult constructor argument 'generatedMTZFile' is not XSDataFile but %s"
                % self._generatedMTZFile.__class__.__name__
            )
            raise BaseException(strMessage)
        if integrationLogFile is None:
            self._integrationLogFile = None
        elif integrationLogFile.__class__.__name__ == "XSDataFile":
            self._integrationLogFile = integrationLogFile
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult constructor argument 'integrationLogFile' is not XSDataFile but %s"
                % self._integrationLogFile.__class__.__name__
            )
            raise BaseException(strMessage)
        if statistics is None:
            self._statistics = None
        elif statistics.__class__.__name__ == "XSDataStatisticsIntegration":
            self._statistics = statistics
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult constructor argument 'statistics' is not XSDataStatisticsIntegration but %s"
                % self._statistics.__class__.__name__
            )
            raise BaseException(strMessage)
        if statisticsPerResolutionBin is None:
            self._statisticsPerResolutionBin = []
        elif statisticsPerResolutionBin.__class__.__name__ == "list":
            self._statisticsPerResolutionBin = statisticsPerResolutionBin
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult constructor argument 'statisticsPerResolutionBin' is not list but %s"
                % self._statisticsPerResolutionBin.__class__.__name__
            )
            raise BaseException(strMessage)
        if subWedgeNumber is None:
            self._subWedgeNumber = None
        elif subWedgeNumber.__class__.__name__ == "XSDataInteger":
            self._subWedgeNumber = subWedgeNumber
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult constructor argument 'subWedgeNumber' is not XSDataInteger but %s"
                % self._subWedgeNumber.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'bestfileDat' attribute
    def getBestfileDat(self):
        return self._bestfileDat

    def setBestfileDat(self, bestfileDat):
        if bestfileDat is None:
            self._bestfileDat = None
        elif bestfileDat.__class__.__name__ == "XSDataString":
            self._bestfileDat = bestfileDat
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult.setBestfileDat argument is not XSDataString but %s"
                % bestfileDat.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBestfileDat(self):
        self._bestfileDat = None

    bestfileDat = property(
        getBestfileDat, setBestfileDat, delBestfileDat, "Property for bestfileDat"
    )
    # Methods and properties for the 'bestfileHKL' attribute

    def getBestfileHKL(self):
        return self._bestfileHKL

    def setBestfileHKL(self, bestfileHKL):
        if bestfileHKL is None:
            self._bestfileHKL = None
        elif bestfileHKL.__class__.__name__ == "XSDataString":
            self._bestfileHKL = bestfileHKL
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult.setBestfileHKL argument is not XSDataString but %s"
                % bestfileHKL.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBestfileHKL(self):
        self._bestfileHKL = None

    bestfileHKL = property(
        getBestfileHKL, setBestfileHKL, delBestfileHKL, "Property for bestfileHKL"
    )
    # Methods and properties for the 'bestfilePar' attribute

    def getBestfilePar(self):
        return self._bestfilePar

    def setBestfilePar(self, bestfilePar):
        if bestfilePar is None:
            self._bestfilePar = None
        elif bestfilePar.__class__.__name__ == "XSDataString":
            self._bestfilePar = bestfilePar
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult.setBestfilePar argument is not XSDataString but %s"
                % bestfilePar.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBestfilePar(self):
        self._bestfilePar = None

    bestfilePar = property(
        getBestfilePar, setBestfilePar, delBestfilePar, "Property for bestfilePar"
    )
    # Methods and properties for the 'experimentalConditionRefined' attribute

    def getExperimentalConditionRefined(self):
        return self._experimentalConditionRefined

    def setExperimentalConditionRefined(self, experimentalConditionRefined):
        if experimentalConditionRefined is None:
            self._experimentalConditionRefined = None
        elif (
            experimentalConditionRefined.__class__.__name__
            == "XSDataExperimentalCondition"
        ):
            self._experimentalConditionRefined = experimentalConditionRefined
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult.setExperimentalConditionRefined argument is not XSDataExperimentalCondition but %s"
                % experimentalConditionRefined.__class__.__name__
            )
            raise BaseException(strMessage)

    def delExperimentalConditionRefined(self):
        self._experimentalConditionRefined = None

    experimentalConditionRefined = property(
        getExperimentalConditionRefined,
        setExperimentalConditionRefined,
        delExperimentalConditionRefined,
        "Property for experimentalConditionRefined",
    )
    # Methods and properties for the 'generatedMTZFile' attribute

    def getGeneratedMTZFile(self):
        return self._generatedMTZFile

    def setGeneratedMTZFile(self, generatedMTZFile):
        if generatedMTZFile is None:
            self._generatedMTZFile = None
        elif generatedMTZFile.__class__.__name__ == "XSDataFile":
            self._generatedMTZFile = generatedMTZFile
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult.setGeneratedMTZFile argument is not XSDataFile but %s"
                % generatedMTZFile.__class__.__name__
            )
            raise BaseException(strMessage)

    def delGeneratedMTZFile(self):
        self._generatedMTZFile = None

    generatedMTZFile = property(
        getGeneratedMTZFile,
        setGeneratedMTZFile,
        delGeneratedMTZFile,
        "Property for generatedMTZFile",
    )
    # Methods and properties for the 'integrationLogFile' attribute

    def getIntegrationLogFile(self):
        return self._integrationLogFile

    def setIntegrationLogFile(self, integrationLogFile):
        if integrationLogFile is None:
            self._integrationLogFile = None
        elif integrationLogFile.__class__.__name__ == "XSDataFile":
            self._integrationLogFile = integrationLogFile
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult.setIntegrationLogFile argument is not XSDataFile but %s"
                % integrationLogFile.__class__.__name__
            )
            raise BaseException(strMessage)

    def delIntegrationLogFile(self):
        self._integrationLogFile = None

    integrationLogFile = property(
        getIntegrationLogFile,
        setIntegrationLogFile,
        delIntegrationLogFile,
        "Property for integrationLogFile",
    )
    # Methods and properties for the 'statistics' attribute

    def getStatistics(self):
        return self._statistics

    def setStatistics(self, statistics):
        if statistics is None:
            self._statistics = None
        elif statistics.__class__.__name__ == "XSDataStatisticsIntegration":
            self._statistics = statistics
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult.setStatistics argument is not XSDataStatisticsIntegration but %s"
                % statistics.__class__.__name__
            )
            raise BaseException(strMessage)

    def delStatistics(self):
        self._statistics = None

    statistics = property(
        getStatistics, setStatistics, delStatistics, "Property for statistics"
    )
    # Methods and properties for the 'statisticsPerResolutionBin' attribute

    def getStatisticsPerResolutionBin(self):
        return self._statisticsPerResolutionBin

    def setStatisticsPerResolutionBin(self, statisticsPerResolutionBin):
        if statisticsPerResolutionBin is None:
            self._statisticsPerResolutionBin = []
        elif statisticsPerResolutionBin.__class__.__name__ == "list":
            self._statisticsPerResolutionBin = statisticsPerResolutionBin
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult.setStatisticsPerResolutionBin argument is not list but %s"
                % statisticsPerResolutionBin.__class__.__name__
            )
            raise BaseException(strMessage)

    def delStatisticsPerResolutionBin(self):
        self._statisticsPerResolutionBin = None

    statisticsPerResolutionBin = property(
        getStatisticsPerResolutionBin,
        setStatisticsPerResolutionBin,
        delStatisticsPerResolutionBin,
        "Property for statisticsPerResolutionBin",
    )

    def addStatisticsPerResolutionBin(self, value):
        if value is None:
            strMessage = "ERROR! XSDataIntegrationSubWedgeResult.addStatisticsPerResolutionBin argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataStatisticsIntegrationPerResolutionBin":
            self._statisticsPerResolutionBin.append(value)
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult.addStatisticsPerResolutionBin argument is not XSDataStatisticsIntegrationPerResolutionBin but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertStatisticsPerResolutionBin(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataIntegrationSubWedgeResult.insertStatisticsPerResolutionBin argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataIntegrationSubWedgeResult.insertStatisticsPerResolutionBin argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataStatisticsIntegrationPerResolutionBin":
            self._statisticsPerResolutionBin[index] = value
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult.addStatisticsPerResolutionBin argument is not XSDataStatisticsIntegrationPerResolutionBin but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'subWedgeNumber' attribute
    def getSubWedgeNumber(self):
        return self._subWedgeNumber

    def setSubWedgeNumber(self, subWedgeNumber):
        if subWedgeNumber is None:
            self._subWedgeNumber = None
        elif subWedgeNumber.__class__.__name__ == "XSDataInteger":
            self._subWedgeNumber = subWedgeNumber
        else:
            strMessage = (
                "ERROR! XSDataIntegrationSubWedgeResult.setSubWedgeNumber argument is not XSDataInteger but %s"
                % subWedgeNumber.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSubWedgeNumber(self):
        self._subWedgeNumber = None

    subWedgeNumber = property(
        getSubWedgeNumber,
        setSubWedgeNumber,
        delSubWedgeNumber,
        "Property for subWedgeNumber",
    )

    def export(self, outfile, level, name_="XSDataIntegrationSubWedgeResult"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataIntegrationSubWedgeResult"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._bestfileDat is not None:
            self.bestfileDat.export(outfile, level, name_="bestfileDat")
        else:
            warnEmptyAttribute("bestfileDat", "XSDataString")
        if self._bestfileHKL is not None:
            self.bestfileHKL.export(outfile, level, name_="bestfileHKL")
        else:
            warnEmptyAttribute("bestfileHKL", "XSDataString")
        if self._bestfilePar is not None:
            self.bestfilePar.export(outfile, level, name_="bestfilePar")
        else:
            warnEmptyAttribute("bestfilePar", "XSDataString")
        if self._experimentalConditionRefined is not None:
            self.experimentalConditionRefined.export(
                outfile, level, name_="experimentalConditionRefined"
            )
        else:
            warnEmptyAttribute(
                "experimentalConditionRefined", "XSDataExperimentalCondition"
            )
        if self._generatedMTZFile is not None:
            self.generatedMTZFile.export(outfile, level, name_="generatedMTZFile")
        else:
            warnEmptyAttribute("generatedMTZFile", "XSDataFile")
        if self._integrationLogFile is not None:
            self.integrationLogFile.export(outfile, level, name_="integrationLogFile")
        else:
            warnEmptyAttribute("integrationLogFile", "XSDataFile")
        if self._statistics is not None:
            self.statistics.export(outfile, level, name_="statistics")
        else:
            warnEmptyAttribute("statistics", "XSDataStatisticsIntegration")
        for statisticsPerResolutionBin_ in self.getStatisticsPerResolutionBin():
            statisticsPerResolutionBin_.export(
                outfile, level, name_="statisticsPerResolutionBin"
            )
        if self.getStatisticsPerResolutionBin() == []:
            warnEmptyAttribute(
                "statisticsPerResolutionBin",
                "XSDataStatisticsIntegrationPerResolutionBin",
            )
        if self._subWedgeNumber is not None:
            self.subWedgeNumber.export(outfile, level, name_="subWedgeNumber")
        else:
            warnEmptyAttribute("subWedgeNumber", "XSDataInteger")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "bestfileDat":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setBestfileDat(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "bestfileHKL":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setBestfileHKL(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "bestfilePar":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setBestfilePar(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "experimentalConditionRefined"
        ):
            obj_ = XSDataExperimentalCondition()
            obj_.build(child_)
            self.setExperimentalConditionRefined(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "generatedMTZFile":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setGeneratedMTZFile(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "integrationLogFile":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setIntegrationLogFile(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "statistics":
            obj_ = XSDataStatisticsIntegration()
            obj_.build(child_)
            self.setStatistics(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "statisticsPerResolutionBin"
        ):
            obj_ = XSDataStatisticsIntegrationPerResolutionBin()
            obj_.build(child_)
            self.statisticsPerResolutionBin.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "subWedgeNumber":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setSubWedgeNumber(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataIntegrationSubWedgeResult")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataIntegrationSubWedgeResult")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataIntegrationSubWedgeResult is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataIntegrationSubWedgeResult.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataIntegrationSubWedgeResult()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataIntegrationSubWedgeResult")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataIntegrationSubWedgeResult()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataIntegrationSubWedgeResult


class XSDataLigand(XSData):
    """A polymer ligand that contains a set of heavy atoms, the number of all the light atoms (weight <= Oxygen) and the number of copies of this particular ligand in the polymer."""

    def __init__(self, numberOfLightAtoms=None, numberOfCopies=None, heavyAtoms=None):
        XSData.__init__(self)
        if heavyAtoms is None:
            self._heavyAtoms = None
        elif heavyAtoms.__class__.__name__ == "XSDataAtomicComposition":
            self._heavyAtoms = heavyAtoms
        else:
            strMessage = (
                "ERROR! XSDataLigand constructor argument 'heavyAtoms' is not XSDataAtomicComposition but %s"
                % self._heavyAtoms.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberOfCopies is None:
            self._numberOfCopies = None
        elif numberOfCopies.__class__.__name__ == "XSDataDouble":
            self._numberOfCopies = numberOfCopies
        else:
            strMessage = (
                "ERROR! XSDataLigand constructor argument 'numberOfCopies' is not XSDataDouble but %s"
                % self._numberOfCopies.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberOfLightAtoms is None:
            self._numberOfLightAtoms = None
        elif numberOfLightAtoms.__class__.__name__ == "XSDataDouble":
            self._numberOfLightAtoms = numberOfLightAtoms
        else:
            strMessage = (
                "ERROR! XSDataLigand constructor argument 'numberOfLightAtoms' is not XSDataDouble but %s"
                % self._numberOfLightAtoms.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'heavyAtoms' attribute
    def getHeavyAtoms(self):
        return self._heavyAtoms

    def setHeavyAtoms(self, heavyAtoms):
        if heavyAtoms is None:
            self._heavyAtoms = None
        elif heavyAtoms.__class__.__name__ == "XSDataAtomicComposition":
            self._heavyAtoms = heavyAtoms
        else:
            strMessage = (
                "ERROR! XSDataLigand.setHeavyAtoms argument is not XSDataAtomicComposition but %s"
                % heavyAtoms.__class__.__name__
            )
            raise BaseException(strMessage)

    def delHeavyAtoms(self):
        self._heavyAtoms = None

    heavyAtoms = property(
        getHeavyAtoms, setHeavyAtoms, delHeavyAtoms, "Property for heavyAtoms"
    )
    # Methods and properties for the 'numberOfCopies' attribute

    def getNumberOfCopies(self):
        return self._numberOfCopies

    def setNumberOfCopies(self, numberOfCopies):
        if numberOfCopies is None:
            self._numberOfCopies = None
        elif numberOfCopies.__class__.__name__ == "XSDataDouble":
            self._numberOfCopies = numberOfCopies
        else:
            strMessage = (
                "ERROR! XSDataLigand.setNumberOfCopies argument is not XSDataDouble but %s"
                % numberOfCopies.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberOfCopies(self):
        self._numberOfCopies = None

    numberOfCopies = property(
        getNumberOfCopies,
        setNumberOfCopies,
        delNumberOfCopies,
        "Property for numberOfCopies",
    )
    # Methods and properties for the 'numberOfLightAtoms' attribute

    def getNumberOfLightAtoms(self):
        return self._numberOfLightAtoms

    def setNumberOfLightAtoms(self, numberOfLightAtoms):
        if numberOfLightAtoms is None:
            self._numberOfLightAtoms = None
        elif numberOfLightAtoms.__class__.__name__ == "XSDataDouble":
            self._numberOfLightAtoms = numberOfLightAtoms
        else:
            strMessage = (
                "ERROR! XSDataLigand.setNumberOfLightAtoms argument is not XSDataDouble but %s"
                % numberOfLightAtoms.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberOfLightAtoms(self):
        self._numberOfLightAtoms = None

    numberOfLightAtoms = property(
        getNumberOfLightAtoms,
        setNumberOfLightAtoms,
        delNumberOfLightAtoms,
        "Property for numberOfLightAtoms",
    )

    def export(self, outfile, level, name_="XSDataLigand"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataLigand"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._heavyAtoms is not None:
            self.heavyAtoms.export(outfile, level, name_="heavyAtoms")
        else:
            warnEmptyAttribute("heavyAtoms", "XSDataAtomicComposition")
        if self._numberOfCopies is not None:
            self.numberOfCopies.export(outfile, level, name_="numberOfCopies")
        else:
            warnEmptyAttribute("numberOfCopies", "XSDataDouble")
        if self._numberOfLightAtoms is not None:
            self.numberOfLightAtoms.export(outfile, level, name_="numberOfLightAtoms")
        else:
            warnEmptyAttribute("numberOfLightAtoms", "XSDataDouble")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "heavyAtoms":
            obj_ = XSDataAtomicComposition()
            obj_.build(child_)
            self.setHeavyAtoms(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "numberOfCopies":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setNumberOfCopies(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "numberOfLightAtoms":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setNumberOfLightAtoms(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataLigand")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataLigand")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataLigand is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataLigand.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataLigand()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataLigand")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataLigand()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataLigand


class XSDataOrientation(XSData):
    def __init__(self, matrixU=None, matrixA=None):
        XSData.__init__(self)
        if matrixA is None:
            self._matrixA = None
        elif matrixA.__class__.__name__ == "XSDataMatrixDouble":
            self._matrixA = matrixA
        else:
            strMessage = (
                "ERROR! XSDataOrientation constructor argument 'matrixA' is not XSDataMatrixDouble but %s"
                % self._matrixA.__class__.__name__
            )
            raise BaseException(strMessage)
        if matrixU is None:
            self._matrixU = None
        elif matrixU.__class__.__name__ == "XSDataMatrixDouble":
            self._matrixU = matrixU
        else:
            strMessage = (
                "ERROR! XSDataOrientation constructor argument 'matrixU' is not XSDataMatrixDouble but %s"
                % self._matrixU.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'matrixA' attribute
    def getMatrixA(self):
        return self._matrixA

    def setMatrixA(self, matrixA):
        if matrixA is None:
            self._matrixA = None
        elif matrixA.__class__.__name__ == "XSDataMatrixDouble":
            self._matrixA = matrixA
        else:
            strMessage = (
                "ERROR! XSDataOrientation.setMatrixA argument is not XSDataMatrixDouble but %s"
                % matrixA.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMatrixA(self):
        self._matrixA = None

    matrixA = property(getMatrixA, setMatrixA, delMatrixA, "Property for matrixA")
    # Methods and properties for the 'matrixU' attribute

    def getMatrixU(self):
        return self._matrixU

    def setMatrixU(self, matrixU):
        if matrixU is None:
            self._matrixU = None
        elif matrixU.__class__.__name__ == "XSDataMatrixDouble":
            self._matrixU = matrixU
        else:
            strMessage = (
                "ERROR! XSDataOrientation.setMatrixU argument is not XSDataMatrixDouble but %s"
                % matrixU.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMatrixU(self):
        self._matrixU = None

    matrixU = property(getMatrixU, setMatrixU, delMatrixU, "Property for matrixU")

    def export(self, outfile, level, name_="XSDataOrientation"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataOrientation"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._matrixA is not None:
            self.matrixA.export(outfile, level, name_="matrixA")
        else:
            warnEmptyAttribute("matrixA", "XSDataMatrixDouble")
        if self._matrixU is not None:
            self.matrixU.export(outfile, level, name_="matrixU")
        else:
            warnEmptyAttribute("matrixU", "XSDataMatrixDouble")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "matrixA":
            obj_ = XSDataMatrixDouble()
            obj_.build(child_)
            self.setMatrixA(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "matrixU":
            obj_ = XSDataMatrixDouble()
            obj_.build(child_)
            self.setMatrixU(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataOrientation")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataOrientation")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataOrientation is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataOrientation.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataOrientation()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataOrientation")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataOrientation()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataOrientation


class XSDataResolutionBin(XSData):
    def __init__(
        self,
        redundancy=None,
        rFriedel=None,
        rFactor=None,
        percentageOverload=None,
        minResolution=None,
        maxResolution=None,
        completeness=None,
        chi2=None,
        averageSigma=None,
        averageIntensityOverAverageSigma=None,
        averageIntensity=None,
        IOverSigmaChi=None,
        IOverSigma=None,
    ):
        XSData.__init__(self)
        if IOverSigma is None:
            self._IOverSigma = None
        elif IOverSigma.__class__.__name__ == "XSDataDouble":
            self._IOverSigma = IOverSigma
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin constructor argument 'IOverSigma' is not XSDataDouble but %s"
                % self._IOverSigma.__class__.__name__
            )
            raise BaseException(strMessage)
        if IOverSigmaChi is None:
            self._IOverSigmaChi = None
        elif IOverSigmaChi.__class__.__name__ == "XSDataDouble":
            self._IOverSigmaChi = IOverSigmaChi
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin constructor argument 'IOverSigmaChi' is not XSDataDouble but %s"
                % self._IOverSigmaChi.__class__.__name__
            )
            raise BaseException(strMessage)
        if averageIntensity is None:
            self._averageIntensity = None
        elif averageIntensity.__class__.__name__ == "XSDataDouble":
            self._averageIntensity = averageIntensity
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin constructor argument 'averageIntensity' is not XSDataDouble but %s"
                % self._averageIntensity.__class__.__name__
            )
            raise BaseException(strMessage)
        if averageIntensityOverAverageSigma is None:
            self._averageIntensityOverAverageSigma = None
        elif averageIntensityOverAverageSigma.__class__.__name__ == "XSDataDouble":
            self._averageIntensityOverAverageSigma = averageIntensityOverAverageSigma
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin constructor argument 'averageIntensityOverAverageSigma' is not XSDataDouble but %s"
                % self._averageIntensityOverAverageSigma.__class__.__name__
            )
            raise BaseException(strMessage)
        if averageSigma is None:
            self._averageSigma = None
        elif averageSigma.__class__.__name__ == "XSDataDouble":
            self._averageSigma = averageSigma
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin constructor argument 'averageSigma' is not XSDataDouble but %s"
                % self._averageSigma.__class__.__name__
            )
            raise BaseException(strMessage)
        if chi2 is None:
            self._chi2 = None
        elif chi2.__class__.__name__ == "XSDataDouble":
            self._chi2 = chi2
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin constructor argument 'chi2' is not XSDataDouble but %s"
                % self._chi2.__class__.__name__
            )
            raise BaseException(strMessage)
        if completeness is None:
            self._completeness = None
        elif completeness.__class__.__name__ == "XSDataDouble":
            self._completeness = completeness
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin constructor argument 'completeness' is not XSDataDouble but %s"
                % self._completeness.__class__.__name__
            )
            raise BaseException(strMessage)
        if maxResolution is None:
            self._maxResolution = None
        elif maxResolution.__class__.__name__ == "XSDataDouble":
            self._maxResolution = maxResolution
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin constructor argument 'maxResolution' is not XSDataDouble but %s"
                % self._maxResolution.__class__.__name__
            )
            raise BaseException(strMessage)
        if minResolution is None:
            self._minResolution = None
        elif minResolution.__class__.__name__ == "XSDataDouble":
            self._minResolution = minResolution
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin constructor argument 'minResolution' is not XSDataDouble but %s"
                % self._minResolution.__class__.__name__
            )
            raise BaseException(strMessage)
        if percentageOverload is None:
            self._percentageOverload = None
        elif percentageOverload.__class__.__name__ == "XSDataDouble":
            self._percentageOverload = percentageOverload
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin constructor argument 'percentageOverload' is not XSDataDouble but %s"
                % self._percentageOverload.__class__.__name__
            )
            raise BaseException(strMessage)
        if rFactor is None:
            self._rFactor = None
        elif rFactor.__class__.__name__ == "XSDataDouble":
            self._rFactor = rFactor
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin constructor argument 'rFactor' is not XSDataDouble but %s"
                % self._rFactor.__class__.__name__
            )
            raise BaseException(strMessage)
        if rFriedel is None:
            self._rFriedel = None
        elif rFriedel.__class__.__name__ == "XSDataDouble":
            self._rFriedel = rFriedel
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin constructor argument 'rFriedel' is not XSDataDouble but %s"
                % self._rFriedel.__class__.__name__
            )
            raise BaseException(strMessage)
        if redundancy is None:
            self._redundancy = None
        elif redundancy.__class__.__name__ == "XSDataDouble":
            self._redundancy = redundancy
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin constructor argument 'redundancy' is not XSDataDouble but %s"
                % self._redundancy.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'IOverSigma' attribute
    def getIOverSigma(self):
        return self._IOverSigma

    def setIOverSigma(self, IOverSigma):
        if IOverSigma is None:
            self._IOverSigma = None
        elif IOverSigma.__class__.__name__ == "XSDataDouble":
            self._IOverSigma = IOverSigma
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin.setIOverSigma argument is not XSDataDouble but %s"
                % IOverSigma.__class__.__name__
            )
            raise BaseException(strMessage)

    def delIOverSigma(self):
        self._IOverSigma = None

    IOverSigma = property(
        getIOverSigma, setIOverSigma, delIOverSigma, "Property for IOverSigma"
    )
    # Methods and properties for the 'IOverSigmaChi' attribute

    def getIOverSigmaChi(self):
        return self._IOverSigmaChi

    def setIOverSigmaChi(self, IOverSigmaChi):
        if IOverSigmaChi is None:
            self._IOverSigmaChi = None
        elif IOverSigmaChi.__class__.__name__ == "XSDataDouble":
            self._IOverSigmaChi = IOverSigmaChi
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin.setIOverSigmaChi argument is not XSDataDouble but %s"
                % IOverSigmaChi.__class__.__name__
            )
            raise BaseException(strMessage)

    def delIOverSigmaChi(self):
        self._IOverSigmaChi = None

    IOverSigmaChi = property(
        getIOverSigmaChi,
        setIOverSigmaChi,
        delIOverSigmaChi,
        "Property for IOverSigmaChi",
    )
    # Methods and properties for the 'averageIntensity' attribute

    def getAverageIntensity(self):
        return self._averageIntensity

    def setAverageIntensity(self, averageIntensity):
        if averageIntensity is None:
            self._averageIntensity = None
        elif averageIntensity.__class__.__name__ == "XSDataDouble":
            self._averageIntensity = averageIntensity
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin.setAverageIntensity argument is not XSDataDouble but %s"
                % averageIntensity.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAverageIntensity(self):
        self._averageIntensity = None

    averageIntensity = property(
        getAverageIntensity,
        setAverageIntensity,
        delAverageIntensity,
        "Property for averageIntensity",
    )
    # Methods and properties for the 'averageIntensityOverAverageSigma' attribute

    def getAverageIntensityOverAverageSigma(self):
        return self._averageIntensityOverAverageSigma

    def setAverageIntensityOverAverageSigma(self, averageIntensityOverAverageSigma):
        if averageIntensityOverAverageSigma is None:
            self._averageIntensityOverAverageSigma = None
        elif averageIntensityOverAverageSigma.__class__.__name__ == "XSDataDouble":
            self._averageIntensityOverAverageSigma = averageIntensityOverAverageSigma
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin.setAverageIntensityOverAverageSigma argument is not XSDataDouble but %s"
                % averageIntensityOverAverageSigma.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAverageIntensityOverAverageSigma(self):
        self._averageIntensityOverAverageSigma = None

    averageIntensityOverAverageSigma = property(
        getAverageIntensityOverAverageSigma,
        setAverageIntensityOverAverageSigma,
        delAverageIntensityOverAverageSigma,
        "Property for averageIntensityOverAverageSigma",
    )
    # Methods and properties for the 'averageSigma' attribute

    def getAverageSigma(self):
        return self._averageSigma

    def setAverageSigma(self, averageSigma):
        if averageSigma is None:
            self._averageSigma = None
        elif averageSigma.__class__.__name__ == "XSDataDouble":
            self._averageSigma = averageSigma
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin.setAverageSigma argument is not XSDataDouble but %s"
                % averageSigma.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAverageSigma(self):
        self._averageSigma = None

    averageSigma = property(
        getAverageSigma, setAverageSigma, delAverageSigma, "Property for averageSigma"
    )
    # Methods and properties for the 'chi2' attribute

    def getChi2(self):
        return self._chi2

    def setChi2(self, chi2):
        if chi2 is None:
            self._chi2 = None
        elif chi2.__class__.__name__ == "XSDataDouble":
            self._chi2 = chi2
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin.setChi2 argument is not XSDataDouble but %s"
                % chi2.__class__.__name__
            )
            raise BaseException(strMessage)

    def delChi2(self):
        self._chi2 = None

    chi2 = property(getChi2, setChi2, delChi2, "Property for chi2")
    # Methods and properties for the 'completeness' attribute

    def getCompleteness(self):
        return self._completeness

    def setCompleteness(self, completeness):
        if completeness is None:
            self._completeness = None
        elif completeness.__class__.__name__ == "XSDataDouble":
            self._completeness = completeness
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin.setCompleteness argument is not XSDataDouble but %s"
                % completeness.__class__.__name__
            )
            raise BaseException(strMessage)

    def delCompleteness(self):
        self._completeness = None

    completeness = property(
        getCompleteness, setCompleteness, delCompleteness, "Property for completeness"
    )
    # Methods and properties for the 'maxResolution' attribute

    def getMaxResolution(self):
        return self._maxResolution

    def setMaxResolution(self, maxResolution):
        if maxResolution is None:
            self._maxResolution = None
        elif maxResolution.__class__.__name__ == "XSDataDouble":
            self._maxResolution = maxResolution
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin.setMaxResolution argument is not XSDataDouble but %s"
                % maxResolution.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMaxResolution(self):
        self._maxResolution = None

    maxResolution = property(
        getMaxResolution,
        setMaxResolution,
        delMaxResolution,
        "Property for maxResolution",
    )
    # Methods and properties for the 'minResolution' attribute

    def getMinResolution(self):
        return self._minResolution

    def setMinResolution(self, minResolution):
        if minResolution is None:
            self._minResolution = None
        elif minResolution.__class__.__name__ == "XSDataDouble":
            self._minResolution = minResolution
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin.setMinResolution argument is not XSDataDouble but %s"
                % minResolution.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMinResolution(self):
        self._minResolution = None

    minResolution = property(
        getMinResolution,
        setMinResolution,
        delMinResolution,
        "Property for minResolution",
    )
    # Methods and properties for the 'percentageOverload' attribute

    def getPercentageOverload(self):
        return self._percentageOverload

    def setPercentageOverload(self, percentageOverload):
        if percentageOverload is None:
            self._percentageOverload = None
        elif percentageOverload.__class__.__name__ == "XSDataDouble":
            self._percentageOverload = percentageOverload
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin.setPercentageOverload argument is not XSDataDouble but %s"
                % percentageOverload.__class__.__name__
            )
            raise BaseException(strMessage)

    def delPercentageOverload(self):
        self._percentageOverload = None

    percentageOverload = property(
        getPercentageOverload,
        setPercentageOverload,
        delPercentageOverload,
        "Property for percentageOverload",
    )
    # Methods and properties for the 'rFactor' attribute

    def getRFactor(self):
        return self._rFactor

    def setRFactor(self, rFactor):
        if rFactor is None:
            self._rFactor = None
        elif rFactor.__class__.__name__ == "XSDataDouble":
            self._rFactor = rFactor
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin.setRFactor argument is not XSDataDouble but %s"
                % rFactor.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRFactor(self):
        self._rFactor = None

    rFactor = property(getRFactor, setRFactor, delRFactor, "Property for rFactor")
    # Methods and properties for the 'rFriedel' attribute

    def getRFriedel(self):
        return self._rFriedel

    def setRFriedel(self, rFriedel):
        if rFriedel is None:
            self._rFriedel = None
        elif rFriedel.__class__.__name__ == "XSDataDouble":
            self._rFriedel = rFriedel
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin.setRFriedel argument is not XSDataDouble but %s"
                % rFriedel.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRFriedel(self):
        self._rFriedel = None

    rFriedel = property(getRFriedel, setRFriedel, delRFriedel, "Property for rFriedel")
    # Methods and properties for the 'redundancy' attribute

    def getRedundancy(self):
        return self._redundancy

    def setRedundancy(self, redundancy):
        if redundancy is None:
            self._redundancy = None
        elif redundancy.__class__.__name__ == "XSDataDouble":
            self._redundancy = redundancy
        else:
            strMessage = (
                "ERROR! XSDataResolutionBin.setRedundancy argument is not XSDataDouble but %s"
                % redundancy.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRedundancy(self):
        self._redundancy = None

    redundancy = property(
        getRedundancy, setRedundancy, delRedundancy, "Property for redundancy"
    )

    def export(self, outfile, level, name_="XSDataResolutionBin"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataResolutionBin"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._IOverSigma is not None:
            self.IOverSigma.export(outfile, level, name_="IOverSigma")
        else:
            warnEmptyAttribute("IOverSigma", "XSDataDouble")
        if self._IOverSigmaChi is not None:
            self.IOverSigmaChi.export(outfile, level, name_="IOverSigmaChi")
        if self._averageIntensity is not None:
            self.averageIntensity.export(outfile, level, name_="averageIntensity")
        else:
            warnEmptyAttribute("averageIntensity", "XSDataDouble")
        if self._averageIntensityOverAverageSigma is not None:
            self.averageIntensityOverAverageSigma.export(
                outfile, level, name_="averageIntensityOverAverageSigma"
            )
        if self._averageSigma is not None:
            self.averageSigma.export(outfile, level, name_="averageSigma")
        else:
            warnEmptyAttribute("averageSigma", "XSDataDouble")
        if self._chi2 is not None:
            self.chi2.export(outfile, level, name_="chi2")
        if self._completeness is not None:
            self.completeness.export(outfile, level, name_="completeness")
        else:
            warnEmptyAttribute("completeness", "XSDataDouble")
        if self._maxResolution is not None:
            self.maxResolution.export(outfile, level, name_="maxResolution")
        else:
            warnEmptyAttribute("maxResolution", "XSDataDouble")
        if self._minResolution is not None:
            self.minResolution.export(outfile, level, name_="minResolution")
        else:
            warnEmptyAttribute("minResolution", "XSDataDouble")
        if self._percentageOverload is not None:
            self.percentageOverload.export(outfile, level, name_="percentageOverload")
        else:
            warnEmptyAttribute("percentageOverload", "XSDataDouble")
        if self._rFactor is not None:
            self.rFactor.export(outfile, level, name_="rFactor")
        else:
            warnEmptyAttribute("rFactor", "XSDataDouble")
        if self._rFriedel is not None:
            self.rFriedel.export(outfile, level, name_="rFriedel")
        if self._redundancy is not None:
            self.redundancy.export(outfile, level, name_="redundancy")
        else:
            warnEmptyAttribute("redundancy", "XSDataDouble")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "IOverSigma":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setIOverSigma(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "IOverSigmaChi":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setIOverSigmaChi(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "averageIntensity":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setAverageIntensity(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "averageIntensityOverAverageSigma"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setAverageIntensityOverAverageSigma(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "averageSigma":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setAverageSigma(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "chi2":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setChi2(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "completeness":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setCompleteness(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "maxResolution":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setMaxResolution(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "minResolution":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setMinResolution(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "percentageOverload":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setPercentageOverload(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "rFactor":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setRFactor(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "rFriedel":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setRFriedel(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "redundancy":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setRedundancy(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataResolutionBin")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataResolutionBin")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataResolutionBin is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataResolutionBin.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResolutionBin()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataResolutionBin")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResolutionBin()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataResolutionBin


class XSDataSample(XSData):
    """This defines the main properties of a sample:
- absorbed dose rate in Gray/sec
- shape: the factor that is related to the sample and the beam size (1 if crystal smaller than beam size or = to the ratio of crystal size to the beam size if the beam is smaller then crystal).
- sample size
- the susceptibility of the sample to radiation damage."""

    def __init__(
        self,
        susceptibility=None,
        size=None,
        shape=None,
        radiationDamageModelGamma=None,
        radiationDamageModelBeta=None,
        absorbedDoseRate=None,
    ):
        XSData.__init__(self)
        if absorbedDoseRate is None:
            self._absorbedDoseRate = None
        elif absorbedDoseRate.__class__.__name__ == "XSDataAbsorbedDoseRate":
            self._absorbedDoseRate = absorbedDoseRate
        else:
            strMessage = (
                "ERROR! XSDataSample constructor argument 'absorbedDoseRate' is not XSDataAbsorbedDoseRate but %s"
                % self._absorbedDoseRate.__class__.__name__
            )
            raise BaseException(strMessage)
        if radiationDamageModelBeta is None:
            self._radiationDamageModelBeta = None
        elif radiationDamageModelBeta.__class__.__name__ == "XSDataDouble":
            self._radiationDamageModelBeta = radiationDamageModelBeta
        else:
            strMessage = (
                "ERROR! XSDataSample constructor argument 'radiationDamageModelBeta' is not XSDataDouble but %s"
                % self._radiationDamageModelBeta.__class__.__name__
            )
            raise BaseException(strMessage)
        if radiationDamageModelGamma is None:
            self._radiationDamageModelGamma = None
        elif radiationDamageModelGamma.__class__.__name__ == "XSDataDouble":
            self._radiationDamageModelGamma = radiationDamageModelGamma
        else:
            strMessage = (
                "ERROR! XSDataSample constructor argument 'radiationDamageModelGamma' is not XSDataDouble but %s"
                % self._radiationDamageModelGamma.__class__.__name__
            )
            raise BaseException(strMessage)
        if shape is None:
            self._shape = None
        elif shape.__class__.__name__ == "XSDataDouble":
            self._shape = shape
        else:
            strMessage = (
                "ERROR! XSDataSample constructor argument 'shape' is not XSDataDouble but %s"
                % self._shape.__class__.__name__
            )
            raise BaseException(strMessage)
        if size is None:
            self._size = None
        elif size.__class__.__name__ == "XSDataSize":
            self._size = size
        else:
            strMessage = (
                "ERROR! XSDataSample constructor argument 'size' is not XSDataSize but %s"
                % self._size.__class__.__name__
            )
            raise BaseException(strMessage)
        if susceptibility is None:
            self._susceptibility = None
        elif susceptibility.__class__.__name__ == "XSDataDouble":
            self._susceptibility = susceptibility
        else:
            strMessage = (
                "ERROR! XSDataSample constructor argument 'susceptibility' is not XSDataDouble but %s"
                % self._susceptibility.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'absorbedDoseRate' attribute
    def getAbsorbedDoseRate(self):
        return self._absorbedDoseRate

    def setAbsorbedDoseRate(self, absorbedDoseRate):
        if absorbedDoseRate is None:
            self._absorbedDoseRate = None
        elif absorbedDoseRate.__class__.__name__ == "XSDataAbsorbedDoseRate":
            self._absorbedDoseRate = absorbedDoseRate
        else:
            strMessage = (
                "ERROR! XSDataSample.setAbsorbedDoseRate argument is not XSDataAbsorbedDoseRate but %s"
                % absorbedDoseRate.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAbsorbedDoseRate(self):
        self._absorbedDoseRate = None

    absorbedDoseRate = property(
        getAbsorbedDoseRate,
        setAbsorbedDoseRate,
        delAbsorbedDoseRate,
        "Property for absorbedDoseRate",
    )
    # Methods and properties for the 'radiationDamageModelBeta' attribute

    def getRadiationDamageModelBeta(self):
        return self._radiationDamageModelBeta

    def setRadiationDamageModelBeta(self, radiationDamageModelBeta):
        if radiationDamageModelBeta is None:
            self._radiationDamageModelBeta = None
        elif radiationDamageModelBeta.__class__.__name__ == "XSDataDouble":
            self._radiationDamageModelBeta = radiationDamageModelBeta
        else:
            strMessage = (
                "ERROR! XSDataSample.setRadiationDamageModelBeta argument is not XSDataDouble but %s"
                % radiationDamageModelBeta.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRadiationDamageModelBeta(self):
        self._radiationDamageModelBeta = None

    radiationDamageModelBeta = property(
        getRadiationDamageModelBeta,
        setRadiationDamageModelBeta,
        delRadiationDamageModelBeta,
        "Property for radiationDamageModelBeta",
    )
    # Methods and properties for the 'radiationDamageModelGamma' attribute

    def getRadiationDamageModelGamma(self):
        return self._radiationDamageModelGamma

    def setRadiationDamageModelGamma(self, radiationDamageModelGamma):
        if radiationDamageModelGamma is None:
            self._radiationDamageModelGamma = None
        elif radiationDamageModelGamma.__class__.__name__ == "XSDataDouble":
            self._radiationDamageModelGamma = radiationDamageModelGamma
        else:
            strMessage = (
                "ERROR! XSDataSample.setRadiationDamageModelGamma argument is not XSDataDouble but %s"
                % radiationDamageModelGamma.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRadiationDamageModelGamma(self):
        self._radiationDamageModelGamma = None

    radiationDamageModelGamma = property(
        getRadiationDamageModelGamma,
        setRadiationDamageModelGamma,
        delRadiationDamageModelGamma,
        "Property for radiationDamageModelGamma",
    )
    # Methods and properties for the 'shape' attribute

    def getShape(self):
        return self._shape

    def setShape(self, shape):
        if shape is None:
            self._shape = None
        elif shape.__class__.__name__ == "XSDataDouble":
            self._shape = shape
        else:
            strMessage = (
                "ERROR! XSDataSample.setShape argument is not XSDataDouble but %s"
                % shape.__class__.__name__
            )
            raise BaseException(strMessage)

    def delShape(self):
        self._shape = None

    shape = property(getShape, setShape, delShape, "Property for shape")
    # Methods and properties for the 'size' attribute

    def getSize(self):
        return self._size

    def setSize(self, size):
        if size is None:
            self._size = None
        elif size.__class__.__name__ == "XSDataSize":
            self._size = size
        else:
            strMessage = (
                "ERROR! XSDataSample.setSize argument is not XSDataSize but %s"
                % size.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSize(self):
        self._size = None

    size = property(getSize, setSize, delSize, "Property for size")
    # Methods and properties for the 'susceptibility' attribute

    def getSusceptibility(self):
        return self._susceptibility

    def setSusceptibility(self, susceptibility):
        if susceptibility is None:
            self._susceptibility = None
        elif susceptibility.__class__.__name__ == "XSDataDouble":
            self._susceptibility = susceptibility
        else:
            strMessage = (
                "ERROR! XSDataSample.setSusceptibility argument is not XSDataDouble but %s"
                % susceptibility.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSusceptibility(self):
        self._susceptibility = None

    susceptibility = property(
        getSusceptibility,
        setSusceptibility,
        delSusceptibility,
        "Property for susceptibility",
    )

    def export(self, outfile, level, name_="XSDataSample"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataSample"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._absorbedDoseRate is not None:
            self.absorbedDoseRate.export(outfile, level, name_="absorbedDoseRate")
        if self._radiationDamageModelBeta is not None:
            self.radiationDamageModelBeta.export(
                outfile, level, name_="radiationDamageModelBeta"
            )
        if self._radiationDamageModelGamma is not None:
            self.radiationDamageModelGamma.export(
                outfile, level, name_="radiationDamageModelGamma"
            )
        if self._shape is not None:
            self.shape.export(outfile, level, name_="shape")
        if self._size is not None:
            self.size.export(outfile, level, name_="size")
        if self._susceptibility is not None:
            self.susceptibility.export(outfile, level, name_="susceptibility")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "absorbedDoseRate":
            obj_ = XSDataAbsorbedDoseRate()
            obj_.build(child_)
            self.setAbsorbedDoseRate(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "radiationDamageModelBeta"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setRadiationDamageModelBeta(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "radiationDamageModelGamma"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setRadiationDamageModelGamma(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "shape":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setShape(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "size":
            obj_ = XSDataSize()
            obj_.build(child_)
            self.setSize(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "susceptibility":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setSusceptibility(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataSample")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataSample")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataSample is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataSample.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataSample()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataSample")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataSample()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataSample


class XSDataSolvent(XSData):
    """Defines the content of the solvent by defining the concentration of elements in millimoles/litre. Note that this atom composition should not include oxygen and lighter atoms."""

    def __init__(self, atoms=None):
        XSData.__init__(self)
        if atoms is None:
            self._atoms = None
        elif atoms.__class__.__name__ == "XSDataAtomicComposition":
            self._atoms = atoms
        else:
            strMessage = (
                "ERROR! XSDataSolvent constructor argument 'atoms' is not XSDataAtomicComposition but %s"
                % self._atoms.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'atoms' attribute
    def getAtoms(self):
        return self._atoms

    def setAtoms(self, atoms):
        if atoms is None:
            self._atoms = None
        elif atoms.__class__.__name__ == "XSDataAtomicComposition":
            self._atoms = atoms
        else:
            strMessage = (
                "ERROR! XSDataSolvent.setAtoms argument is not XSDataAtomicComposition but %s"
                % atoms.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAtoms(self):
        self._atoms = None

    atoms = property(getAtoms, setAtoms, delAtoms, "Property for atoms")

    def export(self, outfile, level, name_="XSDataSolvent"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataSolvent"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._atoms is not None:
            self.atoms.export(outfile, level, name_="atoms")
        else:
            warnEmptyAttribute("atoms", "XSDataAtomicComposition")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "atoms":
            obj_ = XSDataAtomicComposition()
            obj_.build(child_)
            self.setAtoms(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataSolvent")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataSolvent")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataSolvent is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataSolvent.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataSolvent()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataSolvent")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataSolvent()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataSolvent


class XSDataSpaceGroup(XSData):
    """Crystallographic properties"""

    def __init__(self, name=None, ITNumber=None):
        XSData.__init__(self)
        if ITNumber is None:
            self._ITNumber = None
        elif ITNumber.__class__.__name__ == "XSDataInteger":
            self._ITNumber = ITNumber
        else:
            strMessage = (
                "ERROR! XSDataSpaceGroup constructor argument 'ITNumber' is not XSDataInteger but %s"
                % self._ITNumber.__class__.__name__
            )
            raise BaseException(strMessage)
        if name is None:
            self._name = None
        elif name.__class__.__name__ == "XSDataString":
            self._name = name
        else:
            strMessage = (
                "ERROR! XSDataSpaceGroup constructor argument 'name' is not XSDataString but %s"
                % self._name.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'ITNumber' attribute
    def getITNumber(self):
        return self._ITNumber

    def setITNumber(self, ITNumber):
        if ITNumber is None:
            self._ITNumber = None
        elif ITNumber.__class__.__name__ == "XSDataInteger":
            self._ITNumber = ITNumber
        else:
            strMessage = (
                "ERROR! XSDataSpaceGroup.setITNumber argument is not XSDataInteger but %s"
                % ITNumber.__class__.__name__
            )
            raise BaseException(strMessage)

    def delITNumber(self):
        self._ITNumber = None

    ITNumber = property(getITNumber, setITNumber, delITNumber, "Property for ITNumber")
    # Methods and properties for the 'name' attribute

    def getName(self):
        return self._name

    def setName(self, name):
        if name is None:
            self._name = None
        elif name.__class__.__name__ == "XSDataString":
            self._name = name
        else:
            strMessage = (
                "ERROR! XSDataSpaceGroup.setName argument is not XSDataString but %s"
                % name.__class__.__name__
            )
            raise BaseException(strMessage)

    def delName(self):
        self._name = None

    name = property(getName, setName, delName, "Property for name")

    def export(self, outfile, level, name_="XSDataSpaceGroup"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataSpaceGroup"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._ITNumber is not None:
            self.ITNumber.export(outfile, level, name_="ITNumber")
        if self._name is not None:
            self.name.export(outfile, level, name_="name")
        else:
            warnEmptyAttribute("name", "XSDataString")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "ITNumber":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setITNumber(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "name":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setName(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataSpaceGroup")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataSpaceGroup")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataSpaceGroup is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataSpaceGroup.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataSpaceGroup()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataSpaceGroup")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataSpaceGroup()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataSpaceGroup


class XSDataStatisticsIndexing(XSData):
    def __init__(
        self,
        spotsUsed=None,
        spotsTotal=None,
        spotDeviationPositional=None,
        spotDeviationAngular=None,
        beamPositionShiftY=None,
        beamPositionShiftX=None,
    ):
        XSData.__init__(self)
        if beamPositionShiftX is None:
            self._beamPositionShiftX = None
        elif beamPositionShiftX.__class__.__name__ == "XSDataLength":
            self._beamPositionShiftX = beamPositionShiftX
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIndexing constructor argument 'beamPositionShiftX' is not XSDataLength but %s"
                % self._beamPositionShiftX.__class__.__name__
            )
            raise BaseException(strMessage)
        if beamPositionShiftY is None:
            self._beamPositionShiftY = None
        elif beamPositionShiftY.__class__.__name__ == "XSDataLength":
            self._beamPositionShiftY = beamPositionShiftY
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIndexing constructor argument 'beamPositionShiftY' is not XSDataLength but %s"
                % self._beamPositionShiftY.__class__.__name__
            )
            raise BaseException(strMessage)
        if spotDeviationAngular is None:
            self._spotDeviationAngular = None
        elif spotDeviationAngular.__class__.__name__ == "XSDataAngle":
            self._spotDeviationAngular = spotDeviationAngular
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIndexing constructor argument 'spotDeviationAngular' is not XSDataAngle but %s"
                % self._spotDeviationAngular.__class__.__name__
            )
            raise BaseException(strMessage)
        if spotDeviationPositional is None:
            self._spotDeviationPositional = None
        elif spotDeviationPositional.__class__.__name__ == "XSDataLength":
            self._spotDeviationPositional = spotDeviationPositional
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIndexing constructor argument 'spotDeviationPositional' is not XSDataLength but %s"
                % self._spotDeviationPositional.__class__.__name__
            )
            raise BaseException(strMessage)
        if spotsTotal is None:
            self._spotsTotal = None
        elif spotsTotal.__class__.__name__ == "XSDataInteger":
            self._spotsTotal = spotsTotal
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIndexing constructor argument 'spotsTotal' is not XSDataInteger but %s"
                % self._spotsTotal.__class__.__name__
            )
            raise BaseException(strMessage)
        if spotsUsed is None:
            self._spotsUsed = None
        elif spotsUsed.__class__.__name__ == "XSDataInteger":
            self._spotsUsed = spotsUsed
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIndexing constructor argument 'spotsUsed' is not XSDataInteger but %s"
                % self._spotsUsed.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'beamPositionShiftX' attribute
    def getBeamPositionShiftX(self):
        return self._beamPositionShiftX

    def setBeamPositionShiftX(self, beamPositionShiftX):
        if beamPositionShiftX is None:
            self._beamPositionShiftX = None
        elif beamPositionShiftX.__class__.__name__ == "XSDataLength":
            self._beamPositionShiftX = beamPositionShiftX
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIndexing.setBeamPositionShiftX argument is not XSDataLength but %s"
                % beamPositionShiftX.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBeamPositionShiftX(self):
        self._beamPositionShiftX = None

    beamPositionShiftX = property(
        getBeamPositionShiftX,
        setBeamPositionShiftX,
        delBeamPositionShiftX,
        "Property for beamPositionShiftX",
    )
    # Methods and properties for the 'beamPositionShiftY' attribute

    def getBeamPositionShiftY(self):
        return self._beamPositionShiftY

    def setBeamPositionShiftY(self, beamPositionShiftY):
        if beamPositionShiftY is None:
            self._beamPositionShiftY = None
        elif beamPositionShiftY.__class__.__name__ == "XSDataLength":
            self._beamPositionShiftY = beamPositionShiftY
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIndexing.setBeamPositionShiftY argument is not XSDataLength but %s"
                % beamPositionShiftY.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBeamPositionShiftY(self):
        self._beamPositionShiftY = None

    beamPositionShiftY = property(
        getBeamPositionShiftY,
        setBeamPositionShiftY,
        delBeamPositionShiftY,
        "Property for beamPositionShiftY",
    )
    # Methods and properties for the 'spotDeviationAngular' attribute

    def getSpotDeviationAngular(self):
        return self._spotDeviationAngular

    def setSpotDeviationAngular(self, spotDeviationAngular):
        if spotDeviationAngular is None:
            self._spotDeviationAngular = None
        elif spotDeviationAngular.__class__.__name__ == "XSDataAngle":
            self._spotDeviationAngular = spotDeviationAngular
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIndexing.setSpotDeviationAngular argument is not XSDataAngle but %s"
                % spotDeviationAngular.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSpotDeviationAngular(self):
        self._spotDeviationAngular = None

    spotDeviationAngular = property(
        getSpotDeviationAngular,
        setSpotDeviationAngular,
        delSpotDeviationAngular,
        "Property for spotDeviationAngular",
    )
    # Methods and properties for the 'spotDeviationPositional' attribute

    def getSpotDeviationPositional(self):
        return self._spotDeviationPositional

    def setSpotDeviationPositional(self, spotDeviationPositional):
        if spotDeviationPositional is None:
            self._spotDeviationPositional = None
        elif spotDeviationPositional.__class__.__name__ == "XSDataLength":
            self._spotDeviationPositional = spotDeviationPositional
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIndexing.setSpotDeviationPositional argument is not XSDataLength but %s"
                % spotDeviationPositional.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSpotDeviationPositional(self):
        self._spotDeviationPositional = None

    spotDeviationPositional = property(
        getSpotDeviationPositional,
        setSpotDeviationPositional,
        delSpotDeviationPositional,
        "Property for spotDeviationPositional",
    )
    # Methods and properties for the 'spotsTotal' attribute

    def getSpotsTotal(self):
        return self._spotsTotal

    def setSpotsTotal(self, spotsTotal):
        if spotsTotal is None:
            self._spotsTotal = None
        elif spotsTotal.__class__.__name__ == "XSDataInteger":
            self._spotsTotal = spotsTotal
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIndexing.setSpotsTotal argument is not XSDataInteger but %s"
                % spotsTotal.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSpotsTotal(self):
        self._spotsTotal = None

    spotsTotal = property(
        getSpotsTotal, setSpotsTotal, delSpotsTotal, "Property for spotsTotal"
    )
    # Methods and properties for the 'spotsUsed' attribute

    def getSpotsUsed(self):
        return self._spotsUsed

    def setSpotsUsed(self, spotsUsed):
        if spotsUsed is None:
            self._spotsUsed = None
        elif spotsUsed.__class__.__name__ == "XSDataInteger":
            self._spotsUsed = spotsUsed
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIndexing.setSpotsUsed argument is not XSDataInteger but %s"
                % spotsUsed.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSpotsUsed(self):
        self._spotsUsed = None

    spotsUsed = property(
        getSpotsUsed, setSpotsUsed, delSpotsUsed, "Property for spotsUsed"
    )

    def export(self, outfile, level, name_="XSDataStatisticsIndexing"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataStatisticsIndexing"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._beamPositionShiftX is not None:
            self.beamPositionShiftX.export(outfile, level, name_="beamPositionShiftX")
        else:
            warnEmptyAttribute("beamPositionShiftX", "XSDataLength")
        if self._beamPositionShiftY is not None:
            self.beamPositionShiftY.export(outfile, level, name_="beamPositionShiftY")
        else:
            warnEmptyAttribute("beamPositionShiftY", "XSDataLength")
        if self._spotDeviationAngular is not None:
            self.spotDeviationAngular.export(
                outfile, level, name_="spotDeviationAngular"
            )
        else:
            warnEmptyAttribute("spotDeviationAngular", "XSDataAngle")
        if self._spotDeviationPositional is not None:
            self.spotDeviationPositional.export(
                outfile, level, name_="spotDeviationPositional"
            )
        else:
            warnEmptyAttribute("spotDeviationPositional", "XSDataLength")
        if self._spotsTotal is not None:
            self.spotsTotal.export(outfile, level, name_="spotsTotal")
        else:
            warnEmptyAttribute("spotsTotal", "XSDataInteger")
        if self._spotsUsed is not None:
            self.spotsUsed.export(outfile, level, name_="spotsUsed")
        else:
            warnEmptyAttribute("spotsUsed", "XSDataInteger")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "beamPositionShiftX":
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setBeamPositionShiftX(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "beamPositionShiftY":
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setBeamPositionShiftY(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "spotDeviationAngular"
        ):
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setSpotDeviationAngular(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "spotDeviationPositional"
        ):
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setSpotDeviationPositional(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "spotsTotal":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setSpotsTotal(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "spotsUsed":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setSpotsUsed(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataStatisticsIndexing")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataStatisticsIndexing")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataStatisticsIndexing is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataStatisticsIndexing.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataStatisticsIndexing()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataStatisticsIndexing")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataStatisticsIndexing()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataStatisticsIndexing


class XSDataStatisticsIntegration(XSData):
    def __init__(
        self,
        numberOfReflectionsGenerated=None,
        numberOfPartialReflections=None,
        numberOfOverlappedReflections=None,
        numberOfNegativeReflections=None,
        numberOfFullyRecordedReflections=None,
        numberOfBadReflections=None,
        iOverSigmaOverall=None,
        iOverSigmaAtHighestResolution=None,
        RMSSpotDeviation=None,
    ):
        XSData.__init__(self)
        if RMSSpotDeviation is None:
            self._RMSSpotDeviation = None
        elif RMSSpotDeviation.__class__.__name__ == "XSDataLength":
            self._RMSSpotDeviation = RMSSpotDeviation
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration constructor argument 'RMSSpotDeviation' is not XSDataLength but %s"
                % self._RMSSpotDeviation.__class__.__name__
            )
            raise BaseException(strMessage)
        if iOverSigmaAtHighestResolution is None:
            self._iOverSigmaAtHighestResolution = None
        elif iOverSigmaAtHighestResolution.__class__.__name__ == "XSDataDouble":
            self._iOverSigmaAtHighestResolution = iOverSigmaAtHighestResolution
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration constructor argument 'iOverSigmaAtHighestResolution' is not XSDataDouble but %s"
                % self._iOverSigmaAtHighestResolution.__class__.__name__
            )
            raise BaseException(strMessage)
        if iOverSigmaOverall is None:
            self._iOverSigmaOverall = None
        elif iOverSigmaOverall.__class__.__name__ == "XSDataDouble":
            self._iOverSigmaOverall = iOverSigmaOverall
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration constructor argument 'iOverSigmaOverall' is not XSDataDouble but %s"
                % self._iOverSigmaOverall.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberOfBadReflections is None:
            self._numberOfBadReflections = None
        elif numberOfBadReflections.__class__.__name__ == "XSDataInteger":
            self._numberOfBadReflections = numberOfBadReflections
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration constructor argument 'numberOfBadReflections' is not XSDataInteger but %s"
                % self._numberOfBadReflections.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberOfFullyRecordedReflections is None:
            self._numberOfFullyRecordedReflections = None
        elif numberOfFullyRecordedReflections.__class__.__name__ == "XSDataInteger":
            self._numberOfFullyRecordedReflections = numberOfFullyRecordedReflections
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration constructor argument 'numberOfFullyRecordedReflections' is not XSDataInteger but %s"
                % self._numberOfFullyRecordedReflections.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberOfNegativeReflections is None:
            self._numberOfNegativeReflections = None
        elif numberOfNegativeReflections.__class__.__name__ == "XSDataInteger":
            self._numberOfNegativeReflections = numberOfNegativeReflections
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration constructor argument 'numberOfNegativeReflections' is not XSDataInteger but %s"
                % self._numberOfNegativeReflections.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberOfOverlappedReflections is None:
            self._numberOfOverlappedReflections = None
        elif numberOfOverlappedReflections.__class__.__name__ == "XSDataInteger":
            self._numberOfOverlappedReflections = numberOfOverlappedReflections
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration constructor argument 'numberOfOverlappedReflections' is not XSDataInteger but %s"
                % self._numberOfOverlappedReflections.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberOfPartialReflections is None:
            self._numberOfPartialReflections = None
        elif numberOfPartialReflections.__class__.__name__ == "XSDataInteger":
            self._numberOfPartialReflections = numberOfPartialReflections
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration constructor argument 'numberOfPartialReflections' is not XSDataInteger but %s"
                % self._numberOfPartialReflections.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberOfReflectionsGenerated is None:
            self._numberOfReflectionsGenerated = None
        elif numberOfReflectionsGenerated.__class__.__name__ == "XSDataInteger":
            self._numberOfReflectionsGenerated = numberOfReflectionsGenerated
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration constructor argument 'numberOfReflectionsGenerated' is not XSDataInteger but %s"
                % self._numberOfReflectionsGenerated.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'RMSSpotDeviation' attribute
    def getRMSSpotDeviation(self):
        return self._RMSSpotDeviation

    def setRMSSpotDeviation(self, RMSSpotDeviation):
        if RMSSpotDeviation is None:
            self._RMSSpotDeviation = None
        elif RMSSpotDeviation.__class__.__name__ == "XSDataLength":
            self._RMSSpotDeviation = RMSSpotDeviation
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration.setRMSSpotDeviation argument is not XSDataLength but %s"
                % RMSSpotDeviation.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRMSSpotDeviation(self):
        self._RMSSpotDeviation = None

    RMSSpotDeviation = property(
        getRMSSpotDeviation,
        setRMSSpotDeviation,
        delRMSSpotDeviation,
        "Property for RMSSpotDeviation",
    )
    # Methods and properties for the 'iOverSigmaAtHighestResolution' attribute

    def getIOverSigmaAtHighestResolution(self):
        return self._iOverSigmaAtHighestResolution

    def setIOverSigmaAtHighestResolution(self, iOverSigmaAtHighestResolution):
        if iOverSigmaAtHighestResolution is None:
            self._iOverSigmaAtHighestResolution = None
        elif iOverSigmaAtHighestResolution.__class__.__name__ == "XSDataDouble":
            self._iOverSigmaAtHighestResolution = iOverSigmaAtHighestResolution
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration.setIOverSigmaAtHighestResolution argument is not XSDataDouble but %s"
                % iOverSigmaAtHighestResolution.__class__.__name__
            )
            raise BaseException(strMessage)

    def delIOverSigmaAtHighestResolution(self):
        self._iOverSigmaAtHighestResolution = None

    iOverSigmaAtHighestResolution = property(
        getIOverSigmaAtHighestResolution,
        setIOverSigmaAtHighestResolution,
        delIOverSigmaAtHighestResolution,
        "Property for iOverSigmaAtHighestResolution",
    )
    # Methods and properties for the 'iOverSigmaOverall' attribute

    def getIOverSigmaOverall(self):
        return self._iOverSigmaOverall

    def setIOverSigmaOverall(self, iOverSigmaOverall):
        if iOverSigmaOverall is None:
            self._iOverSigmaOverall = None
        elif iOverSigmaOverall.__class__.__name__ == "XSDataDouble":
            self._iOverSigmaOverall = iOverSigmaOverall
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration.setIOverSigmaOverall argument is not XSDataDouble but %s"
                % iOverSigmaOverall.__class__.__name__
            )
            raise BaseException(strMessage)

    def delIOverSigmaOverall(self):
        self._iOverSigmaOverall = None

    iOverSigmaOverall = property(
        getIOverSigmaOverall,
        setIOverSigmaOverall,
        delIOverSigmaOverall,
        "Property for iOverSigmaOverall",
    )
    # Methods and properties for the 'numberOfBadReflections' attribute

    def getNumberOfBadReflections(self):
        return self._numberOfBadReflections

    def setNumberOfBadReflections(self, numberOfBadReflections):
        if numberOfBadReflections is None:
            self._numberOfBadReflections = None
        elif numberOfBadReflections.__class__.__name__ == "XSDataInteger":
            self._numberOfBadReflections = numberOfBadReflections
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration.setNumberOfBadReflections argument is not XSDataInteger but %s"
                % numberOfBadReflections.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberOfBadReflections(self):
        self._numberOfBadReflections = None

    numberOfBadReflections = property(
        getNumberOfBadReflections,
        setNumberOfBadReflections,
        delNumberOfBadReflections,
        "Property for numberOfBadReflections",
    )
    # Methods and properties for the 'numberOfFullyRecordedReflections' attribute

    def getNumberOfFullyRecordedReflections(self):
        return self._numberOfFullyRecordedReflections

    def setNumberOfFullyRecordedReflections(self, numberOfFullyRecordedReflections):
        if numberOfFullyRecordedReflections is None:
            self._numberOfFullyRecordedReflections = None
        elif numberOfFullyRecordedReflections.__class__.__name__ == "XSDataInteger":
            self._numberOfFullyRecordedReflections = numberOfFullyRecordedReflections
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration.setNumberOfFullyRecordedReflections argument is not XSDataInteger but %s"
                % numberOfFullyRecordedReflections.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberOfFullyRecordedReflections(self):
        self._numberOfFullyRecordedReflections = None

    numberOfFullyRecordedReflections = property(
        getNumberOfFullyRecordedReflections,
        setNumberOfFullyRecordedReflections,
        delNumberOfFullyRecordedReflections,
        "Property for numberOfFullyRecordedReflections",
    )
    # Methods and properties for the 'numberOfNegativeReflections' attribute

    def getNumberOfNegativeReflections(self):
        return self._numberOfNegativeReflections

    def setNumberOfNegativeReflections(self, numberOfNegativeReflections):
        if numberOfNegativeReflections is None:
            self._numberOfNegativeReflections = None
        elif numberOfNegativeReflections.__class__.__name__ == "XSDataInteger":
            self._numberOfNegativeReflections = numberOfNegativeReflections
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration.setNumberOfNegativeReflections argument is not XSDataInteger but %s"
                % numberOfNegativeReflections.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberOfNegativeReflections(self):
        self._numberOfNegativeReflections = None

    numberOfNegativeReflections = property(
        getNumberOfNegativeReflections,
        setNumberOfNegativeReflections,
        delNumberOfNegativeReflections,
        "Property for numberOfNegativeReflections",
    )
    # Methods and properties for the 'numberOfOverlappedReflections' attribute

    def getNumberOfOverlappedReflections(self):
        return self._numberOfOverlappedReflections

    def setNumberOfOverlappedReflections(self, numberOfOverlappedReflections):
        if numberOfOverlappedReflections is None:
            self._numberOfOverlappedReflections = None
        elif numberOfOverlappedReflections.__class__.__name__ == "XSDataInteger":
            self._numberOfOverlappedReflections = numberOfOverlappedReflections
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration.setNumberOfOverlappedReflections argument is not XSDataInteger but %s"
                % numberOfOverlappedReflections.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberOfOverlappedReflections(self):
        self._numberOfOverlappedReflections = None

    numberOfOverlappedReflections = property(
        getNumberOfOverlappedReflections,
        setNumberOfOverlappedReflections,
        delNumberOfOverlappedReflections,
        "Property for numberOfOverlappedReflections",
    )
    # Methods and properties for the 'numberOfPartialReflections' attribute

    def getNumberOfPartialReflections(self):
        return self._numberOfPartialReflections

    def setNumberOfPartialReflections(self, numberOfPartialReflections):
        if numberOfPartialReflections is None:
            self._numberOfPartialReflections = None
        elif numberOfPartialReflections.__class__.__name__ == "XSDataInteger":
            self._numberOfPartialReflections = numberOfPartialReflections
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration.setNumberOfPartialReflections argument is not XSDataInteger but %s"
                % numberOfPartialReflections.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberOfPartialReflections(self):
        self._numberOfPartialReflections = None

    numberOfPartialReflections = property(
        getNumberOfPartialReflections,
        setNumberOfPartialReflections,
        delNumberOfPartialReflections,
        "Property for numberOfPartialReflections",
    )
    # Methods and properties for the 'numberOfReflectionsGenerated' attribute

    def getNumberOfReflectionsGenerated(self):
        return self._numberOfReflectionsGenerated

    def setNumberOfReflectionsGenerated(self, numberOfReflectionsGenerated):
        if numberOfReflectionsGenerated is None:
            self._numberOfReflectionsGenerated = None
        elif numberOfReflectionsGenerated.__class__.__name__ == "XSDataInteger":
            self._numberOfReflectionsGenerated = numberOfReflectionsGenerated
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegration.setNumberOfReflectionsGenerated argument is not XSDataInteger but %s"
                % numberOfReflectionsGenerated.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberOfReflectionsGenerated(self):
        self._numberOfReflectionsGenerated = None

    numberOfReflectionsGenerated = property(
        getNumberOfReflectionsGenerated,
        setNumberOfReflectionsGenerated,
        delNumberOfReflectionsGenerated,
        "Property for numberOfReflectionsGenerated",
    )

    def export(self, outfile, level, name_="XSDataStatisticsIntegration"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataStatisticsIntegration"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._RMSSpotDeviation is not None:
            self.RMSSpotDeviation.export(outfile, level, name_="RMSSpotDeviation")
        else:
            warnEmptyAttribute("RMSSpotDeviation", "XSDataLength")
        if self._iOverSigmaAtHighestResolution is not None:
            self.iOverSigmaAtHighestResolution.export(
                outfile, level, name_="iOverSigmaAtHighestResolution"
            )
        else:
            warnEmptyAttribute("iOverSigmaAtHighestResolution", "XSDataDouble")
        if self._iOverSigmaOverall is not None:
            self.iOverSigmaOverall.export(outfile, level, name_="iOverSigmaOverall")
        else:
            warnEmptyAttribute("iOverSigmaOverall", "XSDataDouble")
        if self._numberOfBadReflections is not None:
            self.numberOfBadReflections.export(
                outfile, level, name_="numberOfBadReflections"
            )
        else:
            warnEmptyAttribute("numberOfBadReflections", "XSDataInteger")
        if self._numberOfFullyRecordedReflections is not None:
            self.numberOfFullyRecordedReflections.export(
                outfile, level, name_="numberOfFullyRecordedReflections"
            )
        else:
            warnEmptyAttribute("numberOfFullyRecordedReflections", "XSDataInteger")
        if self._numberOfNegativeReflections is not None:
            self.numberOfNegativeReflections.export(
                outfile, level, name_="numberOfNegativeReflections"
            )
        else:
            warnEmptyAttribute("numberOfNegativeReflections", "XSDataInteger")
        if self._numberOfOverlappedReflections is not None:
            self.numberOfOverlappedReflections.export(
                outfile, level, name_="numberOfOverlappedReflections"
            )
        else:
            warnEmptyAttribute("numberOfOverlappedReflections", "XSDataInteger")
        if self._numberOfPartialReflections is not None:
            self.numberOfPartialReflections.export(
                outfile, level, name_="numberOfPartialReflections"
            )
        else:
            warnEmptyAttribute("numberOfPartialReflections", "XSDataInteger")
        if self._numberOfReflectionsGenerated is not None:
            self.numberOfReflectionsGenerated.export(
                outfile, level, name_="numberOfReflectionsGenerated"
            )
        else:
            warnEmptyAttribute("numberOfReflectionsGenerated", "XSDataInteger")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "RMSSpotDeviation":
            obj_ = XSDataLength()
            obj_.build(child_)
            self.setRMSSpotDeviation(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "iOverSigmaAtHighestResolution"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setIOverSigmaAtHighestResolution(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "iOverSigmaOverall":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setIOverSigmaOverall(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "numberOfBadReflections"
        ):
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumberOfBadReflections(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "numberOfFullyRecordedReflections"
        ):
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumberOfFullyRecordedReflections(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "numberOfNegativeReflections"
        ):
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumberOfNegativeReflections(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "numberOfOverlappedReflections"
        ):
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumberOfOverlappedReflections(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "numberOfPartialReflections"
        ):
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumberOfPartialReflections(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "numberOfReflectionsGenerated"
        ):
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumberOfReflectionsGenerated(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataStatisticsIntegration")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataStatisticsIntegration")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataStatisticsIntegration is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataStatisticsIntegration.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataStatisticsIntegration()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataStatisticsIntegration")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataStatisticsIntegration()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataStatisticsIntegration


class XSDataStatisticsIntegrationPerReflectionType(XSData):
    def __init__(self, partials=None, fullyRecorded=None):
        XSData.__init__(self)
        if fullyRecorded is None:
            self._fullyRecorded = None
        elif (
            fullyRecorded.__class__.__name__
            == "XSDataStatisticsIntegrationAverageAndNumberOfReflections"
        ):
            self._fullyRecorded = fullyRecorded
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationPerReflectionType constructor argument 'fullyRecorded' is not XSDataStatisticsIntegrationAverageAndNumberOfReflections but %s"
                % self._fullyRecorded.__class__.__name__
            )
            raise BaseException(strMessage)
        if partials is None:
            self._partials = None
        elif (
            partials.__class__.__name__
            == "XSDataStatisticsIntegrationAverageAndNumberOfReflections"
        ):
            self._partials = partials
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationPerReflectionType constructor argument 'partials' is not XSDataStatisticsIntegrationAverageAndNumberOfReflections but %s"
                % self._partials.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'fullyRecorded' attribute
    def getFullyRecorded(self):
        return self._fullyRecorded

    def setFullyRecorded(self, fullyRecorded):
        if fullyRecorded is None:
            self._fullyRecorded = None
        elif (
            fullyRecorded.__class__.__name__
            == "XSDataStatisticsIntegrationAverageAndNumberOfReflections"
        ):
            self._fullyRecorded = fullyRecorded
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationPerReflectionType.setFullyRecorded argument is not XSDataStatisticsIntegrationAverageAndNumberOfReflections but %s"
                % fullyRecorded.__class__.__name__
            )
            raise BaseException(strMessage)

    def delFullyRecorded(self):
        self._fullyRecorded = None

    fullyRecorded = property(
        getFullyRecorded,
        setFullyRecorded,
        delFullyRecorded,
        "Property for fullyRecorded",
    )
    # Methods and properties for the 'partials' attribute

    def getPartials(self):
        return self._partials

    def setPartials(self, partials):
        if partials is None:
            self._partials = None
        elif (
            partials.__class__.__name__
            == "XSDataStatisticsIntegrationAverageAndNumberOfReflections"
        ):
            self._partials = partials
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationPerReflectionType.setPartials argument is not XSDataStatisticsIntegrationAverageAndNumberOfReflections but %s"
                % partials.__class__.__name__
            )
            raise BaseException(strMessage)

    def delPartials(self):
        self._partials = None

    partials = property(getPartials, setPartials, delPartials, "Property for partials")

    def export(
        self, outfile, level, name_="XSDataStatisticsIntegrationPerReflectionType"
    ):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(
        self, outfile, level, name_="XSDataStatisticsIntegrationPerReflectionType"
    ):
        XSData.exportChildren(self, outfile, level, name_)
        if self._fullyRecorded is not None:
            self.fullyRecorded.export(outfile, level, name_="fullyRecorded")
        else:
            warnEmptyAttribute(
                "fullyRecorded",
                "XSDataStatisticsIntegrationAverageAndNumberOfReflections",
            )
        if self._partials is not None:
            self.partials.export(outfile, level, name_="partials")
        else:
            warnEmptyAttribute(
                "partials", "XSDataStatisticsIntegrationAverageAndNumberOfReflections"
            )

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "fullyRecorded":
            obj_ = XSDataStatisticsIntegrationAverageAndNumberOfReflections()
            obj_.build(child_)
            self.setFullyRecorded(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "partials":
            obj_ = XSDataStatisticsIntegrationAverageAndNumberOfReflections()
            obj_.build(child_)
            self.setPartials(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(
            oStreamString, 0, name_="XSDataStatisticsIntegrationPerReflectionType"
        )
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataStatisticsIntegrationPerReflectionType")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataStatisticsIntegrationPerReflectionType is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataStatisticsIntegrationPerReflectionType.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataStatisticsIntegrationPerReflectionType()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(
            oStreamString, 0, name_="XSDataStatisticsIntegrationPerReflectionType"
        )
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataStatisticsIntegrationPerReflectionType()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataStatisticsIntegrationPerReflectionType


class XSDataStatisticsIntegrationPerResolutionBin(XSData):
    def __init__(
        self, summation=None, profileFitted=None, minResolution=None, maxResolution=None
    ):
        XSData.__init__(self)
        if maxResolution is None:
            self._maxResolution = None
        elif maxResolution.__class__.__name__ == "XSDataDouble":
            self._maxResolution = maxResolution
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationPerResolutionBin constructor argument 'maxResolution' is not XSDataDouble but %s"
                % self._maxResolution.__class__.__name__
            )
            raise BaseException(strMessage)
        if minResolution is None:
            self._minResolution = None
        elif minResolution.__class__.__name__ == "XSDataDouble":
            self._minResolution = minResolution
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationPerResolutionBin constructor argument 'minResolution' is not XSDataDouble but %s"
                % self._minResolution.__class__.__name__
            )
            raise BaseException(strMessage)
        if profileFitted is None:
            self._profileFitted = None
        elif (
            profileFitted.__class__.__name__
            == "XSDataStatisticsIntegrationPerReflectionType"
        ):
            self._profileFitted = profileFitted
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationPerResolutionBin constructor argument 'profileFitted' is not XSDataStatisticsIntegrationPerReflectionType but %s"
                % self._profileFitted.__class__.__name__
            )
            raise BaseException(strMessage)
        if summation is None:
            self._summation = None
        elif (
            summation.__class__.__name__
            == "XSDataStatisticsIntegrationPerReflectionType"
        ):
            self._summation = summation
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationPerResolutionBin constructor argument 'summation' is not XSDataStatisticsIntegrationPerReflectionType but %s"
                % self._summation.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'maxResolution' attribute
    def getMaxResolution(self):
        return self._maxResolution

    def setMaxResolution(self, maxResolution):
        if maxResolution is None:
            self._maxResolution = None
        elif maxResolution.__class__.__name__ == "XSDataDouble":
            self._maxResolution = maxResolution
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationPerResolutionBin.setMaxResolution argument is not XSDataDouble but %s"
                % maxResolution.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMaxResolution(self):
        self._maxResolution = None

    maxResolution = property(
        getMaxResolution,
        setMaxResolution,
        delMaxResolution,
        "Property for maxResolution",
    )
    # Methods and properties for the 'minResolution' attribute

    def getMinResolution(self):
        return self._minResolution

    def setMinResolution(self, minResolution):
        if minResolution is None:
            self._minResolution = None
        elif minResolution.__class__.__name__ == "XSDataDouble":
            self._minResolution = minResolution
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationPerResolutionBin.setMinResolution argument is not XSDataDouble but %s"
                % minResolution.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMinResolution(self):
        self._minResolution = None

    minResolution = property(
        getMinResolution,
        setMinResolution,
        delMinResolution,
        "Property for minResolution",
    )
    # Methods and properties for the 'profileFitted' attribute

    def getProfileFitted(self):
        return self._profileFitted

    def setProfileFitted(self, profileFitted):
        if profileFitted is None:
            self._profileFitted = None
        elif (
            profileFitted.__class__.__name__
            == "XSDataStatisticsIntegrationPerReflectionType"
        ):
            self._profileFitted = profileFitted
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationPerResolutionBin.setProfileFitted argument is not XSDataStatisticsIntegrationPerReflectionType but %s"
                % profileFitted.__class__.__name__
            )
            raise BaseException(strMessage)

    def delProfileFitted(self):
        self._profileFitted = None

    profileFitted = property(
        getProfileFitted,
        setProfileFitted,
        delProfileFitted,
        "Property for profileFitted",
    )
    # Methods and properties for the 'summation' attribute

    def getSummation(self):
        return self._summation

    def setSummation(self, summation):
        if summation is None:
            self._summation = None
        elif (
            summation.__class__.__name__
            == "XSDataStatisticsIntegrationPerReflectionType"
        ):
            self._summation = summation
        else:
            strMessage = (
                "ERROR! XSDataStatisticsIntegrationPerResolutionBin.setSummation argument is not XSDataStatisticsIntegrationPerReflectionType but %s"
                % summation.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSummation(self):
        self._summation = None

    summation = property(
        getSummation, setSummation, delSummation, "Property for summation"
    )

    def export(
        self, outfile, level, name_="XSDataStatisticsIntegrationPerResolutionBin"
    ):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(
        self, outfile, level, name_="XSDataStatisticsIntegrationPerResolutionBin"
    ):
        XSData.exportChildren(self, outfile, level, name_)
        if self._maxResolution is not None:
            self.maxResolution.export(outfile, level, name_="maxResolution")
        else:
            warnEmptyAttribute("maxResolution", "XSDataDouble")
        if self._minResolution is not None:
            self.minResolution.export(outfile, level, name_="minResolution")
        else:
            warnEmptyAttribute("minResolution", "XSDataDouble")
        if self._profileFitted is not None:
            self.profileFitted.export(outfile, level, name_="profileFitted")
        else:
            warnEmptyAttribute(
                "profileFitted", "XSDataStatisticsIntegrationPerReflectionType"
            )
        if self._summation is not None:
            self.summation.export(outfile, level, name_="summation")
        else:
            warnEmptyAttribute(
                "summation", "XSDataStatisticsIntegrationPerReflectionType"
            )

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "maxResolution":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setMaxResolution(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "minResolution":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setMinResolution(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "profileFitted":
            obj_ = XSDataStatisticsIntegrationPerReflectionType()
            obj_.build(child_)
            self.setProfileFitted(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "summation":
            obj_ = XSDataStatisticsIntegrationPerReflectionType()
            obj_.build(child_)
            self.setSummation(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(
            oStreamString, 0, name_="XSDataStatisticsIntegrationPerResolutionBin"
        )
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataStatisticsIntegrationPerResolutionBin")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataStatisticsIntegrationPerResolutionBin is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataStatisticsIntegrationPerResolutionBin.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataStatisticsIntegrationPerResolutionBin()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(
            oStreamString, 0, name_="XSDataStatisticsIntegrationPerResolutionBin"
        )
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataStatisticsIntegrationPerResolutionBin()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataStatisticsIntegrationPerResolutionBin


class XSDataStatisticsStrategy(XSData):
    def __init__(self, resolutionBin=None):
        XSData.__init__(self)
        if resolutionBin is None:
            self._resolutionBin = []
        elif resolutionBin.__class__.__name__ == "list":
            self._resolutionBin = resolutionBin
        else:
            strMessage = (
                "ERROR! XSDataStatisticsStrategy constructor argument 'resolutionBin' is not list but %s"
                % self._resolutionBin.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'resolutionBin' attribute
    def getResolutionBin(self):
        return self._resolutionBin

    def setResolutionBin(self, resolutionBin):
        if resolutionBin is None:
            self._resolutionBin = []
        elif resolutionBin.__class__.__name__ == "list":
            self._resolutionBin = resolutionBin
        else:
            strMessage = (
                "ERROR! XSDataStatisticsStrategy.setResolutionBin argument is not list but %s"
                % resolutionBin.__class__.__name__
            )
            raise BaseException(strMessage)

    def delResolutionBin(self):
        self._resolutionBin = None

    resolutionBin = property(
        getResolutionBin,
        setResolutionBin,
        delResolutionBin,
        "Property for resolutionBin",
    )

    def addResolutionBin(self, value):
        if value is None:
            strMessage = (
                "ERROR! XSDataStatisticsStrategy.addResolutionBin argument is None"
            )
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataResolutionBin":
            self._resolutionBin.append(value)
        else:
            strMessage = (
                "ERROR! XSDataStatisticsStrategy.addResolutionBin argument is not XSDataResolutionBin but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertResolutionBin(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataStatisticsStrategy.insertResolutionBin argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataStatisticsStrategy.insertResolutionBin argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataResolutionBin":
            self._resolutionBin[index] = value
        else:
            strMessage = (
                "ERROR! XSDataStatisticsStrategy.addResolutionBin argument is not XSDataResolutionBin but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def export(self, outfile, level, name_="XSDataStatisticsStrategy"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataStatisticsStrategy"):
        XSData.exportChildren(self, outfile, level, name_)
        for resolutionBin_ in self.getResolutionBin():
            resolutionBin_.export(outfile, level, name_="resolutionBin")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "resolutionBin":
            obj_ = XSDataResolutionBin()
            obj_.build(child_)
            self.resolutionBin.append(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataStatisticsStrategy")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataStatisticsStrategy")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataStatisticsStrategy is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataStatisticsStrategy.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataStatisticsStrategy()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataStatisticsStrategy")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataStatisticsStrategy()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataStatisticsStrategy


class XSDataStrategySummary(XSData):
    """OBS! The attribute "attenuation" in XSDataStrategySummary is deprecated, see bug #379. Please use instead "transmission" in XSDataBeam."""

    def __init__(
        self,
        totalExposureTime=None,
        totalDataCollectionTime=None,
        resolutionReasoning=None,
        resolution=None,
        redundancy=None,
        rankingResolution=None,
        iSigma=None,
        completeness=None,
        attenuation=None,
    ):
        XSData.__init__(self)
        if attenuation is None:
            self._attenuation = None
        elif attenuation.__class__.__name__ == "XSDataDouble":
            self._attenuation = attenuation
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary constructor argument 'attenuation' is not XSDataDouble but %s"
                % self._attenuation.__class__.__name__
            )
            raise BaseException(strMessage)
        if completeness is None:
            self._completeness = None
        elif completeness.__class__.__name__ == "XSDataDouble":
            self._completeness = completeness
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary constructor argument 'completeness' is not XSDataDouble but %s"
                % self._completeness.__class__.__name__
            )
            raise BaseException(strMessage)
        if iSigma is None:
            self._iSigma = None
        elif iSigma.__class__.__name__ == "XSDataDouble":
            self._iSigma = iSigma
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary constructor argument 'iSigma' is not XSDataDouble but %s"
                % self._iSigma.__class__.__name__
            )
            raise BaseException(strMessage)
        if rankingResolution is None:
            self._rankingResolution = None
        elif rankingResolution.__class__.__name__ == "XSDataDouble":
            self._rankingResolution = rankingResolution
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary constructor argument 'rankingResolution' is not XSDataDouble but %s"
                % self._rankingResolution.__class__.__name__
            )
            raise BaseException(strMessage)
        if redundancy is None:
            self._redundancy = None
        elif redundancy.__class__.__name__ == "XSDataDouble":
            self._redundancy = redundancy
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary constructor argument 'redundancy' is not XSDataDouble but %s"
                % self._redundancy.__class__.__name__
            )
            raise BaseException(strMessage)
        if resolution is None:
            self._resolution = None
        elif resolution.__class__.__name__ == "XSDataDouble":
            self._resolution = resolution
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary constructor argument 'resolution' is not XSDataDouble but %s"
                % self._resolution.__class__.__name__
            )
            raise BaseException(strMessage)
        if resolutionReasoning is None:
            self._resolutionReasoning = None
        elif resolutionReasoning.__class__.__name__ == "XSDataString":
            self._resolutionReasoning = resolutionReasoning
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary constructor argument 'resolutionReasoning' is not XSDataString but %s"
                % self._resolutionReasoning.__class__.__name__
            )
            raise BaseException(strMessage)
        if totalDataCollectionTime is None:
            self._totalDataCollectionTime = None
        elif totalDataCollectionTime.__class__.__name__ == "XSDataTime":
            self._totalDataCollectionTime = totalDataCollectionTime
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary constructor argument 'totalDataCollectionTime' is not XSDataTime but %s"
                % self._totalDataCollectionTime.__class__.__name__
            )
            raise BaseException(strMessage)
        if totalExposureTime is None:
            self._totalExposureTime = None
        elif totalExposureTime.__class__.__name__ == "XSDataTime":
            self._totalExposureTime = totalExposureTime
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary constructor argument 'totalExposureTime' is not XSDataTime but %s"
                % self._totalExposureTime.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'attenuation' attribute
    def getAttenuation(self):
        return self._attenuation

    def setAttenuation(self, attenuation):
        if attenuation is None:
            self._attenuation = None
        elif attenuation.__class__.__name__ == "XSDataDouble":
            self._attenuation = attenuation
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary.setAttenuation argument is not XSDataDouble but %s"
                % attenuation.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAttenuation(self):
        self._attenuation = None

    attenuation = property(
        getAttenuation, setAttenuation, delAttenuation, "Property for attenuation"
    )
    # Methods and properties for the 'completeness' attribute

    def getCompleteness(self):
        return self._completeness

    def setCompleteness(self, completeness):
        if completeness is None:
            self._completeness = None
        elif completeness.__class__.__name__ == "XSDataDouble":
            self._completeness = completeness
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary.setCompleteness argument is not XSDataDouble but %s"
                % completeness.__class__.__name__
            )
            raise BaseException(strMessage)

    def delCompleteness(self):
        self._completeness = None

    completeness = property(
        getCompleteness, setCompleteness, delCompleteness, "Property for completeness"
    )
    # Methods and properties for the 'iSigma' attribute

    def getISigma(self):
        return self._iSigma

    def setISigma(self, iSigma):
        if iSigma is None:
            self._iSigma = None
        elif iSigma.__class__.__name__ == "XSDataDouble":
            self._iSigma = iSigma
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary.setISigma argument is not XSDataDouble but %s"
                % iSigma.__class__.__name__
            )
            raise BaseException(strMessage)

    def delISigma(self):
        self._iSigma = None

    iSigma = property(getISigma, setISigma, delISigma, "Property for iSigma")
    # Methods and properties for the 'rankingResolution' attribute

    def getRankingResolution(self):
        return self._rankingResolution

    def setRankingResolution(self, rankingResolution):
        if rankingResolution is None:
            self._rankingResolution = None
        elif rankingResolution.__class__.__name__ == "XSDataDouble":
            self._rankingResolution = rankingResolution
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary.setRankingResolution argument is not XSDataDouble but %s"
                % rankingResolution.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRankingResolution(self):
        self._rankingResolution = None

    rankingResolution = property(
        getRankingResolution,
        setRankingResolution,
        delRankingResolution,
        "Property for rankingResolution",
    )
    # Methods and properties for the 'redundancy' attribute

    def getRedundancy(self):
        return self._redundancy

    def setRedundancy(self, redundancy):
        if redundancy is None:
            self._redundancy = None
        elif redundancy.__class__.__name__ == "XSDataDouble":
            self._redundancy = redundancy
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary.setRedundancy argument is not XSDataDouble but %s"
                % redundancy.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRedundancy(self):
        self._redundancy = None

    redundancy = property(
        getRedundancy, setRedundancy, delRedundancy, "Property for redundancy"
    )
    # Methods and properties for the 'resolution' attribute

    def getResolution(self):
        return self._resolution

    def setResolution(self, resolution):
        if resolution is None:
            self._resolution = None
        elif resolution.__class__.__name__ == "XSDataDouble":
            self._resolution = resolution
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary.setResolution argument is not XSDataDouble but %s"
                % resolution.__class__.__name__
            )
            raise BaseException(strMessage)

    def delResolution(self):
        self._resolution = None

    resolution = property(
        getResolution, setResolution, delResolution, "Property for resolution"
    )
    # Methods and properties for the 'resolutionReasoning' attribute

    def getResolutionReasoning(self):
        return self._resolutionReasoning

    def setResolutionReasoning(self, resolutionReasoning):
        if resolutionReasoning is None:
            self._resolutionReasoning = None
        elif resolutionReasoning.__class__.__name__ == "XSDataString":
            self._resolutionReasoning = resolutionReasoning
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary.setResolutionReasoning argument is not XSDataString but %s"
                % resolutionReasoning.__class__.__name__
            )
            raise BaseException(strMessage)

    def delResolutionReasoning(self):
        self._resolutionReasoning = None

    resolutionReasoning = property(
        getResolutionReasoning,
        setResolutionReasoning,
        delResolutionReasoning,
        "Property for resolutionReasoning",
    )
    # Methods and properties for the 'totalDataCollectionTime' attribute

    def getTotalDataCollectionTime(self):
        return self._totalDataCollectionTime

    def setTotalDataCollectionTime(self, totalDataCollectionTime):
        if totalDataCollectionTime is None:
            self._totalDataCollectionTime = None
        elif totalDataCollectionTime.__class__.__name__ == "XSDataTime":
            self._totalDataCollectionTime = totalDataCollectionTime
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary.setTotalDataCollectionTime argument is not XSDataTime but %s"
                % totalDataCollectionTime.__class__.__name__
            )
            raise BaseException(strMessage)

    def delTotalDataCollectionTime(self):
        self._totalDataCollectionTime = None

    totalDataCollectionTime = property(
        getTotalDataCollectionTime,
        setTotalDataCollectionTime,
        delTotalDataCollectionTime,
        "Property for totalDataCollectionTime",
    )
    # Methods and properties for the 'totalExposureTime' attribute

    def getTotalExposureTime(self):
        return self._totalExposureTime

    def setTotalExposureTime(self, totalExposureTime):
        if totalExposureTime is None:
            self._totalExposureTime = None
        elif totalExposureTime.__class__.__name__ == "XSDataTime":
            self._totalExposureTime = totalExposureTime
        else:
            strMessage = (
                "ERROR! XSDataStrategySummary.setTotalExposureTime argument is not XSDataTime but %s"
                % totalExposureTime.__class__.__name__
            )
            raise BaseException(strMessage)

    def delTotalExposureTime(self):
        self._totalExposureTime = None

    totalExposureTime = property(
        getTotalExposureTime,
        setTotalExposureTime,
        delTotalExposureTime,
        "Property for totalExposureTime",
    )

    def export(self, outfile, level, name_="XSDataStrategySummary"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataStrategySummary"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._attenuation is not None:
            self.attenuation.export(outfile, level, name_="attenuation")
        if self._completeness is not None:
            self.completeness.export(outfile, level, name_="completeness")
        else:
            warnEmptyAttribute("completeness", "XSDataDouble")
        if self._iSigma is not None:
            self.iSigma.export(outfile, level, name_="iSigma")
        else:
            warnEmptyAttribute("iSigma", "XSDataDouble")
        if self._rankingResolution is not None:
            self.rankingResolution.export(outfile, level, name_="rankingResolution")
        else:
            warnEmptyAttribute("rankingResolution", "XSDataDouble")
        if self._redundancy is not None:
            self.redundancy.export(outfile, level, name_="redundancy")
        else:
            warnEmptyAttribute("redundancy", "XSDataDouble")
        if self._resolution is not None:
            self.resolution.export(outfile, level, name_="resolution")
        else:
            warnEmptyAttribute("resolution", "XSDataDouble")
        if self._resolutionReasoning is not None:
            self.resolutionReasoning.export(outfile, level, name_="resolutionReasoning")
        else:
            warnEmptyAttribute("resolutionReasoning", "XSDataString")
        if self._totalDataCollectionTime is not None:
            self.totalDataCollectionTime.export(
                outfile, level, name_="totalDataCollectionTime"
            )
        else:
            warnEmptyAttribute("totalDataCollectionTime", "XSDataTime")
        if self._totalExposureTime is not None:
            self.totalExposureTime.export(outfile, level, name_="totalExposureTime")
        else:
            warnEmptyAttribute("totalExposureTime", "XSDataTime")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "attenuation":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setAttenuation(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "completeness":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setCompleteness(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "iSigma":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setISigma(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "rankingResolution":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setRankingResolution(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "redundancy":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setRedundancy(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "resolution":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setResolution(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "resolutionReasoning"
        ):
            obj_ = XSDataString()
            obj_.build(child_)
            self.setResolutionReasoning(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "totalDataCollectionTime"
        ):
            obj_ = XSDataTime()
            obj_.build(child_)
            self.setTotalDataCollectionTime(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "totalExposureTime":
            obj_ = XSDataTime()
            obj_.build(child_)
            self.setTotalExposureTime(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataStrategySummary")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataStrategySummary")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataStrategySummary is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataStrategySummary.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataStrategySummary()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataStrategySummary")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataStrategySummary()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataStrategySummary


class XSDataCollectionPlan(XSData):
    """The comment can be used for describing exotic data collections, for example without collecting any images."""

    def __init__(
        self,
        strategySummary=None,
        statistics=None,
        comment=None,
        collectionStrategy=None,
        collectionPlanNumber=None,
    ):
        XSData.__init__(self)
        if collectionPlanNumber is None:
            self._collectionPlanNumber = None
        elif collectionPlanNumber.__class__.__name__ == "XSDataInteger":
            self._collectionPlanNumber = collectionPlanNumber
        else:
            strMessage = (
                "ERROR! XSDataCollectionPlan constructor argument 'collectionPlanNumber' is not XSDataInteger but %s"
                % self._collectionPlanNumber.__class__.__name__
            )
            raise BaseException(strMessage)
        if collectionStrategy is None:
            self._collectionStrategy = None
        elif collectionStrategy.__class__.__name__ == "XSDataCollection":
            self._collectionStrategy = collectionStrategy
        else:
            strMessage = (
                "ERROR! XSDataCollectionPlan constructor argument 'collectionStrategy' is not XSDataCollection but %s"
                % self._collectionStrategy.__class__.__name__
            )
            raise BaseException(strMessage)
        if comment is None:
            self._comment = None
        elif comment.__class__.__name__ == "XSDataString":
            self._comment = comment
        else:
            strMessage = (
                "ERROR! XSDataCollectionPlan constructor argument 'comment' is not XSDataString but %s"
                % self._comment.__class__.__name__
            )
            raise BaseException(strMessage)
        if statistics is None:
            self._statistics = None
        elif statistics.__class__.__name__ == "XSDataStatisticsStrategy":
            self._statistics = statistics
        else:
            strMessage = (
                "ERROR! XSDataCollectionPlan constructor argument 'statistics' is not XSDataStatisticsStrategy but %s"
                % self._statistics.__class__.__name__
            )
            raise BaseException(strMessage)
        if strategySummary is None:
            self._strategySummary = None
        elif strategySummary.__class__.__name__ == "XSDataStrategySummary":
            self._strategySummary = strategySummary
        else:
            strMessage = (
                "ERROR! XSDataCollectionPlan constructor argument 'strategySummary' is not XSDataStrategySummary but %s"
                % self._strategySummary.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'collectionPlanNumber' attribute
    def getCollectionPlanNumber(self):
        return self._collectionPlanNumber

    def setCollectionPlanNumber(self, collectionPlanNumber):
        if collectionPlanNumber is None:
            self._collectionPlanNumber = None
        elif collectionPlanNumber.__class__.__name__ == "XSDataInteger":
            self._collectionPlanNumber = collectionPlanNumber
        else:
            strMessage = (
                "ERROR! XSDataCollectionPlan.setCollectionPlanNumber argument is not XSDataInteger but %s"
                % collectionPlanNumber.__class__.__name__
            )
            raise BaseException(strMessage)

    def delCollectionPlanNumber(self):
        self._collectionPlanNumber = None

    collectionPlanNumber = property(
        getCollectionPlanNumber,
        setCollectionPlanNumber,
        delCollectionPlanNumber,
        "Property for collectionPlanNumber",
    )
    # Methods and properties for the 'collectionStrategy' attribute

    def getCollectionStrategy(self):
        return self._collectionStrategy

    def setCollectionStrategy(self, collectionStrategy):
        if collectionStrategy is None:
            self._collectionStrategy = None
        elif collectionStrategy.__class__.__name__ == "XSDataCollection":
            self._collectionStrategy = collectionStrategy
        else:
            strMessage = (
                "ERROR! XSDataCollectionPlan.setCollectionStrategy argument is not XSDataCollection but %s"
                % collectionStrategy.__class__.__name__
            )
            raise BaseException(strMessage)

    def delCollectionStrategy(self):
        self._collectionStrategy = None

    collectionStrategy = property(
        getCollectionStrategy,
        setCollectionStrategy,
        delCollectionStrategy,
        "Property for collectionStrategy",
    )
    # Methods and properties for the 'comment' attribute

    def getComment(self):
        return self._comment

    def setComment(self, comment):
        if comment is None:
            self._comment = None
        elif comment.__class__.__name__ == "XSDataString":
            self._comment = comment
        else:
            strMessage = (
                "ERROR! XSDataCollectionPlan.setComment argument is not XSDataString but %s"
                % comment.__class__.__name__
            )
            raise BaseException(strMessage)

    def delComment(self):
        self._comment = None

    comment = property(getComment, setComment, delComment, "Property for comment")
    # Methods and properties for the 'statistics' attribute

    def getStatistics(self):
        return self._statistics

    def setStatistics(self, statistics):
        if statistics is None:
            self._statistics = None
        elif statistics.__class__.__name__ == "XSDataStatisticsStrategy":
            self._statistics = statistics
        else:
            strMessage = (
                "ERROR! XSDataCollectionPlan.setStatistics argument is not XSDataStatisticsStrategy but %s"
                % statistics.__class__.__name__
            )
            raise BaseException(strMessage)

    def delStatistics(self):
        self._statistics = None

    statistics = property(
        getStatistics, setStatistics, delStatistics, "Property for statistics"
    )
    # Methods and properties for the 'strategySummary' attribute

    def getStrategySummary(self):
        return self._strategySummary

    def setStrategySummary(self, strategySummary):
        if strategySummary is None:
            self._strategySummary = None
        elif strategySummary.__class__.__name__ == "XSDataStrategySummary":
            self._strategySummary = strategySummary
        else:
            strMessage = (
                "ERROR! XSDataCollectionPlan.setStrategySummary argument is not XSDataStrategySummary but %s"
                % strategySummary.__class__.__name__
            )
            raise BaseException(strMessage)

    def delStrategySummary(self):
        self._strategySummary = None

    strategySummary = property(
        getStrategySummary,
        setStrategySummary,
        delStrategySummary,
        "Property for strategySummary",
    )

    def export(self, outfile, level, name_="XSDataCollectionPlan"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataCollectionPlan"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._collectionPlanNumber is not None:
            self.collectionPlanNumber.export(
                outfile, level, name_="collectionPlanNumber"
            )
        else:
            warnEmptyAttribute("collectionPlanNumber", "XSDataInteger")
        if self._collectionStrategy is not None:
            self.collectionStrategy.export(outfile, level, name_="collectionStrategy")
        else:
            warnEmptyAttribute("collectionStrategy", "XSDataCollection")
        if self._comment is not None:
            self.comment.export(outfile, level, name_="comment")
        if self._statistics is not None:
            self.statistics.export(outfile, level, name_="statistics")
        else:
            warnEmptyAttribute("statistics", "XSDataStatisticsStrategy")
        if self._strategySummary is not None:
            self.strategySummary.export(outfile, level, name_="strategySummary")
        else:
            warnEmptyAttribute("strategySummary", "XSDataStrategySummary")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "collectionPlanNumber":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setCollectionPlanNumber(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "collectionStrategy":
            obj_ = XSDataCollection()
            obj_.build(child_)
            self.setCollectionStrategy(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "comment":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setComment(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "statistics":
            obj_ = XSDataStatisticsStrategy()
            obj_.build(child_)
            self.setStatistics(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "strategySummary":
            obj_ = XSDataStrategySummary()
            obj_.build(child_)
            self.setStrategySummary(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataCollectionPlan")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataCollectionPlan")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataCollectionPlan is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataCollectionPlan.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataCollectionPlan()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataCollectionPlan")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataCollectionPlan()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataCollectionPlan


class XSDataCrystal(XSData):
    """Crystallographic properties"""

    def __init__(self, spaceGroup=None, mosaicity=None, cell=None):
        XSData.__init__(self)
        if cell is None:
            self._cell = None
        elif cell.__class__.__name__ == "XSDataCell":
            self._cell = cell
        else:
            strMessage = (
                "ERROR! XSDataCrystal constructor argument 'cell' is not XSDataCell but %s"
                % self._cell.__class__.__name__
            )
            raise BaseException(strMessage)
        if mosaicity is None:
            self._mosaicity = None
        elif mosaicity.__class__.__name__ == "XSDataDouble":
            self._mosaicity = mosaicity
        else:
            strMessage = (
                "ERROR! XSDataCrystal constructor argument 'mosaicity' is not XSDataDouble but %s"
                % self._mosaicity.__class__.__name__
            )
            raise BaseException(strMessage)
        if spaceGroup is None:
            self._spaceGroup = None
        elif spaceGroup.__class__.__name__ == "XSDataSpaceGroup":
            self._spaceGroup = spaceGroup
        else:
            strMessage = (
                "ERROR! XSDataCrystal constructor argument 'spaceGroup' is not XSDataSpaceGroup but %s"
                % self._spaceGroup.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'cell' attribute
    def getCell(self):
        return self._cell

    def setCell(self, cell):
        if cell is None:
            self._cell = None
        elif cell.__class__.__name__ == "XSDataCell":
            self._cell = cell
        else:
            strMessage = (
                "ERROR! XSDataCrystal.setCell argument is not XSDataCell but %s"
                % cell.__class__.__name__
            )
            raise BaseException(strMessage)

    def delCell(self):
        self._cell = None

    cell = property(getCell, setCell, delCell, "Property for cell")
    # Methods and properties for the 'mosaicity' attribute

    def getMosaicity(self):
        return self._mosaicity

    def setMosaicity(self, mosaicity):
        if mosaicity is None:
            self._mosaicity = None
        elif mosaicity.__class__.__name__ == "XSDataDouble":
            self._mosaicity = mosaicity
        else:
            strMessage = (
                "ERROR! XSDataCrystal.setMosaicity argument is not XSDataDouble but %s"
                % mosaicity.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMosaicity(self):
        self._mosaicity = None

    mosaicity = property(
        getMosaicity, setMosaicity, delMosaicity, "Property for mosaicity"
    )
    # Methods and properties for the 'spaceGroup' attribute

    def getSpaceGroup(self):
        return self._spaceGroup

    def setSpaceGroup(self, spaceGroup):
        if spaceGroup is None:
            self._spaceGroup = None
        elif spaceGroup.__class__.__name__ == "XSDataSpaceGroup":
            self._spaceGroup = spaceGroup
        else:
            strMessage = (
                "ERROR! XSDataCrystal.setSpaceGroup argument is not XSDataSpaceGroup but %s"
                % spaceGroup.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSpaceGroup(self):
        self._spaceGroup = None

    spaceGroup = property(
        getSpaceGroup, setSpaceGroup, delSpaceGroup, "Property for spaceGroup"
    )

    def export(self, outfile, level, name_="XSDataCrystal"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataCrystal"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._cell is not None:
            self.cell.export(outfile, level, name_="cell")
        else:
            warnEmptyAttribute("cell", "XSDataCell")
        if self._mosaicity is not None:
            self.mosaicity.export(outfile, level, name_="mosaicity")
        if self._spaceGroup is not None:
            self.spaceGroup.export(outfile, level, name_="spaceGroup")
        else:
            warnEmptyAttribute("spaceGroup", "XSDataSpaceGroup")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "cell":
            obj_ = XSDataCell()
            obj_.build(child_)
            self.setCell(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "mosaicity":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setMosaicity(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "spaceGroup":
            obj_ = XSDataSpaceGroup()
            obj_.build(child_)
            self.setSpaceGroup(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataCrystal")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataCrystal")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataCrystal is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataCrystal.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataCrystal()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataCrystal")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataCrystal()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataCrystal


class XSDataStructure(XSData):
    """This is the polymer structure composed by a list of chains and a list of ligands.
This structure is also defined by its number in the asymmetric unit."""

    def __init__(self, numberOfCopiesInAsymmetricUnit=None, ligand=None, chain=None):
        XSData.__init__(self)
        if chain is None:
            self._chain = []
        elif chain.__class__.__name__ == "list":
            self._chain = chain
        else:
            strMessage = (
                "ERROR! XSDataStructure constructor argument 'chain' is not list but %s"
                % self._chain.__class__.__name__
            )
            raise BaseException(strMessage)
        if ligand is None:
            self._ligand = []
        elif ligand.__class__.__name__ == "list":
            self._ligand = ligand
        else:
            strMessage = (
                "ERROR! XSDataStructure constructor argument 'ligand' is not list but %s"
                % self._ligand.__class__.__name__
            )
            raise BaseException(strMessage)
        if numberOfCopiesInAsymmetricUnit is None:
            self._numberOfCopiesInAsymmetricUnit = None
        elif numberOfCopiesInAsymmetricUnit.__class__.__name__ == "XSDataDouble":
            self._numberOfCopiesInAsymmetricUnit = numberOfCopiesInAsymmetricUnit
        else:
            strMessage = (
                "ERROR! XSDataStructure constructor argument 'numberOfCopiesInAsymmetricUnit' is not XSDataDouble but %s"
                % self._numberOfCopiesInAsymmetricUnit.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'chain' attribute
    def getChain(self):
        return self._chain

    def setChain(self, chain):
        if chain is None:
            self._chain = []
        elif chain.__class__.__name__ == "list":
            self._chain = chain
        else:
            strMessage = (
                "ERROR! XSDataStructure.setChain argument is not list but %s"
                % chain.__class__.__name__
            )
            raise BaseException(strMessage)

    def delChain(self):
        self._chain = None

    chain = property(getChain, setChain, delChain, "Property for chain")

    def addChain(self, value):
        if value is None:
            strMessage = "ERROR! XSDataStructure.addChain argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataChain":
            self._chain.append(value)
        else:
            strMessage = (
                "ERROR! XSDataStructure.addChain argument is not XSDataChain but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertChain(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataStructure.insertChain argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataStructure.insertChain argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataChain":
            self._chain[index] = value
        else:
            strMessage = (
                "ERROR! XSDataStructure.addChain argument is not XSDataChain but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'ligand' attribute
    def getLigand(self):
        return self._ligand

    def setLigand(self, ligand):
        if ligand is None:
            self._ligand = []
        elif ligand.__class__.__name__ == "list":
            self._ligand = ligand
        else:
            strMessage = (
                "ERROR! XSDataStructure.setLigand argument is not list but %s"
                % ligand.__class__.__name__
            )
            raise BaseException(strMessage)

    def delLigand(self):
        self._ligand = None

    ligand = property(getLigand, setLigand, delLigand, "Property for ligand")

    def addLigand(self, value):
        if value is None:
            strMessage = "ERROR! XSDataStructure.addLigand argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataLigand":
            self._ligand.append(value)
        else:
            strMessage = (
                "ERROR! XSDataStructure.addLigand argument is not XSDataLigand but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertLigand(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataStructure.insertLigand argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataStructure.insertLigand argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataLigand":
            self._ligand[index] = value
        else:
            strMessage = (
                "ERROR! XSDataStructure.addLigand argument is not XSDataLigand but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'numberOfCopiesInAsymmetricUnit' attribute
    def getNumberOfCopiesInAsymmetricUnit(self):
        return self._numberOfCopiesInAsymmetricUnit

    def setNumberOfCopiesInAsymmetricUnit(self, numberOfCopiesInAsymmetricUnit):
        if numberOfCopiesInAsymmetricUnit is None:
            self._numberOfCopiesInAsymmetricUnit = None
        elif numberOfCopiesInAsymmetricUnit.__class__.__name__ == "XSDataDouble":
            self._numberOfCopiesInAsymmetricUnit = numberOfCopiesInAsymmetricUnit
        else:
            strMessage = (
                "ERROR! XSDataStructure.setNumberOfCopiesInAsymmetricUnit argument is not XSDataDouble but %s"
                % numberOfCopiesInAsymmetricUnit.__class__.__name__
            )
            raise BaseException(strMessage)

    def delNumberOfCopiesInAsymmetricUnit(self):
        self._numberOfCopiesInAsymmetricUnit = None

    numberOfCopiesInAsymmetricUnit = property(
        getNumberOfCopiesInAsymmetricUnit,
        setNumberOfCopiesInAsymmetricUnit,
        delNumberOfCopiesInAsymmetricUnit,
        "Property for numberOfCopiesInAsymmetricUnit",
    )

    def export(self, outfile, level, name_="XSDataStructure"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataStructure"):
        XSData.exportChildren(self, outfile, level, name_)
        for chain_ in self.getChain():
            chain_.export(outfile, level, name_="chain")
        for ligand_ in self.getLigand():
            ligand_.export(outfile, level, name_="ligand")
        if self._numberOfCopiesInAsymmetricUnit is not None:
            self.numberOfCopiesInAsymmetricUnit.export(
                outfile, level, name_="numberOfCopiesInAsymmetricUnit"
            )
        else:
            warnEmptyAttribute("numberOfCopiesInAsymmetricUnit", "XSDataDouble")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "chain":
            obj_ = XSDataChain()
            obj_.build(child_)
            self.chain.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "ligand":
            obj_ = XSDataLigand()
            obj_.build(child_)
            self.ligand.append(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "numberOfCopiesInAsymmetricUnit"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setNumberOfCopiesInAsymmetricUnit(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataStructure")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataStructure")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataStructure is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataStructure.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataStructure()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataStructure")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataStructure()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataStructure


class XSDataSubWedge(XSData):
    """A subwedge is defined as a list of images that been collected or is to be collected with some particular experimental condition. If the images are to be collected, the image list is empty.
The subWedgeNumber is an optional number for relating different subwedges, especially for planning data collections."""

    def __init__(
        self, subWedgeNumber=None, image=None, experimentalCondition=None, action=None
    ):
        XSData.__init__(self)
        if action is None:
            self._action = None
        elif action.__class__.__name__ == "XSDataString":
            self._action = action
        else:
            strMessage = (
                "ERROR! XSDataSubWedge constructor argument 'action' is not XSDataString but %s"
                % self._action.__class__.__name__
            )
            raise BaseException(strMessage)
        if experimentalCondition is None:
            self._experimentalCondition = None
        elif experimentalCondition.__class__.__name__ == "XSDataExperimentalCondition":
            self._experimentalCondition = experimentalCondition
        else:
            strMessage = (
                "ERROR! XSDataSubWedge constructor argument 'experimentalCondition' is not XSDataExperimentalCondition but %s"
                % self._experimentalCondition.__class__.__name__
            )
            raise BaseException(strMessage)
        if image is None:
            self._image = []
        elif image.__class__.__name__ == "list":
            self._image = image
        else:
            strMessage = (
                "ERROR! XSDataSubWedge constructor argument 'image' is not list but %s"
                % self._image.__class__.__name__
            )
            raise BaseException(strMessage)
        if subWedgeNumber is None:
            self._subWedgeNumber = None
        elif subWedgeNumber.__class__.__name__ == "XSDataInteger":
            self._subWedgeNumber = subWedgeNumber
        else:
            strMessage = (
                "ERROR! XSDataSubWedge constructor argument 'subWedgeNumber' is not XSDataInteger but %s"
                % self._subWedgeNumber.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'action' attribute
    def getAction(self):
        return self._action

    def setAction(self, action):
        if action is None:
            self._action = None
        elif action.__class__.__name__ == "XSDataString":
            self._action = action
        else:
            strMessage = (
                "ERROR! XSDataSubWedge.setAction argument is not XSDataString but %s"
                % action.__class__.__name__
            )
            raise BaseException(strMessage)

    def delAction(self):
        self._action = None

    action = property(getAction, setAction, delAction, "Property for action")
    # Methods and properties for the 'experimentalCondition' attribute

    def getExperimentalCondition(self):
        return self._experimentalCondition

    def setExperimentalCondition(self, experimentalCondition):
        if experimentalCondition is None:
            self._experimentalCondition = None
        elif experimentalCondition.__class__.__name__ == "XSDataExperimentalCondition":
            self._experimentalCondition = experimentalCondition
        else:
            strMessage = (
                "ERROR! XSDataSubWedge.setExperimentalCondition argument is not XSDataExperimentalCondition but %s"
                % experimentalCondition.__class__.__name__
            )
            raise BaseException(strMessage)

    def delExperimentalCondition(self):
        self._experimentalCondition = None

    experimentalCondition = property(
        getExperimentalCondition,
        setExperimentalCondition,
        delExperimentalCondition,
        "Property for experimentalCondition",
    )
    # Methods and properties for the 'image' attribute

    def getImage(self):
        return self._image

    def setImage(self, image):
        if image is None:
            self._image = []
        elif image.__class__.__name__ == "list":
            self._image = image
        else:
            strMessage = (
                "ERROR! XSDataSubWedge.setImage argument is not list but %s"
                % image.__class__.__name__
            )
            raise BaseException(strMessage)

    def delImage(self):
        self._image = None

    image = property(getImage, setImage, delImage, "Property for image")

    def addImage(self, value):
        if value is None:
            strMessage = "ERROR! XSDataSubWedge.addImage argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataImage":
            self._image.append(value)
        else:
            strMessage = (
                "ERROR! XSDataSubWedge.addImage argument is not XSDataImage but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertImage(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataSubWedge.insertImage argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataSubWedge.insertImage argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataImage":
            self._image[index] = value
        else:
            strMessage = (
                "ERROR! XSDataSubWedge.addImage argument is not XSDataImage but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'subWedgeNumber' attribute
    def getSubWedgeNumber(self):
        return self._subWedgeNumber

    def setSubWedgeNumber(self, subWedgeNumber):
        if subWedgeNumber is None:
            self._subWedgeNumber = None
        elif subWedgeNumber.__class__.__name__ == "XSDataInteger":
            self._subWedgeNumber = subWedgeNumber
        else:
            strMessage = (
                "ERROR! XSDataSubWedge.setSubWedgeNumber argument is not XSDataInteger but %s"
                % subWedgeNumber.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSubWedgeNumber(self):
        self._subWedgeNumber = None

    subWedgeNumber = property(
        getSubWedgeNumber,
        setSubWedgeNumber,
        delSubWedgeNumber,
        "Property for subWedgeNumber",
    )

    def export(self, outfile, level, name_="XSDataSubWedge"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataSubWedge"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._action is not None:
            self.action.export(outfile, level, name_="action")
        if self._experimentalCondition is not None:
            self.experimentalCondition.export(
                outfile, level, name_="experimentalCondition"
            )
        else:
            warnEmptyAttribute("experimentalCondition", "XSDataExperimentalCondition")
        for image_ in self.getImage():
            image_.export(outfile, level, name_="image")
        if self._subWedgeNumber is not None:
            self.subWedgeNumber.export(outfile, level, name_="subWedgeNumber")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "action":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setAction(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "experimentalCondition"
        ):
            obj_ = XSDataExperimentalCondition()
            obj_.build(child_)
            self.setExperimentalCondition(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "image":
            obj_ = XSDataImage()
            obj_.build(child_)
            self.image.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "subWedgeNumber":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setSubWedgeNumber(obj_)
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataSubWedge")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataSubWedge")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataSubWedge is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataSubWedge.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataSubWedge()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataSubWedge")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataSubWedge()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataSubWedge


class XSDataGeneratePredictionInput(XSDataInput):
    """This generalisation is not very logical in terms of names, it should be fixed after the prototype (see bug #49)."""

    def __init__(
        self, configuration=None, selectedIndexingSolution=None, dataCollection=None
    ):
        XSDataInput.__init__(self, configuration)
        if dataCollection is None:
            self._dataCollection = None
        elif dataCollection.__class__.__name__ == "XSDataCollection":
            self._dataCollection = dataCollection
        else:
            strMessage = (
                "ERROR! XSDataGeneratePredictionInput constructor argument 'dataCollection' is not XSDataCollection but %s"
                % self._dataCollection.__class__.__name__
            )
            raise BaseException(strMessage)
        if selectedIndexingSolution is None:
            self._selectedIndexingSolution = None
        elif (
            selectedIndexingSolution.__class__.__name__
            == "XSDataIndexingSolutionSelected"
        ):
            self._selectedIndexingSolution = selectedIndexingSolution
        else:
            strMessage = (
                "ERROR! XSDataGeneratePredictionInput constructor argument 'selectedIndexingSolution' is not XSDataIndexingSolutionSelected but %s"
                % self._selectedIndexingSolution.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'dataCollection' attribute
    def getDataCollection(self):
        return self._dataCollection

    def setDataCollection(self, dataCollection):
        if dataCollection is None:
            self._dataCollection = None
        elif dataCollection.__class__.__name__ == "XSDataCollection":
            self._dataCollection = dataCollection
        else:
            strMessage = (
                "ERROR! XSDataGeneratePredictionInput.setDataCollection argument is not XSDataCollection but %s"
                % dataCollection.__class__.__name__
            )
            raise BaseException(strMessage)

    def delDataCollection(self):
        self._dataCollection = None

    dataCollection = property(
        getDataCollection,
        setDataCollection,
        delDataCollection,
        "Property for dataCollection",
    )
    # Methods and properties for the 'selectedIndexingSolution' attribute

    def getSelectedIndexingSolution(self):
        return self._selectedIndexingSolution

    def setSelectedIndexingSolution(self, selectedIndexingSolution):
        if selectedIndexingSolution is None:
            self._selectedIndexingSolution = None
        elif (
            selectedIndexingSolution.__class__.__name__
            == "XSDataIndexingSolutionSelected"
        ):
            self._selectedIndexingSolution = selectedIndexingSolution
        else:
            strMessage = (
                "ERROR! XSDataGeneratePredictionInput.setSelectedIndexingSolution argument is not XSDataIndexingSolutionSelected but %s"
                % selectedIndexingSolution.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSelectedIndexingSolution(self):
        self._selectedIndexingSolution = None

    selectedIndexingSolution = property(
        getSelectedIndexingSolution,
        setSelectedIndexingSolution,
        delSelectedIndexingSolution,
        "Property for selectedIndexingSolution",
    )

    def export(self, outfile, level, name_="XSDataGeneratePredictionInput"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataGeneratePredictionInput"):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._dataCollection is not None:
            self.dataCollection.export(outfile, level, name_="dataCollection")
        else:
            warnEmptyAttribute("dataCollection", "XSDataCollection")
        if self._selectedIndexingSolution is not None:
            self.selectedIndexingSolution.export(
                outfile, level, name_="selectedIndexingSolution"
            )
        else:
            warnEmptyAttribute(
                "selectedIndexingSolution", "XSDataIndexingSolutionSelected"
            )

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "dataCollection":
            obj_ = XSDataCollection()
            obj_.build(child_)
            self.setDataCollection(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "selectedIndexingSolution"
        ):
            obj_ = XSDataIndexingSolutionSelected()
            obj_.build(child_)
            self.setSelectedIndexingSolution(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataGeneratePredictionInput")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataGeneratePredictionInput")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataGeneratePredictionInput is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataGeneratePredictionInput.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataGeneratePredictionInput()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataGeneratePredictionInput")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataGeneratePredictionInput()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataGeneratePredictionInput


class XSDataGeneratePredictionResult(XSDataResult):
    def __init__(self, status=None, predictionImage=None):
        XSDataResult.__init__(self, status)
        if predictionImage is None:
            self._predictionImage = []
        elif predictionImage.__class__.__name__ == "list":
            self._predictionImage = predictionImage
        else:
            strMessage = (
                "ERROR! XSDataGeneratePredictionResult constructor argument 'predictionImage' is not list but %s"
                % self._predictionImage.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'predictionImage' attribute
    def getPredictionImage(self):
        return self._predictionImage

    def setPredictionImage(self, predictionImage):
        if predictionImage is None:
            self._predictionImage = []
        elif predictionImage.__class__.__name__ == "list":
            self._predictionImage = predictionImage
        else:
            strMessage = (
                "ERROR! XSDataGeneratePredictionResult.setPredictionImage argument is not list but %s"
                % predictionImage.__class__.__name__
            )
            raise BaseException(strMessage)

    def delPredictionImage(self):
        self._predictionImage = None

    predictionImage = property(
        getPredictionImage,
        setPredictionImage,
        delPredictionImage,
        "Property for predictionImage",
    )

    def addPredictionImage(self, value):
        if value is None:
            strMessage = "ERROR! XSDataGeneratePredictionResult.addPredictionImage argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataImage":
            self._predictionImage.append(value)
        else:
            strMessage = (
                "ERROR! XSDataGeneratePredictionResult.addPredictionImage argument is not XSDataImage but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertPredictionImage(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataGeneratePredictionResult.insertPredictionImage argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataGeneratePredictionResult.insertPredictionImage argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataImage":
            self._predictionImage[index] = value
        else:
            strMessage = (
                "ERROR! XSDataGeneratePredictionResult.addPredictionImage argument is not XSDataImage but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def export(self, outfile, level, name_="XSDataGeneratePredictionResult"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataGeneratePredictionResult"):
        XSDataResult.exportChildren(self, outfile, level, name_)
        for predictionImage_ in self.getPredictionImage():
            predictionImage_.export(outfile, level, name_="predictionImage")
        if self.getPredictionImage() == []:
            warnEmptyAttribute("predictionImage", "XSDataImage")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "predictionImage":
            obj_ = XSDataImage()
            obj_.build(child_)
            self.predictionImage.append(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataGeneratePredictionResult")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataGeneratePredictionResult")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataGeneratePredictionResult is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataGeneratePredictionResult.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataGeneratePredictionResult()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataGeneratePredictionResult")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataGeneratePredictionResult()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataGeneratePredictionResult


class XSDataIndexingInput(XSDataInput):
    def __init__(
        self,
        configuration=None,
        experimentalCondition=None,
        dataCollection=None,
        crystal=None,
    ):
        XSDataInput.__init__(self, configuration)
        if crystal is None:
            self._crystal = None
        elif crystal.__class__.__name__ == "XSDataCrystal":
            self._crystal = crystal
        else:
            strMessage = (
                "ERROR! XSDataIndexingInput constructor argument 'crystal' is not XSDataCrystal but %s"
                % self._crystal.__class__.__name__
            )
            raise BaseException(strMessage)
        if dataCollection is None:
            self._dataCollection = None
        elif dataCollection.__class__.__name__ == "XSDataCollection":
            self._dataCollection = dataCollection
        else:
            strMessage = (
                "ERROR! XSDataIndexingInput constructor argument 'dataCollection' is not XSDataCollection but %s"
                % self._dataCollection.__class__.__name__
            )
            raise BaseException(strMessage)
        if experimentalCondition is None:
            self._experimentalCondition = None
        elif experimentalCondition.__class__.__name__ == "XSDataExperimentalCondition":
            self._experimentalCondition = experimentalCondition
        else:
            strMessage = (
                "ERROR! XSDataIndexingInput constructor argument 'experimentalCondition' is not XSDataExperimentalCondition but %s"
                % self._experimentalCondition.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'crystal' attribute
    def getCrystal(self):
        return self._crystal

    def setCrystal(self, crystal):
        if crystal is None:
            self._crystal = None
        elif crystal.__class__.__name__ == "XSDataCrystal":
            self._crystal = crystal
        else:
            strMessage = (
                "ERROR! XSDataIndexingInput.setCrystal argument is not XSDataCrystal but %s"
                % crystal.__class__.__name__
            )
            raise BaseException(strMessage)

    def delCrystal(self):
        self._crystal = None

    crystal = property(getCrystal, setCrystal, delCrystal, "Property for crystal")
    # Methods and properties for the 'dataCollection' attribute

    def getDataCollection(self):
        return self._dataCollection

    def setDataCollection(self, dataCollection):
        if dataCollection is None:
            self._dataCollection = None
        elif dataCollection.__class__.__name__ == "XSDataCollection":
            self._dataCollection = dataCollection
        else:
            strMessage = (
                "ERROR! XSDataIndexingInput.setDataCollection argument is not XSDataCollection but %s"
                % dataCollection.__class__.__name__
            )
            raise BaseException(strMessage)

    def delDataCollection(self):
        self._dataCollection = None

    dataCollection = property(
        getDataCollection,
        setDataCollection,
        delDataCollection,
        "Property for dataCollection",
    )
    # Methods and properties for the 'experimentalCondition' attribute

    def getExperimentalCondition(self):
        return self._experimentalCondition

    def setExperimentalCondition(self, experimentalCondition):
        if experimentalCondition is None:
            self._experimentalCondition = None
        elif experimentalCondition.__class__.__name__ == "XSDataExperimentalCondition":
            self._experimentalCondition = experimentalCondition
        else:
            strMessage = (
                "ERROR! XSDataIndexingInput.setExperimentalCondition argument is not XSDataExperimentalCondition but %s"
                % experimentalCondition.__class__.__name__
            )
            raise BaseException(strMessage)

    def delExperimentalCondition(self):
        self._experimentalCondition = None

    experimentalCondition = property(
        getExperimentalCondition,
        setExperimentalCondition,
        delExperimentalCondition,
        "Property for experimentalCondition",
    )

    def export(self, outfile, level, name_="XSDataIndexingInput"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataIndexingInput"):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._crystal is not None:
            self.crystal.export(outfile, level, name_="crystal")
        if self._dataCollection is not None:
            self.dataCollection.export(outfile, level, name_="dataCollection")
        else:
            warnEmptyAttribute("dataCollection", "XSDataCollection")
        if self._experimentalCondition is not None:
            self.experimentalCondition.export(
                outfile, level, name_="experimentalCondition"
            )

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "crystal":
            obj_ = XSDataCrystal()
            obj_.build(child_)
            self.setCrystal(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "dataCollection":
            obj_ = XSDataCollection()
            obj_.build(child_)
            self.setDataCollection(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "experimentalCondition"
        ):
            obj_ = XSDataExperimentalCondition()
            obj_.build(child_)
            self.setExperimentalCondition(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataIndexingInput")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataIndexingInput")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataIndexingInput is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataIndexingInput.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataIndexingInput()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataIndexingInput")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataIndexingInput()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataIndexingInput


class XSDataIndexingSolutionSelected(XSDataIndexingSolution):
    def __init__(
        self,
        penalty=None,
        number=None,
        crystal=None,
        statistics=None,
        orientation=None,
        mosaicityEstimation=None,
        experimentalConditionRefined=None,
    ):
        XSDataIndexingSolution.__init__(self, penalty, number, crystal)
        if experimentalConditionRefined is None:
            self._experimentalConditionRefined = None
        elif (
            experimentalConditionRefined.__class__.__name__
            == "XSDataExperimentalCondition"
        ):
            self._experimentalConditionRefined = experimentalConditionRefined
        else:
            strMessage = (
                "ERROR! XSDataIndexingSolutionSelected constructor argument 'experimentalConditionRefined' is not XSDataExperimentalCondition but %s"
                % self._experimentalConditionRefined.__class__.__name__
            )
            raise BaseException(strMessage)
        if mosaicityEstimation is None:
            self._mosaicityEstimation = None
        elif mosaicityEstimation.__class__.__name__ == "XSDataFloat":
            self._mosaicityEstimation = mosaicityEstimation
        else:
            strMessage = (
                "ERROR! XSDataIndexingSolutionSelected constructor argument 'mosaicityEstimation' is not XSDataFloat but %s"
                % self._mosaicityEstimation.__class__.__name__
            )
            raise BaseException(strMessage)
        if orientation is None:
            self._orientation = None
        elif orientation.__class__.__name__ == "XSDataOrientation":
            self._orientation = orientation
        else:
            strMessage = (
                "ERROR! XSDataIndexingSolutionSelected constructor argument 'orientation' is not XSDataOrientation but %s"
                % self._orientation.__class__.__name__
            )
            raise BaseException(strMessage)
        if statistics is None:
            self._statistics = None
        elif statistics.__class__.__name__ == "XSDataStatisticsIndexing":
            self._statistics = statistics
        else:
            strMessage = (
                "ERROR! XSDataIndexingSolutionSelected constructor argument 'statistics' is not XSDataStatisticsIndexing but %s"
                % self._statistics.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'experimentalConditionRefined' attribute
    def getExperimentalConditionRefined(self):
        return self._experimentalConditionRefined

    def setExperimentalConditionRefined(self, experimentalConditionRefined):
        if experimentalConditionRefined is None:
            self._experimentalConditionRefined = None
        elif (
            experimentalConditionRefined.__class__.__name__
            == "XSDataExperimentalCondition"
        ):
            self._experimentalConditionRefined = experimentalConditionRefined
        else:
            strMessage = (
                "ERROR! XSDataIndexingSolutionSelected.setExperimentalConditionRefined argument is not XSDataExperimentalCondition but %s"
                % experimentalConditionRefined.__class__.__name__
            )
            raise BaseException(strMessage)

    def delExperimentalConditionRefined(self):
        self._experimentalConditionRefined = None

    experimentalConditionRefined = property(
        getExperimentalConditionRefined,
        setExperimentalConditionRefined,
        delExperimentalConditionRefined,
        "Property for experimentalConditionRefined",
    )
    # Methods and properties for the 'mosaicityEstimation' attribute

    def getMosaicityEstimation(self):
        return self._mosaicityEstimation

    def setMosaicityEstimation(self, mosaicityEstimation):
        if mosaicityEstimation is None:
            self._mosaicityEstimation = None
        elif mosaicityEstimation.__class__.__name__ == "XSDataFloat":
            self._mosaicityEstimation = mosaicityEstimation
        else:
            strMessage = (
                "ERROR! XSDataIndexingSolutionSelected.setMosaicityEstimation argument is not XSDataFloat but %s"
                % mosaicityEstimation.__class__.__name__
            )
            raise BaseException(strMessage)

    def delMosaicityEstimation(self):
        self._mosaicityEstimation = None

    mosaicityEstimation = property(
        getMosaicityEstimation,
        setMosaicityEstimation,
        delMosaicityEstimation,
        "Property for mosaicityEstimation",
    )
    # Methods and properties for the 'orientation' attribute

    def getOrientation(self):
        return self._orientation

    def setOrientation(self, orientation):
        if orientation is None:
            self._orientation = None
        elif orientation.__class__.__name__ == "XSDataOrientation":
            self._orientation = orientation
        else:
            strMessage = (
                "ERROR! XSDataIndexingSolutionSelected.setOrientation argument is not XSDataOrientation but %s"
                % orientation.__class__.__name__
            )
            raise BaseException(strMessage)

    def delOrientation(self):
        self._orientation = None

    orientation = property(
        getOrientation, setOrientation, delOrientation, "Property for orientation"
    )
    # Methods and properties for the 'statistics' attribute

    def getStatistics(self):
        return self._statistics

    def setStatistics(self, statistics):
        if statistics is None:
            self._statistics = None
        elif statistics.__class__.__name__ == "XSDataStatisticsIndexing":
            self._statistics = statistics
        else:
            strMessage = (
                "ERROR! XSDataIndexingSolutionSelected.setStatistics argument is not XSDataStatisticsIndexing but %s"
                % statistics.__class__.__name__
            )
            raise BaseException(strMessage)

    def delStatistics(self):
        self._statistics = None

    statistics = property(
        getStatistics, setStatistics, delStatistics, "Property for statistics"
    )

    def export(self, outfile, level, name_="XSDataIndexingSolutionSelected"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataIndexingSolutionSelected"):
        XSDataIndexingSolution.exportChildren(self, outfile, level, name_)
        if self._experimentalConditionRefined is not None:
            self.experimentalConditionRefined.export(
                outfile, level, name_="experimentalConditionRefined"
            )
        else:
            warnEmptyAttribute(
                "experimentalConditionRefined", "XSDataExperimentalCondition"
            )
        if self._mosaicityEstimation is not None:
            self.mosaicityEstimation.export(outfile, level, name_="mosaicityEstimation")
        if self._orientation is not None:
            self.orientation.export(outfile, level, name_="orientation")
        else:
            warnEmptyAttribute("orientation", "XSDataOrientation")
        if self._statistics is not None:
            self.statistics.export(outfile, level, name_="statistics")
        else:
            warnEmptyAttribute("statistics", "XSDataStatisticsIndexing")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "experimentalConditionRefined"
        ):
            obj_ = XSDataExperimentalCondition()
            obj_.build(child_)
            self.setExperimentalConditionRefined(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "mosaicityEstimation"
        ):
            obj_ = XSDataFloat()
            obj_.build(child_)
            self.setMosaicityEstimation(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "orientation":
            obj_ = XSDataOrientation()
            obj_.build(child_)
            self.setOrientation(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "statistics":
            obj_ = XSDataStatisticsIndexing()
            obj_.build(child_)
            self.setStatistics(obj_)
        XSDataIndexingSolution.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataIndexingSolutionSelected")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataIndexingSolutionSelected")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataIndexingSolutionSelected is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataIndexingSolutionSelected.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataIndexingSolutionSelected()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataIndexingSolutionSelected")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataIndexingSolutionSelected()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataIndexingSolutionSelected


class XSDataIndexingResult(XSDataResult):
    def __init__(
        self,
        status=None,
        solution=None,
        selectedSolution=None,
        predictionResult=None,
        labelitIndexing=None,
        indexingLogFile=None,
        image=None,
    ):
        XSDataResult.__init__(self, status)
        if image is None:
            self._image = []
        elif image.__class__.__name__ == "list":
            self._image = image
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult constructor argument 'image' is not list but %s"
                % self._image.__class__.__name__
            )
            raise BaseException(strMessage)
        if indexingLogFile is None:
            self._indexingLogFile = None
        elif indexingLogFile.__class__.__name__ == "XSDataFile":
            self._indexingLogFile = indexingLogFile
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult constructor argument 'indexingLogFile' is not XSDataFile but %s"
                % self._indexingLogFile.__class__.__name__
            )
            raise BaseException(strMessage)
        if labelitIndexing is None:
            self._labelitIndexing = None
        elif labelitIndexing.__class__.__name__ == "XSDataBoolean":
            self._labelitIndexing = labelitIndexing
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult constructor argument 'labelitIndexing' is not XSDataBoolean but %s"
                % self._labelitIndexing.__class__.__name__
            )
            raise BaseException(strMessage)
        if predictionResult is None:
            self._predictionResult = None
        elif predictionResult.__class__.__name__ == "XSDataGeneratePredictionResult":
            self._predictionResult = predictionResult
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult constructor argument 'predictionResult' is not XSDataGeneratePredictionResult but %s"
                % self._predictionResult.__class__.__name__
            )
            raise BaseException(strMessage)
        if selectedSolution is None:
            self._selectedSolution = None
        elif selectedSolution.__class__.__name__ == "XSDataIndexingSolutionSelected":
            self._selectedSolution = selectedSolution
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult constructor argument 'selectedSolution' is not XSDataIndexingSolutionSelected but %s"
                % self._selectedSolution.__class__.__name__
            )
            raise BaseException(strMessage)
        if solution is None:
            self._solution = []
        elif solution.__class__.__name__ == "list":
            self._solution = solution
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult constructor argument 'solution' is not list but %s"
                % self._solution.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'image' attribute
    def getImage(self):
        return self._image

    def setImage(self, image):
        if image is None:
            self._image = []
        elif image.__class__.__name__ == "list":
            self._image = image
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult.setImage argument is not list but %s"
                % image.__class__.__name__
            )
            raise BaseException(strMessage)

    def delImage(self):
        self._image = None

    image = property(getImage, setImage, delImage, "Property for image")

    def addImage(self, value):
        if value is None:
            strMessage = "ERROR! XSDataIndexingResult.addImage argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataImage":
            self._image.append(value)
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult.addImage argument is not XSDataImage but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertImage(self, index, value):
        if index is None:
            strMessage = (
                "ERROR! XSDataIndexingResult.insertImage argument 'index' is None"
            )
            raise BaseException(strMessage)
        if value is None:
            strMessage = (
                "ERROR! XSDataIndexingResult.insertImage argument 'value' is None"
            )
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataImage":
            self._image[index] = value
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult.addImage argument is not XSDataImage but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'indexingLogFile' attribute
    def getIndexingLogFile(self):
        return self._indexingLogFile

    def setIndexingLogFile(self, indexingLogFile):
        if indexingLogFile is None:
            self._indexingLogFile = None
        elif indexingLogFile.__class__.__name__ == "XSDataFile":
            self._indexingLogFile = indexingLogFile
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult.setIndexingLogFile argument is not XSDataFile but %s"
                % indexingLogFile.__class__.__name__
            )
            raise BaseException(strMessage)

    def delIndexingLogFile(self):
        self._indexingLogFile = None

    indexingLogFile = property(
        getIndexingLogFile,
        setIndexingLogFile,
        delIndexingLogFile,
        "Property for indexingLogFile",
    )
    # Methods and properties for the 'labelitIndexing' attribute

    def getLabelitIndexing(self):
        return self._labelitIndexing

    def setLabelitIndexing(self, labelitIndexing):
        if labelitIndexing is None:
            self._labelitIndexing = None
        elif labelitIndexing.__class__.__name__ == "XSDataBoolean":
            self._labelitIndexing = labelitIndexing
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult.setLabelitIndexing argument is not XSDataBoolean but %s"
                % labelitIndexing.__class__.__name__
            )
            raise BaseException(strMessage)

    def delLabelitIndexing(self):
        self._labelitIndexing = None

    labelitIndexing = property(
        getLabelitIndexing,
        setLabelitIndexing,
        delLabelitIndexing,
        "Property for labelitIndexing",
    )
    # Methods and properties for the 'predictionResult' attribute

    def getPredictionResult(self):
        return self._predictionResult

    def setPredictionResult(self, predictionResult):
        if predictionResult is None:
            self._predictionResult = None
        elif predictionResult.__class__.__name__ == "XSDataGeneratePredictionResult":
            self._predictionResult = predictionResult
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult.setPredictionResult argument is not XSDataGeneratePredictionResult but %s"
                % predictionResult.__class__.__name__
            )
            raise BaseException(strMessage)

    def delPredictionResult(self):
        self._predictionResult = None

    predictionResult = property(
        getPredictionResult,
        setPredictionResult,
        delPredictionResult,
        "Property for predictionResult",
    )
    # Methods and properties for the 'selectedSolution' attribute

    def getSelectedSolution(self):
        return self._selectedSolution

    def setSelectedSolution(self, selectedSolution):
        if selectedSolution is None:
            self._selectedSolution = None
        elif selectedSolution.__class__.__name__ == "XSDataIndexingSolutionSelected":
            self._selectedSolution = selectedSolution
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult.setSelectedSolution argument is not XSDataIndexingSolutionSelected but %s"
                % selectedSolution.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSelectedSolution(self):
        self._selectedSolution = None

    selectedSolution = property(
        getSelectedSolution,
        setSelectedSolution,
        delSelectedSolution,
        "Property for selectedSolution",
    )
    # Methods and properties for the 'solution' attribute

    def getSolution(self):
        return self._solution

    def setSolution(self, solution):
        if solution is None:
            self._solution = []
        elif solution.__class__.__name__ == "list":
            self._solution = solution
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult.setSolution argument is not list but %s"
                % solution.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSolution(self):
        self._solution = None

    solution = property(getSolution, setSolution, delSolution, "Property for solution")

    def addSolution(self, value):
        if value is None:
            strMessage = "ERROR! XSDataIndexingResult.addSolution argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataIndexingSolution":
            self._solution.append(value)
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult.addSolution argument is not XSDataIndexingSolution but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertSolution(self, index, value):
        if index is None:
            strMessage = (
                "ERROR! XSDataIndexingResult.insertSolution argument 'index' is None"
            )
            raise BaseException(strMessage)
        if value is None:
            strMessage = (
                "ERROR! XSDataIndexingResult.insertSolution argument 'value' is None"
            )
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataIndexingSolution":
            self._solution[index] = value
        else:
            strMessage = (
                "ERROR! XSDataIndexingResult.addSolution argument is not XSDataIndexingSolution but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def export(self, outfile, level, name_="XSDataIndexingResult"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataIndexingResult"):
        XSDataResult.exportChildren(self, outfile, level, name_)
        for image_ in self.getImage():
            image_.export(outfile, level, name_="image")
        if self.getImage() == []:
            warnEmptyAttribute("image", "XSDataImage")
        if self._indexingLogFile is not None:
            self.indexingLogFile.export(outfile, level, name_="indexingLogFile")
        if self._labelitIndexing is not None:
            self.labelitIndexing.export(outfile, level, name_="labelitIndexing")
        else:
            warnEmptyAttribute("labelitIndexing", "XSDataBoolean")
        if self._predictionResult is not None:
            self.predictionResult.export(outfile, level, name_="predictionResult")
        if self._selectedSolution is not None:
            self.selectedSolution.export(outfile, level, name_="selectedSolution")
        for solution_ in self.getSolution():
            solution_.export(outfile, level, name_="solution")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "image":
            obj_ = XSDataImage()
            obj_.build(child_)
            self.image.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "indexingLogFile":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setIndexingLogFile(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "labelitIndexing":
            obj_ = XSDataBoolean()
            obj_.build(child_)
            self.setLabelitIndexing(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "predictionResult":
            obj_ = XSDataGeneratePredictionResult()
            obj_.build(child_)
            self.setPredictionResult(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "selectedSolution":
            obj_ = XSDataIndexingSolutionSelected()
            obj_.build(child_)
            self.setSelectedSolution(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "solution":
            obj_ = XSDataIndexingSolution()
            obj_.build(child_)
            self.solution.append(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataIndexingResult")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataIndexingResult")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataIndexingResult is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataIndexingResult.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataIndexingResult()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataIndexingResult")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataIndexingResult()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataIndexingResult


class XSDataInputCharacterisation(XSDataInput):
    def __init__(self, configuration=None, dataCollection=None):
        XSDataInput.__init__(self, configuration)
        if dataCollection is None:
            self._dataCollection = None
        elif dataCollection.__class__.__name__ == "XSDataCollection":
            self._dataCollection = dataCollection
        else:
            strMessage = (
                "ERROR! XSDataInputCharacterisation constructor argument 'dataCollection' is not XSDataCollection but %s"
                % self._dataCollection.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'dataCollection' attribute
    def getDataCollection(self):
        return self._dataCollection

    def setDataCollection(self, dataCollection):
        if dataCollection is None:
            self._dataCollection = None
        elif dataCollection.__class__.__name__ == "XSDataCollection":
            self._dataCollection = dataCollection
        else:
            strMessage = (
                "ERROR! XSDataInputCharacterisation.setDataCollection argument is not XSDataCollection but %s"
                % dataCollection.__class__.__name__
            )
            raise BaseException(strMessage)

    def delDataCollection(self):
        self._dataCollection = None

    dataCollection = property(
        getDataCollection,
        setDataCollection,
        delDataCollection,
        "Property for dataCollection",
    )

    def export(self, outfile, level, name_="XSDataInputCharacterisation"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataInputCharacterisation"):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._dataCollection is not None:
            self.dataCollection.export(outfile, level, name_="dataCollection")
        else:
            warnEmptyAttribute("dataCollection", "XSDataCollection")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "dataCollection":
            obj_ = XSDataCollection()
            obj_.build(child_)
            self.setDataCollection(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataInputCharacterisation")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataInputCharacterisation")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataInputCharacterisation is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataInputCharacterisation.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputCharacterisation()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataInputCharacterisation")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputCharacterisation()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataInputCharacterisation


class XSDataInputControlISPyB(XSDataInput):
    def __init__(
        self,
        configuration=None,
        phi=None,
        kappa=None,
        dataCollectionId=None,
        characterisationResult=None,
    ):
        XSDataInput.__init__(self, configuration)
        if characterisationResult is None:
            self._characterisationResult = None
        elif (
            characterisationResult.__class__.__name__ == "XSDataResultCharacterisation"
        ):
            self._characterisationResult = characterisationResult
        else:
            strMessage = (
                "ERROR! XSDataInputControlISPyB constructor argument 'characterisationResult' is not XSDataResultCharacterisation but %s"
                % self._characterisationResult.__class__.__name__
            )
            raise BaseException(strMessage)
        if dataCollectionId is None:
            self._dataCollectionId = None
        elif dataCollectionId.__class__.__name__ == "XSDataInteger":
            self._dataCollectionId = dataCollectionId
        else:
            strMessage = (
                "ERROR! XSDataInputControlISPyB constructor argument 'dataCollectionId' is not XSDataInteger but %s"
                % self._dataCollectionId.__class__.__name__
            )
            raise BaseException(strMessage)
        if kappa is None:
            self._kappa = None
        elif kappa.__class__.__name__ == "XSDataAngle":
            self._kappa = kappa
        else:
            strMessage = (
                "ERROR! XSDataInputControlISPyB constructor argument 'kappa' is not XSDataAngle but %s"
                % self._kappa.__class__.__name__
            )
            raise BaseException(strMessage)
        if phi is None:
            self._phi = None
        elif phi.__class__.__name__ == "XSDataAngle":
            self._phi = phi
        else:
            strMessage = (
                "ERROR! XSDataInputControlISPyB constructor argument 'phi' is not XSDataAngle but %s"
                % self._phi.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'characterisationResult' attribute
    def getCharacterisationResult(self):
        return self._characterisationResult

    def setCharacterisationResult(self, characterisationResult):
        if characterisationResult is None:
            self._characterisationResult = None
        elif (
            characterisationResult.__class__.__name__ == "XSDataResultCharacterisation"
        ):
            self._characterisationResult = characterisationResult
        else:
            strMessage = (
                "ERROR! XSDataInputControlISPyB.setCharacterisationResult argument is not XSDataResultCharacterisation but %s"
                % characterisationResult.__class__.__name__
            )
            raise BaseException(strMessage)

    def delCharacterisationResult(self):
        self._characterisationResult = None

    characterisationResult = property(
        getCharacterisationResult,
        setCharacterisationResult,
        delCharacterisationResult,
        "Property for characterisationResult",
    )
    # Methods and properties for the 'dataCollectionId' attribute

    def getDataCollectionId(self):
        return self._dataCollectionId

    def setDataCollectionId(self, dataCollectionId):
        if dataCollectionId is None:
            self._dataCollectionId = None
        elif dataCollectionId.__class__.__name__ == "XSDataInteger":
            self._dataCollectionId = dataCollectionId
        else:
            strMessage = (
                "ERROR! XSDataInputControlISPyB.setDataCollectionId argument is not XSDataInteger but %s"
                % dataCollectionId.__class__.__name__
            )
            raise BaseException(strMessage)

    def delDataCollectionId(self):
        self._dataCollectionId = None

    dataCollectionId = property(
        getDataCollectionId,
        setDataCollectionId,
        delDataCollectionId,
        "Property for dataCollectionId",
    )
    # Methods and properties for the 'kappa' attribute

    def getKappa(self):
        return self._kappa

    def setKappa(self, kappa):
        if kappa is None:
            self._kappa = None
        elif kappa.__class__.__name__ == "XSDataAngle":
            self._kappa = kappa
        else:
            strMessage = (
                "ERROR! XSDataInputControlISPyB.setKappa argument is not XSDataAngle but %s"
                % kappa.__class__.__name__
            )
            raise BaseException(strMessage)

    def delKappa(self):
        self._kappa = None

    kappa = property(getKappa, setKappa, delKappa, "Property for kappa")
    # Methods and properties for the 'phi' attribute

    def getPhi(self):
        return self._phi

    def setPhi(self, phi):
        if phi is None:
            self._phi = None
        elif phi.__class__.__name__ == "XSDataAngle":
            self._phi = phi
        else:
            strMessage = (
                "ERROR! XSDataInputControlISPyB.setPhi argument is not XSDataAngle but %s"
                % phi.__class__.__name__
            )
            raise BaseException(strMessage)

    def delPhi(self):
        self._phi = None

    phi = property(getPhi, setPhi, delPhi, "Property for phi")

    def export(self, outfile, level, name_="XSDataInputControlISPyB"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataInputControlISPyB"):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._characterisationResult is not None:
            self.characterisationResult.export(
                outfile, level, name_="characterisationResult"
            )
        else:
            warnEmptyAttribute("characterisationResult", "XSDataResultCharacterisation")
        if self._dataCollectionId is not None:
            self.dataCollectionId.export(outfile, level, name_="dataCollectionId")
        if self._kappa is not None:
            self.kappa.export(outfile, level, name_="kappa")
        if self._phi is not None:
            self.phi.export(outfile, level, name_="phi")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "characterisationResult"
        ):
            obj_ = XSDataResultCharacterisation()
            obj_.build(child_)
            self.setCharacterisationResult(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "dataCollectionId":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setDataCollectionId(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "kappa":
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setKappa(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "phi":
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setPhi(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataInputControlISPyB")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataInputControlISPyB")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataInputControlISPyB is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataInputControlISPyB.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputControlISPyB()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataInputControlISPyB")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputControlISPyB()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataInputControlISPyB


class XSDataInputControlImageQualityIndicators(XSDataInput):
    def __init__(self, configuration=None, image=None):
        XSDataInput.__init__(self, configuration)
        if image is None:
            self._image = []
        elif image.__class__.__name__ == "list":
            self._image = image
        else:
            strMessage = (
                "ERROR! XSDataInputControlImageQualityIndicators constructor argument 'image' is not list but %s"
                % self._image.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'image' attribute
    def getImage(self):
        return self._image

    def setImage(self, image):
        if image is None:
            self._image = []
        elif image.__class__.__name__ == "list":
            self._image = image
        else:
            strMessage = (
                "ERROR! XSDataInputControlImageQualityIndicators.setImage argument is not list but %s"
                % image.__class__.__name__
            )
            raise BaseException(strMessage)

    def delImage(self):
        self._image = None

    image = property(getImage, setImage, delImage, "Property for image")

    def addImage(self, value):
        if value is None:
            strMessage = "ERROR! XSDataInputControlImageQualityIndicators.addImage argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataImage":
            self._image.append(value)
        else:
            strMessage = (
                "ERROR! XSDataInputControlImageQualityIndicators.addImage argument is not XSDataImage but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertImage(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataInputControlImageQualityIndicators.insertImage argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataInputControlImageQualityIndicators.insertImage argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataImage":
            self._image[index] = value
        else:
            strMessage = (
                "ERROR! XSDataInputControlImageQualityIndicators.addImage argument is not XSDataImage but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def export(self, outfile, level, name_="XSDataInputControlImageQualityIndicators"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(
        self, outfile, level, name_="XSDataInputControlImageQualityIndicators"
    ):
        XSDataInput.exportChildren(self, outfile, level, name_)
        for image_ in self.getImage():
            image_.export(outfile, level, name_="image")
        if self.getImage() == []:
            warnEmptyAttribute("image", "XSDataImage")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "image":
            obj_ = XSDataImage()
            obj_.build(child_)
            self.image.append(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataInputControlImageQualityIndicators")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataInputControlImageQualityIndicators")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataInputControlImageQualityIndicators is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataInputControlImageQualityIndicators.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputControlImageQualityIndicators()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(
            oStreamString, 0, name_="XSDataInputControlImageQualityIndicators"
        )
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputControlImageQualityIndicators()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataInputControlImageQualityIndicators


class XSDataInputControlXDSGenerateBackgroundImage(XSDataInput):
    def __init__(self, configuration=None, dataCollection=None):
        XSDataInput.__init__(self, configuration)
        if dataCollection is None:
            self._dataCollection = None
        elif dataCollection.__class__.__name__ == "XSDataCollection":
            self._dataCollection = dataCollection
        else:
            strMessage = (
                "ERROR! XSDataInputControlXDSGenerateBackgroundImage constructor argument 'dataCollection' is not XSDataCollection but %s"
                % self._dataCollection.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'dataCollection' attribute
    def getDataCollection(self):
        return self._dataCollection

    def setDataCollection(self, dataCollection):
        if dataCollection is None:
            self._dataCollection = None
        elif dataCollection.__class__.__name__ == "XSDataCollection":
            self._dataCollection = dataCollection
        else:
            strMessage = (
                "ERROR! XSDataInputControlXDSGenerateBackgroundImage.setDataCollection argument is not XSDataCollection but %s"
                % dataCollection.__class__.__name__
            )
            raise BaseException(strMessage)

    def delDataCollection(self):
        self._dataCollection = None

    dataCollection = property(
        getDataCollection,
        setDataCollection,
        delDataCollection,
        "Property for dataCollection",
    )

    def export(
        self, outfile, level, name_="XSDataInputControlXDSGenerateBackgroundImage"
    ):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(
        self, outfile, level, name_="XSDataInputControlXDSGenerateBackgroundImage"
    ):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._dataCollection is not None:
            self.dataCollection.export(outfile, level, name_="dataCollection")
        else:
            warnEmptyAttribute("dataCollection", "XSDataCollection")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "dataCollection":
            obj_ = XSDataCollection()
            obj_.build(child_)
            self.setDataCollection(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(
            oStreamString, 0, name_="XSDataInputControlXDSGenerateBackgroundImage"
        )
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataInputControlXDSGenerateBackgroundImage")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataInputControlXDSGenerateBackgroundImage is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataInputControlXDSGenerateBackgroundImage.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputControlXDSGenerateBackgroundImage()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(
            oStreamString, 0, name_="XSDataInputControlXDSGenerateBackgroundImage"
        )
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputControlXDSGenerateBackgroundImage()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataInputControlXDSGenerateBackgroundImage


class XSDataInputInducedRadiationProcess(XSDataInput):
    def __init__(self, configuration=None, characterisationResult=None):
        XSDataInput.__init__(self, configuration)
        if characterisationResult is None:
            self._characterisationResult = None
        elif (
            characterisationResult.__class__.__name__ == "XSDataResultCharacterisation"
        ):
            self._characterisationResult = characterisationResult
        else:
            strMessage = (
                "ERROR! XSDataInputInducedRadiationProcess constructor argument 'characterisationResult' is not XSDataResultCharacterisation but %s"
                % self._characterisationResult.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'characterisationResult' attribute
    def getCharacterisationResult(self):
        return self._characterisationResult

    def setCharacterisationResult(self, characterisationResult):
        if characterisationResult is None:
            self._characterisationResult = None
        elif (
            characterisationResult.__class__.__name__ == "XSDataResultCharacterisation"
        ):
            self._characterisationResult = characterisationResult
        else:
            strMessage = (
                "ERROR! XSDataInputInducedRadiationProcess.setCharacterisationResult argument is not XSDataResultCharacterisation but %s"
                % characterisationResult.__class__.__name__
            )
            raise BaseException(strMessage)

    def delCharacterisationResult(self):
        self._characterisationResult = None

    characterisationResult = property(
        getCharacterisationResult,
        setCharacterisationResult,
        delCharacterisationResult,
        "Property for characterisationResult",
    )

    def export(self, outfile, level, name_="XSDataInputInducedRadiationProcess"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(
        self, outfile, level, name_="XSDataInputInducedRadiationProcess"
    ):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._characterisationResult is not None:
            self.characterisationResult.export(
                outfile, level, name_="characterisationResult"
            )
        else:
            warnEmptyAttribute("characterisationResult", "XSDataResultCharacterisation")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "characterisationResult"
        ):
            obj_ = XSDataResultCharacterisation()
            obj_.build(child_)
            self.setCharacterisationResult(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataInputInducedRadiationProcess")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataInputInducedRadiationProcess")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataInputInducedRadiationProcess is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataInputInducedRadiationProcess.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputInducedRadiationProcess()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataInputInducedRadiationProcess")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputInducedRadiationProcess()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataInputInducedRadiationProcess


class XSDataInputReadImageHeader(XSDataInput):
    """These two definitions are used by the read image header plugin."""

    def __init__(self, configuration=None, image=None):
        XSDataInput.__init__(self, configuration)
        if image is None:
            self._image = None
        elif image.__class__.__name__ == "XSDataFile":
            self._image = image
        else:
            strMessage = (
                "ERROR! XSDataInputReadImageHeader constructor argument 'image' is not XSDataFile but %s"
                % self._image.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'image' attribute
    def getImage(self):
        return self._image

    def setImage(self, image):
        if image is None:
            self._image = None
        elif image.__class__.__name__ == "XSDataFile":
            self._image = image
        else:
            strMessage = (
                "ERROR! XSDataInputReadImageHeader.setImage argument is not XSDataFile but %s"
                % image.__class__.__name__
            )
            raise BaseException(strMessage)

    def delImage(self):
        self._image = None

    image = property(getImage, setImage, delImage, "Property for image")

    def export(self, outfile, level, name_="XSDataInputReadImageHeader"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataInputReadImageHeader"):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._image is not None:
            self.image.export(outfile, level, name_="image")
        else:
            warnEmptyAttribute("image", "XSDataFile")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "image":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setImage(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataInputReadImageHeader")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataInputReadImageHeader")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataInputReadImageHeader is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataInputReadImageHeader.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputReadImageHeader()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataInputReadImageHeader")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputReadImageHeader()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataInputReadImageHeader


class XSDataInputStrategy(XSDataInput):
    def __init__(
        self,
        configuration=None,
        xdsBackgroundImage=None,
        sample=None,
        experimentalCondition=None,
        diffractionPlan=None,
        crystalRefined=None,
        bestFileContentPar=None,
        bestFileContentHKL=None,
        bestFileContentDat=None,
    ):
        XSDataInput.__init__(self, configuration)
        if bestFileContentDat is None:
            self._bestFileContentDat = None
        elif bestFileContentDat.__class__.__name__ == "XSDataString":
            self._bestFileContentDat = bestFileContentDat
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy constructor argument 'bestFileContentDat' is not XSDataString but %s"
                % self._bestFileContentDat.__class__.__name__
            )
            raise BaseException(strMessage)
        if bestFileContentHKL is None:
            self._bestFileContentHKL = []
        elif bestFileContentHKL.__class__.__name__ == "list":
            self._bestFileContentHKL = bestFileContentHKL
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy constructor argument 'bestFileContentHKL' is not list but %s"
                % self._bestFileContentHKL.__class__.__name__
            )
            raise BaseException(strMessage)
        if bestFileContentPar is None:
            self._bestFileContentPar = None
        elif bestFileContentPar.__class__.__name__ == "XSDataString":
            self._bestFileContentPar = bestFileContentPar
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy constructor argument 'bestFileContentPar' is not XSDataString but %s"
                % self._bestFileContentPar.__class__.__name__
            )
            raise BaseException(strMessage)
        if crystalRefined is None:
            self._crystalRefined = None
        elif crystalRefined.__class__.__name__ == "XSDataCrystal":
            self._crystalRefined = crystalRefined
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy constructor argument 'crystalRefined' is not XSDataCrystal but %s"
                % self._crystalRefined.__class__.__name__
            )
            raise BaseException(strMessage)
        if diffractionPlan is None:
            self._diffractionPlan = None
        elif diffractionPlan.__class__.__name__ == "XSDataDiffractionPlan":
            self._diffractionPlan = diffractionPlan
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy constructor argument 'diffractionPlan' is not XSDataDiffractionPlan but %s"
                % self._diffractionPlan.__class__.__name__
            )
            raise BaseException(strMessage)
        if experimentalCondition is None:
            self._experimentalCondition = None
        elif experimentalCondition.__class__.__name__ == "XSDataExperimentalCondition":
            self._experimentalCondition = experimentalCondition
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy constructor argument 'experimentalCondition' is not XSDataExperimentalCondition but %s"
                % self._experimentalCondition.__class__.__name__
            )
            raise BaseException(strMessage)
        if sample is None:
            self._sample = None
        elif sample.__class__.__name__ == "XSDataSampleCrystalMM":
            self._sample = sample
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy constructor argument 'sample' is not XSDataSampleCrystalMM but %s"
                % self._sample.__class__.__name__
            )
            raise BaseException(strMessage)
        if xdsBackgroundImage is None:
            self._xdsBackgroundImage = None
        elif xdsBackgroundImage.__class__.__name__ == "XSDataFile":
            self._xdsBackgroundImage = xdsBackgroundImage
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy constructor argument 'xdsBackgroundImage' is not XSDataFile but %s"
                % self._xdsBackgroundImage.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'bestFileContentDat' attribute
    def getBestFileContentDat(self):
        return self._bestFileContentDat

    def setBestFileContentDat(self, bestFileContentDat):
        if bestFileContentDat is None:
            self._bestFileContentDat = None
        elif bestFileContentDat.__class__.__name__ == "XSDataString":
            self._bestFileContentDat = bestFileContentDat
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy.setBestFileContentDat argument is not XSDataString but %s"
                % bestFileContentDat.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBestFileContentDat(self):
        self._bestFileContentDat = None

    bestFileContentDat = property(
        getBestFileContentDat,
        setBestFileContentDat,
        delBestFileContentDat,
        "Property for bestFileContentDat",
    )
    # Methods and properties for the 'bestFileContentHKL' attribute

    def getBestFileContentHKL(self):
        return self._bestFileContentHKL

    def setBestFileContentHKL(self, bestFileContentHKL):
        if bestFileContentHKL is None:
            self._bestFileContentHKL = []
        elif bestFileContentHKL.__class__.__name__ == "list":
            self._bestFileContentHKL = bestFileContentHKL
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy.setBestFileContentHKL argument is not list but %s"
                % bestFileContentHKL.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBestFileContentHKL(self):
        self._bestFileContentHKL = None

    bestFileContentHKL = property(
        getBestFileContentHKL,
        setBestFileContentHKL,
        delBestFileContentHKL,
        "Property for bestFileContentHKL",
    )

    def addBestFileContentHKL(self, value):
        if value is None:
            strMessage = (
                "ERROR! XSDataInputStrategy.addBestFileContentHKL argument is None"
            )
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataString":
            self._bestFileContentHKL.append(value)
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy.addBestFileContentHKL argument is not XSDataString but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertBestFileContentHKL(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataInputStrategy.insertBestFileContentHKL argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataInputStrategy.insertBestFileContentHKL argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataString":
            self._bestFileContentHKL[index] = value
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy.addBestFileContentHKL argument is not XSDataString but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'bestFileContentPar' attribute
    def getBestFileContentPar(self):
        return self._bestFileContentPar

    def setBestFileContentPar(self, bestFileContentPar):
        if bestFileContentPar is None:
            self._bestFileContentPar = None
        elif bestFileContentPar.__class__.__name__ == "XSDataString":
            self._bestFileContentPar = bestFileContentPar
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy.setBestFileContentPar argument is not XSDataString but %s"
                % bestFileContentPar.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBestFileContentPar(self):
        self._bestFileContentPar = None

    bestFileContentPar = property(
        getBestFileContentPar,
        setBestFileContentPar,
        delBestFileContentPar,
        "Property for bestFileContentPar",
    )
    # Methods and properties for the 'crystalRefined' attribute

    def getCrystalRefined(self):
        return self._crystalRefined

    def setCrystalRefined(self, crystalRefined):
        if crystalRefined is None:
            self._crystalRefined = None
        elif crystalRefined.__class__.__name__ == "XSDataCrystal":
            self._crystalRefined = crystalRefined
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy.setCrystalRefined argument is not XSDataCrystal but %s"
                % crystalRefined.__class__.__name__
            )
            raise BaseException(strMessage)

    def delCrystalRefined(self):
        self._crystalRefined = None

    crystalRefined = property(
        getCrystalRefined,
        setCrystalRefined,
        delCrystalRefined,
        "Property for crystalRefined",
    )
    # Methods and properties for the 'diffractionPlan' attribute

    def getDiffractionPlan(self):
        return self._diffractionPlan

    def setDiffractionPlan(self, diffractionPlan):
        if diffractionPlan is None:
            self._diffractionPlan = None
        elif diffractionPlan.__class__.__name__ == "XSDataDiffractionPlan":
            self._diffractionPlan = diffractionPlan
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy.setDiffractionPlan argument is not XSDataDiffractionPlan but %s"
                % diffractionPlan.__class__.__name__
            )
            raise BaseException(strMessage)

    def delDiffractionPlan(self):
        self._diffractionPlan = None

    diffractionPlan = property(
        getDiffractionPlan,
        setDiffractionPlan,
        delDiffractionPlan,
        "Property for diffractionPlan",
    )
    # Methods and properties for the 'experimentalCondition' attribute

    def getExperimentalCondition(self):
        return self._experimentalCondition

    def setExperimentalCondition(self, experimentalCondition):
        if experimentalCondition is None:
            self._experimentalCondition = None
        elif experimentalCondition.__class__.__name__ == "XSDataExperimentalCondition":
            self._experimentalCondition = experimentalCondition
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy.setExperimentalCondition argument is not XSDataExperimentalCondition but %s"
                % experimentalCondition.__class__.__name__
            )
            raise BaseException(strMessage)

    def delExperimentalCondition(self):
        self._experimentalCondition = None

    experimentalCondition = property(
        getExperimentalCondition,
        setExperimentalCondition,
        delExperimentalCondition,
        "Property for experimentalCondition",
    )
    # Methods and properties for the 'sample' attribute

    def getSample(self):
        return self._sample

    def setSample(self, sample):
        if sample is None:
            self._sample = None
        elif sample.__class__.__name__ == "XSDataSampleCrystalMM":
            self._sample = sample
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy.setSample argument is not XSDataSampleCrystalMM but %s"
                % sample.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSample(self):
        self._sample = None

    sample = property(getSample, setSample, delSample, "Property for sample")
    # Methods and properties for the 'xdsBackgroundImage' attribute

    def getXdsBackgroundImage(self):
        return self._xdsBackgroundImage

    def setXdsBackgroundImage(self, xdsBackgroundImage):
        if xdsBackgroundImage is None:
            self._xdsBackgroundImage = None
        elif xdsBackgroundImage.__class__.__name__ == "XSDataFile":
            self._xdsBackgroundImage = xdsBackgroundImage
        else:
            strMessage = (
                "ERROR! XSDataInputStrategy.setXdsBackgroundImage argument is not XSDataFile but %s"
                % xdsBackgroundImage.__class__.__name__
            )
            raise BaseException(strMessage)

    def delXdsBackgroundImage(self):
        self._xdsBackgroundImage = None

    xdsBackgroundImage = property(
        getXdsBackgroundImage,
        setXdsBackgroundImage,
        delXdsBackgroundImage,
        "Property for xdsBackgroundImage",
    )

    def export(self, outfile, level, name_="XSDataInputStrategy"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataInputStrategy"):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._bestFileContentDat is not None:
            self.bestFileContentDat.export(outfile, level, name_="bestFileContentDat")
        else:
            warnEmptyAttribute("bestFileContentDat", "XSDataString")
        for bestFileContentHKL_ in self.getBestFileContentHKL():
            bestFileContentHKL_.export(outfile, level, name_="bestFileContentHKL")
        if self.getBestFileContentHKL() == []:
            warnEmptyAttribute("bestFileContentHKL", "XSDataString")
        if self._bestFileContentPar is not None:
            self.bestFileContentPar.export(outfile, level, name_="bestFileContentPar")
        else:
            warnEmptyAttribute("bestFileContentPar", "XSDataString")
        if self._crystalRefined is not None:
            self.crystalRefined.export(outfile, level, name_="crystalRefined")
        else:
            warnEmptyAttribute("crystalRefined", "XSDataCrystal")
        if self._diffractionPlan is not None:
            self.diffractionPlan.export(outfile, level, name_="diffractionPlan")
        else:
            warnEmptyAttribute("diffractionPlan", "XSDataDiffractionPlan")
        if self._experimentalCondition is not None:
            self.experimentalCondition.export(
                outfile, level, name_="experimentalCondition"
            )
        else:
            warnEmptyAttribute("experimentalCondition", "XSDataExperimentalCondition")
        if self._sample is not None:
            self.sample.export(outfile, level, name_="sample")
        else:
            warnEmptyAttribute("sample", "XSDataSampleCrystalMM")
        if self._xdsBackgroundImage is not None:
            self.xdsBackgroundImage.export(outfile, level, name_="xdsBackgroundImage")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "bestFileContentDat":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setBestFileContentDat(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "bestFileContentHKL":
            obj_ = XSDataString()
            obj_.build(child_)
            self.bestFileContentHKL.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "bestFileContentPar":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setBestFileContentPar(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "crystalRefined":
            obj_ = XSDataCrystal()
            obj_.build(child_)
            self.setCrystalRefined(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "diffractionPlan":
            obj_ = XSDataDiffractionPlan()
            obj_.build(child_)
            self.setDiffractionPlan(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "experimentalCondition"
        ):
            obj_ = XSDataExperimentalCondition()
            obj_.build(child_)
            self.setExperimentalCondition(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "sample":
            obj_ = XSDataSampleCrystalMM()
            obj_.build(child_)
            self.setSample(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "xdsBackgroundImage":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setXdsBackgroundImage(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataInputStrategy")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataInputStrategy")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataInputStrategy is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataInputStrategy.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputStrategy()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataInputStrategy")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputStrategy()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataInputStrategy


class XSDataInputSubWedgeAssemble(XSDataInput):
    """These two definitions are used by the sub wedge assemble plugin."""

    def __init__(self, configuration=None, file=None):
        XSDataInput.__init__(self, configuration)
        if file is None:
            self._file = []
        elif file.__class__.__name__ == "list":
            self._file = file
        else:
            strMessage = (
                "ERROR! XSDataInputSubWedgeAssemble constructor argument 'file' is not list but %s"
                % self._file.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'file' attribute
    def getFile(self):
        return self._file

    def setFile(self, file):
        if file is None:
            self._file = []
        elif file.__class__.__name__ == "list":
            self._file = file
        else:
            strMessage = (
                "ERROR! XSDataInputSubWedgeAssemble.setFile argument is not list but %s"
                % file.__class__.__name__
            )
            raise BaseException(strMessage)

    def delFile(self):
        self._file = None

    file = property(getFile, setFile, delFile, "Property for file")

    def addFile(self, value):
        if value is None:
            strMessage = "ERROR! XSDataInputSubWedgeAssemble.addFile argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataFile":
            self._file.append(value)
        else:
            strMessage = (
                "ERROR! XSDataInputSubWedgeAssemble.addFile argument is not XSDataFile but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertFile(self, index, value):
        if index is None:
            strMessage = (
                "ERROR! XSDataInputSubWedgeAssemble.insertFile argument 'index' is None"
            )
            raise BaseException(strMessage)
        if value is None:
            strMessage = (
                "ERROR! XSDataInputSubWedgeAssemble.insertFile argument 'value' is None"
            )
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataFile":
            self._file[index] = value
        else:
            strMessage = (
                "ERROR! XSDataInputSubWedgeAssemble.addFile argument is not XSDataFile but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def export(self, outfile, level, name_="XSDataInputSubWedgeAssemble"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataInputSubWedgeAssemble"):
        XSDataInput.exportChildren(self, outfile, level, name_)
        for file_ in self.getFile():
            file_.export(outfile, level, name_="file")
        if self.getFile() == []:
            warnEmptyAttribute("file", "XSDataFile")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "file":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.file.append(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataInputSubWedgeAssemble")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataInputSubWedgeAssemble")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataInputSubWedgeAssemble is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataInputSubWedgeAssemble.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputSubWedgeAssemble()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataInputSubWedgeAssemble")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputSubWedgeAssemble()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataInputSubWedgeAssemble


class XSDataInputSubWedgeMerge(XSDataInput):
    """These two definitions are used by the sub wedge merge plugins."""

    def __init__(self, configuration=None, subWedge=None):
        XSDataInput.__init__(self, configuration)
        if subWedge is None:
            self._subWedge = []
        elif subWedge.__class__.__name__ == "list":
            self._subWedge = subWedge
        else:
            strMessage = (
                "ERROR! XSDataInputSubWedgeMerge constructor argument 'subWedge' is not list but %s"
                % self._subWedge.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'subWedge' attribute
    def getSubWedge(self):
        return self._subWedge

    def setSubWedge(self, subWedge):
        if subWedge is None:
            self._subWedge = []
        elif subWedge.__class__.__name__ == "list":
            self._subWedge = subWedge
        else:
            strMessage = (
                "ERROR! XSDataInputSubWedgeMerge.setSubWedge argument is not list but %s"
                % subWedge.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSubWedge(self):
        self._subWedge = None

    subWedge = property(getSubWedge, setSubWedge, delSubWedge, "Property for subWedge")

    def addSubWedge(self, value):
        if value is None:
            strMessage = "ERROR! XSDataInputSubWedgeMerge.addSubWedge argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataSubWedge":
            self._subWedge.append(value)
        else:
            strMessage = (
                "ERROR! XSDataInputSubWedgeMerge.addSubWedge argument is not XSDataSubWedge but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertSubWedge(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataInputSubWedgeMerge.insertSubWedge argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataInputSubWedgeMerge.insertSubWedge argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataSubWedge":
            self._subWedge[index] = value
        else:
            strMessage = (
                "ERROR! XSDataInputSubWedgeMerge.addSubWedge argument is not XSDataSubWedge but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def export(self, outfile, level, name_="XSDataInputSubWedgeMerge"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataInputSubWedgeMerge"):
        XSDataInput.exportChildren(self, outfile, level, name_)
        for subWedge_ in self.getSubWedge():
            subWedge_.export(outfile, level, name_="subWedge")
        if self.getSubWedge() == []:
            warnEmptyAttribute("subWedge", "XSDataSubWedge")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "subWedge":
            obj_ = XSDataSubWedge()
            obj_.build(child_)
            self.subWedge.append(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataInputSubWedgeMerge")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataInputSubWedgeMerge")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataInputSubWedgeMerge is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataInputSubWedgeMerge.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputSubWedgeMerge()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataInputSubWedgeMerge")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputSubWedgeMerge()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataInputSubWedgeMerge


class XSDataIntegrationResult(XSDataResult):
    def __init__(self, status=None, integrationSubWedgeResult=None):
        XSDataResult.__init__(self, status)
        if integrationSubWedgeResult is None:
            self._integrationSubWedgeResult = []
        elif integrationSubWedgeResult.__class__.__name__ == "list":
            self._integrationSubWedgeResult = integrationSubWedgeResult
        else:
            strMessage = (
                "ERROR! XSDataIntegrationResult constructor argument 'integrationSubWedgeResult' is not list but %s"
                % self._integrationSubWedgeResult.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'integrationSubWedgeResult' attribute
    def getIntegrationSubWedgeResult(self):
        return self._integrationSubWedgeResult

    def setIntegrationSubWedgeResult(self, integrationSubWedgeResult):
        if integrationSubWedgeResult is None:
            self._integrationSubWedgeResult = []
        elif integrationSubWedgeResult.__class__.__name__ == "list":
            self._integrationSubWedgeResult = integrationSubWedgeResult
        else:
            strMessage = (
                "ERROR! XSDataIntegrationResult.setIntegrationSubWedgeResult argument is not list but %s"
                % integrationSubWedgeResult.__class__.__name__
            )
            raise BaseException(strMessage)

    def delIntegrationSubWedgeResult(self):
        self._integrationSubWedgeResult = None

    integrationSubWedgeResult = property(
        getIntegrationSubWedgeResult,
        setIntegrationSubWedgeResult,
        delIntegrationSubWedgeResult,
        "Property for integrationSubWedgeResult",
    )

    def addIntegrationSubWedgeResult(self, value):
        if value is None:
            strMessage = "ERROR! XSDataIntegrationResult.addIntegrationSubWedgeResult argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataIntegrationSubWedgeResult":
            self._integrationSubWedgeResult.append(value)
        else:
            strMessage = (
                "ERROR! XSDataIntegrationResult.addIntegrationSubWedgeResult argument is not XSDataIntegrationSubWedgeResult but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertIntegrationSubWedgeResult(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataIntegrationResult.insertIntegrationSubWedgeResult argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataIntegrationResult.insertIntegrationSubWedgeResult argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataIntegrationSubWedgeResult":
            self._integrationSubWedgeResult[index] = value
        else:
            strMessage = (
                "ERROR! XSDataIntegrationResult.addIntegrationSubWedgeResult argument is not XSDataIntegrationSubWedgeResult but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def export(self, outfile, level, name_="XSDataIntegrationResult"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataIntegrationResult"):
        XSDataResult.exportChildren(self, outfile, level, name_)
        for integrationSubWedgeResult_ in self.getIntegrationSubWedgeResult():
            integrationSubWedgeResult_.export(
                outfile, level, name_="integrationSubWedgeResult"
            )

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "integrationSubWedgeResult"
        ):
            obj_ = XSDataIntegrationSubWedgeResult()
            obj_.build(child_)
            self.integrationSubWedgeResult.append(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataIntegrationResult")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataIntegrationResult")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataIntegrationResult is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataIntegrationResult.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataIntegrationResult()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataIntegrationResult")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataIntegrationResult()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataIntegrationResult


class XSDataResultCharacterisation(XSDataResult):
    def __init__(
        self,
        status=None,
        xdsBackgroundImage=None,
        strategyResult=None,
        statusMessage=None,
        shortSummary=None,
        integrationResult=None,
        indexingResult=None,
        imageQualityIndicators=None,
        executiveSummary=None,
        dataCollection=None,
    ):
        XSDataResult.__init__(self, status)
        if dataCollection is None:
            self._dataCollection = None
        elif dataCollection.__class__.__name__ == "XSDataCollection":
            self._dataCollection = dataCollection
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation constructor argument 'dataCollection' is not XSDataCollection but %s"
                % self._dataCollection.__class__.__name__
            )
            raise BaseException(strMessage)
        if executiveSummary is None:
            self._executiveSummary = None
        elif executiveSummary.__class__.__name__ == "XSDataString":
            self._executiveSummary = executiveSummary
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation constructor argument 'executiveSummary' is not XSDataString but %s"
                % self._executiveSummary.__class__.__name__
            )
            raise BaseException(strMessage)
        if imageQualityIndicators is None:
            self._imageQualityIndicators = []
        elif imageQualityIndicators.__class__.__name__ == "list":
            self._imageQualityIndicators = imageQualityIndicators
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation constructor argument 'imageQualityIndicators' is not list but %s"
                % self._imageQualityIndicators.__class__.__name__
            )
            raise BaseException(strMessage)
        if indexingResult is None:
            self._indexingResult = None
        elif indexingResult.__class__.__name__ == "XSDataIndexingResult":
            self._indexingResult = indexingResult
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation constructor argument 'indexingResult' is not XSDataIndexingResult but %s"
                % self._indexingResult.__class__.__name__
            )
            raise BaseException(strMessage)
        if integrationResult is None:
            self._integrationResult = None
        elif integrationResult.__class__.__name__ == "XSDataIntegrationResult":
            self._integrationResult = integrationResult
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation constructor argument 'integrationResult' is not XSDataIntegrationResult but %s"
                % self._integrationResult.__class__.__name__
            )
            raise BaseException(strMessage)
        if shortSummary is None:
            self._shortSummary = None
        elif shortSummary.__class__.__name__ == "XSDataString":
            self._shortSummary = shortSummary
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation constructor argument 'shortSummary' is not XSDataString but %s"
                % self._shortSummary.__class__.__name__
            )
            raise BaseException(strMessage)
        if statusMessage is None:
            self._statusMessage = None
        elif statusMessage.__class__.__name__ == "XSDataString":
            self._statusMessage = statusMessage
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation constructor argument 'statusMessage' is not XSDataString but %s"
                % self._statusMessage.__class__.__name__
            )
            raise BaseException(strMessage)
        if strategyResult is None:
            self._strategyResult = None
        elif strategyResult.__class__.__name__ == "XSDataResultStrategy":
            self._strategyResult = strategyResult
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation constructor argument 'strategyResult' is not XSDataResultStrategy but %s"
                % self._strategyResult.__class__.__name__
            )
            raise BaseException(strMessage)
        if xdsBackgroundImage is None:
            self._xdsBackgroundImage = None
        elif xdsBackgroundImage.__class__.__name__ == "XSDataFile":
            self._xdsBackgroundImage = xdsBackgroundImage
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation constructor argument 'xdsBackgroundImage' is not XSDataFile but %s"
                % self._xdsBackgroundImage.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'dataCollection' attribute
    def getDataCollection(self):
        return self._dataCollection

    def setDataCollection(self, dataCollection):
        if dataCollection is None:
            self._dataCollection = None
        elif dataCollection.__class__.__name__ == "XSDataCollection":
            self._dataCollection = dataCollection
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation.setDataCollection argument is not XSDataCollection but %s"
                % dataCollection.__class__.__name__
            )
            raise BaseException(strMessage)

    def delDataCollection(self):
        self._dataCollection = None

    dataCollection = property(
        getDataCollection,
        setDataCollection,
        delDataCollection,
        "Property for dataCollection",
    )
    # Methods and properties for the 'executiveSummary' attribute

    def getExecutiveSummary(self):
        return self._executiveSummary

    def setExecutiveSummary(self, executiveSummary):
        if executiveSummary is None:
            self._executiveSummary = None
        elif executiveSummary.__class__.__name__ == "XSDataString":
            self._executiveSummary = executiveSummary
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation.setExecutiveSummary argument is not XSDataString but %s"
                % executiveSummary.__class__.__name__
            )
            raise BaseException(strMessage)

    def delExecutiveSummary(self):
        self._executiveSummary = None

    executiveSummary = property(
        getExecutiveSummary,
        setExecutiveSummary,
        delExecutiveSummary,
        "Property for executiveSummary",
    )
    # Methods and properties for the 'imageQualityIndicators' attribute

    def getImageQualityIndicators(self):
        return self._imageQualityIndicators

    def setImageQualityIndicators(self, imageQualityIndicators):
        if imageQualityIndicators is None:
            self._imageQualityIndicators = []
        elif imageQualityIndicators.__class__.__name__ == "list":
            self._imageQualityIndicators = imageQualityIndicators
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation.setImageQualityIndicators argument is not list but %s"
                % imageQualityIndicators.__class__.__name__
            )
            raise BaseException(strMessage)

    def delImageQualityIndicators(self):
        self._imageQualityIndicators = None

    imageQualityIndicators = property(
        getImageQualityIndicators,
        setImageQualityIndicators,
        delImageQualityIndicators,
        "Property for imageQualityIndicators",
    )

    def addImageQualityIndicators(self, value):
        if value is None:
            strMessage = "ERROR! XSDataResultCharacterisation.addImageQualityIndicators argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataImageQualityIndicators":
            self._imageQualityIndicators.append(value)
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation.addImageQualityIndicators argument is not XSDataImageQualityIndicators but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertImageQualityIndicators(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataResultCharacterisation.insertImageQualityIndicators argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataResultCharacterisation.insertImageQualityIndicators argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataImageQualityIndicators":
            self._imageQualityIndicators[index] = value
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation.addImageQualityIndicators argument is not XSDataImageQualityIndicators but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'indexingResult' attribute
    def getIndexingResult(self):
        return self._indexingResult

    def setIndexingResult(self, indexingResult):
        if indexingResult is None:
            self._indexingResult = None
        elif indexingResult.__class__.__name__ == "XSDataIndexingResult":
            self._indexingResult = indexingResult
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation.setIndexingResult argument is not XSDataIndexingResult but %s"
                % indexingResult.__class__.__name__
            )
            raise BaseException(strMessage)

    def delIndexingResult(self):
        self._indexingResult = None

    indexingResult = property(
        getIndexingResult,
        setIndexingResult,
        delIndexingResult,
        "Property for indexingResult",
    )
    # Methods and properties for the 'integrationResult' attribute

    def getIntegrationResult(self):
        return self._integrationResult

    def setIntegrationResult(self, integrationResult):
        if integrationResult is None:
            self._integrationResult = None
        elif integrationResult.__class__.__name__ == "XSDataIntegrationResult":
            self._integrationResult = integrationResult
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation.setIntegrationResult argument is not XSDataIntegrationResult but %s"
                % integrationResult.__class__.__name__
            )
            raise BaseException(strMessage)

    def delIntegrationResult(self):
        self._integrationResult = None

    integrationResult = property(
        getIntegrationResult,
        setIntegrationResult,
        delIntegrationResult,
        "Property for integrationResult",
    )
    # Methods and properties for the 'shortSummary' attribute

    def getShortSummary(self):
        return self._shortSummary

    def setShortSummary(self, shortSummary):
        if shortSummary is None:
            self._shortSummary = None
        elif shortSummary.__class__.__name__ == "XSDataString":
            self._shortSummary = shortSummary
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation.setShortSummary argument is not XSDataString but %s"
                % shortSummary.__class__.__name__
            )
            raise BaseException(strMessage)

    def delShortSummary(self):
        self._shortSummary = None

    shortSummary = property(
        getShortSummary, setShortSummary, delShortSummary, "Property for shortSummary"
    )
    # Methods and properties for the 'statusMessage' attribute

    def getStatusMessage(self):
        return self._statusMessage

    def setStatusMessage(self, statusMessage):
        if statusMessage is None:
            self._statusMessage = None
        elif statusMessage.__class__.__name__ == "XSDataString":
            self._statusMessage = statusMessage
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation.setStatusMessage argument is not XSDataString but %s"
                % statusMessage.__class__.__name__
            )
            raise BaseException(strMessage)

    def delStatusMessage(self):
        self._statusMessage = None

    statusMessage = property(
        getStatusMessage,
        setStatusMessage,
        delStatusMessage,
        "Property for statusMessage",
    )
    # Methods and properties for the 'strategyResult' attribute

    def getStrategyResult(self):
        return self._strategyResult

    def setStrategyResult(self, strategyResult):
        if strategyResult is None:
            self._strategyResult = None
        elif strategyResult.__class__.__name__ == "XSDataResultStrategy":
            self._strategyResult = strategyResult
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation.setStrategyResult argument is not XSDataResultStrategy but %s"
                % strategyResult.__class__.__name__
            )
            raise BaseException(strMessage)

    def delStrategyResult(self):
        self._strategyResult = None

    strategyResult = property(
        getStrategyResult,
        setStrategyResult,
        delStrategyResult,
        "Property for strategyResult",
    )
    # Methods and properties for the 'xdsBackgroundImage' attribute

    def getXdsBackgroundImage(self):
        return self._xdsBackgroundImage

    def setXdsBackgroundImage(self, xdsBackgroundImage):
        if xdsBackgroundImage is None:
            self._xdsBackgroundImage = None
        elif xdsBackgroundImage.__class__.__name__ == "XSDataFile":
            self._xdsBackgroundImage = xdsBackgroundImage
        else:
            strMessage = (
                "ERROR! XSDataResultCharacterisation.setXdsBackgroundImage argument is not XSDataFile but %s"
                % xdsBackgroundImage.__class__.__name__
            )
            raise BaseException(strMessage)

    def delXdsBackgroundImage(self):
        self._xdsBackgroundImage = None

    xdsBackgroundImage = property(
        getXdsBackgroundImage,
        setXdsBackgroundImage,
        delXdsBackgroundImage,
        "Property for xdsBackgroundImage",
    )

    def export(self, outfile, level, name_="XSDataResultCharacterisation"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataResultCharacterisation"):
        XSDataResult.exportChildren(self, outfile, level, name_)
        if self._dataCollection is not None:
            self.dataCollection.export(outfile, level, name_="dataCollection")
        else:
            warnEmptyAttribute("dataCollection", "XSDataCollection")
        if self._executiveSummary is not None:
            self.executiveSummary.export(outfile, level, name_="executiveSummary")
        else:
            warnEmptyAttribute("executiveSummary", "XSDataString")
        for imageQualityIndicators_ in self.getImageQualityIndicators():
            imageQualityIndicators_.export(
                outfile, level, name_="imageQualityIndicators"
            )
        if self._indexingResult is not None:
            self.indexingResult.export(outfile, level, name_="indexingResult")
        if self._integrationResult is not None:
            self.integrationResult.export(outfile, level, name_="integrationResult")
        if self._shortSummary is not None:
            self.shortSummary.export(outfile, level, name_="shortSummary")
        else:
            warnEmptyAttribute("shortSummary", "XSDataString")
        if self._statusMessage is not None:
            self.statusMessage.export(outfile, level, name_="statusMessage")
        else:
            warnEmptyAttribute("statusMessage", "XSDataString")
        if self._strategyResult is not None:
            self.strategyResult.export(outfile, level, name_="strategyResult")
        if self._xdsBackgroundImage is not None:
            self.xdsBackgroundImage.export(outfile, level, name_="xdsBackgroundImage")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "dataCollection":
            obj_ = XSDataCollection()
            obj_.build(child_)
            self.setDataCollection(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "executiveSummary":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setExecutiveSummary(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "imageQualityIndicators"
        ):
            obj_ = XSDataImageQualityIndicators()
            obj_.build(child_)
            self.imageQualityIndicators.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "indexingResult":
            obj_ = XSDataIndexingResult()
            obj_.build(child_)
            self.setIndexingResult(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "integrationResult":
            obj_ = XSDataIntegrationResult()
            obj_.build(child_)
            self.setIntegrationResult(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "shortSummary":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setShortSummary(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "statusMessage":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setStatusMessage(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "strategyResult":
            obj_ = XSDataResultStrategy()
            obj_.build(child_)
            self.setStrategyResult(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "xdsBackgroundImage":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setXdsBackgroundImage(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataResultCharacterisation")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataResultCharacterisation")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataResultCharacterisation is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataResultCharacterisation.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultCharacterisation()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataResultCharacterisation")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultCharacterisation()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataResultCharacterisation


class XSDataResultControlISPyB(XSDataResult):
    """No attributes - the return value is XSDataStatus provided by XSDataResult"""

    def __init__(self, status=None, screeningId=None):
        XSDataResult.__init__(self, status)
        if screeningId is None:
            self._screeningId = None
        elif screeningId.__class__.__name__ == "XSDataInteger":
            self._screeningId = screeningId
        else:
            strMessage = (
                "ERROR! XSDataResultControlISPyB constructor argument 'screeningId' is not XSDataInteger but %s"
                % self._screeningId.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'screeningId' attribute
    def getScreeningId(self):
        return self._screeningId

    def setScreeningId(self, screeningId):
        if screeningId is None:
            self._screeningId = None
        elif screeningId.__class__.__name__ == "XSDataInteger":
            self._screeningId = screeningId
        else:
            strMessage = (
                "ERROR! XSDataResultControlISPyB.setScreeningId argument is not XSDataInteger but %s"
                % screeningId.__class__.__name__
            )
            raise BaseException(strMessage)

    def delScreeningId(self):
        self._screeningId = None

    screeningId = property(
        getScreeningId, setScreeningId, delScreeningId, "Property for screeningId"
    )

    def export(self, outfile, level, name_="XSDataResultControlISPyB"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataResultControlISPyB"):
        XSDataResult.exportChildren(self, outfile, level, name_)
        if self._screeningId is not None:
            self.screeningId.export(outfile, level, name_="screeningId")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "screeningId":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setScreeningId(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataResultControlISPyB")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataResultControlISPyB")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataResultControlISPyB is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataResultControlISPyB.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultControlISPyB()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataResultControlISPyB")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultControlISPyB()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataResultControlISPyB


class XSDataResultControlImageQualityIndicators(XSDataResult):
    def __init__(self, status=None, imageQualityIndicators=None):
        XSDataResult.__init__(self, status)
        if imageQualityIndicators is None:
            self._imageQualityIndicators = []
        elif imageQualityIndicators.__class__.__name__ == "list":
            self._imageQualityIndicators = imageQualityIndicators
        else:
            strMessage = (
                "ERROR! XSDataResultControlImageQualityIndicators constructor argument 'imageQualityIndicators' is not list but %s"
                % self._imageQualityIndicators.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'imageQualityIndicators' attribute
    def getImageQualityIndicators(self):
        return self._imageQualityIndicators

    def setImageQualityIndicators(self, imageQualityIndicators):
        if imageQualityIndicators is None:
            self._imageQualityIndicators = []
        elif imageQualityIndicators.__class__.__name__ == "list":
            self._imageQualityIndicators = imageQualityIndicators
        else:
            strMessage = (
                "ERROR! XSDataResultControlImageQualityIndicators.setImageQualityIndicators argument is not list but %s"
                % imageQualityIndicators.__class__.__name__
            )
            raise BaseException(strMessage)

    def delImageQualityIndicators(self):
        self._imageQualityIndicators = None

    imageQualityIndicators = property(
        getImageQualityIndicators,
        setImageQualityIndicators,
        delImageQualityIndicators,
        "Property for imageQualityIndicators",
    )

    def addImageQualityIndicators(self, value):
        if value is None:
            strMessage = "ERROR! XSDataResultControlImageQualityIndicators.addImageQualityIndicators argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataImageQualityIndicators":
            self._imageQualityIndicators.append(value)
        else:
            strMessage = (
                "ERROR! XSDataResultControlImageQualityIndicators.addImageQualityIndicators argument is not XSDataImageQualityIndicators but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertImageQualityIndicators(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataResultControlImageQualityIndicators.insertImageQualityIndicators argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataResultControlImageQualityIndicators.insertImageQualityIndicators argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataImageQualityIndicators":
            self._imageQualityIndicators[index] = value
        else:
            strMessage = (
                "ERROR! XSDataResultControlImageQualityIndicators.addImageQualityIndicators argument is not XSDataImageQualityIndicators but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def export(self, outfile, level, name_="XSDataResultControlImageQualityIndicators"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(
        self, outfile, level, name_="XSDataResultControlImageQualityIndicators"
    ):
        XSDataResult.exportChildren(self, outfile, level, name_)
        for imageQualityIndicators_ in self.getImageQualityIndicators():
            imageQualityIndicators_.export(
                outfile, level, name_="imageQualityIndicators"
            )

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "imageQualityIndicators"
        ):
            obj_ = XSDataImageQualityIndicators()
            obj_.build(child_)
            self.imageQualityIndicators.append(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataResultControlImageQualityIndicators")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataResultControlImageQualityIndicators")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataResultControlImageQualityIndicators is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataResultControlImageQualityIndicators.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultControlImageQualityIndicators()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(
            oStreamString, 0, name_="XSDataResultControlImageQualityIndicators"
        )
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultControlImageQualityIndicators()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataResultControlImageQualityIndicators


class XSDataResultControlXDSGenerateBackgroundImage(XSDataResult):
    def __init__(self, status=None, xdsBackgroundImage=None):
        XSDataResult.__init__(self, status)
        if xdsBackgroundImage is None:
            self._xdsBackgroundImage = None
        elif xdsBackgroundImage.__class__.__name__ == "XSDataFile":
            self._xdsBackgroundImage = xdsBackgroundImage
        else:
            strMessage = (
                "ERROR! XSDataResultControlXDSGenerateBackgroundImage constructor argument 'xdsBackgroundImage' is not XSDataFile but %s"
                % self._xdsBackgroundImage.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'xdsBackgroundImage' attribute
    def getXdsBackgroundImage(self):
        return self._xdsBackgroundImage

    def setXdsBackgroundImage(self, xdsBackgroundImage):
        if xdsBackgroundImage is None:
            self._xdsBackgroundImage = None
        elif xdsBackgroundImage.__class__.__name__ == "XSDataFile":
            self._xdsBackgroundImage = xdsBackgroundImage
        else:
            strMessage = (
                "ERROR! XSDataResultControlXDSGenerateBackgroundImage.setXdsBackgroundImage argument is not XSDataFile but %s"
                % xdsBackgroundImage.__class__.__name__
            )
            raise BaseException(strMessage)

    def delXdsBackgroundImage(self):
        self._xdsBackgroundImage = None

    xdsBackgroundImage = property(
        getXdsBackgroundImage,
        setXdsBackgroundImage,
        delXdsBackgroundImage,
        "Property for xdsBackgroundImage",
    )

    def export(
        self, outfile, level, name_="XSDataResultControlXDSGenerateBackgroundImage"
    ):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(
        self, outfile, level, name_="XSDataResultControlXDSGenerateBackgroundImage"
    ):
        XSDataResult.exportChildren(self, outfile, level, name_)
        if self._xdsBackgroundImage is not None:
            self.xdsBackgroundImage.export(outfile, level, name_="xdsBackgroundImage")
        else:
            warnEmptyAttribute("xdsBackgroundImage", "XSDataFile")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "xdsBackgroundImage":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setXdsBackgroundImage(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(
            oStreamString, 0, name_="XSDataResultControlXDSGenerateBackgroundImage"
        )
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataResultControlXDSGenerateBackgroundImage")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataResultControlXDSGenerateBackgroundImage is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataResultControlXDSGenerateBackgroundImage.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultControlXDSGenerateBackgroundImage()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(
            oStreamString, 0, name_="XSDataResultControlXDSGenerateBackgroundImage"
        )
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultControlXDSGenerateBackgroundImage()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataResultControlXDSGenerateBackgroundImage


class XSDataResultInducedRadiationProcess(XSDataResult):
    def __init__(self, status=None, scale=None, crystal=None, bFactor=None):
        XSDataResult.__init__(self, status)
        if bFactor is None:
            self._bFactor = None
        elif bFactor.__class__.__name__ == "XSDataDouble":
            self._bFactor = bFactor
        else:
            strMessage = (
                "ERROR! XSDataResultInducedRadiationProcess constructor argument 'bFactor' is not XSDataDouble but %s"
                % self._bFactor.__class__.__name__
            )
            raise BaseException(strMessage)
        if crystal is None:
            self._crystal = None
        elif crystal.__class__.__name__ == "XSDataCrystal":
            self._crystal = crystal
        else:
            strMessage = (
                "ERROR! XSDataResultInducedRadiationProcess constructor argument 'crystal' is not XSDataCrystal but %s"
                % self._crystal.__class__.__name__
            )
            raise BaseException(strMessage)
        if scale is None:
            self._scale = None
        elif scale.__class__.__name__ == "XSDataDouble":
            self._scale = scale
        else:
            strMessage = (
                "ERROR! XSDataResultInducedRadiationProcess constructor argument 'scale' is not XSDataDouble but %s"
                % self._scale.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'bFactor' attribute
    def getBFactor(self):
        return self._bFactor

    def setBFactor(self, bFactor):
        if bFactor is None:
            self._bFactor = None
        elif bFactor.__class__.__name__ == "XSDataDouble":
            self._bFactor = bFactor
        else:
            strMessage = (
                "ERROR! XSDataResultInducedRadiationProcess.setBFactor argument is not XSDataDouble but %s"
                % bFactor.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBFactor(self):
        self._bFactor = None

    bFactor = property(getBFactor, setBFactor, delBFactor, "Property for bFactor")
    # Methods and properties for the 'crystal' attribute

    def getCrystal(self):
        return self._crystal

    def setCrystal(self, crystal):
        if crystal is None:
            self._crystal = None
        elif crystal.__class__.__name__ == "XSDataCrystal":
            self._crystal = crystal
        else:
            strMessage = (
                "ERROR! XSDataResultInducedRadiationProcess.setCrystal argument is not XSDataCrystal but %s"
                % crystal.__class__.__name__
            )
            raise BaseException(strMessage)

    def delCrystal(self):
        self._crystal = None

    crystal = property(getCrystal, setCrystal, delCrystal, "Property for crystal")
    # Methods and properties for the 'scale' attribute

    def getScale(self):
        return self._scale

    def setScale(self, scale):
        if scale is None:
            self._scale = None
        elif scale.__class__.__name__ == "XSDataDouble":
            self._scale = scale
        else:
            strMessage = (
                "ERROR! XSDataResultInducedRadiationProcess.setScale argument is not XSDataDouble but %s"
                % scale.__class__.__name__
            )
            raise BaseException(strMessage)

    def delScale(self):
        self._scale = None

    scale = property(getScale, setScale, delScale, "Property for scale")

    def export(self, outfile, level, name_="XSDataResultInducedRadiationProcess"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(
        self, outfile, level, name_="XSDataResultInducedRadiationProcess"
    ):
        XSDataResult.exportChildren(self, outfile, level, name_)
        if self._bFactor is not None:
            self.bFactor.export(outfile, level, name_="bFactor")
        else:
            warnEmptyAttribute("bFactor", "XSDataDouble")
        if self._crystal is not None:
            self.crystal.export(outfile, level, name_="crystal")
        else:
            warnEmptyAttribute("crystal", "XSDataCrystal")
        if self._scale is not None:
            self.scale.export(outfile, level, name_="scale")
        else:
            warnEmptyAttribute("scale", "XSDataDouble")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "bFactor":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setBFactor(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "crystal":
            obj_ = XSDataCrystal()
            obj_.build(child_)
            self.setCrystal(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "scale":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setScale(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataResultInducedRadiationProcess")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataResultInducedRadiationProcess")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataResultInducedRadiationProcess is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataResultInducedRadiationProcess.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultInducedRadiationProcess()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataResultInducedRadiationProcess")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultInducedRadiationProcess()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataResultInducedRadiationProcess


class XSDataResultReadImageHeader(XSDataResult):
    """These two definitions are used by the read image header plugin."""

    def __init__(self, status=None, subWedge=None):
        XSDataResult.__init__(self, status)
        if subWedge is None:
            self._subWedge = None
        elif subWedge.__class__.__name__ == "XSDataSubWedge":
            self._subWedge = subWedge
        else:
            strMessage = (
                "ERROR! XSDataResultReadImageHeader constructor argument 'subWedge' is not XSDataSubWedge but %s"
                % self._subWedge.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'subWedge' attribute
    def getSubWedge(self):
        return self._subWedge

    def setSubWedge(self, subWedge):
        if subWedge is None:
            self._subWedge = None
        elif subWedge.__class__.__name__ == "XSDataSubWedge":
            self._subWedge = subWedge
        else:
            strMessage = (
                "ERROR! XSDataResultReadImageHeader.setSubWedge argument is not XSDataSubWedge but %s"
                % subWedge.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSubWedge(self):
        self._subWedge = None

    subWedge = property(getSubWedge, setSubWedge, delSubWedge, "Property for subWedge")

    def export(self, outfile, level, name_="XSDataResultReadImageHeader"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataResultReadImageHeader"):
        XSDataResult.exportChildren(self, outfile, level, name_)
        if self._subWedge is not None:
            self.subWedge.export(outfile, level, name_="subWedge")
        else:
            warnEmptyAttribute("subWedge", "XSDataSubWedge")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "subWedge":
            obj_ = XSDataSubWedge()
            obj_.build(child_)
            self.setSubWedge(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataResultReadImageHeader")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataResultReadImageHeader")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataResultReadImageHeader is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataResultReadImageHeader.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultReadImageHeader()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataResultReadImageHeader")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultReadImageHeader()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataResultReadImageHeader


class XSDataResultStrategy(XSDataResult):
    """Several collection plans could be present in case of multi-sweep strategy"""

    def __init__(
        self,
        status=None,
        sample=None,
        raddoseLogFile=None,
        collectionPlan=None,
        bestLogFile=None,
        bestGraphFile=None,
    ):
        XSDataResult.__init__(self, status)
        if bestGraphFile is None:
            self._bestGraphFile = []
        elif bestGraphFile.__class__.__name__ == "list":
            self._bestGraphFile = bestGraphFile
        else:
            strMessage = (
                "ERROR! XSDataResultStrategy constructor argument 'bestGraphFile' is not list but %s"
                % self._bestGraphFile.__class__.__name__
            )
            raise BaseException(strMessage)
        if bestLogFile is None:
            self._bestLogFile = None
        elif bestLogFile.__class__.__name__ == "XSDataFile":
            self._bestLogFile = bestLogFile
        else:
            strMessage = (
                "ERROR! XSDataResultStrategy constructor argument 'bestLogFile' is not XSDataFile but %s"
                % self._bestLogFile.__class__.__name__
            )
            raise BaseException(strMessage)
        if collectionPlan is None:
            self._collectionPlan = []
        elif collectionPlan.__class__.__name__ == "list":
            self._collectionPlan = collectionPlan
        else:
            strMessage = (
                "ERROR! XSDataResultStrategy constructor argument 'collectionPlan' is not list but %s"
                % self._collectionPlan.__class__.__name__
            )
            raise BaseException(strMessage)
        if raddoseLogFile is None:
            self._raddoseLogFile = None
        elif raddoseLogFile.__class__.__name__ == "XSDataFile":
            self._raddoseLogFile = raddoseLogFile
        else:
            strMessage = (
                "ERROR! XSDataResultStrategy constructor argument 'raddoseLogFile' is not XSDataFile but %s"
                % self._raddoseLogFile.__class__.__name__
            )
            raise BaseException(strMessage)
        if sample is None:
            self._sample = None
        elif sample.__class__.__name__ == "XSDataSampleCrystalMM":
            self._sample = sample
        else:
            strMessage = (
                "ERROR! XSDataResultStrategy constructor argument 'sample' is not XSDataSampleCrystalMM but %s"
                % self._sample.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'bestGraphFile' attribute
    def getBestGraphFile(self):
        return self._bestGraphFile

    def setBestGraphFile(self, bestGraphFile):
        if bestGraphFile is None:
            self._bestGraphFile = []
        elif bestGraphFile.__class__.__name__ == "list":
            self._bestGraphFile = bestGraphFile
        else:
            strMessage = (
                "ERROR! XSDataResultStrategy.setBestGraphFile argument is not list but %s"
                % bestGraphFile.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBestGraphFile(self):
        self._bestGraphFile = None

    bestGraphFile = property(
        getBestGraphFile,
        setBestGraphFile,
        delBestGraphFile,
        "Property for bestGraphFile",
    )

    def addBestGraphFile(self, value):
        if value is None:
            strMessage = "ERROR! XSDataResultStrategy.addBestGraphFile argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataFile":
            self._bestGraphFile.append(value)
        else:
            strMessage = (
                "ERROR! XSDataResultStrategy.addBestGraphFile argument is not XSDataFile but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertBestGraphFile(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataResultStrategy.insertBestGraphFile argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataResultStrategy.insertBestGraphFile argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataFile":
            self._bestGraphFile[index] = value
        else:
            strMessage = (
                "ERROR! XSDataResultStrategy.addBestGraphFile argument is not XSDataFile but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'bestLogFile' attribute
    def getBestLogFile(self):
        return self._bestLogFile

    def setBestLogFile(self, bestLogFile):
        if bestLogFile is None:
            self._bestLogFile = None
        elif bestLogFile.__class__.__name__ == "XSDataFile":
            self._bestLogFile = bestLogFile
        else:
            strMessage = (
                "ERROR! XSDataResultStrategy.setBestLogFile argument is not XSDataFile but %s"
                % bestLogFile.__class__.__name__
            )
            raise BaseException(strMessage)

    def delBestLogFile(self):
        self._bestLogFile = None

    bestLogFile = property(
        getBestLogFile, setBestLogFile, delBestLogFile, "Property for bestLogFile"
    )
    # Methods and properties for the 'collectionPlan' attribute

    def getCollectionPlan(self):
        return self._collectionPlan

    def setCollectionPlan(self, collectionPlan):
        if collectionPlan is None:
            self._collectionPlan = []
        elif collectionPlan.__class__.__name__ == "list":
            self._collectionPlan = collectionPlan
        else:
            strMessage = (
                "ERROR! XSDataResultStrategy.setCollectionPlan argument is not list but %s"
                % collectionPlan.__class__.__name__
            )
            raise BaseException(strMessage)

    def delCollectionPlan(self):
        self._collectionPlan = None

    collectionPlan = property(
        getCollectionPlan,
        setCollectionPlan,
        delCollectionPlan,
        "Property for collectionPlan",
    )

    def addCollectionPlan(self, value):
        if value is None:
            strMessage = (
                "ERROR! XSDataResultStrategy.addCollectionPlan argument is None"
            )
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataCollectionPlan":
            self._collectionPlan.append(value)
        else:
            strMessage = (
                "ERROR! XSDataResultStrategy.addCollectionPlan argument is not XSDataCollectionPlan but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertCollectionPlan(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataResultStrategy.insertCollectionPlan argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataResultStrategy.insertCollectionPlan argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataCollectionPlan":
            self._collectionPlan[index] = value
        else:
            strMessage = (
                "ERROR! XSDataResultStrategy.addCollectionPlan argument is not XSDataCollectionPlan but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'raddoseLogFile' attribute
    def getRaddoseLogFile(self):
        return self._raddoseLogFile

    def setRaddoseLogFile(self, raddoseLogFile):
        if raddoseLogFile is None:
            self._raddoseLogFile = None
        elif raddoseLogFile.__class__.__name__ == "XSDataFile":
            self._raddoseLogFile = raddoseLogFile
        else:
            strMessage = (
                "ERROR! XSDataResultStrategy.setRaddoseLogFile argument is not XSDataFile but %s"
                % raddoseLogFile.__class__.__name__
            )
            raise BaseException(strMessage)

    def delRaddoseLogFile(self):
        self._raddoseLogFile = None

    raddoseLogFile = property(
        getRaddoseLogFile,
        setRaddoseLogFile,
        delRaddoseLogFile,
        "Property for raddoseLogFile",
    )
    # Methods and properties for the 'sample' attribute

    def getSample(self):
        return self._sample

    def setSample(self, sample):
        if sample is None:
            self._sample = None
        elif sample.__class__.__name__ == "XSDataSampleCrystalMM":
            self._sample = sample
        else:
            strMessage = (
                "ERROR! XSDataResultStrategy.setSample argument is not XSDataSampleCrystalMM but %s"
                % sample.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSample(self):
        self._sample = None

    sample = property(getSample, setSample, delSample, "Property for sample")

    def export(self, outfile, level, name_="XSDataResultStrategy"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataResultStrategy"):
        XSDataResult.exportChildren(self, outfile, level, name_)
        for bestGraphFile_ in self.getBestGraphFile():
            bestGraphFile_.export(outfile, level, name_="bestGraphFile")
        if self._bestLogFile is not None:
            self.bestLogFile.export(outfile, level, name_="bestLogFile")
        for collectionPlan_ in self.getCollectionPlan():
            collectionPlan_.export(outfile, level, name_="collectionPlan")
        if self._raddoseLogFile is not None:
            self.raddoseLogFile.export(outfile, level, name_="raddoseLogFile")
        if self._sample is not None:
            self.sample.export(outfile, level, name_="sample")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "bestGraphFile":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.bestGraphFile.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "bestLogFile":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setBestLogFile(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "collectionPlan":
            obj_ = XSDataCollectionPlan()
            obj_.build(child_)
            self.collectionPlan.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "raddoseLogFile":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setRaddoseLogFile(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "sample":
            obj_ = XSDataSampleCrystalMM()
            obj_.build(child_)
            self.setSample(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataResultStrategy")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataResultStrategy")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataResultStrategy is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataResultStrategy.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultStrategy()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataResultStrategy")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultStrategy()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataResultStrategy


class XSDataResultSubWedgeAssemble(XSDataResult):
    """These two definitions are used by the sub wedge assemble plugin."""

    def __init__(self, status=None, subWedge=None):
        XSDataResult.__init__(self, status)
        if subWedge is None:
            self._subWedge = []
        elif subWedge.__class__.__name__ == "list":
            self._subWedge = subWedge
        else:
            strMessage = (
                "ERROR! XSDataResultSubWedgeAssemble constructor argument 'subWedge' is not list but %s"
                % self._subWedge.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'subWedge' attribute
    def getSubWedge(self):
        return self._subWedge

    def setSubWedge(self, subWedge):
        if subWedge is None:
            self._subWedge = []
        elif subWedge.__class__.__name__ == "list":
            self._subWedge = subWedge
        else:
            strMessage = (
                "ERROR! XSDataResultSubWedgeAssemble.setSubWedge argument is not list but %s"
                % subWedge.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSubWedge(self):
        self._subWedge = None

    subWedge = property(getSubWedge, setSubWedge, delSubWedge, "Property for subWedge")

    def addSubWedge(self, value):
        if value is None:
            strMessage = (
                "ERROR! XSDataResultSubWedgeAssemble.addSubWedge argument is None"
            )
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataSubWedge":
            self._subWedge.append(value)
        else:
            strMessage = (
                "ERROR! XSDataResultSubWedgeAssemble.addSubWedge argument is not XSDataSubWedge but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertSubWedge(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataResultSubWedgeAssemble.insertSubWedge argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataResultSubWedgeAssemble.insertSubWedge argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataSubWedge":
            self._subWedge[index] = value
        else:
            strMessage = (
                "ERROR! XSDataResultSubWedgeAssemble.addSubWedge argument is not XSDataSubWedge but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def export(self, outfile, level, name_="XSDataResultSubWedgeAssemble"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataResultSubWedgeAssemble"):
        XSDataResult.exportChildren(self, outfile, level, name_)
        for subWedge_ in self.getSubWedge():
            subWedge_.export(outfile, level, name_="subWedge")
        if self.getSubWedge() == []:
            warnEmptyAttribute("subWedge", "XSDataSubWedge")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "subWedge":
            obj_ = XSDataSubWedge()
            obj_.build(child_)
            self.subWedge.append(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataResultSubWedgeAssemble")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataResultSubWedgeAssemble")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataResultSubWedgeAssemble is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataResultSubWedgeAssemble.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultSubWedgeAssemble()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataResultSubWedgeAssemble")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultSubWedgeAssemble()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataResultSubWedgeAssemble


class XSDataResultSubWedgeMerge(XSDataResult):
    """These two definitions are used by the sub wedge merge plugins."""

    def __init__(self, status=None, subWedge=None):
        XSDataResult.__init__(self, status)
        if subWedge is None:
            self._subWedge = []
        elif subWedge.__class__.__name__ == "list":
            self._subWedge = subWedge
        else:
            strMessage = (
                "ERROR! XSDataResultSubWedgeMerge constructor argument 'subWedge' is not list but %s"
                % self._subWedge.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'subWedge' attribute
    def getSubWedge(self):
        return self._subWedge

    def setSubWedge(self, subWedge):
        if subWedge is None:
            self._subWedge = []
        elif subWedge.__class__.__name__ == "list":
            self._subWedge = subWedge
        else:
            strMessage = (
                "ERROR! XSDataResultSubWedgeMerge.setSubWedge argument is not list but %s"
                % subWedge.__class__.__name__
            )
            raise BaseException(strMessage)

    def delSubWedge(self):
        self._subWedge = None

    subWedge = property(getSubWedge, setSubWedge, delSubWedge, "Property for subWedge")

    def addSubWedge(self, value):
        if value is None:
            strMessage = "ERROR! XSDataResultSubWedgeMerge.addSubWedge argument is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataSubWedge":
            self._subWedge.append(value)
        else:
            strMessage = (
                "ERROR! XSDataResultSubWedgeMerge.addSubWedge argument is not XSDataSubWedge but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def insertSubWedge(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataResultSubWedgeMerge.insertSubWedge argument 'index' is None"
            raise BaseException(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataResultSubWedgeMerge.insertSubWedge argument 'value' is None"
            raise BaseException(strMessage)
        elif value.__class__.__name__ == "XSDataSubWedge":
            self._subWedge[index] = value
        else:
            strMessage = (
                "ERROR! XSDataResultSubWedgeMerge.addSubWedge argument is not XSDataSubWedge but %s"
                % value.__class__.__name__
            )
            raise BaseException(strMessage)

    def export(self, outfile, level, name_="XSDataResultSubWedgeMerge"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataResultSubWedgeMerge"):
        XSDataResult.exportChildren(self, outfile, level, name_)
        for subWedge_ in self.getSubWedge():
            subWedge_.export(outfile, level, name_="subWedge")
        if self.getSubWedge() == []:
            warnEmptyAttribute("subWedge", "XSDataSubWedge")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "subWedge":
            obj_ = XSDataSubWedge()
            obj_.build(child_)
            self.subWedge.append(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataResultSubWedgeMerge")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataResultSubWedgeMerge")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataResultSubWedgeMerge is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataResultSubWedgeMerge.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultSubWedgeMerge()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataResultSubWedgeMerge")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultSubWedgeMerge()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataResultSubWedgeMerge


class XSDataSampleCrystal(XSDataSample):
    """A crystal sample. Inherites of all the XSDataSample attributes (inheritance relationship). In addition has the crystallographic properties (cell, mosaicity, space, group)"""

    def __init__(
        self,
        susceptibility=None,
        size=None,
        shape=None,
        radiationDamageModelGamma=None,
        radiationDamageModelBeta=None,
        absorbedDoseRate=None,
        crystal=None,
    ):
        XSDataSample.__init__(
            self,
            susceptibility,
            size,
            shape,
            radiationDamageModelGamma,
            radiationDamageModelBeta,
            absorbedDoseRate,
        )
        if crystal is None:
            self._crystal = None
        elif crystal.__class__.__name__ == "XSDataCrystal":
            self._crystal = crystal
        else:
            strMessage = (
                "ERROR! XSDataSampleCrystal constructor argument 'crystal' is not XSDataCrystal but %s"
                % self._crystal.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'crystal' attribute
    def getCrystal(self):
        return self._crystal

    def setCrystal(self, crystal):
        if crystal is None:
            self._crystal = None
        elif crystal.__class__.__name__ == "XSDataCrystal":
            self._crystal = crystal
        else:
            strMessage = (
                "ERROR! XSDataSampleCrystal.setCrystal argument is not XSDataCrystal but %s"
                % crystal.__class__.__name__
            )
            raise BaseException(strMessage)

    def delCrystal(self):
        self._crystal = None

    crystal = property(getCrystal, setCrystal, delCrystal, "Property for crystal")

    def export(self, outfile, level, name_="XSDataSampleCrystal"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataSampleCrystal"):
        XSDataSample.exportChildren(self, outfile, level, name_)
        if self._crystal is not None:
            self.crystal.export(outfile, level, name_="crystal")
        else:
            warnEmptyAttribute("crystal", "XSDataCrystal")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "crystal":
            obj_ = XSDataCrystal()
            obj_.build(child_)
            self.setCrystal(obj_)
        XSDataSample.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataSampleCrystal")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataSampleCrystal")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataSampleCrystal is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataSampleCrystal.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataSampleCrystal()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataSampleCrystal")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataSampleCrystal()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataSampleCrystal


class XSDataIntegrationInput(XSDataGeneratePredictionInput):
    """This generalisation is not very logical in terms of names, it should be fixed after the prototype (see bug #49)."""

    def __init__(
        self,
        configuration=None,
        selectedIndexingSolution=None,
        dataCollection=None,
        experimentalConditionRefined=None,
        crystalRefined=None,
    ):
        XSDataGeneratePredictionInput.__init__(
            self, configuration, selectedIndexingSolution, dataCollection
        )
        if crystalRefined is None:
            self._crystalRefined = None
        elif crystalRefined.__class__.__name__ == "XSDataCrystal":
            self._crystalRefined = crystalRefined
        else:
            strMessage = (
                "ERROR! XSDataIntegrationInput constructor argument 'crystalRefined' is not XSDataCrystal but %s"
                % self._crystalRefined.__class__.__name__
            )
            raise BaseException(strMessage)
        if experimentalConditionRefined is None:
            self._experimentalConditionRefined = None
        elif (
            experimentalConditionRefined.__class__.__name__
            == "XSDataExperimentalCondition"
        ):
            self._experimentalConditionRefined = experimentalConditionRefined
        else:
            strMessage = (
                "ERROR! XSDataIntegrationInput constructor argument 'experimentalConditionRefined' is not XSDataExperimentalCondition but %s"
                % self._experimentalConditionRefined.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'crystalRefined' attribute
    def getCrystalRefined(self):
        return self._crystalRefined

    def setCrystalRefined(self, crystalRefined):
        if crystalRefined is None:
            self._crystalRefined = None
        elif crystalRefined.__class__.__name__ == "XSDataCrystal":
            self._crystalRefined = crystalRefined
        else:
            strMessage = (
                "ERROR! XSDataIntegrationInput.setCrystalRefined argument is not XSDataCrystal but %s"
                % crystalRefined.__class__.__name__
            )
            raise BaseException(strMessage)

    def delCrystalRefined(self):
        self._crystalRefined = None

    crystalRefined = property(
        getCrystalRefined,
        setCrystalRefined,
        delCrystalRefined,
        "Property for crystalRefined",
    )
    # Methods and properties for the 'experimentalConditionRefined' attribute

    def getExperimentalConditionRefined(self):
        return self._experimentalConditionRefined

    def setExperimentalConditionRefined(self, experimentalConditionRefined):
        if experimentalConditionRefined is None:
            self._experimentalConditionRefined = None
        elif (
            experimentalConditionRefined.__class__.__name__
            == "XSDataExperimentalCondition"
        ):
            self._experimentalConditionRefined = experimentalConditionRefined
        else:
            strMessage = (
                "ERROR! XSDataIntegrationInput.setExperimentalConditionRefined argument is not XSDataExperimentalCondition but %s"
                % experimentalConditionRefined.__class__.__name__
            )
            raise BaseException(strMessage)

    def delExperimentalConditionRefined(self):
        self._experimentalConditionRefined = None

    experimentalConditionRefined = property(
        getExperimentalConditionRefined,
        setExperimentalConditionRefined,
        delExperimentalConditionRefined,
        "Property for experimentalConditionRefined",
    )

    def export(self, outfile, level, name_="XSDataIntegrationInput"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataIntegrationInput"):
        XSDataGeneratePredictionInput.exportChildren(self, outfile, level, name_)
        if self._crystalRefined is not None:
            self.crystalRefined.export(outfile, level, name_="crystalRefined")
        if self._experimentalConditionRefined is not None:
            self.experimentalConditionRefined.export(
                outfile, level, name_="experimentalConditionRefined"
            )

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "crystalRefined":
            obj_ = XSDataCrystal()
            obj_.build(child_)
            self.setCrystalRefined(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "experimentalConditionRefined"
        ):
            obj_ = XSDataExperimentalCondition()
            obj_.build(child_)
            self.setExperimentalConditionRefined(obj_)
        XSDataGeneratePredictionInput.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataIntegrationInput")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataIntegrationInput")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataIntegrationInput is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataIntegrationInput.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataIntegrationInput()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataIntegrationInput")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataIntegrationInput()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataIntegrationInput


class XSDataSampleCrystalMM(XSDataSampleCrystal):
    """A particular crystal sample that contains a macro molecule defined by its chemical composition."""

    def __init__(
        self,
        susceptibility=None,
        size=None,
        shape=None,
        radiationDamageModelGamma=None,
        radiationDamageModelBeta=None,
        absorbedDoseRate=None,
        crystal=None,
        chemicalComposition=None,
    ):
        XSDataSampleCrystal.__init__(
            self,
            susceptibility,
            size,
            shape,
            radiationDamageModelGamma,
            radiationDamageModelBeta,
            absorbedDoseRate,
            crystal,
        )
        if chemicalComposition is None:
            self._chemicalComposition = None
        elif chemicalComposition.__class__.__name__ == "XSDataChemicalCompositionMM":
            self._chemicalComposition = chemicalComposition
        else:
            strMessage = (
                "ERROR! XSDataSampleCrystalMM constructor argument 'chemicalComposition' is not XSDataChemicalCompositionMM but %s"
                % self._chemicalComposition.__class__.__name__
            )
            raise BaseException(strMessage)

    # Methods and properties for the 'chemicalComposition' attribute
    def getChemicalComposition(self):
        return self._chemicalComposition

    def setChemicalComposition(self, chemicalComposition):
        if chemicalComposition is None:
            self._chemicalComposition = None
        elif chemicalComposition.__class__.__name__ == "XSDataChemicalCompositionMM":
            self._chemicalComposition = chemicalComposition
        else:
            strMessage = (
                "ERROR! XSDataSampleCrystalMM.setChemicalComposition argument is not XSDataChemicalCompositionMM but %s"
                % chemicalComposition.__class__.__name__
            )
            raise BaseException(strMessage)

    def delChemicalComposition(self):
        self._chemicalComposition = None

    chemicalComposition = property(
        getChemicalComposition,
        setChemicalComposition,
        delChemicalComposition,
        "Property for chemicalComposition",
    )

    def export(self, outfile, level, name_="XSDataSampleCrystalMM"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataSampleCrystalMM"):
        XSDataSampleCrystal.exportChildren(self, outfile, level, name_)
        if self._chemicalComposition is not None:
            self.chemicalComposition.export(outfile, level, name_="chemicalComposition")
        else:
            warnEmptyAttribute("chemicalComposition", "XSDataChemicalCompositionMM")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "chemicalComposition":
            obj_ = XSDataChemicalCompositionMM()
            obj_.build(child_)
            self.setChemicalComposition(obj_)
        XSDataSampleCrystal.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataSampleCrystalMM")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataSampleCrystalMM")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataSampleCrystalMM is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataSampleCrystalMM.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataSampleCrystalMM()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataSampleCrystalMM")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataSampleCrystalMM()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataSampleCrystalMM


# End of data representation classes.
