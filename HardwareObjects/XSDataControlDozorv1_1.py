#!/usr/bin/env python

#
# Generated Fri Feb 20 04:42::27 2015 by EDGenerateDS.
#

from XSDataCommon import XSDataString
from XSDataCommon import XSDataResult
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataInput
from XSDataCommon import XSDataFile
from XSDataCommon import XSDataDouble
from XSDataCommon import XSDataBoolean
import os
import sys
from xml.dom import minidom
from xml.dom import Node


strEdnaHome = os.environ.get("EDNA_HOME", None)

dictLocation = {
    "XSDataCommon": "kernel/datamodel/.",
    "XSDataCommon": "kernel/datamodel/.",
    "XSDataCommon": "kernel/datamodel/.",
    "XSDataCommon": "kernel/datamodel/.",
    "XSDataCommon": "kernel/datamodel/.",
    "XSDataCommon": "kernel/datamodel/.",
    "XSDataCommon": "kernel/datamodel/.",
}

try:
    from XSDataCommon import XSDataBoolean
    from XSDataCommon import XSDataDouble
    from XSDataCommon import XSDataFile
    from XSDataCommon import XSDataInput
    from XSDataCommon import XSDataInteger
    from XSDataCommon import XSDataResult
    from XSDataCommon import XSDataString
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


