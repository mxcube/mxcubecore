#!/usr/bin/env python

#
# Generated Mon May 14 10:32::39 2012 by EDGenerateDS.
#

import os
import sys
from xml.dom import (
    Node,
    minidom,
)

from XSDataCommon import (
    XSData,
    XSDataDictionary,
    XSDataFile,
    XSDataInput,
    XSDataInteger,
    XSDataResult,
    XSDataString,
)
from XSDataMXv1 import (
    XSDataCollectionPlan,
    XSDataDiffractionPlan,
    XSDataExperimentalCondition,
    XSDataInputCharacterisation,
    XSDataResultCharacterisation,
    XSDataSampleCrystalMM,
)

strEdnaHome = os.environ.get("EDNA_HOME", None)

dictLocation = {
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataCommon": "kernel/datamodel",
    "XSDataMXv1": "mxv1/datamodel",
    "XSDataMXv1": "mxv1/datamodel",
    "XSDataMXv1": "mxv1/datamodel",
    "XSDataMXv1": "mxv1/datamodel",
    "XSDataMXv1": "mxv1/datamodel",
    "XSDataMXv1": "mxv1/datamodel",
}

try:
    from XSDataCommon import (
        XSData,
        XSDataDictionary,
        XSDataFile,
        XSDataInput,
        XSDataInteger,
        XSDataResult,
        XSDataString,
    )
    from XSDataMXv1 import (
        XSDataCollectionPlan,
        XSDataDiffractionPlan,
        XSDataExperimentalCondition,
        XSDataInputCharacterisation,
        XSDataResultCharacterisation,
        XSDataSampleCrystalMM,
    )
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
    if _strTypeName not in ["float", "double", "string", "boolean", "integer"]:
        print(
            (
                "Warning! Non-optional attribute %s of type %s is None!"
                % (_strName, _strTypeName)
            )
        )


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


