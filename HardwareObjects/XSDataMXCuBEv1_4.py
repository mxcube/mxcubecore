#!/usr/bin/env python

#
# Generated Thu Sep 17 03:33::44 2020 by EDGenerateDS.
#

import os, sys
from xml.dom import minidom
from xml.dom import Node


strEdnaHome = os.environ.get("EDNA_HOME", None)

dictLocation = { \
 "XSDataCommon": "kernel/datamodel", \
 "XSDataCommon": "kernel/datamodel", \
 "XSDataCommon": "kernel/datamodel", \
 "XSDataCommon": "kernel/datamodel", \
 "XSDataCommon": "kernel/datamodel", \
 "XSDataCommon": "kernel/datamodel", \
 "XSDataCommon": "kernel/datamodel", \
 "XSDataMXv1": "mxv1/datamodel", \
 "XSDataMXv1": "mxv1/datamodel", \
 "XSDataMXv1": "mxv1/datamodel", \
 "XSDataMXv1": "mxv1/datamodel", \
 "XSDataMXv1": "mxv1/datamodel", \
 "XSDataMXv1": "mxv1/datamodel", \
}

try:
    from XSDataCommon import XSData
    from XSDataCommon import XSDataDictionary
    from XSDataCommon import XSDataFile
    from XSDataCommon import XSDataInput
    from XSDataCommon import XSDataInteger
    from XSDataCommon import XSDataResult
    from XSDataCommon import XSDataString
    from XSDataMXv1 import XSDataCollectionPlan
    from XSDataMXv1 import XSDataDiffractionPlan
    from XSDataMXv1 import XSDataExperimentalCondition
    from XSDataMXv1 import XSDataInputCharacterisation
    from XSDataMXv1 import XSDataResultCharacterisation
    from XSDataMXv1 import XSDataSampleCrystalMM
except ImportError as error:
    if strEdnaHome is not None:
        for strXsdName in dictLocation:
            strXsdModule = strXsdName + ".py"
            strRootdir = os.path.dirname(os.path.abspath(os.path.join(strEdnaHome, dictLocation[strXsdName])))
            for strRoot, listDirs, listFiles in os.walk(strRootdir):
                if strXsdModule in listFiles:
                    sys.path.append(strRoot)
    else:
        raise error
from XSDataCommon import XSData
from XSDataCommon import XSDataDictionary
from XSDataCommon import XSDataFile
from XSDataCommon import XSDataInput
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataResult
from XSDataCommon import XSDataString
from XSDataMXv1 import XSDataCollectionPlan
from XSDataMXv1 import XSDataDiffractionPlan
from XSDataMXv1 import XSDataExperimentalCondition
from XSDataMXv1 import XSDataInputCharacterisation
from XSDataMXv1 import XSDataResultCharacterisation
from XSDataMXv1 import XSDataSampleCrystalMM




#
# Support/utility functions.
#

# Compabiltity between Python 2 and 3:
if sys.version.startswith('3'):
    unicode = str
    from io import StringIO
else:
    from StringIO import StringIO


def showIndent(outfile, level):
    for idx in range(level):
        outfile.write(unicode('    '))


def warnEmptyAttribute(_strName, _strTypeName):
    pass
    #if not _strTypeName in ["float", "double", "string", "boolean", "integer"]:
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
        else:     # category == MixedContainer.CategoryComplex
            self.value.export(outfile, level, name)
    def exportSimple(self, outfile, level, name):
        if self.content_type == MixedContainer.TypeString:
            outfile.write(unicode('<%s>%s</%s>' % (self.name, self.value, self.name)))
        elif self.content_type == MixedContainer.TypeInteger or \
                self.content_type == MixedContainer.TypeBoolean:
            outfile.write(unicode('<%s>%d</%s>' % (self.name, self.value, self.name)))
        elif self.content_type == MixedContainer.TypeFloat or \
                self.content_type == MixedContainer.TypeDecimal:
            outfile.write(unicode('<%s>%f</%s>' % (self.name, self.value, self.name)))
        elif self.content_type == MixedContainer.TypeDouble:
            outfile.write(unicode('<%s>%g</%s>' % (self.name, self.value, self.name)))

#
# Data representation classes.
#