class XSDataControlImageDozor(object):
    def __init__(
        self,
        score=None,
        powder_wilson_rfactor=None,
        powder_wilson_correlation=None,
        powder_wilson_resolution=None,
        powder_wilson_bfactor=None,
        powder_wilson_scale=None,
        spots_resolution=None,
        spots_int_aver=None,
        spots_num_of=None,
        number=None,
        image=None,
    ):
        if image is None:
            self._image = None
        elif image.__class__.__name__ == "XSDataFile":
            self._image = image
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor constructor argument 'image' is not XSDataFile but %s"
                % self._image.__class__.__name__
            )
            raise Exception(strMessage)
        if number is None:
            self._number = None
        elif number.__class__.__name__ == "XSDataInteger":
            self._number = number
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor constructor argument 'number' is not XSDataInteger but %s"
                % self._number.__class__.__name__
            )
            raise Exception(strMessage)
        if spots_num_of is None:
            self._spots_num_of = None
        elif spots_num_of.__class__.__name__ == "XSDataInteger":
            self._spots_num_of = spots_num_of
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor constructor argument 'spots_num_of' is not XSDataInteger but %s"
                % self._spots_num_of.__class__.__name__
            )
            raise Exception(strMessage)
        if spots_int_aver is None:
            self._spots_int_aver = None
        elif spots_int_aver.__class__.__name__ == "XSDataDouble":
            self._spots_int_aver = spots_int_aver
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor constructor argument 'spots_int_aver' is not XSDataDouble but %s"
                % self._spots_int_aver.__class__.__name__
            )
            raise Exception(strMessage)
        if spots_resolution is None:
            self._spots_resolution = None
        elif spots_resolution.__class__.__name__ == "XSDataDouble":
            self._spots_resolution = spots_resolution
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor constructor argument 'spots_resolution' is not XSDataDouble but %s"
                % self._spots_resolution.__class__.__name__
            )
            raise Exception(strMessage)
        if powder_wilson_scale is None:
            self._powder_wilson_scale = None
        elif powder_wilson_scale.__class__.__name__ == "XSDataDouble":
            self._powder_wilson_scale = powder_wilson_scale
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor constructor argument 'powder_wilson_scale' is not XSDataDouble but %s"
                % self._powder_wilson_scale.__class__.__name__
            )
            raise Exception(strMessage)
        if powder_wilson_bfactor is None:
            self._powder_wilson_bfactor = None
        elif powder_wilson_bfactor.__class__.__name__ == "XSDataDouble":
            self._powder_wilson_bfactor = powder_wilson_bfactor
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor constructor argument 'powder_wilson_bfactor' is not XSDataDouble but %s"
                % self._powder_wilson_bfactor.__class__.__name__
            )
            raise Exception(strMessage)
        if powder_wilson_resolution is None:
            self._powder_wilson_resolution = None
        elif powder_wilson_resolution.__class__.__name__ == "XSDataDouble":
            self._powder_wilson_resolution = powder_wilson_resolution
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor constructor argument 'powder_wilson_resolution' is not XSDataDouble but %s"
                % self._powder_wilson_resolution.__class__.__name__
            )
            raise Exception(strMessage)
        if powder_wilson_correlation is None:
            self._powder_wilson_correlation = None
        elif powder_wilson_correlation.__class__.__name__ == "XSDataDouble":
            self._powder_wilson_correlation = powder_wilson_correlation
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor constructor argument 'powder_wilson_correlation' is not XSDataDouble but %s"
                % self._powder_wilson_correlation.__class__.__name__
            )
            raise Exception(strMessage)
        if powder_wilson_rfactor is None:
            self._powder_wilson_rfactor = None
        elif powder_wilson_rfactor.__class__.__name__ == "XSDataDouble":
            self._powder_wilson_rfactor = powder_wilson_rfactor
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor constructor argument 'powder_wilson_rfactor' is not XSDataDouble but %s"
                % self._powder_wilson_rfactor.__class__.__name__
            )
            raise Exception(strMessage)
        if score is None:
            self._score = None
        elif score.__class__.__name__ == "XSDataDouble":
            self._score = score
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor constructor argument 'score' is not XSDataDouble but %s"
                % self._score.__class__.__name__
            )
            raise Exception(strMessage)

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
                "ERROR! XSDataControlImageDozor.setImage argument is not XSDataFile but %s"
                % image.__class__.__name__
            )
            raise Exception(strMessage)

    def delImage(self):
        self._image = None

    image = property(getImage, setImage, delImage, "Property for image")
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
                "ERROR! XSDataControlImageDozor.setNumber argument is not XSDataInteger but %s"
                % number.__class__.__name__
            )
            raise Exception(strMessage)

    def delNumber(self):
        self._number = None

    number = property(getNumber, setNumber, delNumber, "Property for number")
    # Methods and properties for the 'spots_num_of' attribute

    def getSpots_num_of(self):
        return self._spots_num_of

    def setSpots_num_of(self, spots_num_of):
        if spots_num_of is None:
            self._spots_num_of = None
        elif spots_num_of.__class__.__name__ == "XSDataInteger":
            self._spots_num_of = spots_num_of
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor.setSpots_num_of argument is not XSDataInteger but %s"
                % spots_num_of.__class__.__name__
            )
            raise Exception(strMessage)

    def delSpots_num_of(self):
        self._spots_num_of = None

    spots_num_of = property(
        getSpots_num_of, setSpots_num_of, delSpots_num_of, "Property for spots_num_of"
    )
    # Methods and properties for the 'spots_int_aver' attribute

    def getSpots_int_aver(self):
        return self._spots_int_aver

    def setSpots_int_aver(self, spots_int_aver):
        if spots_int_aver is None:
            self._spots_int_aver = None
        elif spots_int_aver.__class__.__name__ == "XSDataDouble":
            self._spots_int_aver = spots_int_aver
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor.setSpots_int_aver argument is not XSDataDouble but %s"
                % spots_int_aver.__class__.__name__
            )
            raise Exception(strMessage)

    def delSpots_int_aver(self):
        self._spots_int_aver = None

    spots_int_aver = property(
        getSpots_int_aver,
        setSpots_int_aver,
        delSpots_int_aver,
        "Property for spots_int_aver",
    )
    # Methods and properties for the 'spots_resolution' attribute

    def getSpots_resolution(self):
        return self._spots_resolution

    def setSpots_resolution(self, spots_resolution):
        if spots_resolution is None:
            self._spots_resolution = None
        elif spots_resolution.__class__.__name__ == "XSDataDouble":
            self._spots_resolution = spots_resolution
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor.setSpots_resolution argument is not XSDataDouble but %s"
                % spots_resolution.__class__.__name__
            )
            raise Exception(strMessage)

    def delSpots_resolution(self):
        self._spots_resolution = None

    spots_resolution = property(
        getSpots_resolution,
        setSpots_resolution,
        delSpots_resolution,
        "Property for spots_resolution",
    )
    # Methods and properties for the 'powder_wilson_scale' attribute

    def getPowder_wilson_scale(self):
        return self._powder_wilson_scale

    def setPowder_wilson_scale(self, powder_wilson_scale):
        if powder_wilson_scale is None:
            self._powder_wilson_scale = None
        elif powder_wilson_scale.__class__.__name__ == "XSDataDouble":
            self._powder_wilson_scale = powder_wilson_scale
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor.setPowder_wilson_scale argument is not XSDataDouble but %s"
                % powder_wilson_scale.__class__.__name__
            )
            raise Exception(strMessage)

    def delPowder_wilson_scale(self):
        self._powder_wilson_scale = None

    powder_wilson_scale = property(
        getPowder_wilson_scale,
        setPowder_wilson_scale,
        delPowder_wilson_scale,
        "Property for powder_wilson_scale",
    )
    # Methods and properties for the 'powder_wilson_bfactor' attribute

    def getPowder_wilson_bfactor(self):
        return self._powder_wilson_bfactor

    def setPowder_wilson_bfactor(self, powder_wilson_bfactor):
        if powder_wilson_bfactor is None:
            self._powder_wilson_bfactor = None
        elif powder_wilson_bfactor.__class__.__name__ == "XSDataDouble":
            self._powder_wilson_bfactor = powder_wilson_bfactor
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor.setPowder_wilson_bfactor argument is not XSDataDouble but %s"
                % powder_wilson_bfactor.__class__.__name__
            )
            raise Exception(strMessage)

    def delPowder_wilson_bfactor(self):
        self._powder_wilson_bfactor = None

    powder_wilson_bfactor = property(
        getPowder_wilson_bfactor,
        setPowder_wilson_bfactor,
        delPowder_wilson_bfactor,
        "Property for powder_wilson_bfactor",
    )
    # Methods and properties for the 'powder_wilson_resolution' attribute

    def getPowder_wilson_resolution(self):
        return self._powder_wilson_resolution

    def setPowder_wilson_resolution(self, powder_wilson_resolution):
        if powder_wilson_resolution is None:
            self._powder_wilson_resolution = None
        elif powder_wilson_resolution.__class__.__name__ == "XSDataDouble":
            self._powder_wilson_resolution = powder_wilson_resolution
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor.setPowder_wilson_resolution argument is not XSDataDouble but %s"
                % powder_wilson_resolution.__class__.__name__
            )
            raise Exception(strMessage)

    def delPowder_wilson_resolution(self):
        self._powder_wilson_resolution = None

    powder_wilson_resolution = property(
        getPowder_wilson_resolution,
        setPowder_wilson_resolution,
        delPowder_wilson_resolution,
        "Property for powder_wilson_resolution",
    )
    # Methods and properties for the 'powder_wilson_correlation' attribute

    def getPowder_wilson_correlation(self):
        return self._powder_wilson_correlation

    def setPowder_wilson_correlation(self, powder_wilson_correlation):
        if powder_wilson_correlation is None:
            self._powder_wilson_correlation = None
        elif powder_wilson_correlation.__class__.__name__ == "XSDataDouble":
            self._powder_wilson_correlation = powder_wilson_correlation
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor.setPowder_wilson_correlation argument is not XSDataDouble but %s"
                % powder_wilson_correlation.__class__.__name__
            )
            raise Exception(strMessage)

    def delPowder_wilson_correlation(self):
        self._powder_wilson_correlation = None

    powder_wilson_correlation = property(
        getPowder_wilson_correlation,
        setPowder_wilson_correlation,
        delPowder_wilson_correlation,
        "Property for powder_wilson_correlation",
    )
    # Methods and properties for the 'powder_wilson_rfactor' attribute

    def getPowder_wilson_rfactor(self):
        return self._powder_wilson_rfactor

    def setPowder_wilson_rfactor(self, powder_wilson_rfactor):
        if powder_wilson_rfactor is None:
            self._powder_wilson_rfactor = None
        elif powder_wilson_rfactor.__class__.__name__ == "XSDataDouble":
            self._powder_wilson_rfactor = powder_wilson_rfactor
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor.setPowder_wilson_rfactor argument is not XSDataDouble but %s"
                % powder_wilson_rfactor.__class__.__name__
            )
            raise Exception(strMessage)

    def delPowder_wilson_rfactor(self):
        self._powder_wilson_rfactor = None

    powder_wilson_rfactor = property(
        getPowder_wilson_rfactor,
        setPowder_wilson_rfactor,
        delPowder_wilson_rfactor,
        "Property for powder_wilson_rfactor",
    )
    # Methods and properties for the 'score' attribute

    def getScore(self):
        return self._score

    def setScore(self, score):
        if score is None:
            self._score = None
        elif score.__class__.__name__ == "XSDataDouble":
            self._score = score
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor.setScore argument is not XSDataDouble but %s"
                % score.__class__.__name__
            )
            raise Exception(strMessage)

    def delScore(self):
        self._score = None

    score = property(getScore, setScore, delScore, "Property for score")

    def export(self, outfile, level, name_="XSDataControlImageDozor"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataControlImageDozor"):
        if self._image is not None:
            self.image.export(outfile, level, name_="image")
        else:
            warnEmptyAttribute("image", "XSDataFile")
        if self._number is not None:
            self.number.export(outfile, level, name_="number")
        if self._spots_num_of is not None:
            self.spots_num_of.export(outfile, level, name_="spots_num_of")
        else:
            warnEmptyAttribute("spots_num_of", "XSDataInteger")
        if self._spots_int_aver is not None:
            self.spots_int_aver.export(outfile, level, name_="spots_int_aver")
        else:
            warnEmptyAttribute("spots_int_aver", "XSDataDouble")
        if self._spots_resolution is not None:
            self.spots_resolution.export(outfile, level, name_="spots_resolution")
        if self._powder_wilson_scale is not None:
            self.powder_wilson_scale.export(outfile, level, name_="powder_wilson_scale")
        if self._powder_wilson_bfactor is not None:
            self.powder_wilson_bfactor.export(
                outfile, level, name_="powder_wilson_bfactor"
            )
        if self._powder_wilson_resolution is not None:
            self.powder_wilson_resolution.export(
                outfile, level, name_="powder_wilson_resolution"
            )
        if self._powder_wilson_correlation is not None:
            self.powder_wilson_correlation.export(
                outfile, level, name_="powder_wilson_correlation"
            )
        if self._powder_wilson_rfactor is not None:
            self.powder_wilson_rfactor.export(
                outfile, level, name_="powder_wilson_rfactor"
            )
        if self._score is not None:
            self.score.export(outfile, level, name_="score")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "image":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setImage(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "number":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumber(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "spots_num_of":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setSpots_num_of(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "spots_int_aver":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setSpots_int_aver(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "spots_resolution":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setSpots_resolution(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "powder_wilson_scale"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setPowder_wilson_scale(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "powder_wilson_bfactor"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setPowder_wilson_bfactor(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "powder_wilson_resolution"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setPowder_wilson_resolution(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "powder_wilson_correlation"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setPowder_wilson_correlation(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "powder_wilson_rfactor"
        ):
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setPowder_wilson_rfactor(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "score":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setScore(obj_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataControlImageDozor")
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataControlImageDozor")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataControlImageDozor is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataControlImageDozor.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataControlImageDozor()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataControlImageDozor")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataControlImageDozor()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataControlImageDozor


class XSDataInputControlDozor(XSDataInput):
    def __init__(
        self,
        configuration=None,
        beamstopDistance=None,
        beamstopSize=None,
        beamstopDirection=None,
        pixelMax=None,
        pixelMin=None,
        reversing_rotation=None,
        line_number_of=None,
        last_run_number=None,
        first_run_number=None,
        last_image_number=None,
        first_image_number=None,
        template=None,
    ):
        XSDataInput.__init__(self, configuration)
        if template is None:
            self._template = None
        elif template.__class__.__name__ == "XSDataString":
            self._template = template
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor constructor argument 'template' is not XSDataString but %s"
                % self._template.__class__.__name__
            )
            raise Exception(strMessage)
        if first_image_number is None:
            self._first_image_number = None
        elif first_image_number.__class__.__name__ == "XSDataInteger":
            self._first_image_number = first_image_number
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor constructor argument 'first_image_number' is not XSDataInteger but %s"
                % self._first_image_number.__class__.__name__
            )
            raise Exception(strMessage)
        if last_image_number is None:
            self._last_image_number = None
        elif last_image_number.__class__.__name__ == "XSDataInteger":
            self._last_image_number = last_image_number
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor constructor argument 'last_image_number' is not XSDataInteger but %s"
                % self._last_image_number.__class__.__name__
            )
            raise Exception(strMessage)
        if first_run_number is None:
            self._first_run_number = None
        elif first_run_number.__class__.__name__ == "XSDataInteger":
            self._first_run_number = first_run_number
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor constructor argument 'first_run_number' is not XSDataInteger but %s"
                % self._first_run_number.__class__.__name__
            )
            raise Exception(strMessage)
        if last_run_number is None:
            self._last_run_number = None
        elif last_run_number.__class__.__name__ == "XSDataInteger":
            self._last_run_number = last_run_number
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor constructor argument 'last_run_number' is not XSDataInteger but %s"
                % self._last_run_number.__class__.__name__
            )
            raise Exception(strMessage)
        if line_number_of is None:
            self._line_number_of = None
        elif line_number_of.__class__.__name__ == "XSDataInteger":
            self._line_number_of = line_number_of
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor constructor argument 'line_number_of' is not XSDataInteger but %s"
                % self._line_number_of.__class__.__name__
            )
            raise Exception(strMessage)
        if reversing_rotation is None:
            self._reversing_rotation = None
        elif reversing_rotation.__class__.__name__ == "XSDataBoolean":
            self._reversing_rotation = reversing_rotation
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor constructor argument 'reversing_rotation' is not XSDataBoolean but %s"
                % self._reversing_rotation.__class__.__name__
            )
            raise Exception(strMessage)
        if pixelMin is None:
            self._pixelMin = None
        elif pixelMin.__class__.__name__ == "XSDataInteger":
            self._pixelMin = pixelMin
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor constructor argument 'pixelMin' is not XSDataInteger but %s"
                % self._pixelMin.__class__.__name__
            )
            raise Exception(strMessage)
        if pixelMax is None:
            self._pixelMax = None
        elif pixelMax.__class__.__name__ == "XSDataInteger":
            self._pixelMax = pixelMax
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor constructor argument 'pixelMax' is not XSDataInteger but %s"
                % self._pixelMax.__class__.__name__
            )
            raise Exception(strMessage)
        if beamstopDirection is None:
            self._beamstopDirection = None
        elif beamstopDirection.__class__.__name__ == "XSDataString":
            self._beamstopDirection = beamstopDirection
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor constructor argument 'beamstopDirection' is not XSDataString but %s"
                % self._beamstopDirection.__class__.__name__
            )
            raise Exception(strMessage)
        if beamstopSize is None:
            self._beamstopSize = None
        elif beamstopSize.__class__.__name__ == "XSDataDouble":
            self._beamstopSize = beamstopSize
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor constructor argument 'beamstopSize' is not XSDataDouble but %s"
                % self._beamstopSize.__class__.__name__
            )
            raise Exception(strMessage)
        if beamstopDistance is None:
            self._beamstopDistance = None
        elif beamstopDistance.__class__.__name__ == "XSDataDouble":
            self._beamstopDistance = beamstopDistance
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor constructor argument 'beamstopDistance' is not XSDataDouble but %s"
                % self._beamstopDistance.__class__.__name__
            )
            raise Exception(strMessage)

    # Methods and properties for the 'template' attribute
    def getTemplate(self):
        return self._template

    def setTemplate(self, template):
        if template is None:
            self._template = None
        elif template.__class__.__name__ == "XSDataString":
            self._template = template
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor.setTemplate argument is not XSDataString but %s"
                % template.__class__.__name__
            )
            raise Exception(strMessage)

    def delTemplate(self):
        self._template = None

    template = property(getTemplate, setTemplate, delTemplate, "Property for template")
    # Methods and properties for the 'first_image_number' attribute

    def getFirst_image_number(self):
        return self._first_image_number

    def setFirst_image_number(self, first_image_number):
        if first_image_number is None:
            self._first_image_number = None
        elif first_image_number.__class__.__name__ == "XSDataInteger":
            self._first_image_number = first_image_number
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor.setFirst_image_number argument is not XSDataInteger but %s"
                % first_image_number.__class__.__name__
            )
            raise Exception(strMessage)

    def delFirst_image_number(self):
        self._first_image_number = None

    first_image_number = property(
        getFirst_image_number,
        setFirst_image_number,
        delFirst_image_number,
        "Property for first_image_number",
    )
    # Methods and properties for the 'last_image_number' attribute

    def getLast_image_number(self):
        return self._last_image_number

    def setLast_image_number(self, last_image_number):
        if last_image_number is None:
            self._last_image_number = None
        elif last_image_number.__class__.__name__ == "XSDataInteger":
            self._last_image_number = last_image_number
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor.setLast_image_number argument is not XSDataInteger but %s"
                % last_image_number.__class__.__name__
            )
            raise Exception(strMessage)

    def delLast_image_number(self):
        self._last_image_number = None

    last_image_number = property(
        getLast_image_number,
        setLast_image_number,
        delLast_image_number,
        "Property for last_image_number",
    )
    # Methods and properties for the 'first_run_number' attribute

    def getFirst_run_number(self):
        return self._first_run_number

    def setFirst_run_number(self, first_run_number):
        if first_run_number is None:
            self._first_run_number = None
        elif first_run_number.__class__.__name__ == "XSDataInteger":
            self._first_run_number = first_run_number
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor.setFirst_run_number argument is not XSDataInteger but %s"
                % first_run_number.__class__.__name__
            )
            raise Exception(strMessage)

    def delFirst_run_number(self):
        self._first_run_number = None

    first_run_number = property(
        getFirst_run_number,
        setFirst_run_number,
        delFirst_run_number,
        "Property for first_run_number",
    )
    # Methods and properties for the 'last_run_number' attribute

    def getLast_run_number(self):
        return self._last_run_number

    def setLast_run_number(self, last_run_number):
        if last_run_number is None:
            self._last_run_number = None
        elif last_run_number.__class__.__name__ == "XSDataInteger":
            self._last_run_number = last_run_number
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor.setLast_run_number argument is not XSDataInteger but %s"
                % last_run_number.__class__.__name__
            )
            raise Exception(strMessage)

    def delLast_run_number(self):
        self._last_run_number = None

    last_run_number = property(
        getLast_run_number,
        setLast_run_number,
        delLast_run_number,
        "Property for last_run_number",
    )
    # Methods and properties for the 'line_number_of' attribute

    def getLine_number_of(self):
        return self._line_number_of

    def setLine_number_of(self, line_number_of):
        if line_number_of is None:
            self._line_number_of = None
        elif line_number_of.__class__.__name__ == "XSDataInteger":
            self._line_number_of = line_number_of
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor.setLine_number_of argument is not XSDataInteger but %s"
                % line_number_of.__class__.__name__
            )
            raise Exception(strMessage)

    def delLine_number_of(self):
        self._line_number_of = None

    line_number_of = property(
        getLine_number_of,
        setLine_number_of,
        delLine_number_of,
        "Property for line_number_of",
    )
    # Methods and properties for the 'reversing_rotation' attribute

    def getReversing_rotation(self):
        return self._reversing_rotation

    def setReversing_rotation(self, reversing_rotation):
        if reversing_rotation is None:
            self._reversing_rotation = None
        elif reversing_rotation.__class__.__name__ == "XSDataBoolean":
            self._reversing_rotation = reversing_rotation
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor.setReversing_rotation argument is not XSDataBoolean but %s"
                % reversing_rotation.__class__.__name__
            )
            raise Exception(strMessage)

    def delReversing_rotation(self):
        self._reversing_rotation = None

    reversing_rotation = property(
        getReversing_rotation,
        setReversing_rotation,
        delReversing_rotation,
        "Property for reversing_rotation",
    )
    # Methods and properties for the 'pixelMin' attribute

    def getPixelMin(self):
        return self._pixelMin

    def setPixelMin(self, pixelMin):
        if pixelMin is None:
            self._pixelMin = None
        elif pixelMin.__class__.__name__ == "XSDataInteger":
            self._pixelMin = pixelMin
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor.setPixelMin argument is not XSDataInteger but %s"
                % pixelMin.__class__.__name__
            )
            raise Exception(strMessage)

    def delPixelMin(self):
        self._pixelMin = None

    pixelMin = property(getPixelMin, setPixelMin, delPixelMin, "Property for pixelMin")
    # Methods and properties for the 'pixelMax' attribute

    def getPixelMax(self):
        return self._pixelMax

    def setPixelMax(self, pixelMax):
        if pixelMax is None:
            self._pixelMax = None
        elif pixelMax.__class__.__name__ == "XSDataInteger":
            self._pixelMax = pixelMax
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor.setPixelMax argument is not XSDataInteger but %s"
                % pixelMax.__class__.__name__
            )
            raise Exception(strMessage)

    def delPixelMax(self):
        self._pixelMax = None

    pixelMax = property(getPixelMax, setPixelMax, delPixelMax, "Property for pixelMax")
    # Methods and properties for the 'beamstopDirection' attribute

    def getBeamstopDirection(self):
        return self._beamstopDirection

    def setBeamstopDirection(self, beamstopDirection):
        if beamstopDirection is None:
            self._beamstopDirection = None
        elif beamstopDirection.__class__.__name__ == "XSDataString":
            self._beamstopDirection = beamstopDirection
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor.setBeamstopDirection argument is not XSDataString but %s"
                % beamstopDirection.__class__.__name__
            )
            raise Exception(strMessage)

    def delBeamstopDirection(self):
        self._beamstopDirection = None

    beamstopDirection = property(
        getBeamstopDirection,
        setBeamstopDirection,
        delBeamstopDirection,
        "Property for beamstopDirection",
    )
    # Methods and properties for the 'beamstopSize' attribute

    def getBeamstopSize(self):
        return self._beamstopSize

    def setBeamstopSize(self, beamstopSize):
        if beamstopSize is None:
            self._beamstopSize = None
        elif beamstopSize.__class__.__name__ == "XSDataDouble":
            self._beamstopSize = beamstopSize
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor.setBeamstopSize argument is not XSDataDouble but %s"
                % beamstopSize.__class__.__name__
            )
            raise Exception(strMessage)

    def delBeamstopSize(self):
        self._beamstopSize = None

    beamstopSize = property(
        getBeamstopSize, setBeamstopSize, delBeamstopSize, "Property for beamstopSize"
    )
    # Methods and properties for the 'beamstopDistance' attribute

    def getBeamstopDistance(self):
        return self._beamstopDistance

    def setBeamstopDistance(self, beamstopDistance):
        if beamstopDistance is None:
            self._beamstopDistance = None
        elif beamstopDistance.__class__.__name__ == "XSDataDouble":
            self._beamstopDistance = beamstopDistance
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor.setBeamstopDistance argument is not XSDataDouble but %s"
                % beamstopDistance.__class__.__name__
            )
            raise Exception(strMessage)

    def delBeamstopDistance(self):
        self._beamstopDistance = None

    beamstopDistance = property(
        getBeamstopDistance,
        setBeamstopDistance,
        delBeamstopDistance,
        "Property for beamstopDistance",
    )

    def export(self, outfile, level, name_="XSDataInputControlDozor"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataInputControlDozor"):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._template is not None:
            self.template.export(outfile, level, name_="template")
        else:
            warnEmptyAttribute("template", "XSDataString")
        if self._first_image_number is not None:
            self.first_image_number.export(outfile, level, name_="first_image_number")
        else:
            warnEmptyAttribute("first_image_number", "XSDataInteger")
        if self._last_image_number is not None:
            self.last_image_number.export(outfile, level, name_="last_image_number")
        else:
            warnEmptyAttribute("last_image_number", "XSDataInteger")
        if self._first_run_number is not None:
            self.first_run_number.export(outfile, level, name_="first_run_number")
        else:
            warnEmptyAttribute("first_run_number", "XSDataInteger")
        if self._last_run_number is not None:
            self.last_run_number.export(outfile, level, name_="last_run_number")
        else:
            warnEmptyAttribute("last_run_number", "XSDataInteger")
        if self._line_number_of is not None:
            self.line_number_of.export(outfile, level, name_="line_number_of")
        else:
            warnEmptyAttribute("line_number_of", "XSDataInteger")
        if self._reversing_rotation is not None:
            self.reversing_rotation.export(outfile, level, name_="reversing_rotation")
        else:
            warnEmptyAttribute("reversing_rotation", "XSDataBoolean")
        if self._pixelMin is not None:
            self.pixelMin.export(outfile, level, name_="pixelMin")
        if self._pixelMax is not None:
            self.pixelMax.export(outfile, level, name_="pixelMax")
        if self._beamstopDirection is not None:
            self.beamstopDirection.export(outfile, level, name_="beamstopDirection")
        if self._beamstopSize is not None:
            self.beamstopSize.export(outfile, level, name_="beamstopSize")
        if self._beamstopDistance is not None:
            self.beamstopDistance.export(outfile, level, name_="beamstopDistance")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "template":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setTemplate(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "first_image_number":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setFirst_image_number(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "last_image_number":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setLast_image_number(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "first_run_number":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setFirst_run_number(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "last_run_number":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setLast_run_number(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "line_number_of":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setLine_number_of(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "reversing_rotation":
            obj_ = XSDataBoolean()
            obj_.build(child_)
            self.setReversing_rotation(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "pixelMin":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setPixelMin(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "pixelMax":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setPixelMax(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "beamstopDirection":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setBeamstopDirection(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "beamstopSize":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setBeamstopSize(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "beamstopDistance":
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setBeamstopDistance(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataInputControlDozor")
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataInputControlDozor")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataInputControlDozor is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataInputControlDozor.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputControlDozor()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataInputControlDozor")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputControlDozor()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataInputControlDozor


class XSDataResultControlDozor(XSDataResult):
    def __init__(self, status=None, imageDozor=None):
        XSDataResult.__init__(self, status)
        if imageDozor is None:
            self._imageDozor = []
        elif imageDozor.__class__.__name__ == "list":
            self._imageDozor = imageDozor
        else:
            strMessage = (
                "ERROR! XSDataResultControlDozor constructor argument 'imageDozor' is not list but %s"
                % self._imageDozor.__class__.__name__
            )
            raise Exception(strMessage)

    # Methods and properties for the 'imageDozor' attribute
    def getImageDozor(self):
        return self._imageDozor

    def setImageDozor(self, imageDozor):
        if imageDozor is None:
            self._imageDozor = []
        elif imageDozor.__class__.__name__ == "list":
            self._imageDozor = imageDozor
        else:
            strMessage = (
                "ERROR! XSDataResultControlDozor.setImageDozor argument is not list but %s"
                % imageDozor.__class__.__name__
            )
            raise Exception(strMessage)

    def delImageDozor(self):
        self._imageDozor = None

    imageDozor = property(
        getImageDozor, setImageDozor, delImageDozor, "Property for imageDozor"
    )

    def addImageDozor(self, value):
        if value is None:
            strMessage = (
                "ERROR! XSDataResultControlDozor.addImageDozor argument is None"
            )
            raise Exception(strMessage)
        elif value.__class__.__name__ == "XSDataControlImageDozor":
            self._imageDozor.append(value)
        else:
            strMessage = (
                "ERROR! XSDataResultControlDozor.addImageDozor argument is not XSDataControlImageDozor but %s"
                % value.__class__.__name__
            )
            raise Exception(strMessage)

    def insertImageDozor(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataResultControlDozor.insertImageDozor argument 'index' is None"
            raise Exception(strMessage)
        if value is None:
            strMessage = "ERROR! XSDataResultControlDozor.insertImageDozor argument 'value' is None"
            raise Exception(strMessage)
        elif value.__class__.__name__ == "XSDataControlImageDozor":
            self._imageDozor[index] = value
        else:
            strMessage = (
                "ERROR! XSDataResultControlDozor.addImageDozor argument is not XSDataControlImageDozor but %s"
                % value.__class__.__name__
            )
            raise Exception(strMessage)

    def export(self, outfile, level, name_="XSDataResultControlDozor"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataResultControlDozor"):
        XSDataResult.exportChildren(self, outfile, level, name_)
        for imageDozor_ in self.getImageDozor():
            imageDozor_.export(outfile, level, name_="imageDozor")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "imageDozor":
            obj_ = XSDataControlImageDozor()
            obj_.build(child_)
            self.imageDozor.append(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object
    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataResultControlDozor")
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk
    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataResultControlDozor")
        outfile.close()

    # Deprecated method, replaced by exportToFile
    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataResultControlDozor is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance
    def copy(self):
        return XSDataResultControlDozor.parseString(self.marshal())

    # Static method for parsing a string
    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultControlDozor()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataResultControlDozor")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultControlDozor()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataResultControlDozor


# End of data representation classes.