class XSDataMXCuBEDataSet(object):
    def __init__(self, imageFile=None):
        if imageFile is None:
            self._imageFile = []
        else:
            checkType(
                "XSDataMXCuBEDataSet",
                "Constructor of XSDataMXCuBEDataSet",
                imageFile,
                "list",
            )
            self._imageFile = imageFile

    def getImageFile(self):
        return self._imageFile

    def setImageFile(self, imageFile):
        checkType("XSDataMXCuBEDataSet", "setImageFile", imageFile, "list")
        self._imageFile = imageFile

    def delImageFile(self):
        self._imageFile = None

    # Properties
    imageFile = property(
        getImageFile, setImageFile, delImageFile, "Property for imageFile"
    )

    def addImageFile(self, value):
        checkType("XSDataMXCuBEDataSet", "setImageFile", value, "XSDataFile")
        self._imageFile.append(value)

    def insertImageFile(self, index, value):
        checkType("XSDataMXCuBEDataSet", "setImageFile", value, "XSDataFile")
        self._imageFile[index] = value

    def export(self, outfile, level, name_="XSDataMXCuBEDataSet"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataMXCuBEDataSet"):
        for imageFile_ in self.getImageFile():
            imageFile_.export(outfile, level, name_="imageFile")
        if self.getImageFile() == []:
            warnEmptyAttribute("imageFile", "XSDataFile")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "imageFile":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.imageFile.append(obj_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataMXCuBEDataSet")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataMXCuBEDataSet")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataMXCuBEDataSet is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataMXCuBEDataSet.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataMXCuBEDataSet()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataMXCuBEDataSet")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataMXCuBEDataSet()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataMXCuBEDataSet


class XSDataMXCuBEParameters(XSData):
    def __init__(
        self,
        transmission=None,
        output_file=None,
        current_osc_start=None,
        current_energy=None,
        directory=None,
        number_passes=None,
        anomalous=None,
        phiStart=None,
        current_wavelength=None,
        run_number=None,
        residues=None,
        current_detdistance=None,
        number_images=None,
        inverse_beam=None,
        processing=None,
        kappaStart=None,
        template=None,
        first_image=None,
        osc_range=None,
        comments=None,
        mad_energies=None,
        detector_mode=None,
        sum_images=None,
        process_directory=None,
        osc_start=None,
        overlap=None,
        prefix=None,
        mad_4_energy=None,
        mad_3_energy=None,
        mad_2_energy=None,
        mad_1_energy=None,
        beam_size_y=None,
        beam_size_x=None,
        y_beam=None,
        x_beam=None,
        resolution_at_corner=None,
        resolution=None,
        exposure_time=None,
        blSampleId=None,
        sessionId=None,
    ):
        XSData.__init__(self)

        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            sessionId,
            "integer",
        )
        self._sessionId = sessionId
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            blSampleId,
            "integer",
        )
        self._blSampleId = blSampleId
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            exposure_time,
            "float",
        )
        self._exposure_time = exposure_time
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            resolution,
            "float",
        )
        self._resolution = resolution
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            resolution_at_corner,
            "float",
        )
        self._resolution_at_corner = resolution_at_corner
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            x_beam,
            "float",
        )
        self._x_beam = x_beam
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            y_beam,
            "float",
        )
        self._y_beam = y_beam
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            beam_size_x,
            "float",
        )
        self._beam_size_x = beam_size_x
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            beam_size_y,
            "float",
        )
        self._beam_size_y = beam_size_y
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            mad_1_energy,
            "float",
        )
        self._mad_1_energy = mad_1_energy
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            mad_2_energy,
            "float",
        )
        self._mad_2_energy = mad_2_energy
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            mad_3_energy,
            "float",
        )
        self._mad_3_energy = mad_3_energy
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            mad_4_energy,
            "float",
        )
        self._mad_4_energy = mad_4_energy
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            prefix,
            "string",
        )
        self._prefix = prefix
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            overlap,
            "float",
        )
        self._overlap = overlap
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            osc_start,
            "float",
        )
        self._osc_start = osc_start
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            process_directory,
            "string",
        )
        self._process_directory = process_directory
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            sum_images,
            "float",
        )
        self._sum_images = sum_images
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            detector_mode,
            "string",
        )
        self._detector_mode = detector_mode
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            mad_energies,
            "string",
        )
        self._mad_energies = mad_energies
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            comments,
            "string",
        )
        self._comments = comments
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            osc_range,
            "float",
        )
        self._osc_range = osc_range
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            first_image,
            "integer",
        )
        self._first_image = first_image
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            template,
            "string",
        )
        self._template = template
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            kappaStart,
            "float",
        )
        self._kappaStart = kappaStart
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            processing,
            "boolean",
        )
        self._processing = processing
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            inverse_beam,
            "float",
        )
        self._inverse_beam = inverse_beam
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            number_images,
            "integer",
        )
        self._number_images = number_images
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            current_detdistance,
            "float",
        )
        self._current_detdistance = current_detdistance
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            residues,
            "string",
        )
        self._residues = residues
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            run_number,
            "integer",
        )
        self._run_number = run_number
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            current_wavelength,
            "float",
        )
        self._current_wavelength = current_wavelength
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            phiStart,
            "float",
        )
        self._phiStart = phiStart
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            anomalous,
            "boolean",
        )
        self._anomalous = anomalous
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            number_passes,
            "integer",
        )
        self._number_passes = number_passes
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            directory,
            "string",
        )
        self._directory = directory
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            current_energy,
            "float",
        )
        self._current_energy = current_energy
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            current_osc_start,
            "float",
        )
        self._current_osc_start = current_osc_start
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            output_file,
            "string",
        )
        self._output_file = output_file
        checkType(
            "XSDataMXCuBEParameters",
            "Constructor of XSDataMXCuBEParameters",
            transmission,
            "float",
        )
        self._transmission = transmission

    def getSessionId(self):
        return self._sessionId

    def setSessionId(self, sessionId):
        checkType("XSDataMXCuBEParameters", "setSessionId", sessionId, "integer")
        self._sessionId = sessionId

    def delSessionId(self):
        self._sessionId = None

    # Properties
    sessionId = property(
        getSessionId, setSessionId, delSessionId, "Property for sessionId"
    )

    def getBlSampleId(self):
        return self._blSampleId

    def setBlSampleId(self, blSampleId):
        checkType("XSDataMXCuBEParameters", "setBlSampleId", blSampleId, "integer")
        self._blSampleId = blSampleId

    def delBlSampleId(self):
        self._blSampleId = None

    # Properties
    blSampleId = property(
        getBlSampleId, setBlSampleId, delBlSampleId, "Property for blSampleId"
    )

    def getExposure_time(self):
        return self._exposure_time

    def setExposure_time(self, exposure_time):
        checkType("XSDataMXCuBEParameters", "setExposure_time", exposure_time, "float")
        self._exposure_time = exposure_time

    def delExposure_time(self):
        self._exposure_time = None

    # Properties
    exposure_time = property(
        getExposure_time,
        setExposure_time,
        delExposure_time,
        "Property for exposure_time",
    )

    def getResolution(self):
        return self._resolution

    def setResolution(self, resolution):
        checkType("XSDataMXCuBEParameters", "setResolution", resolution, "float")
        self._resolution = resolution

    def delResolution(self):
        self._resolution = None

    # Properties
    resolution = property(
        getResolution, setResolution, delResolution, "Property for resolution"
    )

    def getResolution_at_corner(self):
        return self._resolution_at_corner

    def setResolution_at_corner(self, resolution_at_corner):
        checkType(
            "XSDataMXCuBEParameters",
            "setResolution_at_corner",
            resolution_at_corner,
            "float",
        )
        self._resolution_at_corner = resolution_at_corner

    def delResolution_at_corner(self):
        self._resolution_at_corner = None

    # Properties
    resolution_at_corner = property(
        getResolution_at_corner,
        setResolution_at_corner,
        delResolution_at_corner,
        "Property for resolution_at_corner",
    )

    def getX_beam(self):
        return self._x_beam

    def setX_beam(self, x_beam):
        checkType("XSDataMXCuBEParameters", "setX_beam", x_beam, "float")
        self._x_beam = x_beam

    def delX_beam(self):
        self._x_beam = None

    # Properties
    x_beam = property(getX_beam, setX_beam, delX_beam, "Property for x_beam")

    def getY_beam(self):
        return self._y_beam

    def setY_beam(self, y_beam):
        checkType("XSDataMXCuBEParameters", "setY_beam", y_beam, "float")
        self._y_beam = y_beam

    def delY_beam(self):
        self._y_beam = None

    # Properties
    y_beam = property(getY_beam, setY_beam, delY_beam, "Property for y_beam")

    def getBeam_size_x(self):
        return self._beam_size_x

    def setBeam_size_x(self, beam_size_x):
        checkType("XSDataMXCuBEParameters", "setBeam_size_x", beam_size_x, "float")
        self._beam_size_x = beam_size_x

    def delBeam_size_x(self):
        self._beam_size_x = None

    # Properties
    beam_size_x = property(
        getBeam_size_x, setBeam_size_x, delBeam_size_x, "Property for beam_size_x"
    )

    def getBeam_size_y(self):
        return self._beam_size_y

    def setBeam_size_y(self, beam_size_y):
        checkType("XSDataMXCuBEParameters", "setBeam_size_y", beam_size_y, "float")
        self._beam_size_y = beam_size_y

    def delBeam_size_y(self):
        self._beam_size_y = None

    # Properties
    beam_size_y = property(
        getBeam_size_y, setBeam_size_y, delBeam_size_y, "Property for beam_size_y"
    )

    def getMad_1_energy(self):
        return self._mad_1_energy

    def setMad_1_energy(self, mad_1_energy):
        checkType("XSDataMXCuBEParameters", "setMad_1_energy", mad_1_energy, "float")
        self._mad_1_energy = mad_1_energy

    def delMad_1_energy(self):
        self._mad_1_energy = None

    # Properties
    mad_1_energy = property(
        getMad_1_energy, setMad_1_energy, delMad_1_energy, "Property for mad_1_energy"
    )

    def getMad_2_energy(self):
        return self._mad_2_energy

    def setMad_2_energy(self, mad_2_energy):
        checkType("XSDataMXCuBEParameters", "setMad_2_energy", mad_2_energy, "float")
        self._mad_2_energy = mad_2_energy

    def delMad_2_energy(self):
        self._mad_2_energy = None

    # Properties
    mad_2_energy = property(
        getMad_2_energy, setMad_2_energy, delMad_2_energy, "Property for mad_2_energy"
    )

    def getMad_3_energy(self):
        return self._mad_3_energy

    def setMad_3_energy(self, mad_3_energy):
        checkType("XSDataMXCuBEParameters", "setMad_3_energy", mad_3_energy, "float")
        self._mad_3_energy = mad_3_energy

    def delMad_3_energy(self):
        self._mad_3_energy = None

    # Properties
    mad_3_energy = property(
        getMad_3_energy, setMad_3_energy, delMad_3_energy, "Property for mad_3_energy"
    )

    def getMad_4_energy(self):
        return self._mad_4_energy

    def setMad_4_energy(self, mad_4_energy):
        checkType("XSDataMXCuBEParameters", "setMad_4_energy", mad_4_energy, "float")
        self._mad_4_energy = mad_4_energy

    def delMad_4_energy(self):
        self._mad_4_energy = None

    # Properties
    mad_4_energy = property(
        getMad_4_energy, setMad_4_energy, delMad_4_energy, "Property for mad_4_energy"
    )

    def getPrefix(self):
        return self._prefix

    def setPrefix(self, prefix):
        checkType("XSDataMXCuBEParameters", "setPrefix", prefix, "string")
        self._prefix = prefix

    def delPrefix(self):
        self._prefix = None

    # Properties
    prefix = property(getPrefix, setPrefix, delPrefix, "Property for prefix")

    def getOverlap(self):
        return self._overlap

    def setOverlap(self, overlap):
        checkType("XSDataMXCuBEParameters", "setOverlap", overlap, "float")
        self._overlap = overlap

    def delOverlap(self):
        self._overlap = None

    # Properties
    overlap = property(getOverlap, setOverlap, delOverlap, "Property for overlap")

    def getOsc_start(self):
        return self._osc_start

    def setOsc_start(self, osc_start):
        checkType("XSDataMXCuBEParameters", "setOsc_start", osc_start, "float")
        self._osc_start = osc_start

    def delOsc_start(self):
        self._osc_start = None

    # Properties
    osc_start = property(
        getOsc_start, setOsc_start, delOsc_start, "Property for osc_start"
    )

    def getProcess_directory(self):
        return self._process_directory

    def setProcess_directory(self, process_directory):
        checkType(
            "XSDataMXCuBEParameters",
            "setProcess_directory",
            process_directory,
            "string",
        )
        self._process_directory = process_directory

    def delProcess_directory(self):
        self._process_directory = None

    # Properties
    process_directory = property(
        getProcess_directory,
        setProcess_directory,
        delProcess_directory,
        "Property for process_directory",
    )

    def getSum_images(self):
        return self._sum_images

    def setSum_images(self, sum_images):
        checkType("XSDataMXCuBEParameters", "setSum_images", sum_images, "float")
        self._sum_images = sum_images

    def delSum_images(self):
        self._sum_images = None

    # Properties
    sum_images = property(
        getSum_images, setSum_images, delSum_images, "Property for sum_images"
    )

    def getDetector_mode(self):
        return self._detector_mode

    def setDetector_mode(self, detector_mode):
        checkType("XSDataMXCuBEParameters", "setDetector_mode", detector_mode, "string")
        self._detector_mode = detector_mode

    def delDetector_mode(self):
        self._detector_mode = None

    # Properties
    detector_mode = property(
        getDetector_mode,
        setDetector_mode,
        delDetector_mode,
        "Property for detector_mode",
    )

    def getMad_energies(self):
        return self._mad_energies

    def setMad_energies(self, mad_energies):
        checkType("XSDataMXCuBEParameters", "setMad_energies", mad_energies, "string")
        self._mad_energies = mad_energies

    def delMad_energies(self):
        self._mad_energies = None

    # Properties
    mad_energies = property(
        getMad_energies, setMad_energies, delMad_energies, "Property for mad_energies"
    )

    def getComments(self):
        return self._comments

    def setComments(self, comments):
        checkType("XSDataMXCuBEParameters", "setComments", comments, "string")
        self._comments = comments

    def delComments(self):
        self._comments = None

    # Properties
    comments = property(getComments, setComments, delComments, "Property for comments")

    def getOsc_range(self):
        return self._osc_range

    def setOsc_range(self, osc_range):
        checkType("XSDataMXCuBEParameters", "setOsc_range", osc_range, "float")
        self._osc_range = osc_range

    def delOsc_range(self):
        self._osc_range = None

    # Properties
    osc_range = property(
        getOsc_range, setOsc_range, delOsc_range, "Property for osc_range"
    )

    def getFirst_image(self):
        return self._first_image

    def setFirst_image(self, first_image):
        checkType("XSDataMXCuBEParameters", "setFirst_image", first_image, "integer")
        self._first_image = first_image

    def delFirst_image(self):
        self._first_image = None

    # Properties
    first_image = property(
        getFirst_image, setFirst_image, delFirst_image, "Property for first_image"
    )

    def getTemplate(self):
        return self._template

    def setTemplate(self, template):
        checkType("XSDataMXCuBEParameters", "setTemplate", template, "string")
        self._template = template

    def delTemplate(self):
        self._template = None

    # Properties
    template = property(getTemplate, setTemplate, delTemplate, "Property for template")

    def getKappaStart(self):
        return self._kappaStart

    def setKappaStart(self, kappaStart):
        checkType("XSDataMXCuBEParameters", "setKappaStart", kappaStart, "float")
        self._kappaStart = kappaStart

    def delKappaStart(self):
        self._kappaStart = None

    # Properties
    kappaStart = property(
        getKappaStart, setKappaStart, delKappaStart, "Property for kappaStart"
    )

    def getProcessing(self):
        return self._processing

    def setProcessing(self, processing):
        checkType("XSDataMXCuBEParameters", "setProcessing", processing, "boolean")
        self._processing = processing

    def delProcessing(self):
        self._processing = None

    # Properties
    processing = property(
        getProcessing, setProcessing, delProcessing, "Property for processing"
    )

    def getInverse_beam(self):
        return self._inverse_beam

    def setInverse_beam(self, inverse_beam):
        checkType("XSDataMXCuBEParameters", "setInverse_beam", inverse_beam, "float")
        self._inverse_beam = inverse_beam

    def delInverse_beam(self):
        self._inverse_beam = None

    # Properties
    inverse_beam = property(
        getInverse_beam, setInverse_beam, delInverse_beam, "Property for inverse_beam"
    )

    def getNumber_images(self):
        return self._number_images

    def setNumber_images(self, number_images):
        checkType(
            "XSDataMXCuBEParameters", "setNumber_images", number_images, "integer"
        )
        self._number_images = number_images

    def delNumber_images(self):
        self._number_images = None

    # Properties
    number_images = property(
        getNumber_images,
        setNumber_images,
        delNumber_images,
        "Property for number_images",
    )

    def getCurrent_detdistance(self):
        return self._current_detdistance

    def setCurrent_detdistance(self, current_detdistance):
        checkType(
            "XSDataMXCuBEParameters",
            "setCurrent_detdistance",
            current_detdistance,
            "float",
        )
        self._current_detdistance = current_detdistance

    def delCurrent_detdistance(self):
        self._current_detdistance = None

    # Properties
    current_detdistance = property(
        getCurrent_detdistance,
        setCurrent_detdistance,
        delCurrent_detdistance,
        "Property for current_detdistance",
    )

    def getResidues(self):
        return self._residues

    def setResidues(self, residues):
        checkType("XSDataMXCuBEParameters", "setResidues", residues, "string")
        self._residues = residues

    def delResidues(self):
        self._residues = None

    # Properties
    residues = property(getResidues, setResidues, delResidues, "Property for residues")

    def getRun_number(self):
        return self._run_number

    def setRun_number(self, run_number):
        checkType("XSDataMXCuBEParameters", "setRun_number", run_number, "integer")
        self._run_number = run_number

    def delRun_number(self):
        self._run_number = None

    # Properties
    run_number = property(
        getRun_number, setRun_number, delRun_number, "Property for run_number"
    )

    def getCurrent_wavelength(self):
        return self._current_wavelength

    def setCurrent_wavelength(self, current_wavelength):
        checkType(
            "XSDataMXCuBEParameters",
            "setCurrent_wavelength",
            current_wavelength,
            "float",
        )
        self._current_wavelength = current_wavelength

    def delCurrent_wavelength(self):
        self._current_wavelength = None

    # Properties
    current_wavelength = property(
        getCurrent_wavelength,
        setCurrent_wavelength,
        delCurrent_wavelength,
        "Property for current_wavelength",
    )

    def getPhiStart(self):
        return self._phiStart

    def setPhiStart(self, phiStart):
        checkType("XSDataMXCuBEParameters", "setPhiStart", phiStart, "float")
        self._phiStart = phiStart

    def delPhiStart(self):
        self._phiStart = None

    # Properties
    phiStart = property(getPhiStart, setPhiStart, delPhiStart, "Property for phiStart")

    def getAnomalous(self):
        return self._anomalous

    def setAnomalous(self, anomalous):
        checkType("XSDataMXCuBEParameters", "setAnomalous", anomalous, "boolean")
        self._anomalous = anomalous

    def delAnomalous(self):
        self._anomalous = None

    # Properties
    anomalous = property(
        getAnomalous, setAnomalous, delAnomalous, "Property for anomalous"
    )

    def getNumber_passes(self):
        return self._number_passes

    def setNumber_passes(self, number_passes):
        checkType(
            "XSDataMXCuBEParameters", "setNumber_passes", number_passes, "integer"
        )
        self._number_passes = number_passes

    def delNumber_passes(self):
        self._number_passes = None

    # Properties
    number_passes = property(
        getNumber_passes,
        setNumber_passes,
        delNumber_passes,
        "Property for number_passes",
    )

    def getDirectory(self):
        return self._directory

    def setDirectory(self, directory):
        checkType("XSDataMXCuBEParameters", "setDirectory", directory, "string")
        self._directory = directory

    def delDirectory(self):
        self._directory = None

    # Properties
    directory = property(
        getDirectory, setDirectory, delDirectory, "Property for directory"
    )

    def getCurrent_energy(self):
        return self._current_energy

    def setCurrent_energy(self, current_energy):
        checkType(
            "XSDataMXCuBEParameters", "setCurrent_energy", current_energy, "float"
        )
        self._current_energy = current_energy

    def delCurrent_energy(self):
        self._current_energy = None

    # Properties
    current_energy = property(
        getCurrent_energy,
        setCurrent_energy,
        delCurrent_energy,
        "Property for current_energy",
    )

    def getCurrent_osc_start(self):
        return self._current_osc_start

    def setCurrent_osc_start(self, current_osc_start):
        checkType(
            "XSDataMXCuBEParameters", "setCurrent_osc_start", current_osc_start, "float"
        )
        self._current_osc_start = current_osc_start

    def delCurrent_osc_start(self):
        self._current_osc_start = None

    # Properties
    current_osc_start = property(
        getCurrent_osc_start,
        setCurrent_osc_start,
        delCurrent_osc_start,
        "Property for current_osc_start",
    )

    def getOutput_file(self):
        return self._output_file

    def setOutput_file(self, output_file):
        checkType("XSDataMXCuBEParameters", "setOutput_file", output_file, "string")
        self._output_file = output_file

    def delOutput_file(self):
        self._output_file = None

    # Properties
    output_file = property(
        getOutput_file, setOutput_file, delOutput_file, "Property for output_file"
    )

    def getTransmission(self):
        return self._transmission

    def setTransmission(self, transmission):
        checkType("XSDataMXCuBEParameters", "setTransmission", transmission, "float")
        self._transmission = transmission

    def delTransmission(self):
        self._transmission = None

    # Properties
    transmission = property(
        getTransmission, setTransmission, delTransmission, "Property for transmission"
    )

    def export(self, outfile, level, name_="XSDataMXCuBEParameters"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataMXCuBEParameters"):
        XSData.exportChildren(self, outfile, level, name_)
        if self._sessionId is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<sessionId>%d</sessionId>\n" % self._sessionId))
        else:
            warnEmptyAttribute("sessionId", "integer")
        if self._blSampleId is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<blSampleId>%d</blSampleId>\n" % self._blSampleId))
        else:
            warnEmptyAttribute("blSampleId", "integer")
        if self._exposure_time is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<exposure_time>%e</exposure_time>\n" % self._exposure_time)
            )
        else:
            warnEmptyAttribute("exposure_time", "float")
        if self._resolution is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<resolution>%e</resolution>\n" % self._resolution))
        else:
            warnEmptyAttribute("resolution", "float")
        if self._resolution_at_corner is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode(
                    "<resolution_at_corner>%e</resolution_at_corner>\n"
                    % self._resolution_at_corner
                )
            )
        else:
            warnEmptyAttribute("resolution_at_corner", "float")
        if self._x_beam is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<x_beam>%e</x_beam>\n" % self._x_beam))
        else:
            warnEmptyAttribute("x_beam", "float")
        if self._y_beam is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<y_beam>%e</y_beam>\n" % self._y_beam))
        else:
            warnEmptyAttribute("y_beam", "float")
        if self._beam_size_x is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<beam_size_x>%e</beam_size_x>\n" % self._beam_size_x)
            )
        else:
            warnEmptyAttribute("beam_size_x", "float")
        if self._beam_size_y is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<beam_size_y>%e</beam_size_y>\n" % self._beam_size_y)
            )
        else:
            warnEmptyAttribute("beam_size_y", "float")
        if self._mad_1_energy is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<mad_1_energy>%e</mad_1_energy>\n" % self._mad_1_energy)
            )
        else:
            warnEmptyAttribute("mad_1_energy", "float")
        if self._mad_2_energy is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<mad_2_energy>%e</mad_2_energy>\n" % self._mad_2_energy)
            )
        else:
            warnEmptyAttribute("mad_2_energy", "float")
        if self._mad_3_energy is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<mad_3_energy>%e</mad_3_energy>\n" % self._mad_3_energy)
            )
        else:
            warnEmptyAttribute("mad_3_energy", "float")
        if self._mad_4_energy is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<mad_4_energy>%e</mad_4_energy>\n" % self._mad_4_energy)
            )
        else:
            warnEmptyAttribute("mad_4_energy", "float")
        if self._prefix is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<prefix>%s</prefix>\n" % self._prefix))
        else:
            warnEmptyAttribute("prefix", "string")
        if self._overlap is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<overlap>%e</overlap>\n" % self._overlap))
        else:
            warnEmptyAttribute("overlap", "float")
        if self._osc_start is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<osc_start>%e</osc_start>\n" % self._osc_start))
        else:
            warnEmptyAttribute("osc_start", "float")
        if self._process_directory is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode(
                    "<process_directory>%s</process_directory>\n"
                    % self._process_directory
                )
            )
        else:
            warnEmptyAttribute("process_directory", "string")
        if self._sum_images is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<sum_images>%e</sum_images>\n" % self._sum_images))
        else:
            warnEmptyAttribute("sum_images", "float")
        if self._detector_mode is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<detector_mode>%s</detector_mode>\n" % self._detector_mode)
            )
        else:
            warnEmptyAttribute("detector_mode", "string")
        if self._mad_energies is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<mad_energies>%s</mad_energies>\n" % self._mad_energies)
            )
        else:
            warnEmptyAttribute("mad_energies", "string")
        if self._comments is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<comments>%s</comments>\n" % self._comments))
        else:
            warnEmptyAttribute("comments", "string")
        if self._osc_range is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<osc_range>%e</osc_range>\n" % self._osc_range))
        else:
            warnEmptyAttribute("osc_range", "float")
        if self._first_image is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<first_image>%d</first_image>\n" % self._first_image)
            )
        else:
            warnEmptyAttribute("first_image", "integer")
        if self._template is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<template>%s</template>\n" % self._template))
        else:
            warnEmptyAttribute("template", "string")
        if self._kappaStart is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<kappaStart>%e</kappaStart>\n" % self._kappaStart))
        else:
            warnEmptyAttribute("kappaStart", "float")
        if self._processing is not None:
            showIndent(outfile, level)
            if self._processing:
                outfile.write(unicode("<processing>true</processing>\n"))
            else:
                outfile.write(unicode("<processing>false</processing>\n"))
        else:
            warnEmptyAttribute("processing", "boolean")
        if self._inverse_beam is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<inverse_beam>%e</inverse_beam>\n" % self._inverse_beam)
            )
        else:
            warnEmptyAttribute("inverse_beam", "float")
        if self._number_images is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<number_images>%d</number_images>\n" % self._number_images)
            )
        else:
            warnEmptyAttribute("number_images", "integer")
        if self._current_detdistance is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode(
                    "<current_detdistance>%e</current_detdistance>\n"
                    % self._current_detdistance
                )
            )
        else:
            warnEmptyAttribute("current_detdistance", "float")
        if self._residues is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<residues>%s</residues>\n" % self._residues))
        else:
            warnEmptyAttribute("residues", "string")
        if self._run_number is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<run_number>%d</run_number>\n" % self._run_number))
        else:
            warnEmptyAttribute("run_number", "integer")
        if self._current_wavelength is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode(
                    "<current_wavelength>%e</current_wavelength>\n"
                    % self._current_wavelength
                )
            )
        else:
            warnEmptyAttribute("current_wavelength", "float")
        if self._phiStart is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<phiStart>%e</phiStart>\n" % self._phiStart))
        else:
            warnEmptyAttribute("phiStart", "float")
        if self._anomalous is not None:
            showIndent(outfile, level)
            if self._anomalous:
                outfile.write(unicode("<anomalous>true</anomalous>\n"))
            else:
                outfile.write(unicode("<anomalous>false</anomalous>\n"))
        else:
            warnEmptyAttribute("anomalous", "boolean")
        if self._number_passes is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<number_passes>%d</number_passes>\n" % self._number_passes)
            )
        else:
            warnEmptyAttribute("number_passes", "integer")
        if self._directory is not None:
            showIndent(outfile, level)
            outfile.write(unicode("<directory>%s</directory>\n" % self._directory))
        else:
            warnEmptyAttribute("directory", "string")
        if self._current_energy is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<current_energy>%e</current_energy>\n" % self._current_energy)
            )
        else:
            warnEmptyAttribute("current_energy", "float")
        if self._current_osc_start is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode(
                    "<current_osc_start>%e</current_osc_start>\n"
                    % self._current_osc_start
                )
            )
        else:
            warnEmptyAttribute("current_osc_start", "float")
        if self._output_file is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<output_file>%s</output_file>\n" % self._output_file)
            )
        else:
            warnEmptyAttribute("output_file", "string")
        if self._transmission is not None:
            showIndent(outfile, level)
            outfile.write(
                unicode("<transmission>%e</transmission>\n" % self._transmission)
            )
        else:
            warnEmptyAttribute("transmission", "float")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "sessionId":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self._sessionId = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "blSampleId":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self._blSampleId = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "exposure_time":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._exposure_time = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "resolution":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._resolution = fval_
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "resolution_at_corner"
        ):
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._resolution_at_corner = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "x_beam":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._x_beam = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "y_beam":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._y_beam = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "beam_size_x":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._beam_size_x = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "beam_size_y":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._beam_size_y = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "mad_1_energy":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._mad_1_energy = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "mad_2_energy":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._mad_2_energy = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "mad_3_energy":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._mad_3_energy = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "mad_4_energy":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._mad_4_energy = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "prefix":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._prefix = value_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "overlap":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._overlap = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "osc_start":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._osc_start = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "process_directory":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._process_directory = value_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "sum_images":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._sum_images = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "detector_mode":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._detector_mode = value_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "mad_energies":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._mad_energies = value_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "comments":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._comments = value_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "osc_range":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._osc_range = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "first_image":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self._first_image = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "template":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._template = value_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "kappaStart":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._kappaStart = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "processing":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                if sval_ in ("True", "true", "1"):
                    ival_ = True
                elif sval_ in ("False", "false", "0"):
                    ival_ = False
                else:
                    raise ValueError("requires boolean -- %s" % child_.toxml())
                self._processing = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "inverse_beam":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._inverse_beam = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "number_images":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self._number_images = ival_
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "current_detdistance"
        ):
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._current_detdistance = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "residues":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._residues = value_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "run_number":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self._run_number = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "current_wavelength":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._current_wavelength = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "phiStart":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._phiStart = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "anomalous":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                if sval_ in ("True", "true", "1"):
                    ival_ = True
                elif sval_ in ("False", "false", "0"):
                    ival_ = False
                else:
                    raise ValueError("requires boolean -- %s" % child_.toxml())
                self._anomalous = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "number_passes":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError("requires integer -- %s" % child_.toxml())
                self._number_passes = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "directory":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._directory = value_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "current_energy":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._current_energy = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "current_osc_start":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._current_osc_start = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "output_file":
            value_ = ""
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._output_file = value_
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "transmission":
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError(
                        "requires float (or double) -- %s" % child_.toxml()
                    )
                self._transmission = fval_
        XSData.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataMXCuBEParameters")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataMXCuBEParameters")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataMXCuBEParameters is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataMXCuBEParameters.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataMXCuBEParameters()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataMXCuBEParameters")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataMXCuBEParameters()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataMXCuBEParameters


class XSDataInputMXCuBE(XSDataInput):
    def __init__(
        self,
        configuration=None,
        dataSet=None,
        sample=None,
        outputFileDirectory=None,
        experimentalCondition=None,
        diffractionPlan=None,
        dataCollectionId=None,
        characterisationInput=None,
    ):
        XSDataInput.__init__(self, configuration)

        checkType(
            "XSDataInputMXCuBE",
            "Constructor of XSDataInputMXCuBE",
            characterisationInput,
            "XSDataInputCharacterisation",
        )
        self._characterisationInput = characterisationInput
        checkType(
            "XSDataInputMXCuBE",
            "Constructor of XSDataInputMXCuBE",
            dataCollectionId,
            "XSDataInteger",
        )
        self._dataCollectionId = dataCollectionId
        checkType(
            "XSDataInputMXCuBE",
            "Constructor of XSDataInputMXCuBE",
            diffractionPlan,
            "XSDataDiffractionPlan",
        )
        self._diffractionPlan = diffractionPlan
        checkType(
            "XSDataInputMXCuBE",
            "Constructor of XSDataInputMXCuBE",
            experimentalCondition,
            "XSDataExperimentalCondition",
        )
        self._experimentalCondition = experimentalCondition
        checkType(
            "XSDataInputMXCuBE",
            "Constructor of XSDataInputMXCuBE",
            outputFileDirectory,
            "XSDataFile",
        )
        self._outputFileDirectory = outputFileDirectory
        checkType(
            "XSDataInputMXCuBE",
            "Constructor of XSDataInputMXCuBE",
            sample,
            "XSDataSampleCrystalMM",
        )
        self._sample = sample
        if dataSet is None:
            self._dataSet = []
        else:
            checkType(
                "XSDataInputMXCuBE", "Constructor of XSDataInputMXCuBE", dataSet, "list"
            )
            self._dataSet = dataSet

    def getCharacterisationInput(self):
        return self._characterisationInput

    def setCharacterisationInput(self, characterisationInput):
        checkType(
            "XSDataInputMXCuBE",
            "setCharacterisationInput",
            characterisationInput,
            "XSDataInputCharacterisation",
        )
        self._characterisationInput = characterisationInput

    def delCharacterisationInput(self):
        self._characterisationInput = None

    # Properties
    characterisationInput = property(
        getCharacterisationInput,
        setCharacterisationInput,
        delCharacterisationInput,
        "Property for characterisationInput",
    )

    def getDataCollectionId(self):
        return self._dataCollectionId

    def setDataCollectionId(self, dataCollectionId):
        checkType(
            "XSDataInputMXCuBE",
            "setDataCollectionId",
            dataCollectionId,
            "XSDataInteger",
        )
        self._dataCollectionId = dataCollectionId

    def delDataCollectionId(self):
        self._dataCollectionId = None

    # Properties
    dataCollectionId = property(
        getDataCollectionId,
        setDataCollectionId,
        delDataCollectionId,
        "Property for dataCollectionId",
    )

    def getDiffractionPlan(self):
        return self._diffractionPlan

    def setDiffractionPlan(self, diffractionPlan):
        checkType(
            "XSDataInputMXCuBE",
            "setDiffractionPlan",
            diffractionPlan,
            "XSDataDiffractionPlan",
        )
        self._diffractionPlan = diffractionPlan

    def delDiffractionPlan(self):
        self._diffractionPlan = None

    # Properties
    diffractionPlan = property(
        getDiffractionPlan,
        setDiffractionPlan,
        delDiffractionPlan,
        "Property for diffractionPlan",
    )

    def getExperimentalCondition(self):
        return self._experimentalCondition

    def setExperimentalCondition(self, experimentalCondition):
        checkType(
            "XSDataInputMXCuBE",
            "setExperimentalCondition",
            experimentalCondition,
            "XSDataExperimentalCondition",
        )
        self._experimentalCondition = experimentalCondition

    def delExperimentalCondition(self):
        self._experimentalCondition = None

    # Properties
    experimentalCondition = property(
        getExperimentalCondition,
        setExperimentalCondition,
        delExperimentalCondition,
        "Property for experimentalCondition",
    )

    def getOutputFileDirectory(self):
        return self._outputFileDirectory

    def setOutputFileDirectory(self, outputFileDirectory):
        checkType(
            "XSDataInputMXCuBE",
            "setOutputFileDirectory",
            outputFileDirectory,
            "XSDataFile",
        )
        self._outputFileDirectory = outputFileDirectory

    def delOutputFileDirectory(self):
        self._outputFileDirectory = None

    # Properties
    outputFileDirectory = property(
        getOutputFileDirectory,
        setOutputFileDirectory,
        delOutputFileDirectory,
        "Property for outputFileDirectory",
    )

    def getSample(self):
        return self._sample

    def setSample(self, sample):
        checkType("XSDataInputMXCuBE", "setSample", sample, "XSDataSampleCrystalMM")
        self._sample = sample

    def delSample(self):
        self._sample = None

    # Properties
    sample = property(getSample, setSample, delSample, "Property for sample")

    def getDataSet(self):
        return self._dataSet

    def setDataSet(self, dataSet):
        checkType("XSDataInputMXCuBE", "setDataSet", dataSet, "list")
        self._dataSet = dataSet

    def delDataSet(self):
        self._dataSet = None

    # Properties
    dataSet = property(getDataSet, setDataSet, delDataSet, "Property for dataSet")

    def addDataSet(self, value):
        checkType("XSDataInputMXCuBE", "setDataSet", value, "XSDataMXCuBEDataSet")
        self._dataSet.append(value)

    def insertDataSet(self, index, value):
        checkType("XSDataInputMXCuBE", "setDataSet", value, "XSDataMXCuBEDataSet")
        self._dataSet[index] = value

    def export(self, outfile, level, name_="XSDataInputMXCuBE"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataInputMXCuBE"):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._characterisationInput is not None:
            self.characterisationInput.export(
                outfile, level, name_="characterisationInput"
            )
        if self._dataCollectionId is not None:
            self.dataCollectionId.export(outfile, level, name_="dataCollectionId")
        if self._diffractionPlan is not None:
            self.diffractionPlan.export(outfile, level, name_="diffractionPlan")
        if self._experimentalCondition is not None:
            self.experimentalCondition.export(
                outfile, level, name_="experimentalCondition"
            )
        if self._outputFileDirectory is not None:
            self.outputFileDirectory.export(outfile, level, name_="outputFileDirectory")
        if self._sample is not None:
            self.sample.export(outfile, level, name_="sample")
        for dataSet_ in self.getDataSet():
            dataSet_.export(outfile, level, name_="dataSet")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "characterisationInput"
        ):
            obj_ = XSDataInputCharacterisation()
            obj_.build(child_)
            self.setCharacterisationInput(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "dataCollectionId":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setDataCollectionId(obj_)
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
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "outputFileDirectory"
        ):
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setOutputFileDirectory(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "sample":
            obj_ = XSDataSampleCrystalMM()
            obj_.build(child_)
            self.setSample(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "dataSet":
            obj_ = XSDataMXCuBEDataSet()
            obj_.build(child_)
            self.dataSet.append(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataInputMXCuBE")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataInputMXCuBE")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataInputMXCuBE is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataInputMXCuBE.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputMXCuBE()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataInputMXCuBE")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputMXCuBE()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataInputMXCuBE


class XSDataResultMXCuBE(XSDataResult):
    def __init__(
        self,
        status=None,
        screeningId=None,
        htmlPage=None,
        outputFileDictionary=None,
        listOfOutputFiles=None,
        collectionPlan=None,
        characterisationResult=None,
        characterisationExecutiveSummary=None,
    ):
        XSDataResult.__init__(self, status)

        checkType(
            "XSDataResultMXCuBE",
            "Constructor of XSDataResultMXCuBE",
            characterisationExecutiveSummary,
            "XSDataString",
        )
        self._characterisationExecutiveSummary = characterisationExecutiveSummary
        checkType(
            "XSDataResultMXCuBE",
            "Constructor of XSDataResultMXCuBE",
            characterisationResult,
            "XSDataResultCharacterisation",
        )
        self._characterisationResult = characterisationResult
        if collectionPlan is None:
            self._collectionPlan = []
        else:
            checkType(
                "XSDataResultMXCuBE",
                "Constructor of XSDataResultMXCuBE",
                collectionPlan,
                "list",
            )
            self._collectionPlan = collectionPlan
        checkType(
            "XSDataResultMXCuBE",
            "Constructor of XSDataResultMXCuBE",
            listOfOutputFiles,
            "XSDataString",
        )
        self._listOfOutputFiles = listOfOutputFiles
        checkType(
            "XSDataResultMXCuBE",
            "Constructor of XSDataResultMXCuBE",
            outputFileDictionary,
            "XSDataDictionary",
        )
        self._outputFileDictionary = outputFileDictionary
        checkType(
            "XSDataResultMXCuBE",
            "Constructor of XSDataResultMXCuBE",
            htmlPage,
            "XSDataFile",
        )
        self._htmlPage = htmlPage
        checkType(
            "XSDataResultMXCuBE",
            "Constructor of XSDataResultMXCuBE",
            screeningId,
            "XSDataInteger",
        )
        self._screeningId = screeningId

    def getCharacterisationExecutiveSummary(self):
        return self._characterisationExecutiveSummary

    def setCharacterisationExecutiveSummary(self, characterisationExecutiveSummary):
        checkType(
            "XSDataResultMXCuBE",
            "setCharacterisationExecutiveSummary",
            characterisationExecutiveSummary,
            "XSDataString",
        )
        self._characterisationExecutiveSummary = characterisationExecutiveSummary

    def delCharacterisationExecutiveSummary(self):
        self._characterisationExecutiveSummary = None

    # Properties
    characterisationExecutiveSummary = property(
        getCharacterisationExecutiveSummary,
        setCharacterisationExecutiveSummary,
        delCharacterisationExecutiveSummary,
        "Property for characterisationExecutiveSummary",
    )

    def getCharacterisationResult(self):
        return self._characterisationResult

    def setCharacterisationResult(self, characterisationResult):
        checkType(
            "XSDataResultMXCuBE",
            "setCharacterisationResult",
            characterisationResult,
            "XSDataResultCharacterisation",
        )
        self._characterisationResult = characterisationResult

    def delCharacterisationResult(self):
        self._characterisationResult = None

    # Properties
    characterisationResult = property(
        getCharacterisationResult,
        setCharacterisationResult,
        delCharacterisationResult,
        "Property for characterisationResult",
    )

    def getCollectionPlan(self):
        return self._collectionPlan

    def setCollectionPlan(self, collectionPlan):
        checkType("XSDataResultMXCuBE", "setCollectionPlan", collectionPlan, "list")
        self._collectionPlan = collectionPlan

    def delCollectionPlan(self):
        self._collectionPlan = None

    # Properties
    collectionPlan = property(
        getCollectionPlan,
        setCollectionPlan,
        delCollectionPlan,
        "Property for collectionPlan",
    )

    def addCollectionPlan(self, value):
        checkType(
            "XSDataResultMXCuBE", "setCollectionPlan", value, "XSDataCollectionPlan"
        )
        self._collectionPlan.append(value)

    def insertCollectionPlan(self, index, value):
        checkType(
            "XSDataResultMXCuBE", "setCollectionPlan", value, "XSDataCollectionPlan"
        )
        self._collectionPlan[index] = value

    def getListOfOutputFiles(self):
        return self._listOfOutputFiles

    def setListOfOutputFiles(self, listOfOutputFiles):
        checkType(
            "XSDataResultMXCuBE",
            "setListOfOutputFiles",
            listOfOutputFiles,
            "XSDataString",
        )
        self._listOfOutputFiles = listOfOutputFiles

    def delListOfOutputFiles(self):
        self._listOfOutputFiles = None

    # Properties
    listOfOutputFiles = property(
        getListOfOutputFiles,
        setListOfOutputFiles,
        delListOfOutputFiles,
        "Property for listOfOutputFiles",
    )

    def getOutputFileDictionary(self):
        return self._outputFileDictionary

    def setOutputFileDictionary(self, outputFileDictionary):
        checkType(
            "XSDataResultMXCuBE",
            "setOutputFileDictionary",
            outputFileDictionary,
            "XSDataDictionary",
        )
        self._outputFileDictionary = outputFileDictionary

    def delOutputFileDictionary(self):
        self._outputFileDictionary = None

    # Properties
    outputFileDictionary = property(
        getOutputFileDictionary,
        setOutputFileDictionary,
        delOutputFileDictionary,
        "Property for outputFileDictionary",
    )

    def getHtmlPage(self):
        return self._htmlPage

    def setHtmlPage(self, htmlPage):
        checkType("XSDataResultMXCuBE", "setHtmlPage", htmlPage, "XSDataFile")
        self._htmlPage = htmlPage

    def delHtmlPage(self):
        self._htmlPage = None

    # Properties
    htmlPage = property(getHtmlPage, setHtmlPage, delHtmlPage, "Property for htmlPage")

    def getScreeningId(self):
        return self._screeningId

    def setScreeningId(self, screeningId):
        checkType("XSDataResultMXCuBE", "setScreeningId", screeningId, "XSDataInteger")
        self._screeningId = screeningId

    def delScreeningId(self):
        self._screeningId = None

    # Properties
    screeningId = property(
        getScreeningId, setScreeningId, delScreeningId, "Property for screeningId"
    )

    def export(self, outfile, level, name_="XSDataResultMXCuBE"):
        showIndent(outfile, level)
        outfile.write(unicode("<%s>\n" % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode("</%s>\n" % name_))

    def exportChildren(self, outfile, level, name_="XSDataResultMXCuBE"):
        XSDataResult.exportChildren(self, outfile, level, name_)
        if self._characterisationExecutiveSummary is not None:
            self.characterisationExecutiveSummary.export(
                outfile, level, name_="characterisationExecutiveSummary"
            )
        if self._characterisationResult is not None:
            self.characterisationResult.export(
                outfile, level, name_="characterisationResult"
            )
        for collectionPlan_ in self.getCollectionPlan():
            collectionPlan_.export(outfile, level, name_="collectionPlan")
        if self._listOfOutputFiles is not None:
            self.listOfOutputFiles.export(outfile, level, name_="listOfOutputFiles")
        if self._outputFileDictionary is not None:
            self.outputFileDictionary.export(
                outfile, level, name_="outputFileDictionary"
            )
        if self._htmlPage is not None:
            self.htmlPage.export(outfile, level, name_="htmlPage")
        if self._screeningId is not None:
            self.screeningId.export(outfile, level, name_="screeningId")

    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(":")[-1]
            self.buildChildren(child_, nodeName_)

    def buildChildren(self, child_, nodeName_):
        if (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "characterisationExecutiveSummary"
        ):
            obj_ = XSDataString()
            obj_.build(child_)
            self.setCharacterisationExecutiveSummary(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE
            and nodeName_ == "characterisationResult"
        ):
            obj_ = XSDataResultCharacterisation()
            obj_.build(child_)
            self.setCharacterisationResult(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "collectionPlan":
            obj_ = XSDataCollectionPlan()
            obj_.build(child_)
            self.collectionPlan.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "listOfOutputFiles":
            obj_ = XSDataString()
            obj_.build(child_)
            self.setListOfOutputFiles(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "outputFileDictionary"
        ):
            obj_ = XSDataDictionary()
            obj_.build(child_)
            self.setOutputFileDictionary(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "htmlPage":
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setHtmlPage(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and nodeName_ == "screeningId":
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setScreeningId(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)

    # Method for marshalling an object

    def marshal(self):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(oStreamString, 0, name_="XSDataResultMXCuBE")
        oStringXML = oStreamString.getValue()
        oStreamString.close()
        return oStringXML

    # Only to export the entire XML tree to a file stream on disk

    def exportToFile(self, _outfileName):
        outfile = open(_outfileName, "w")
        outfile.write(unicode('<?xml version="1.0" ?>\n'))
        self.export(outfile, 0, name_="XSDataResultMXCuBE")
        outfile.close()

    # Deprecated method, replaced by exportToFile

    def outputFile(self, _outfileName):
        print(
            "WARNING: Method outputFile in class XSDataResultMXCuBE is deprecated, please use instead exportToFile!"
        )
        self.exportToFile(_outfileName)

    # Method for making a copy in a new instance

    def copy(self):
        return XSDataResultMXCuBE.parseString(self.marshal())

    # Static method for parsing a string

    def parseString(_inString):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultMXCuBE()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export(oStreamString, 0, name_="XSDataResultMXCuBE")
        oStreamString.close()
        return rootObj

    parseString = staticmethod(parseString)
    # Static method for parsing a file

    def parseFile(_inFilePath):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultMXCuBE()
        rootObj.build(rootNode)
        return rootObj

    parseFile = staticmethod(parseFile)


# end class XSDataResultMXCuBE


# End of data representation classes.