class XSDataMXCuBEDataSet(object):
    def __init__(self, imageFile=None):
        if imageFile is None:
            self._imageFile = []
        elif imageFile.__class__.__name__ == "list":
            self._imageFile = imageFile
        else:
            strMessage = "ERROR! XSDataMXCuBEDataSet constructor argument 'imageFile' is not list but %s" % self._imageFile.__class__.__name__
            raise BaseException(strMessage)
    # Methods and properties for the 'imageFile' attribute
    def getImageFile(self): return self._imageFile
    def setImageFile(self, imageFile):
        if imageFile is None:
            self._imageFile = []
        elif imageFile.__class__.__name__ == "list":
            self._imageFile = imageFile
        else:
            strMessage = "ERROR! XSDataMXCuBEDataSet.setImageFile argument is not list but %s" % imageFile.__class__.__name__
            raise BaseException(strMessage)
    def delImageFile(self): self._imageFile = None
    imageFile = property(getImageFile, setImageFile, delImageFile, "Property for imageFile")
    def addImageFile(self, value):
        if value is None:
            strMessage = "ERROR! XSDataMXCuBEDataSet.addImageFile argument is None"
            raise BaseException(strMessage)            
        elif value.__class__.__name__ == "XSDataFile":
            self._imageFile.append(value)
        else:
            strMessage = "ERROR! XSDataMXCuBEDataSet.addImageFile argument is not XSDataFile but %s" % value.__class__.__name__
            raise BaseException(strMessage)
    def insertImageFile(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataMXCuBEDataSet.insertImageFile argument 'index' is None"
            raise BaseException(strMessage)            
        if value is None:
            strMessage = "ERROR! XSDataMXCuBEDataSet.insertImageFile argument 'value' is None"
            raise BaseException(strMessage)            
        elif value.__class__.__name__ == "XSDataFile":
            self._imageFile[index] = value
        else:
            strMessage = "ERROR! XSDataMXCuBEDataSet.addImageFile argument is not XSDataFile but %s" % value.__class__.__name__
            raise BaseException(strMessage)
    def export(self, outfile, level, name_='XSDataMXCuBEDataSet'):
        showIndent(outfile, level)
        outfile.write(unicode('<%s>\n' % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode('</%s>\n' % name_))
    def exportChildren(self, outfile, level, name_='XSDataMXCuBEDataSet'):
        pass
        for imageFile_ in self.getImageFile():
            imageFile_.export(outfile, level, name_='imageFile')
        if self.getImageFile() == []:
            warnEmptyAttribute("imageFile", "XSDataFile")
    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'imageFile':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.imageFile.append(obj_)
    #Method for marshalling an object
    def marshal( self ):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export( oStreamString, 0, name_="XSDataMXCuBEDataSet" )
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML
    #Only to export the entire XML tree to a file stream on disk
    def exportToFile( self, _outfileName ):
        outfile = open( _outfileName, "w" )
        outfile.write(unicode('<?xml version=\"1.0\" ?>\n'))
        self.export( outfile, 0, name_='XSDataMXCuBEDataSet' )
        outfile.close()
    #Deprecated method, replaced by exportToFile
    def outputFile( self, _outfileName ):
        print("WARNING: Method outputFile in class XSDataMXCuBEDataSet is deprecated, please use instead exportToFile!")
        self.exportToFile(_outfileName)
    #Method for making a copy in a new instance
    def copy( self ):
        return XSDataMXCuBEDataSet.parseString(self.marshal())
    #Static method for parsing a string
    def parseString( _inString ):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataMXCuBEDataSet()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export( oStreamString, 0, name_="XSDataMXCuBEDataSet" )
        oStreamString.close()
        return rootObj
    parseString = staticmethod( parseString )
    #Static method for parsing a file
    def parseFile( _inFilePath ):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataMXCuBEDataSet()
        rootObj.build(rootNode)
        return rootObj
    parseFile = staticmethod( parseFile )
# end class XSDataMXCuBEDataSet


class XSDataMXCuBEParameters(XSData):
    def __init__(self, transmission=None, output_file=None, current_osc_start=None, current_energy=None, directory=None, number_passes=None, anomalous=None, phiStart=None, current_wavelength=None, run_number=None, residues=None, current_detdistance=None, number_images=None, inverse_beam=None, processing=None, kappaStart=None, template=None, first_image=None, osc_range=None, comments=None, mad_energies=None, detector_mode=None, sum_images=None, process_directory=None, osc_start=None, overlap=None, prefix=None, mad_4_energy=None, mad_3_energy=None, mad_2_energy=None, mad_1_energy=None, beam_size_y=None, beam_size_x=None, y_beam=None, x_beam=None, resolution_at_corner=None, resolution=None, exposure_time=None, blSampleId=None, sessionId=None):
        XSData.__init__(self, )
        if sessionId is None:
            self._sessionId = None
        else:
            self._sessionId = int(sessionId)
        if blSampleId is None:
            self._blSampleId = None
        else:
            self._blSampleId = int(blSampleId)
        if exposure_time is None:
            self._exposure_time = None
        else:
            self._exposure_time = float(exposure_time)
        if resolution is None:
            self._resolution = None
        else:
            self._resolution = float(resolution)
        if resolution_at_corner is None:
            self._resolution_at_corner = None
        else:
            self._resolution_at_corner = float(resolution_at_corner)
        if x_beam is None:
            self._x_beam = None
        else:
            self._x_beam = float(x_beam)
        if y_beam is None:
            self._y_beam = None
        else:
            self._y_beam = float(y_beam)
        if beam_size_x is None:
            self._beam_size_x = None
        else:
            self._beam_size_x = float(beam_size_x)
        if beam_size_y is None:
            self._beam_size_y = None
        else:
            self._beam_size_y = float(beam_size_y)
        if mad_1_energy is None:
            self._mad_1_energy = None
        else:
            self._mad_1_energy = float(mad_1_energy)
        if mad_2_energy is None:
            self._mad_2_energy = None
        else:
            self._mad_2_energy = float(mad_2_energy)
        if mad_3_energy is None:
            self._mad_3_energy = None
        else:
            self._mad_3_energy = float(mad_3_energy)
        if mad_4_energy is None:
            self._mad_4_energy = None
        else:
            self._mad_4_energy = float(mad_4_energy)
        self._prefix = str(prefix)
        if overlap is None:
            self._overlap = None
        else:
            self._overlap = float(overlap)
        if osc_start is None:
            self._osc_start = None
        else:
            self._osc_start = float(osc_start)
        self._process_directory = str(process_directory)
        if sum_images is None:
            self._sum_images = None
        else:
            self._sum_images = float(sum_images)
        self._detector_mode = str(detector_mode)
        self._mad_energies = str(mad_energies)
        self._comments = str(comments)
        if osc_range is None:
            self._osc_range = None
        else:
            self._osc_range = float(osc_range)
        if first_image is None:
            self._first_image = None
        else:
            self._first_image = int(first_image)
        self._template = str(template)
        if kappaStart is None:
            self._kappaStart = None
        else:
            self._kappaStart = float(kappaStart)
        self._processing = bool(processing)
        if inverse_beam is None:
            self._inverse_beam = None
        else:
            self._inverse_beam = float(inverse_beam)
        if number_images is None:
            self._number_images = None
        else:
            self._number_images = int(number_images)
        if current_detdistance is None:
            self._current_detdistance = None
        else:
            self._current_detdistance = float(current_detdistance)
        self._residues = str(residues)
        if run_number is None:
            self._run_number = None
        else:
            self._run_number = int(run_number)
        if current_wavelength is None:
            self._current_wavelength = None
        else:
            self._current_wavelength = float(current_wavelength)
        if phiStart is None:
            self._phiStart = None
        else:
            self._phiStart = float(phiStart)
        self._anomalous = bool(anomalous)
        if number_passes is None:
            self._number_passes = None
        else:
            self._number_passes = int(number_passes)
        self._directory = str(directory)
        if current_energy is None:
            self._current_energy = None
        else:
            self._current_energy = float(current_energy)
        if current_osc_start is None:
            self._current_osc_start = None
        else:
            self._current_osc_start = float(current_osc_start)
        self._output_file = str(output_file)
        if transmission is None:
            self._transmission = None
        else:
            self._transmission = float(transmission)
    # Methods and properties for the 'sessionId' attribute
    def getSessionId(self): return self._sessionId
    def setSessionId(self, sessionId):
        if sessionId is None:
            self._sessionId = None
        else:
            self._sessionId = int(sessionId)
    def delSessionId(self): self._sessionId = None
    sessionId = property(getSessionId, setSessionId, delSessionId, "Property for sessionId")
    # Methods and properties for the 'blSampleId' attribute
    def getBlSampleId(self): return self._blSampleId
    def setBlSampleId(self, blSampleId):
        if blSampleId is None:
            self._blSampleId = None
        else:
            self._blSampleId = int(blSampleId)
    def delBlSampleId(self): self._blSampleId = None
    blSampleId = property(getBlSampleId, setBlSampleId, delBlSampleId, "Property for blSampleId")
    # Methods and properties for the 'exposure_time' attribute
    def getExposure_time(self): return self._exposure_time
    def setExposure_time(self, exposure_time):
        if exposure_time is None:
            self._exposure_time = None
        else:
            self._exposure_time = float(exposure_time)
    def delExposure_time(self): self._exposure_time = None
    exposure_time = property(getExposure_time, setExposure_time, delExposure_time, "Property for exposure_time")
    # Methods and properties for the 'resolution' attribute
    def getResolution(self): return self._resolution
    def setResolution(self, resolution):
        if resolution is None:
            self._resolution = None
        else:
            self._resolution = float(resolution)
    def delResolution(self): self._resolution = None
    resolution = property(getResolution, setResolution, delResolution, "Property for resolution")
    # Methods and properties for the 'resolution_at_corner' attribute
    def getResolution_at_corner(self): return self._resolution_at_corner
    def setResolution_at_corner(self, resolution_at_corner):
        if resolution_at_corner is None:
            self._resolution_at_corner = None
        else:
            self._resolution_at_corner = float(resolution_at_corner)
    def delResolution_at_corner(self): self._resolution_at_corner = None
    resolution_at_corner = property(getResolution_at_corner, setResolution_at_corner, delResolution_at_corner, "Property for resolution_at_corner")
    # Methods and properties for the 'x_beam' attribute
    def getX_beam(self): return self._x_beam
    def setX_beam(self, x_beam):
        if x_beam is None:
            self._x_beam = None
        else:
            self._x_beam = float(x_beam)
    def delX_beam(self): self._x_beam = None
    x_beam = property(getX_beam, setX_beam, delX_beam, "Property for x_beam")
    # Methods and properties for the 'y_beam' attribute
    def getY_beam(self): return self._y_beam
    def setY_beam(self, y_beam):
        if y_beam is None:
            self._y_beam = None
        else:
            self._y_beam = float(y_beam)
    def delY_beam(self): self._y_beam = None
    y_beam = property(getY_beam, setY_beam, delY_beam, "Property for y_beam")
    # Methods and properties for the 'beam_size_x' attribute
    def getBeam_size_x(self): return self._beam_size_x
    def setBeam_size_x(self, beam_size_x):
        if beam_size_x is None:
            self._beam_size_x = None
        else:
            self._beam_size_x = float(beam_size_x)
    def delBeam_size_x(self): self._beam_size_x = None
    beam_size_x = property(getBeam_size_x, setBeam_size_x, delBeam_size_x, "Property for beam_size_x")
    # Methods and properties for the 'beam_size_y' attribute
    def getBeam_size_y(self): return self._beam_size_y
    def setBeam_size_y(self, beam_size_y):
        if beam_size_y is None:
            self._beam_size_y = None
        else:
            self._beam_size_y = float(beam_size_y)
    def delBeam_size_y(self): self._beam_size_y = None
    beam_size_y = property(getBeam_size_y, setBeam_size_y, delBeam_size_y, "Property for beam_size_y")
    # Methods and properties for the 'mad_1_energy' attribute
    def getMad_1_energy(self): return self._mad_1_energy
    def setMad_1_energy(self, mad_1_energy):
        if mad_1_energy is None:
            self._mad_1_energy = None
        else:
            self._mad_1_energy = float(mad_1_energy)
    def delMad_1_energy(self): self._mad_1_energy = None
    mad_1_energy = property(getMad_1_energy, setMad_1_energy, delMad_1_energy, "Property for mad_1_energy")
    # Methods and properties for the 'mad_2_energy' attribute
    def getMad_2_energy(self): return self._mad_2_energy
    def setMad_2_energy(self, mad_2_energy):
        if mad_2_energy is None:
            self._mad_2_energy = None
        else:
            self._mad_2_energy = float(mad_2_energy)
    def delMad_2_energy(self): self._mad_2_energy = None
    mad_2_energy = property(getMad_2_energy, setMad_2_energy, delMad_2_energy, "Property for mad_2_energy")
    # Methods and properties for the 'mad_3_energy' attribute
    def getMad_3_energy(self): return self._mad_3_energy
    def setMad_3_energy(self, mad_3_energy):
        if mad_3_energy is None:
            self._mad_3_energy = None
        else:
            self._mad_3_energy = float(mad_3_energy)
    def delMad_3_energy(self): self._mad_3_energy = None
    mad_3_energy = property(getMad_3_energy, setMad_3_energy, delMad_3_energy, "Property for mad_3_energy")
    # Methods and properties for the 'mad_4_energy' attribute
    def getMad_4_energy(self): return self._mad_4_energy
    def setMad_4_energy(self, mad_4_energy):
        if mad_4_energy is None:
            self._mad_4_energy = None
        else:
            self._mad_4_energy = float(mad_4_energy)
    def delMad_4_energy(self): self._mad_4_energy = None
    mad_4_energy = property(getMad_4_energy, setMad_4_energy, delMad_4_energy, "Property for mad_4_energy")
    # Methods and properties for the 'prefix' attribute
    def getPrefix(self): return self._prefix
    def setPrefix(self, prefix):
        self._prefix = str(prefix)
    def delPrefix(self): self._prefix = None
    prefix = property(getPrefix, setPrefix, delPrefix, "Property for prefix")
    # Methods and properties for the 'overlap' attribute
    def getOverlap(self): return self._overlap
    def setOverlap(self, overlap):
        if overlap is None:
            self._overlap = None
        else:
            self._overlap = float(overlap)
    def delOverlap(self): self._overlap = None
    overlap = property(getOverlap, setOverlap, delOverlap, "Property for overlap")
    # Methods and properties for the 'osc_start' attribute
    def getOsc_start(self): return self._osc_start
    def setOsc_start(self, osc_start):
        if osc_start is None:
            self._osc_start = None
        else:
            self._osc_start = float(osc_start)
    def delOsc_start(self): self._osc_start = None
    osc_start = property(getOsc_start, setOsc_start, delOsc_start, "Property for osc_start")
    # Methods and properties for the 'process_directory' attribute
    def getProcess_directory(self): return self._process_directory
    def setProcess_directory(self, process_directory):
        self._process_directory = str(process_directory)
    def delProcess_directory(self): self._process_directory = None
    process_directory = property(getProcess_directory, setProcess_directory, delProcess_directory, "Property for process_directory")
    # Methods and properties for the 'sum_images' attribute
    def getSum_images(self): return self._sum_images
    def setSum_images(self, sum_images):
        if sum_images is None:
            self._sum_images = None
        else:
            self._sum_images = float(sum_images)
    def delSum_images(self): self._sum_images = None
    sum_images = property(getSum_images, setSum_images, delSum_images, "Property for sum_images")
    # Methods and properties for the 'detector_mode' attribute
    def getDetector_mode(self): return self._detector_mode
    def setDetector_mode(self, detector_mode):
        self._detector_mode = str(detector_mode)
    def delDetector_mode(self): self._detector_mode = None
    detector_mode = property(getDetector_mode, setDetector_mode, delDetector_mode, "Property for detector_mode")
    # Methods and properties for the 'mad_energies' attribute
    def getMad_energies(self): return self._mad_energies
    def setMad_energies(self, mad_energies):
        self._mad_energies = str(mad_energies)
    def delMad_energies(self): self._mad_energies = None
    mad_energies = property(getMad_energies, setMad_energies, delMad_energies, "Property for mad_energies")
    # Methods and properties for the 'comments' attribute
    def getComments(self): return self._comments
    def setComments(self, comments):
        self._comments = str(comments)
    def delComments(self): self._comments = None
    comments = property(getComments, setComments, delComments, "Property for comments")
    # Methods and properties for the 'osc_range' attribute
    def getOsc_range(self): return self._osc_range
    def setOsc_range(self, osc_range):
        if osc_range is None:
            self._osc_range = None
        else:
            self._osc_range = float(osc_range)
    def delOsc_range(self): self._osc_range = None
    osc_range = property(getOsc_range, setOsc_range, delOsc_range, "Property for osc_range")
    # Methods and properties for the 'first_image' attribute
    def getFirst_image(self): return self._first_image
    def setFirst_image(self, first_image):
        if first_image is None:
            self._first_image = None
        else:
            self._first_image = int(first_image)
    def delFirst_image(self): self._first_image = None
    first_image = property(getFirst_image, setFirst_image, delFirst_image, "Property for first_image")
    # Methods and properties for the 'template' attribute
    def getTemplate(self): return self._template
    def setTemplate(self, template):
        self._template = str(template)
    def delTemplate(self): self._template = None
    template = property(getTemplate, setTemplate, delTemplate, "Property for template")
    # Methods and properties for the 'kappaStart' attribute
    def getKappaStart(self): return self._kappaStart
    def setKappaStart(self, kappaStart):
        if kappaStart is None:
            self._kappaStart = None
        else:
            self._kappaStart = float(kappaStart)
    def delKappaStart(self): self._kappaStart = None
    kappaStart = property(getKappaStart, setKappaStart, delKappaStart, "Property for kappaStart")
    # Methods and properties for the 'processing' attribute
    def getProcessing(self): return self._processing
    def setProcessing(self, processing):
        self._processing = bool(processing)
    def delProcessing(self): self._processing = None
    processing = property(getProcessing, setProcessing, delProcessing, "Property for processing")
    # Methods and properties for the 'inverse_beam' attribute
    def getInverse_beam(self): return self._inverse_beam
    def setInverse_beam(self, inverse_beam):
        if inverse_beam is None:
            self._inverse_beam = None
        else:
            self._inverse_beam = float(inverse_beam)
    def delInverse_beam(self): self._inverse_beam = None
    inverse_beam = property(getInverse_beam, setInverse_beam, delInverse_beam, "Property for inverse_beam")
    # Methods and properties for the 'number_images' attribute
    def getNumber_images(self): return self._number_images
    def setNumber_images(self, number_images):
        if number_images is None:
            self._number_images = None
        else:
            self._number_images = int(number_images)
    def delNumber_images(self): self._number_images = None
    number_images = property(getNumber_images, setNumber_images, delNumber_images, "Property for number_images")
    # Methods and properties for the 'current_detdistance' attribute
    def getCurrent_detdistance(self): return self._current_detdistance
    def setCurrent_detdistance(self, current_detdistance):
        if current_detdistance is None:
            self._current_detdistance = None
        else:
            self._current_detdistance = float(current_detdistance)
    def delCurrent_detdistance(self): self._current_detdistance = None
    current_detdistance = property(getCurrent_detdistance, setCurrent_detdistance, delCurrent_detdistance, "Property for current_detdistance")
    # Methods and properties for the 'residues' attribute
    def getResidues(self): return self._residues
    def setResidues(self, residues):
        self._residues = str(residues)
    def delResidues(self): self._residues = None
    residues = property(getResidues, setResidues, delResidues, "Property for residues")
    # Methods and properties for the 'run_number' attribute
    def getRun_number(self): return self._run_number
    def setRun_number(self, run_number):
        if run_number is None:
            self._run_number = None
        else:
            self._run_number = int(run_number)
    def delRun_number(self): self._run_number = None
    run_number = property(getRun_number, setRun_number, delRun_number, "Property for run_number")
    # Methods and properties for the 'current_wavelength' attribute
    def getCurrent_wavelength(self): return self._current_wavelength
    def setCurrent_wavelength(self, current_wavelength):
        if current_wavelength is None:
            self._current_wavelength = None
        else:
            self._current_wavelength = float(current_wavelength)
    def delCurrent_wavelength(self): self._current_wavelength = None
    current_wavelength = property(getCurrent_wavelength, setCurrent_wavelength, delCurrent_wavelength, "Property for current_wavelength")
    # Methods and properties for the 'phiStart' attribute
    def getPhiStart(self): return self._phiStart
    def setPhiStart(self, phiStart):
        if phiStart is None:
            self._phiStart = None
        else:
            self._phiStart = float(phiStart)
    def delPhiStart(self): self._phiStart = None
    phiStart = property(getPhiStart, setPhiStart, delPhiStart, "Property for phiStart")
    # Methods and properties for the 'anomalous' attribute
    def getAnomalous(self): return self._anomalous
    def setAnomalous(self, anomalous):
        self._anomalous = bool(anomalous)
    def delAnomalous(self): self._anomalous = None
    anomalous = property(getAnomalous, setAnomalous, delAnomalous, "Property for anomalous")
    # Methods and properties for the 'number_passes' attribute
    def getNumber_passes(self): return self._number_passes
    def setNumber_passes(self, number_passes):
        if number_passes is None:
            self._number_passes = None
        else:
            self._number_passes = int(number_passes)
    def delNumber_passes(self): self._number_passes = None
    number_passes = property(getNumber_passes, setNumber_passes, delNumber_passes, "Property for number_passes")
    # Methods and properties for the 'directory' attribute
    def getDirectory(self): return self._directory
    def setDirectory(self, directory):
        self._directory = str(directory)
    def delDirectory(self): self._directory = None
    directory = property(getDirectory, setDirectory, delDirectory, "Property for directory")
    # Methods and properties for the 'current_energy' attribute
    def getCurrent_energy(self): return self._current_energy
    def setCurrent_energy(self, current_energy):
        if current_energy is None:
            self._current_energy = None
        else:
            self._current_energy = float(current_energy)
    def delCurrent_energy(self): self._current_energy = None
    current_energy = property(getCurrent_energy, setCurrent_energy, delCurrent_energy, "Property for current_energy")
    # Methods and properties for the 'current_osc_start' attribute
    def getCurrent_osc_start(self): return self._current_osc_start
    def setCurrent_osc_start(self, current_osc_start):
        if current_osc_start is None:
            self._current_osc_start = None
        else:
            self._current_osc_start = float(current_osc_start)
    def delCurrent_osc_start(self): self._current_osc_start = None
    current_osc_start = property(getCurrent_osc_start, setCurrent_osc_start, delCurrent_osc_start, "Property for current_osc_start")
    # Methods and properties for the 'output_file' attribute
    def getOutput_file(self): return self._output_file
    def setOutput_file(self, output_file):
        self._output_file = str(output_file)
    def delOutput_file(self): self._output_file = None
    output_file = property(getOutput_file, setOutput_file, delOutput_file, "Property for output_file")
    # Methods and properties for the 'transmission' attribute
    def getTransmission(self): return self._transmission
    def setTransmission(self, transmission):
        if transmission is None:
            self._transmission = None
        else:
            self._transmission = float(transmission)
    def delTransmission(self): self._transmission = None
    transmission = property(getTransmission, setTransmission, delTransmission, "Property for transmission")
    def export(self, outfile, level, name_='XSDataMXCuBEParameters'):
        showIndent(outfile, level)
        outfile.write(unicode('<%s>\n' % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode('</%s>\n' % name_))
    def exportChildren(self, outfile, level, name_='XSDataMXCuBEParameters'):
        XSData.exportChildren(self, outfile, level, name_)
        if self._sessionId is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<sessionId>%d</sessionId>\n' % self._sessionId))
        else:
            warnEmptyAttribute("sessionId", "integer")
        if self._blSampleId is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<blSampleId>%d</blSampleId>\n' % self._blSampleId))
        else:
            warnEmptyAttribute("blSampleId", "integer")
        if self._exposure_time is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<exposure_time>%e</exposure_time>\n' % self._exposure_time))
        else:
            warnEmptyAttribute("exposure_time", "float")
        if self._resolution is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<resolution>%e</resolution>\n' % self._resolution))
        else:
            warnEmptyAttribute("resolution", "float")
        if self._resolution_at_corner is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<resolution_at_corner>%e</resolution_at_corner>\n' % self._resolution_at_corner))
        else:
            warnEmptyAttribute("resolution_at_corner", "float")
        if self._x_beam is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<x_beam>%e</x_beam>\n' % self._x_beam))
        else:
            warnEmptyAttribute("x_beam", "float")
        if self._y_beam is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<y_beam>%e</y_beam>\n' % self._y_beam))
        else:
            warnEmptyAttribute("y_beam", "float")
        if self._beam_size_x is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<beam_size_x>%e</beam_size_x>\n' % self._beam_size_x))
        else:
            warnEmptyAttribute("beam_size_x", "float")
        if self._beam_size_y is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<beam_size_y>%e</beam_size_y>\n' % self._beam_size_y))
        else:
            warnEmptyAttribute("beam_size_y", "float")
        if self._mad_1_energy is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<mad_1_energy>%e</mad_1_energy>\n' % self._mad_1_energy))
        else:
            warnEmptyAttribute("mad_1_energy", "float")
        if self._mad_2_energy is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<mad_2_energy>%e</mad_2_energy>\n' % self._mad_2_energy))
        else:
            warnEmptyAttribute("mad_2_energy", "float")
        if self._mad_3_energy is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<mad_3_energy>%e</mad_3_energy>\n' % self._mad_3_energy))
        else:
            warnEmptyAttribute("mad_3_energy", "float")
        if self._mad_4_energy is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<mad_4_energy>%e</mad_4_energy>\n' % self._mad_4_energy))
        else:
            warnEmptyAttribute("mad_4_energy", "float")
        if self._prefix is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<prefix>%s</prefix>\n' % self._prefix))
        else:
            warnEmptyAttribute("prefix", "string")
        if self._overlap is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<overlap>%e</overlap>\n' % self._overlap))
        else:
            warnEmptyAttribute("overlap", "float")
        if self._osc_start is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<osc_start>%e</osc_start>\n' % self._osc_start))
        else:
            warnEmptyAttribute("osc_start", "float")
        if self._process_directory is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<process_directory>%s</process_directory>\n' % self._process_directory))
        else:
            warnEmptyAttribute("process_directory", "string")
        if self._sum_images is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<sum_images>%e</sum_images>\n' % self._sum_images))
        else:
            warnEmptyAttribute("sum_images", "float")
        if self._detector_mode is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<detector_mode>%s</detector_mode>\n' % self._detector_mode))
        else:
            warnEmptyAttribute("detector_mode", "string")
        if self._mad_energies is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<mad_energies>%s</mad_energies>\n' % self._mad_energies))
        else:
            warnEmptyAttribute("mad_energies", "string")
        if self._comments is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<comments>%s</comments>\n' % self._comments))
        else:
            warnEmptyAttribute("comments", "string")
        if self._osc_range is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<osc_range>%e</osc_range>\n' % self._osc_range))
        else:
            warnEmptyAttribute("osc_range", "float")
        if self._first_image is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<first_image>%d</first_image>\n' % self._first_image))
        else:
            warnEmptyAttribute("first_image", "integer")
        if self._template is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<template>%s</template>\n' % self._template))
        else:
            warnEmptyAttribute("template", "string")
        if self._kappaStart is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<kappaStart>%e</kappaStart>\n' % self._kappaStart))
        else:
            warnEmptyAttribute("kappaStart", "float")
        if self._processing is not None:
            showIndent(outfile, level)
            if self._processing:
                outfile.write(unicode('<processing>true</processing>\n'))
            else:
                outfile.write(unicode('<processing>false</processing>\n'))
        else:
            warnEmptyAttribute("processing", "boolean")
        if self._inverse_beam is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<inverse_beam>%e</inverse_beam>\n' % self._inverse_beam))
        else:
            warnEmptyAttribute("inverse_beam", "float")
        if self._number_images is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<number_images>%d</number_images>\n' % self._number_images))
        else:
            warnEmptyAttribute("number_images", "integer")
        if self._current_detdistance is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<current_detdistance>%e</current_detdistance>\n' % self._current_detdistance))
        else:
            warnEmptyAttribute("current_detdistance", "float")
        if self._residues is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<residues>%s</residues>\n' % self._residues))
        else:
            warnEmptyAttribute("residues", "string")
        if self._run_number is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<run_number>%d</run_number>\n' % self._run_number))
        else:
            warnEmptyAttribute("run_number", "integer")
        if self._current_wavelength is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<current_wavelength>%e</current_wavelength>\n' % self._current_wavelength))
        else:
            warnEmptyAttribute("current_wavelength", "float")
        if self._phiStart is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<phiStart>%e</phiStart>\n' % self._phiStart))
        else:
            warnEmptyAttribute("phiStart", "float")
        if self._anomalous is not None:
            showIndent(outfile, level)
            if self._anomalous:
                outfile.write(unicode('<anomalous>true</anomalous>\n'))
            else:
                outfile.write(unicode('<anomalous>false</anomalous>\n'))
        else:
            warnEmptyAttribute("anomalous", "boolean")
        if self._number_passes is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<number_passes>%d</number_passes>\n' % self._number_passes))
        else:
            warnEmptyAttribute("number_passes", "integer")
        if self._directory is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<directory>%s</directory>\n' % self._directory))
        else:
            warnEmptyAttribute("directory", "string")
        if self._current_energy is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<current_energy>%e</current_energy>\n' % self._current_energy))
        else:
            warnEmptyAttribute("current_energy", "float")
        if self._current_osc_start is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<current_osc_start>%e</current_osc_start>\n' % self._current_osc_start))
        else:
            warnEmptyAttribute("current_osc_start", "float")
        if self._output_file is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<output_file>%s</output_file>\n' % self._output_file))
        else:
            warnEmptyAttribute("output_file", "string")
        if self._transmission is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<transmission>%e</transmission>\n' % self._transmission))
        else:
            warnEmptyAttribute("transmission", "float")
    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sessionId':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError('requires integer -- %s' % child_.toxml())
                self._sessionId = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'blSampleId':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError('requires integer -- %s' % child_.toxml())
                self._blSampleId = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'exposure_time':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._exposure_time = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'resolution':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._resolution = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'resolution_at_corner':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._resolution_at_corner = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'x_beam':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._x_beam = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'y_beam':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._y_beam = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'beam_size_x':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._beam_size_x = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'beam_size_y':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._beam_size_y = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'mad_1_energy':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._mad_1_energy = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'mad_2_energy':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._mad_2_energy = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'mad_3_energy':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._mad_3_energy = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'mad_4_energy':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._mad_4_energy = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'prefix':
            value_ = ''
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._prefix = value_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'overlap':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._overlap = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'osc_start':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._osc_start = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'process_directory':
            value_ = ''
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._process_directory = value_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sum_images':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._sum_images = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'detector_mode':
            value_ = ''
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._detector_mode = value_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'mad_energies':
            value_ = ''
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._mad_energies = value_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'comments':
            value_ = ''
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._comments = value_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'osc_range':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._osc_range = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'first_image':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError('requires integer -- %s' % child_.toxml())
                self._first_image = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'template':
            value_ = ''
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._template = value_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'kappaStart':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._kappaStart = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'processing':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                if sval_ in ('True', 'true', '1'):
                    ival_ = True
                elif sval_ in ('False', 'false', '0'):
                    ival_ = False
                else:
                    raise ValueError('requires boolean -- %s' % child_.toxml())
                self._processing = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'inverse_beam':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._inverse_beam = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'number_images':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError('requires integer -- %s' % child_.toxml())
                self._number_images = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'current_detdistance':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._current_detdistance = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'residues':
            value_ = ''
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._residues = value_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'run_number':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError('requires integer -- %s' % child_.toxml())
                self._run_number = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'current_wavelength':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._current_wavelength = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'phiStart':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._phiStart = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'anomalous':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                if sval_ in ('True', 'true', '1'):
                    ival_ = True
                elif sval_ in ('False', 'false', '0'):
                    ival_ = False
                else:
                    raise ValueError('requires boolean -- %s' % child_.toxml())
                self._anomalous = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'number_passes':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    ival_ = int(sval_)
                except ValueError:
                    raise ValueError('requires integer -- %s' % child_.toxml())
                self._number_passes = ival_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'directory':
            value_ = ''
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._directory = value_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'current_energy':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._current_energy = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'current_osc_start':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._current_osc_start = fval_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'output_file':
            value_ = ''
            for text__content_ in child_.childNodes:
                if text__content_.nodeValue is not None:
                    value_ += text__content_.nodeValue
            self._output_file = value_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'transmission':
            if child_.firstChild:
                sval_ = child_.firstChild.nodeValue
                try:
                    fval_ = float(sval_)
                except ValueError:
                    raise ValueError('requires float (or double) -- %s' % child_.toxml())
                self._transmission = fval_
        XSData.buildChildren(self, child_, nodeName_)
    #Method for marshalling an object
    def marshal( self ):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export( oStreamString, 0, name_="XSDataMXCuBEParameters" )
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML
    #Only to export the entire XML tree to a file stream on disk
    def exportToFile( self, _outfileName ):
        outfile = open( _outfileName, "w" )
        outfile.write(unicode('<?xml version=\"1.0\" ?>\n'))
        self.export( outfile, 0, name_='XSDataMXCuBEParameters' )
        outfile.close()
    #Deprecated method, replaced by exportToFile
    def outputFile( self, _outfileName ):
        print("WARNING: Method outputFile in class XSDataMXCuBEParameters is deprecated, please use instead exportToFile!")
        self.exportToFile(_outfileName)
    #Method for making a copy in a new instance
    def copy( self ):
        return XSDataMXCuBEParameters.parseString(self.marshal())
    #Static method for parsing a string
    def parseString( _inString ):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataMXCuBEParameters()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export( oStreamString, 0, name_="XSDataMXCuBEParameters" )
        oStreamString.close()
        return rootObj
    parseString = staticmethod( parseString )
    #Static method for parsing a file
    def parseFile( _inFilePath ):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataMXCuBEParameters()
        rootObj.build(rootNode)
        return rootObj
    parseFile = staticmethod( parseFile )
# end class XSDataMXCuBEParameters


class XSDataInputMXCuBE(XSDataInput):
    def __init__(self, configuration=None, token=None, htmlDir=None, dataSet=None, sample=None, outputFileDirectory=None, experimentalCondition=None, diffractionPlan=None, dataCollectionId=None, characterisationInput=None):
        XSDataInput.__init__(self, configuration)
        if characterisationInput is None:
            self._characterisationInput = None
        elif characterisationInput.__class__.__name__ == "XSDataInputCharacterisation":
            self._characterisationInput = characterisationInput
        else:
            strMessage = "ERROR! XSDataInputMXCuBE constructor argument 'characterisationInput' is not XSDataInputCharacterisation but %s" % self._characterisationInput.__class__.__name__
            raise BaseException(strMessage)
        if dataCollectionId is None:
            self._dataCollectionId = None
        elif dataCollectionId.__class__.__name__ == "XSDataInteger":
            self._dataCollectionId = dataCollectionId
        else:
            strMessage = "ERROR! XSDataInputMXCuBE constructor argument 'dataCollectionId' is not XSDataInteger but %s" % self._dataCollectionId.__class__.__name__
            raise BaseException(strMessage)
        if diffractionPlan is None:
            self._diffractionPlan = None
        elif diffractionPlan.__class__.__name__ == "XSDataDiffractionPlan":
            self._diffractionPlan = diffractionPlan
        else:
            strMessage = "ERROR! XSDataInputMXCuBE constructor argument 'diffractionPlan' is not XSDataDiffractionPlan but %s" % self._diffractionPlan.__class__.__name__
            raise BaseException(strMessage)
        if experimentalCondition is None:
            self._experimentalCondition = None
        elif experimentalCondition.__class__.__name__ == "XSDataExperimentalCondition":
            self._experimentalCondition = experimentalCondition
        else:
            strMessage = "ERROR! XSDataInputMXCuBE constructor argument 'experimentalCondition' is not XSDataExperimentalCondition but %s" % self._experimentalCondition.__class__.__name__
            raise BaseException(strMessage)
        if outputFileDirectory is None:
            self._outputFileDirectory = None
        elif outputFileDirectory.__class__.__name__ == "XSDataFile":
            self._outputFileDirectory = outputFileDirectory
        else:
            strMessage = "ERROR! XSDataInputMXCuBE constructor argument 'outputFileDirectory' is not XSDataFile but %s" % self._outputFileDirectory.__class__.__name__
            raise BaseException(strMessage)
        if sample is None:
            self._sample = None
        elif sample.__class__.__name__ == "XSDataSampleCrystalMM":
            self._sample = sample
        else:
            strMessage = "ERROR! XSDataInputMXCuBE constructor argument 'sample' is not XSDataSampleCrystalMM but %s" % self._sample.__class__.__name__
            raise BaseException(strMessage)
        if dataSet is None:
            self._dataSet = []
        elif dataSet.__class__.__name__ == "list":
            self._dataSet = dataSet
        else:
            strMessage = "ERROR! XSDataInputMXCuBE constructor argument 'dataSet' is not list but %s" % self._dataSet.__class__.__name__
            raise BaseException(strMessage)
        if htmlDir is None:
            self._htmlDir = None
        elif htmlDir.__class__.__name__ == "XSDataFile":
            self._htmlDir = htmlDir
        else:
            strMessage = "ERROR! XSDataInputMXCuBE constructor argument 'htmlDir' is not XSDataFile but %s" % self._htmlDir.__class__.__name__
            raise BaseException(strMessage)
        if token is None:
            self._token = None
        elif token.__class__.__name__ == "XSDataString":
            self._token = token
        else:
            strMessage = "ERROR! XSDataInputMXCuBE constructor argument 'token' is not XSDataString but %s" % self._token.__class__.__name__
            raise BaseException(strMessage)
    # Methods and properties for the 'characterisationInput' attribute
    def getCharacterisationInput(self): return self._characterisationInput
    def setCharacterisationInput(self, characterisationInput):
        if characterisationInput is None:
            self._characterisationInput = None
        elif characterisationInput.__class__.__name__ == "XSDataInputCharacterisation":
            self._characterisationInput = characterisationInput
        else:
            strMessage = "ERROR! XSDataInputMXCuBE.setCharacterisationInput argument is not XSDataInputCharacterisation but %s" % characterisationInput.__class__.__name__
            raise BaseException(strMessage)
    def delCharacterisationInput(self): self._characterisationInput = None
    characterisationInput = property(getCharacterisationInput, setCharacterisationInput, delCharacterisationInput, "Property for characterisationInput")
    # Methods and properties for the 'dataCollectionId' attribute
    def getDataCollectionId(self): return self._dataCollectionId
    def setDataCollectionId(self, dataCollectionId):
        if dataCollectionId is None:
            self._dataCollectionId = None
        elif dataCollectionId.__class__.__name__ == "XSDataInteger":
            self._dataCollectionId = dataCollectionId
        else:
            strMessage = "ERROR! XSDataInputMXCuBE.setDataCollectionId argument is not XSDataInteger but %s" % dataCollectionId.__class__.__name__
            raise BaseException(strMessage)
    def delDataCollectionId(self): self._dataCollectionId = None
    dataCollectionId = property(getDataCollectionId, setDataCollectionId, delDataCollectionId, "Property for dataCollectionId")
    # Methods and properties for the 'diffractionPlan' attribute
    def getDiffractionPlan(self): return self._diffractionPlan
    def setDiffractionPlan(self, diffractionPlan):
        if diffractionPlan is None:
            self._diffractionPlan = None
        elif diffractionPlan.__class__.__name__ == "XSDataDiffractionPlan":
            self._diffractionPlan = diffractionPlan
        else:
            strMessage = "ERROR! XSDataInputMXCuBE.setDiffractionPlan argument is not XSDataDiffractionPlan but %s" % diffractionPlan.__class__.__name__
            raise BaseException(strMessage)
    def delDiffractionPlan(self): self._diffractionPlan = None
    diffractionPlan = property(getDiffractionPlan, setDiffractionPlan, delDiffractionPlan, "Property for diffractionPlan")
    # Methods and properties for the 'experimentalCondition' attribute
    def getExperimentalCondition(self): return self._experimentalCondition
    def setExperimentalCondition(self, experimentalCondition):
        if experimentalCondition is None:
            self._experimentalCondition = None
        elif experimentalCondition.__class__.__name__ == "XSDataExperimentalCondition":
            self._experimentalCondition = experimentalCondition
        else:
            strMessage = "ERROR! XSDataInputMXCuBE.setExperimentalCondition argument is not XSDataExperimentalCondition but %s" % experimentalCondition.__class__.__name__
            raise BaseException(strMessage)
    def delExperimentalCondition(self): self._experimentalCondition = None
    experimentalCondition = property(getExperimentalCondition, setExperimentalCondition, delExperimentalCondition, "Property for experimentalCondition")
    # Methods and properties for the 'outputFileDirectory' attribute
    def getOutputFileDirectory(self): return self._outputFileDirectory
    def setOutputFileDirectory(self, outputFileDirectory):
        if outputFileDirectory is None:
            self._outputFileDirectory = None
        elif outputFileDirectory.__class__.__name__ == "XSDataFile":
            self._outputFileDirectory = outputFileDirectory
        else:
            strMessage = "ERROR! XSDataInputMXCuBE.setOutputFileDirectory argument is not XSDataFile but %s" % outputFileDirectory.__class__.__name__
            raise BaseException(strMessage)
    def delOutputFileDirectory(self): self._outputFileDirectory = None
    outputFileDirectory = property(getOutputFileDirectory, setOutputFileDirectory, delOutputFileDirectory, "Property for outputFileDirectory")
    # Methods and properties for the 'sample' attribute
    def getSample(self): return self._sample
    def setSample(self, sample):
        if sample is None:
            self._sample = None
        elif sample.__class__.__name__ == "XSDataSampleCrystalMM":
            self._sample = sample
        else:
            strMessage = "ERROR! XSDataInputMXCuBE.setSample argument is not XSDataSampleCrystalMM but %s" % sample.__class__.__name__
            raise BaseException(strMessage)
    def delSample(self): self._sample = None
    sample = property(getSample, setSample, delSample, "Property for sample")
    # Methods and properties for the 'dataSet' attribute
    def getDataSet(self): return self._dataSet
    def setDataSet(self, dataSet):
        if dataSet is None:
            self._dataSet = []
        elif dataSet.__class__.__name__ == "list":
            self._dataSet = dataSet
        else:
            strMessage = "ERROR! XSDataInputMXCuBE.setDataSet argument is not list but %s" % dataSet.__class__.__name__
            raise BaseException(strMessage)
    def delDataSet(self): self._dataSet = None
    dataSet = property(getDataSet, setDataSet, delDataSet, "Property for dataSet")
    def addDataSet(self, value):
        if value is None:
            strMessage = "ERROR! XSDataInputMXCuBE.addDataSet argument is None"
            raise BaseException(strMessage)            
        elif value.__class__.__name__ == "XSDataMXCuBEDataSet":
            self._dataSet.append(value)
        else:
            strMessage = "ERROR! XSDataInputMXCuBE.addDataSet argument is not XSDataMXCuBEDataSet but %s" % value.__class__.__name__
            raise BaseException(strMessage)
    def insertDataSet(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataInputMXCuBE.insertDataSet argument 'index' is None"
            raise BaseException(strMessage)            
        if value is None:
            strMessage = "ERROR! XSDataInputMXCuBE.insertDataSet argument 'value' is None"
            raise BaseException(strMessage)            
        elif value.__class__.__name__ == "XSDataMXCuBEDataSet":
            self._dataSet[index] = value
        else:
            strMessage = "ERROR! XSDataInputMXCuBE.addDataSet argument is not XSDataMXCuBEDataSet but %s" % value.__class__.__name__
            raise BaseException(strMessage)
    # Methods and properties for the 'htmlDir' attribute
    def getHtmlDir(self): return self._htmlDir
    def setHtmlDir(self, htmlDir):
        if htmlDir is None:
            self._htmlDir = None
        elif htmlDir.__class__.__name__ == "XSDataFile":
            self._htmlDir = htmlDir
        else:
            strMessage = "ERROR! XSDataInputMXCuBE.setHtmlDir argument is not XSDataFile but %s" % htmlDir.__class__.__name__
            raise BaseException(strMessage)
    def delHtmlDir(self): self._htmlDir = None
    htmlDir = property(getHtmlDir, setHtmlDir, delHtmlDir, "Property for htmlDir")
    # Methods and properties for the 'token' attribute
    def getToken(self): return self._token
    def setToken(self, token):
        if token is None:
            self._token = None
        elif token.__class__.__name__ == "XSDataString":
            self._token = token
        else:
            strMessage = "ERROR! XSDataInputMXCuBE.setToken argument is not XSDataString but %s" % token.__class__.__name__
            raise BaseException(strMessage)
    def delToken(self): self._token = None
    token = property(getToken, setToken, delToken, "Property for token")
    def export(self, outfile, level, name_='XSDataInputMXCuBE'):
        showIndent(outfile, level)
        outfile.write(unicode('<%s>\n' % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode('</%s>\n' % name_))
    def exportChildren(self, outfile, level, name_='XSDataInputMXCuBE'):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._characterisationInput is not None:
            self.characterisationInput.export(outfile, level, name_='characterisationInput')
        if self._dataCollectionId is not None:
            self.dataCollectionId.export(outfile, level, name_='dataCollectionId')
        if self._diffractionPlan is not None:
            self.diffractionPlan.export(outfile, level, name_='diffractionPlan')
        if self._experimentalCondition is not None:
            self.experimentalCondition.export(outfile, level, name_='experimentalCondition')
        if self._outputFileDirectory is not None:
            self.outputFileDirectory.export(outfile, level, name_='outputFileDirectory')
        if self._sample is not None:
            self.sample.export(outfile, level, name_='sample')
        for dataSet_ in self.getDataSet():
            dataSet_.export(outfile, level, name_='dataSet')
        if self._htmlDir is not None:
            self.htmlDir.export(outfile, level, name_='htmlDir')
        if self._token is not None:
            self.token.export(outfile, level, name_='token')
    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'characterisationInput':
            obj_ = XSDataInputCharacterisation()
            obj_.build(child_)
            self.setCharacterisationInput(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'dataCollectionId':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setDataCollectionId(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'diffractionPlan':
            obj_ = XSDataDiffractionPlan()
            obj_.build(child_)
            self.setDiffractionPlan(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'experimentalCondition':
            obj_ = XSDataExperimentalCondition()
            obj_.build(child_)
            self.setExperimentalCondition(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'outputFileDirectory':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setOutputFileDirectory(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sample':
            obj_ = XSDataSampleCrystalMM()
            obj_.build(child_)
            self.setSample(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'dataSet':
            obj_ = XSDataMXCuBEDataSet()
            obj_.build(child_)
            self.dataSet.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'htmlDir':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setHtmlDir(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'token':
            obj_ = XSDataString()
            obj_.build(child_)
            self.setToken(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)
    #Method for marshalling an object
    def marshal( self ):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export( oStreamString, 0, name_="XSDataInputMXCuBE" )
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML
    #Only to export the entire XML tree to a file stream on disk
    def exportToFile( self, _outfileName ):
        outfile = open( _outfileName, "w" )
        outfile.write(unicode('<?xml version=\"1.0\" ?>\n'))
        self.export( outfile, 0, name_='XSDataInputMXCuBE' )
        outfile.close()
    #Deprecated method, replaced by exportToFile
    def outputFile( self, _outfileName ):
        print("WARNING: Method outputFile in class XSDataInputMXCuBE is deprecated, please use instead exportToFile!")
        self.exportToFile(_outfileName)
    #Method for making a copy in a new instance
    def copy( self ):
        return XSDataInputMXCuBE.parseString(self.marshal())
    #Static method for parsing a string
    def parseString( _inString ):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputMXCuBE()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export( oStreamString, 0, name_="XSDataInputMXCuBE" )
        oStreamString.close()
        return rootObj
    parseString = staticmethod( parseString )
    #Static method for parsing a file
    def parseFile( _inFilePath ):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputMXCuBE()
        rootObj.build(rootNode)
        return rootObj
    parseFile = staticmethod( parseFile )
# end class XSDataInputMXCuBE


class XSDataResultMXCuBE(XSDataResult):
    def __init__(self, status=None, screeningId=None, htmlPage=None, outputFileDictionary=None, listOfOutputFiles=None, collectionPlan=None, characterisationResult=None, characterisationExecutiveSummary=None):
        XSDataResult.__init__(self, status)
        if characterisationExecutiveSummary is None:
            self._characterisationExecutiveSummary = None
        elif characterisationExecutiveSummary.__class__.__name__ == "XSDataString":
            self._characterisationExecutiveSummary = characterisationExecutiveSummary
        else:
            strMessage = "ERROR! XSDataResultMXCuBE constructor argument 'characterisationExecutiveSummary' is not XSDataString but %s" % self._characterisationExecutiveSummary.__class__.__name__
            raise BaseException(strMessage)
        if characterisationResult is None:
            self._characterisationResult = None
        elif characterisationResult.__class__.__name__ == "XSDataResultCharacterisation":
            self._characterisationResult = characterisationResult
        else:
            strMessage = "ERROR! XSDataResultMXCuBE constructor argument 'characterisationResult' is not XSDataResultCharacterisation but %s" % self._characterisationResult.__class__.__name__
            raise BaseException(strMessage)
        if collectionPlan is None:
            self._collectionPlan = []
        elif collectionPlan.__class__.__name__ == "list":
            self._collectionPlan = collectionPlan
        else:
            strMessage = "ERROR! XSDataResultMXCuBE constructor argument 'collectionPlan' is not list but %s" % self._collectionPlan.__class__.__name__
            raise BaseException(strMessage)
        if listOfOutputFiles is None:
            self._listOfOutputFiles = None
        elif listOfOutputFiles.__class__.__name__ == "XSDataString":
            self._listOfOutputFiles = listOfOutputFiles
        else:
            strMessage = "ERROR! XSDataResultMXCuBE constructor argument 'listOfOutputFiles' is not XSDataString but %s" % self._listOfOutputFiles.__class__.__name__
            raise BaseException(strMessage)
        if outputFileDictionary is None:
            self._outputFileDictionary = None
        elif outputFileDictionary.__class__.__name__ == "XSDataDictionary":
            self._outputFileDictionary = outputFileDictionary
        else:
            strMessage = "ERROR! XSDataResultMXCuBE constructor argument 'outputFileDictionary' is not XSDataDictionary but %s" % self._outputFileDictionary.__class__.__name__
            raise BaseException(strMessage)
        if htmlPage is None:
            self._htmlPage = None
        elif htmlPage.__class__.__name__ == "XSDataFile":
            self._htmlPage = htmlPage
        else:
            strMessage = "ERROR! XSDataResultMXCuBE constructor argument 'htmlPage' is not XSDataFile but %s" % self._htmlPage.__class__.__name__
            raise BaseException(strMessage)
        if screeningId is None:
            self._screeningId = None
        elif screeningId.__class__.__name__ == "XSDataInteger":
            self._screeningId = screeningId
        else:
            strMessage = "ERROR! XSDataResultMXCuBE constructor argument 'screeningId' is not XSDataInteger but %s" % self._screeningId.__class__.__name__
            raise BaseException(strMessage)
    # Methods and properties for the 'characterisationExecutiveSummary' attribute
    def getCharacterisationExecutiveSummary(self): return self._characterisationExecutiveSummary
    def setCharacterisationExecutiveSummary(self, characterisationExecutiveSummary):
        if characterisationExecutiveSummary is None:
            self._characterisationExecutiveSummary = None
        elif characterisationExecutiveSummary.__class__.__name__ == "XSDataString":
            self._characterisationExecutiveSummary = characterisationExecutiveSummary
        else:
            strMessage = "ERROR! XSDataResultMXCuBE.setCharacterisationExecutiveSummary argument is not XSDataString but %s" % characterisationExecutiveSummary.__class__.__name__
            raise BaseException(strMessage)
    def delCharacterisationExecutiveSummary(self): self._characterisationExecutiveSummary = None
    characterisationExecutiveSummary = property(getCharacterisationExecutiveSummary, setCharacterisationExecutiveSummary, delCharacterisationExecutiveSummary, "Property for characterisationExecutiveSummary")
    # Methods and properties for the 'characterisationResult' attribute
    def getCharacterisationResult(self): return self._characterisationResult
    def setCharacterisationResult(self, characterisationResult):
        if characterisationResult is None:
            self._characterisationResult = None
        elif characterisationResult.__class__.__name__ == "XSDataResultCharacterisation":
            self._characterisationResult = characterisationResult
        else:
            strMessage = "ERROR! XSDataResultMXCuBE.setCharacterisationResult argument is not XSDataResultCharacterisation but %s" % characterisationResult.__class__.__name__
            raise BaseException(strMessage)
    def delCharacterisationResult(self): self._characterisationResult = None
    characterisationResult = property(getCharacterisationResult, setCharacterisationResult, delCharacterisationResult, "Property for characterisationResult")
    # Methods and properties for the 'collectionPlan' attribute
    def getCollectionPlan(self): return self._collectionPlan
    def setCollectionPlan(self, collectionPlan):
        if collectionPlan is None:
            self._collectionPlan = []
        elif collectionPlan.__class__.__name__ == "list":
            self._collectionPlan = collectionPlan
        else:
            strMessage = "ERROR! XSDataResultMXCuBE.setCollectionPlan argument is not list but %s" % collectionPlan.__class__.__name__
            raise BaseException(strMessage)
    def delCollectionPlan(self): self._collectionPlan = None
    collectionPlan = property(getCollectionPlan, setCollectionPlan, delCollectionPlan, "Property for collectionPlan")
    def addCollectionPlan(self, value):
        if value is None:
            strMessage = "ERROR! XSDataResultMXCuBE.addCollectionPlan argument is None"
            raise BaseException(strMessage)            
        elif value.__class__.__name__ == "XSDataCollectionPlan":
            self._collectionPlan.append(value)
        else:
            strMessage = "ERROR! XSDataResultMXCuBE.addCollectionPlan argument is not XSDataCollectionPlan but %s" % value.__class__.__name__
            raise BaseException(strMessage)
    def insertCollectionPlan(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataResultMXCuBE.insertCollectionPlan argument 'index' is None"
            raise BaseException(strMessage)            
        if value is None:
            strMessage = "ERROR! XSDataResultMXCuBE.insertCollectionPlan argument 'value' is None"
            raise BaseException(strMessage)            
        elif value.__class__.__name__ == "XSDataCollectionPlan":
            self._collectionPlan[index] = value
        else:
            strMessage = "ERROR! XSDataResultMXCuBE.addCollectionPlan argument is not XSDataCollectionPlan but %s" % value.__class__.__name__
            raise BaseException(strMessage)
    # Methods and properties for the 'listOfOutputFiles' attribute
    def getListOfOutputFiles(self): return self._listOfOutputFiles
    def setListOfOutputFiles(self, listOfOutputFiles):
        if listOfOutputFiles is None:
            self._listOfOutputFiles = None
        elif listOfOutputFiles.__class__.__name__ == "XSDataString":
            self._listOfOutputFiles = listOfOutputFiles
        else:
            strMessage = "ERROR! XSDataResultMXCuBE.setListOfOutputFiles argument is not XSDataString but %s" % listOfOutputFiles.__class__.__name__
            raise BaseException(strMessage)
    def delListOfOutputFiles(self): self._listOfOutputFiles = None
    listOfOutputFiles = property(getListOfOutputFiles, setListOfOutputFiles, delListOfOutputFiles, "Property for listOfOutputFiles")
    # Methods and properties for the 'outputFileDictionary' attribute
    def getOutputFileDictionary(self): return self._outputFileDictionary
    def setOutputFileDictionary(self, outputFileDictionary):
        if outputFileDictionary is None:
            self._outputFileDictionary = None
        elif outputFileDictionary.__class__.__name__ == "XSDataDictionary":
            self._outputFileDictionary = outputFileDictionary
        else:
            strMessage = "ERROR! XSDataResultMXCuBE.setOutputFileDictionary argument is not XSDataDictionary but %s" % outputFileDictionary.__class__.__name__
            raise BaseException(strMessage)
    def delOutputFileDictionary(self): self._outputFileDictionary = None
    outputFileDictionary = property(getOutputFileDictionary, setOutputFileDictionary, delOutputFileDictionary, "Property for outputFileDictionary")
    # Methods and properties for the 'htmlPage' attribute
    def getHtmlPage(self): return self._htmlPage
    def setHtmlPage(self, htmlPage):
        if htmlPage is None:
            self._htmlPage = None
        elif htmlPage.__class__.__name__ == "XSDataFile":
            self._htmlPage = htmlPage
        else:
            strMessage = "ERROR! XSDataResultMXCuBE.setHtmlPage argument is not XSDataFile but %s" % htmlPage.__class__.__name__
            raise BaseException(strMessage)
    def delHtmlPage(self): self._htmlPage = None
    htmlPage = property(getHtmlPage, setHtmlPage, delHtmlPage, "Property for htmlPage")
    # Methods and properties for the 'screeningId' attribute
    def getScreeningId(self): return self._screeningId
    def setScreeningId(self, screeningId):
        if screeningId is None:
            self._screeningId = None
        elif screeningId.__class__.__name__ == "XSDataInteger":
            self._screeningId = screeningId
        else:
            strMessage = "ERROR! XSDataResultMXCuBE.setScreeningId argument is not XSDataInteger but %s" % screeningId.__class__.__name__
            raise BaseException(strMessage)
    def delScreeningId(self): self._screeningId = None
    screeningId = property(getScreeningId, setScreeningId, delScreeningId, "Property for screeningId")
    def export(self, outfile, level, name_='XSDataResultMXCuBE'):
        showIndent(outfile, level)
        outfile.write(unicode('<%s>\n' % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode('</%s>\n' % name_))
    def exportChildren(self, outfile, level, name_='XSDataResultMXCuBE'):
        XSDataResult.exportChildren(self, outfile, level, name_)
        if self._characterisationExecutiveSummary is not None:
            self.characterisationExecutiveSummary.export(outfile, level, name_='characterisationExecutiveSummary')
        if self._characterisationResult is not None:
            self.characterisationResult.export(outfile, level, name_='characterisationResult')
        for collectionPlan_ in self.getCollectionPlan():
            collectionPlan_.export(outfile, level, name_='collectionPlan')
        if self._listOfOutputFiles is not None:
            self.listOfOutputFiles.export(outfile, level, name_='listOfOutputFiles')
        if self._outputFileDictionary is not None:
            self.outputFileDictionary.export(outfile, level, name_='outputFileDictionary')
        if self._htmlPage is not None:
            self.htmlPage.export(outfile, level, name_='htmlPage')
        if self._screeningId is not None:
            self.screeningId.export(outfile, level, name_='screeningId')
    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'characterisationExecutiveSummary':
            obj_ = XSDataString()
            obj_.build(child_)
            self.setCharacterisationExecutiveSummary(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'characterisationResult':
            obj_ = XSDataResultCharacterisation()
            obj_.build(child_)
            self.setCharacterisationResult(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'collectionPlan':
            obj_ = XSDataCollectionPlan()
            obj_.build(child_)
            self.collectionPlan.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'listOfOutputFiles':
            obj_ = XSDataString()
            obj_.build(child_)
            self.setListOfOutputFiles(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'outputFileDictionary':
            obj_ = XSDataDictionary()
            obj_.build(child_)
            self.setOutputFileDictionary(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'htmlPage':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setHtmlPage(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'screeningId':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setScreeningId(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)
    #Method for marshalling an object
    def marshal( self ):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export( oStreamString, 0, name_="XSDataResultMXCuBE" )
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML
    #Only to export the entire XML tree to a file stream on disk
    def exportToFile( self, _outfileName ):
        outfile = open( _outfileName, "w" )
        outfile.write(unicode('<?xml version=\"1.0\" ?>\n'))
        self.export( outfile, 0, name_='XSDataResultMXCuBE' )
        outfile.close()
    #Deprecated method, replaced by exportToFile
    def outputFile( self, _outfileName ):
        print("WARNING: Method outputFile in class XSDataResultMXCuBE is deprecated, please use instead exportToFile!")
        self.exportToFile(_outfileName)
    #Method for making a copy in a new instance
    def copy( self ):
        return XSDataResultMXCuBE.parseString(self.marshal())
    #Static method for parsing a string
    def parseString( _inString ):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultMXCuBE()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export( oStreamString, 0, name_="XSDataResultMXCuBE" )
        oStreamString.close()
        return rootObj
    parseString = staticmethod( parseString )
    #Static method for parsing a file
    def parseFile( _inFilePath ):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultMXCuBE()
        rootObj.build(rootNode)
        return rootObj
    parseFile = staticmethod( parseFile )
# end class XSDataResultMXCuBE



# End of data representation classes.


