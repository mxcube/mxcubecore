#!/usr/bin/env python

#
# Generated Thu Jan 12 03:59::59 2017 by EDGenerateDS.
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
 "XSDataCommon": "kernel/datamodel", \
}

try:
    from XSDataCommon import XSDataBoolean
    from XSDataCommon import XSDataDouble
    from XSDataCommon import XSDataFile
    from XSDataCommon import XSDataInput
    from XSDataCommon import XSDataInteger
    from XSDataCommon import XSDataResult
    from XSDataCommon import XSDataString
    from XSDataCommon import XSDataAngle
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
from XSDataCommon import XSDataBoolean
from XSDataCommon import XSDataDouble
from XSDataCommon import XSDataFile
from XSDataCommon import XSDataInput
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataResult
from XSDataCommon import XSDataString
from XSDataCommon import XSDataAngle




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



class XSDataControlImageDozor(object):
    def __init__(self, angle=None, spotFile=None, visibleResolution=None, spotScore=None, mainScore=None, powderWilsonRfactor=None, powderWilsonCorrelation=None, powderWilsonResolution=None, powderWilsonBfactor=None, powderWilsonScale=None, spotsResolution=None, spotsIntAver=None, spotsNumOf=None, image=None, number=None):
        if number is None:
            self._number = None
        elif number.__class__.__name__ == "XSDataInteger":
            self._number = number
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'number' is not XSDataInteger but %s" % self._number.__class__.__name__
            raise BaseException(strMessage)
        if image is None:
            self._image = None
        elif image.__class__.__name__ == "XSDataFile":
            self._image = image
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'image' is not XSDataFile but %s" % self._image.__class__.__name__
            raise BaseException(strMessage)
        if spotsNumOf is None:
            self._spotsNumOf = None
        elif spotsNumOf.__class__.__name__ == "XSDataInteger":
            self._spotsNumOf = spotsNumOf
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'spotsNumOf' is not XSDataInteger but %s" % self._spotsNumOf.__class__.__name__
            raise BaseException(strMessage)
        if spotsIntAver is None:
            self._spotsIntAver = None
        elif spotsIntAver.__class__.__name__ == "XSDataDouble":
            self._spotsIntAver = spotsIntAver
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'spotsIntAver' is not XSDataDouble but %s" % self._spotsIntAver.__class__.__name__
            raise BaseException(strMessage)
        if spotsResolution is None:
            self._spotsResolution = None
        elif spotsResolution.__class__.__name__ == "XSDataDouble":
            self._spotsResolution = spotsResolution
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'spotsResolution' is not XSDataDouble but %s" % self._spotsResolution.__class__.__name__
            raise BaseException(strMessage)
        if powderWilsonScale is None:
            self._powderWilsonScale = None
        elif powderWilsonScale.__class__.__name__ == "XSDataDouble":
            self._powderWilsonScale = powderWilsonScale
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'powderWilsonScale' is not XSDataDouble but %s" % self._powderWilsonScale.__class__.__name__
            raise BaseException(strMessage)
        if powderWilsonBfactor is None:
            self._powderWilsonBfactor = None
        elif powderWilsonBfactor.__class__.__name__ == "XSDataDouble":
            self._powderWilsonBfactor = powderWilsonBfactor
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'powderWilsonBfactor' is not XSDataDouble but %s" % self._powderWilsonBfactor.__class__.__name__
            raise BaseException(strMessage)
        if powderWilsonResolution is None:
            self._powderWilsonResolution = None
        elif powderWilsonResolution.__class__.__name__ == "XSDataDouble":
            self._powderWilsonResolution = powderWilsonResolution
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'powderWilsonResolution' is not XSDataDouble but %s" % self._powderWilsonResolution.__class__.__name__
            raise BaseException(strMessage)
        if powderWilsonCorrelation is None:
            self._powderWilsonCorrelation = None
        elif powderWilsonCorrelation.__class__.__name__ == "XSDataDouble":
            self._powderWilsonCorrelation = powderWilsonCorrelation
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'powderWilsonCorrelation' is not XSDataDouble but %s" % self._powderWilsonCorrelation.__class__.__name__
            raise BaseException(strMessage)
        if powderWilsonRfactor is None:
            self._powderWilsonRfactor = None
        elif powderWilsonRfactor.__class__.__name__ == "XSDataDouble":
            self._powderWilsonRfactor = powderWilsonRfactor
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'powderWilsonRfactor' is not XSDataDouble but %s" % self._powderWilsonRfactor.__class__.__name__
            raise BaseException(strMessage)
        if mainScore is None:
            self._mainScore = None
        elif mainScore.__class__.__name__ == "XSDataDouble":
            self._mainScore = mainScore
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'mainScore' is not XSDataDouble but %s" % self._mainScore.__class__.__name__
            raise BaseException(strMessage)
        if spotScore is None:
            self._spotScore = None
        elif spotScore.__class__.__name__ == "XSDataDouble":
            self._spotScore = spotScore
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'spotScore' is not XSDataDouble but %s" % self._spotScore.__class__.__name__
            raise BaseException(strMessage)
        if visibleResolution is None:
            self._visibleResolution = None
        elif visibleResolution.__class__.__name__ == "XSDataDouble":
            self._visibleResolution = visibleResolution
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'visibleResolution' is not XSDataDouble but %s" % self._visibleResolution.__class__.__name__
            raise BaseException(strMessage)
        if spotFile is None:
            self._spotFile = None
        elif spotFile.__class__.__name__ == "XSDataFile":
            self._spotFile = spotFile
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'spotFile' is not XSDataFile but %s" % self._spotFile.__class__.__name__
            raise BaseException(strMessage)
        if angle is None:
            self._angle = None
        elif angle.__class__.__name__ == "XSDataAngle":
            self._angle = angle
        else:
            strMessage = "ERROR! XSDataControlImageDozor constructor argument 'angle' is not XSDataAngle but %s" % self._angle.__class__.__name__
            raise BaseException(strMessage)
    # Methods and properties for the 'number' attribute
    def getNumber(self): return self._number
    def setNumber(self, number):
        if number is None:
            self._number = None
        elif number.__class__.__name__ == "XSDataInteger":
            self._number = number
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setNumber argument is not XSDataInteger but %s" % number.__class__.__name__
            raise BaseException(strMessage)
    def delNumber(self): self._number = None
    number = property(getNumber, setNumber, delNumber, "Property for number")
    # Methods and properties for the 'image' attribute
    def getImage(self): return self._image
    def setImage(self, image):
        if image is None:
            self._image = None
        elif image.__class__.__name__ == "XSDataFile":
            self._image = image
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setImage argument is not XSDataFile but %s" % image.__class__.__name__
            raise BaseException(strMessage)
    def delImage(self): self._image = None
    image = property(getImage, setImage, delImage, "Property for image")
    # Methods and properties for the 'spotsNumOf' attribute
    def getSpotsNumOf(self): return self._spotsNumOf
    def setSpotsNumOf(self, spotsNumOf):
        if spotsNumOf is None:
            self._spotsNumOf = None
        elif spotsNumOf.__class__.__name__ == "XSDataInteger":
            self._spotsNumOf = spotsNumOf
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setSpotsNumOf argument is not XSDataInteger but %s" % spotsNumOf.__class__.__name__
            raise BaseException(strMessage)
    def delSpotsNumOf(self): self._spotsNumOf = None
    spotsNumOf = property(getSpotsNumOf, setSpotsNumOf, delSpotsNumOf, "Property for spotsNumOf")
    # Methods and properties for the 'spotsIntAver' attribute
    def getSpotsIntAver(self): return self._spotsIntAver
    def setSpotsIntAver(self, spotsIntAver):
        if spotsIntAver is None:
            self._spotsIntAver = None
        elif spotsIntAver.__class__.__name__ == "XSDataDouble":
            self._spotsIntAver = spotsIntAver
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setSpotsIntAver argument is not XSDataDouble but %s" % spotsIntAver.__class__.__name__
            raise BaseException(strMessage)
    def delSpotsIntAver(self): self._spotsIntAver = None
    spotsIntAver = property(getSpotsIntAver, setSpotsIntAver, delSpotsIntAver, "Property for spotsIntAver")
    # Methods and properties for the 'spotsResolution' attribute
    def getSpotsResolution(self): return self._spotsResolution
    def setSpotsResolution(self, spotsResolution):
        if spotsResolution is None:
            self._spotsResolution = None
        elif spotsResolution.__class__.__name__ == "XSDataDouble":
            self._spotsResolution = spotsResolution
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setSpotsResolution argument is not XSDataDouble but %s" % spotsResolution.__class__.__name__
            raise BaseException(strMessage)
    def delSpotsResolution(self): self._spotsResolution = None
    spotsResolution = property(getSpotsResolution, setSpotsResolution, delSpotsResolution, "Property for spotsResolution")
    # Methods and properties for the 'powderWilsonScale' attribute
    def getPowderWilsonScale(self): return self._powderWilsonScale
    def setPowderWilsonScale(self, powderWilsonScale):
        if powderWilsonScale is None:
            self._powderWilsonScale = None
        elif powderWilsonScale.__class__.__name__ == "XSDataDouble":
            self._powderWilsonScale = powderWilsonScale
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setPowderWilsonScale argument is not XSDataDouble but %s" % powderWilsonScale.__class__.__name__
            raise BaseException(strMessage)
    def delPowderWilsonScale(self): self._powderWilsonScale = None
    powderWilsonScale = property(getPowderWilsonScale, setPowderWilsonScale, delPowderWilsonScale, "Property for powderWilsonScale")
    # Methods and properties for the 'powderWilsonBfactor' attribute
    def getPowderWilsonBfactor(self): return self._powderWilsonBfactor
    def setPowderWilsonBfactor(self, powderWilsonBfactor):
        if powderWilsonBfactor is None:
            self._powderWilsonBfactor = None
        elif powderWilsonBfactor.__class__.__name__ == "XSDataDouble":
            self._powderWilsonBfactor = powderWilsonBfactor
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setPowderWilsonBfactor argument is not XSDataDouble but %s" % powderWilsonBfactor.__class__.__name__
            raise BaseException(strMessage)
    def delPowderWilsonBfactor(self): self._powderWilsonBfactor = None
    powderWilsonBfactor = property(getPowderWilsonBfactor, setPowderWilsonBfactor, delPowderWilsonBfactor, "Property for powderWilsonBfactor")
    # Methods and properties for the 'powderWilsonResolution' attribute
    def getPowderWilsonResolution(self): return self._powderWilsonResolution
    def setPowderWilsonResolution(self, powderWilsonResolution):
        if powderWilsonResolution is None:
            self._powderWilsonResolution = None
        elif powderWilsonResolution.__class__.__name__ == "XSDataDouble":
            self._powderWilsonResolution = powderWilsonResolution
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setPowderWilsonResolution argument is not XSDataDouble but %s" % powderWilsonResolution.__class__.__name__
            raise BaseException(strMessage)
    def delPowderWilsonResolution(self): self._powderWilsonResolution = None
    powderWilsonResolution = property(getPowderWilsonResolution, setPowderWilsonResolution, delPowderWilsonResolution, "Property for powderWilsonResolution")
    # Methods and properties for the 'powderWilsonCorrelation' attribute
    def getPowderWilsonCorrelation(self): return self._powderWilsonCorrelation
    def setPowderWilsonCorrelation(self, powderWilsonCorrelation):
        if powderWilsonCorrelation is None:
            self._powderWilsonCorrelation = None
        elif powderWilsonCorrelation.__class__.__name__ == "XSDataDouble":
            self._powderWilsonCorrelation = powderWilsonCorrelation
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setPowderWilsonCorrelation argument is not XSDataDouble but %s" % powderWilsonCorrelation.__class__.__name__
            raise BaseException(strMessage)
    def delPowderWilsonCorrelation(self): self._powderWilsonCorrelation = None
    powderWilsonCorrelation = property(getPowderWilsonCorrelation, setPowderWilsonCorrelation, delPowderWilsonCorrelation, "Property for powderWilsonCorrelation")
    # Methods and properties for the 'powderWilsonRfactor' attribute
    def getPowderWilsonRfactor(self): return self._powderWilsonRfactor
    def setPowderWilsonRfactor(self, powderWilsonRfactor):
        if powderWilsonRfactor is None:
            self._powderWilsonRfactor = None
        elif powderWilsonRfactor.__class__.__name__ == "XSDataDouble":
            self._powderWilsonRfactor = powderWilsonRfactor
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setPowderWilsonRfactor argument is not XSDataDouble but %s" % powderWilsonRfactor.__class__.__name__
            raise BaseException(strMessage)
    def delPowderWilsonRfactor(self): self._powderWilsonRfactor = None
    powderWilsonRfactor = property(getPowderWilsonRfactor, setPowderWilsonRfactor, delPowderWilsonRfactor, "Property for powderWilsonRfactor")
    # Methods and properties for the 'mainScore' attribute
    def getMainScore(self): return self._mainScore
    def setMainScore(self, mainScore):
        if mainScore is None:
            self._mainScore = None
        elif mainScore.__class__.__name__ == "XSDataDouble":
            self._mainScore = mainScore
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setMainScore argument is not XSDataDouble but %s" % mainScore.__class__.__name__
            raise BaseException(strMessage)
    def delMainScore(self): self._mainScore = None
    mainScore = property(getMainScore, setMainScore, delMainScore, "Property for mainScore")
    # Methods and properties for the 'spotScore' attribute
    def getSpotScore(self): return self._spotScore
    def setSpotScore(self, spotScore):
        if spotScore is None:
            self._spotScore = None
        elif spotScore.__class__.__name__ == "XSDataDouble":
            self._spotScore = spotScore
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setSpotScore argument is not XSDataDouble but %s" % spotScore.__class__.__name__
            raise BaseException(strMessage)
    def delSpotScore(self): self._spotScore = None
    spotScore = property(getSpotScore, setSpotScore, delSpotScore, "Property for spotScore")
    # Methods and properties for the 'visibleResolution' attribute
    def getVisibleResolution(self): return self._visibleResolution
    def setVisibleResolution(self, visibleResolution):
        if visibleResolution is None:
            self._visibleResolution = None
        elif visibleResolution.__class__.__name__ == "XSDataDouble":
            self._visibleResolution = visibleResolution
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setVisibleResolution argument is not XSDataDouble but %s" % visibleResolution.__class__.__name__
            raise BaseException(strMessage)
    def delVisibleResolution(self): self._visibleResolution = None
    visibleResolution = property(getVisibleResolution, setVisibleResolution, delVisibleResolution, "Property for visibleResolution")
    # Methods and properties for the 'spotFile' attribute
    def getSpotFile(self): return self._spotFile
    def setSpotFile(self, spotFile):
        if spotFile is None:
            self._spotFile = None
        elif spotFile.__class__.__name__ == "XSDataFile":
            self._spotFile = spotFile
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setSpotFile argument is not XSDataFile but %s" % spotFile.__class__.__name__
            raise BaseException(strMessage)
    def delSpotFile(self): self._spotFile = None
    spotFile = property(getSpotFile, setSpotFile, delSpotFile, "Property for spotFile")
    # Methods and properties for the 'angle' attribute
    def getAngle(self): return self._angle
    def setAngle(self, angle):
        if angle is None:
            self._angle = None
        elif angle.__class__.__name__ == "XSDataAngle":
            self._angle = angle
        else:
            strMessage = "ERROR! XSDataControlImageDozor.setAngle argument is not XSDataAngle but %s" % angle.__class__.__name__
            raise BaseException(strMessage)
    def delAngle(self): self._angle = None
    angle = property(getAngle, setAngle, delAngle, "Property for angle")
    def export(self, outfile, level, name_='XSDataControlImageDozor'):
        showIndent(outfile, level)
        outfile.write(unicode('<%s>\n' % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode('</%s>\n' % name_))
    def exportChildren(self, outfile, level, name_='XSDataControlImageDozor'):
        pass
        if self._number is not None:
            self.number.export(outfile, level, name_='number')
        else:
            warnEmptyAttribute("number", "XSDataInteger")
        if self._image is not None:
            self.image.export(outfile, level, name_='image')
        else:
            warnEmptyAttribute("image", "XSDataFile")
        if self._spotsNumOf is not None:
            self.spotsNumOf.export(outfile, level, name_='spotsNumOf')
        else:
            warnEmptyAttribute("spotsNumOf", "XSDataInteger")
        if self._spotsIntAver is not None:
            self.spotsIntAver.export(outfile, level, name_='spotsIntAver')
        else:
            warnEmptyAttribute("spotsIntAver", "XSDataDouble")
        if self._spotsResolution is not None:
            self.spotsResolution.export(outfile, level, name_='spotsResolution')
        if self._powderWilsonScale is not None:
            self.powderWilsonScale.export(outfile, level, name_='powderWilsonScale')
        if self._powderWilsonBfactor is not None:
            self.powderWilsonBfactor.export(outfile, level, name_='powderWilsonBfactor')
        if self._powderWilsonResolution is not None:
            self.powderWilsonResolution.export(outfile, level, name_='powderWilsonResolution')
        if self._powderWilsonCorrelation is not None:
            self.powderWilsonCorrelation.export(outfile, level, name_='powderWilsonCorrelation')
        if self._powderWilsonRfactor is not None:
            self.powderWilsonRfactor.export(outfile, level, name_='powderWilsonRfactor')
        if self._mainScore is not None:
            self.mainScore.export(outfile, level, name_='mainScore')
        if self._spotScore is not None:
            self.spotScore.export(outfile, level, name_='spotScore')
        if self._visibleResolution is not None:
            self.visibleResolution.export(outfile, level, name_='visibleResolution')
        if self._spotFile is not None:
            self.spotFile.export(outfile, level, name_='spotFile')
        if self._angle is not None:
            self.angle.export(outfile, level, name_='angle')
    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'number':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumber(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'image':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setImage(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'spotsNumOf':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setSpotsNumOf(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'spotsIntAver':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setSpotsIntAver(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'spotsResolution':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setSpotsResolution(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'powderWilsonScale':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setPowderWilsonScale(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'powderWilsonBfactor':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setPowderWilsonBfactor(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'powderWilsonResolution':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setPowderWilsonResolution(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'powderWilsonCorrelation':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setPowderWilsonCorrelation(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'powderWilsonRfactor':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setPowderWilsonRfactor(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'mainScore':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setMainScore(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'spotScore':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setSpotScore(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'visibleResolution':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setVisibleResolution(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'spotFile':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setSpotFile(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'angle':
            obj_ = XSDataAngle()
            obj_.build(child_)
            self.setAngle(obj_)
    #Method for marshalling an object
    def marshal( self ):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export( oStreamString, 0, name_="XSDataControlImageDozor" )
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML
    #Only to export the entire XML tree to a file stream on disk
    def exportToFile( self, _outfileName ):
        outfile = open( _outfileName, "w" )
        outfile.write(unicode('<?xml version=\"1.0\" ?>\n'))
        self.export( outfile, 0, name_='XSDataControlImageDozor' )
        outfile.close()
    #Deprecated method, replaced by exportToFile
    def outputFile( self, _outfileName ):
        print("WARNING: Method outputFile in class XSDataControlImageDozor is deprecated, please use instead exportToFile!")
        self.exportToFile(_outfileName)
    #Method for making a copy in a new instance
    def copy( self ):
        return XSDataControlImageDozor.parseString(self.marshal())
    #Static method for parsing a string
    def parseString( _inString ):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataControlImageDozor()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export( oStreamString, 0, name_="XSDataControlImageDozor" )
        oStreamString.close()
        return rootObj
    parseString = staticmethod( parseString )
    #Static method for parsing a file
    def parseFile( _inFilePath ):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataControlImageDozor()
        rootObj.build(rootNode)
        return rootObj
    parseFile = staticmethod( parseFile )
# end class XSDataControlImageDozor


class XSDataDozorInput(XSDataInput):
    def __init__(self, configuration=None, nameTemplateImage=None, numberImages=None, firstImageNumber=None, startingAngle=None, imageStep=None,
        oscillationRange=None, orgy=None, orgx=None, fractionPolarization=None, wavelength=None, detectorDistance=None, spotSize=None, exposureTime=None, detectorType=None,         
    ):
        XSDataInput.__init__(self, configuration)
        if detectorType is None:
            self._detectorType = None
        elif detectorType.__class__.__name__ == "XSDataString":
            self._detectorType = detectorType
        else:
            strMessage = "ERROR! XSDataDozorInput constructor argument 'detectorType' is not XSDataString but %s" % self._detectorType.__class__.__name__
            raise BaseException(strMessage)
        if exposureTime is None:
            self._exposureTime = None
        elif exposureTime.__class__.__name__ == "XSDataDouble":
            self._exposureTime = exposureTime
        else:
            strMessage = "ERROR! XSDataDozorInput constructor argument 'exposureTime' is not XSDataDouble but %s" % self._exposureTime.__class__.__name__
            raise BaseException(strMessage)
        if spotSize is None:
            self._spotSize = None
        elif spotSize.__class__.__name__ == "XSDataInteger":
            self._spotSize = spotSize
        else:
            strMessage = "ERROR! XSDataDozorInput constructor argument 'spotSize' is not XSDataInteger but %s" % self._spotSize.__class__.__name__
            raise BaseException(strMessage)
        if detectorDistance is None:
            self._detectorDistance = None
        elif detectorDistance.__class__.__name__ == "XSDataDouble":
            self._detectorDistance = detectorDistance
        else:
            strMessage = "ERROR! XSDataDozorInput constructor argument 'detectorDistance' is not XSDataDouble but %s" % self._detectorDistance.__class__.__name__
            raise BaseException(strMessage)
        if wavelength is None:
            self._wavelength = None
        elif wavelength.__class__.__name__ == "XSDataDouble":
            self._wavelength = wavelength
        else:
            strMessage = "ERROR! XSDataDozorInput constructor argument 'wavelength' is not XSDataDouble but %s" % self._wavelength.__class__.__name__
            raise BaseException(strMessage)
        if fractionPolarization is None:
            self._fractionPolarization = None
        elif fractionPolarization.__class__.__name__ == "XSDataDouble":
            self._fractionPolarization = fractionPolarization
        else:
            strMessage = "ERROR! XSDataDozorInput constructor argument 'fractionPolarization' is not XSDataDouble but %s" % self._fractionPolarization.__class__.__name__
            raise BaseException(strMessage)
        if orgx is None:
            self._orgx = None
        elif orgx.__class__.__name__ == "XSDataDouble":
            self._orgx = orgx
        else:
            strMessage = "ERROR! XSDataDozorInput constructor argument 'orgx' is not XSDataDouble but %s" % self._orgx.__class__.__name__
            raise BaseException(strMessage)
        if orgy is None:
            self._orgy = None
        elif orgy.__class__.__name__ == "XSDataDouble":
            self._orgy = orgy
        else:
            strMessage = "ERROR! XSDataDozorInput constructor argument 'orgy' is not XSDataDouble but %s" % self._orgy.__class__.__name__
            raise BaseException(strMessage)
        if oscillationRange is None:
            self._oscillationRange = None
        elif oscillationRange.__class__.__name__ == "XSDataDouble":
            self._oscillationRange = oscillationRange
        else:
            strMessage = "ERROR! XSDataDozorInput constructor argument 'oscillationRange' is not XSDataDouble but %s" % self._oscillationRange.__class__.__name__
            raise BaseException(strMessage)
        if imageStep is None:
            self._imageStep = None
        elif imageStep.__class__.__name__ == "XSDataDouble":
            self._imageStep = imageStep
        else:
            strMessage = "ERROR! XSDataDozorInput constructor argument 'imageStep' is not XSDataDouble but %s" % self._imageStep.__class__.__name__
            raise BaseException(strMessage)
        if startingAngle is None:
            self._startingAngle = None
        elif startingAngle.__class__.__name__ == "XSDataDouble":
            self._startingAngle = startingAngle
        else:
            strMessage = "ERROR! XSDataDozorInput constructor argument 'startingAngle' is not XSDataDouble but %s" % self._startingAngle.__class__.__name__
            raise BaseException(strMessage)
        if firstImageNumber is None:
            self._firstImageNumber = None
        elif firstImageNumber.__class__.__name__ == "XSDataInteger":
            self._firstImageNumber = firstImageNumber
        else:
            strMessage = "ERROR! XSDataDozorInput constructor argument 'firstImageNumber' is not XSDataInteger but %s" % self._firstImageNumber.__class__.__name__
            raise BaseException(strMessage)
        if numberImages is None:
            self._numberImages = None
        elif numberImages.__class__.__name__ == "XSDataInteger":
            self._numberImages = numberImages
        else:
            strMessage = "ERROR! XSDataDozorInput constructor argument 'numberImages' is not XSDataInteger but %s" % self._numberImages.__class__.__name__
            raise BaseException(strMessage)
        if nameTemplateImage is None:
            self._nameTemplateImage = None
        elif nameTemplateImage.__class__.__name__ == "XSDataString":
            self._nameTemplateImage = nameTemplateImage
        else:
            strMessage = "ERROR! XSDataDozorInput constructor argument 'nameTemplateImage' is not XSDataString but %s" % self._nameTemplateImage.__class__.__name__
            raise BaseException(strMessage)
    # Methods and properties for the 'detectorType' attribute
    def getDetectorType(self): return self._detectorType
    def setDetectorType(self, detectorType):
        if detectorType is None:
            self._detectorType = None
        elif detectorType.__class__.__name__ == "XSDataString":
            self._detectorType = detectorType
        else:
            strMessage = "ERROR! XSDataDozorInput.setDetectorType argument is not XSDataString but %s" % detectorType.__class__.__name__
            raise BaseException(strMessage)
    def delDetectorType(self): self._detectorType = None
    detectorType = property(getDetectorType, setDetectorType, delDetectorType, "Property for detectorType")
    # Methods and properties for the 'exposureTime' attribute
    def getExposureTime(self): return self._exposureTime
    def setExposureTime(self, exposureTime):
        if exposureTime is None:
            self._exposureTime = None
        elif exposureTime.__class__.__name__ == "XSDataDouble":
            self._exposureTime = exposureTime
        else:
            strMessage = "ERROR! XSDataDozorInput.setExposureTime argument is not XSDataDouble but %s" % exposureTime.__class__.__name__
            raise BaseException(strMessage)
    def delExposureTime(self): self._exposureTime = None
    exposureTime = property(getExposureTime, setExposureTime, delExposureTime, "Property for exposureTime")
    # Methods and properties for the 'spotSize' attribute
    def getSpotSize(self): return self._spotSize
    def setSpotSize(self, spotSize):
        if spotSize is None:
            self._spotSize = None
        elif spotSize.__class__.__name__ == "XSDataInteger":
            self._spotSize = spotSize
        else:
            strMessage = "ERROR! XSDataDozorInput.setSpotSize argument is not XSDataInteger but %s" % spotSize.__class__.__name__
            raise BaseException(strMessage)
    def delSpotSize(self): self._spotSize = None
    spotSize = property(getSpotSize, setSpotSize, delSpotSize, "Property for spotSize")
    # Methods and properties for the 'detectorDistance' attribute
    def getDetectorDistance(self): return self._detectorDistance
    def setDetectorDistance(self, detectorDistance):
        if detectorDistance is None:
            self._detectorDistance = None
        elif detectorDistance.__class__.__name__ == "XSDataDouble":
            self._detectorDistance = detectorDistance
        else:
            strMessage = "ERROR! XSDataDozorInput.setDetectorDistance argument is not XSDataDouble but %s" % detectorDistance.__class__.__name__
            raise BaseException(strMessage)
    def delDetectorDistance(self): self._detectorDistance = None
    detectorDistance = property(getDetectorDistance, setDetectorDistance, delDetectorDistance, "Property for detectorDistance")
    # Methods and properties for the 'wavelength' attribute
    def getWavelength(self): return self._wavelength
    def setWavelength(self, wavelength):
        if wavelength is None:
            self._wavelength = None
        elif wavelength.__class__.__name__ == "XSDataDouble":
            self._wavelength = wavelength
        else:
            strMessage = "ERROR! XSDataDozorInput.setWavelength argument is not XSDataDouble but %s" % wavelength.__class__.__name__
            raise BaseException(strMessage)
    def delWavelength(self): self._wavelength = None
    wavelength = property(getWavelength, setWavelength, delWavelength, "Property for wavelength")
    # Methods and properties for the 'fractionPolarization' attribute
    def getFractionPolarization(self): return self._fractionPolarization
    def setFractionPolarization(self, fractionPolarization):
        if fractionPolarization is None:
            self._fractionPolarization = None
        elif fractionPolarization.__class__.__name__ == "XSDataDouble":
            self._fractionPolarization = fractionPolarization
        else:
            strMessage = "ERROR! XSDataDozorInput.setFractionPolarization argument is not XSDataDouble but %s" % fractionPolarization.__class__.__name__
            raise BaseException(strMessage)
    def delFractionPolarization(self): self._fractionPolarization = None
    fractionPolarization = property(getFractionPolarization, setFractionPolarization, delFractionPolarization, "Property for fractionPolarization")
    # Methods and properties for the 'orgx' attribute
    def getOrgx(self): return self._orgx
    def setOrgx(self, orgx):
        if orgx is None:
            self._orgx = None
        elif orgx.__class__.__name__ == "XSDataDouble":
            self._orgx = orgx
        else:
            strMessage = "ERROR! XSDataDozorInput.setOrgx argument is not XSDataDouble but %s" % orgx.__class__.__name__
            raise BaseException(strMessage)
    def delOrgx(self): self._orgx = None
    orgx = property(getOrgx, setOrgx, delOrgx, "Property for orgx")
    # Methods and properties for the 'orgy' attribute
    def getOrgy(self): return self._orgy
    def setOrgy(self, orgy):
        if orgy is None:
            self._orgy = None
        elif orgy.__class__.__name__ == "XSDataDouble":
            self._orgy = orgy
        else:
            strMessage = "ERROR! XSDataDozorInput.setOrgy argument is not XSDataDouble but %s" % orgy.__class__.__name__
            raise BaseException(strMessage)
    def delOrgy(self): self._orgy = None
    orgy = property(getOrgy, setOrgy, delOrgy, "Property for orgy")
    # Methods and properties for the 'oscillationRange' attribute
    def getOscillationRange(self): return self._oscillationRange
    def setOscillationRange(self, oscillationRange):
        if oscillationRange is None:
            self._oscillationRange = None
        elif oscillationRange.__class__.__name__ == "XSDataDouble":
            self._oscillationRange = oscillationRange
        else:
            strMessage = "ERROR! XSDataDozorInput.setOscillationRange argument is not XSDataDouble but %s" % oscillationRange.__class__.__name__
            raise BaseException(strMessage)
    def delOscillationRange(self): self._oscillationRange = None
    oscillationRange = property(getOscillationRange, setOscillationRange, delOscillationRange, "Property for oscillationRange")
    # Methods and properties for the 'imageStep' attribute
    def getImageStep(self): return self._imageStep
    def setImageStep(self, imageStep):
        if imageStep is None:
            self._imageStep = None
        elif imageStep.__class__.__name__ == "XSDataDouble":
            self._imageStep = imageStep
        else:
            strMessage = "ERROR! XSDataDozorInput.setImageStep argument is not XSDataDouble but %s" % imageStep.__class__.__name__
            raise BaseException(strMessage)
    def delImageStep(self): self._imageStep = None
    imageStep = property(getImageStep, setImageStep, delImageStep, "Property for imageStep")
    # Methods and properties for the 'startingAngle' attribute
    def getStartingAngle(self): return self._startingAngle
    def setStartingAngle(self, startingAngle):
        if startingAngle is None:
            self._startingAngle = None
        elif startingAngle.__class__.__name__ == "XSDataDouble":
            self._startingAngle = startingAngle
        else:
            strMessage = "ERROR! XSDataDozorInput.setStartingAngle argument is not XSDataDouble but %s" % startingAngle.__class__.__name__
            raise BaseException(strMessage)
    def delStartingAngle(self): self._startingAngle = None
    startingAngle = property(getStartingAngle, setStartingAngle, delStartingAngle, "Property for startingAngle")
    # Methods and properties for the 'firstImageNumber' attribute
    def getFirstImageNumber(self): return self._firstImageNumber
    def setFirstImageNumber(self, firstImageNumber):
        if firstImageNumber is None:
            self._firstImageNumber = None
        elif firstImageNumber.__class__.__name__ == "XSDataInteger":
            self._firstImageNumber = firstImageNumber
        else:
            strMessage = "ERROR! XSDataDozorInput.setFirstImageNumber argument is not XSDataInteger but %s" % firstImageNumber.__class__.__name__
            raise BaseException(strMessage)
    def delFirstImageNumber(self): self._firstImageNumber = None
    firstImageNumber = property(getFirstImageNumber, setFirstImageNumber, delFirstImageNumber, "Property for firstImageNumber")
    # Methods and properties for the 'numberImages' attribute
    def getNumberImages(self): return self._numberImages
    def setNumberImages(self, numberImages):
        if numberImages is None:
            self._numberImages = None
        elif numberImages.__class__.__name__ == "XSDataInteger":
            self._numberImages = numberImages
        else:
            strMessage = "ERROR! XSDataDozorInput.setNumberImages argument is not XSDataInteger but %s" % numberImages.__class__.__name__
            raise BaseException(strMessage)
    def delNumberImages(self): self._numberImages = None
    numberImages = property(getNumberImages, setNumberImages, delNumberImages, "Property for numberImages")
    # Methods and properties for the 'nameTemplateImage' attribute
    def getNameTemplateImage(self): return self._nameTemplateImage
    def setNameTemplateImage(self, nameTemplateImage):
        if nameTemplateImage is None:
            self._nameTemplateImage = None
        elif nameTemplateImage.__class__.__name__ == "XSDataString":
            self._nameTemplateImage = nameTemplateImage
        else:
            strMessage = "ERROR! XSDataDozorInput.setNameTemplateImage argument is not XSDataString but %s" % nameTemplateImage.__class__.__name__
            raise BaseException(strMessage)
    def delNameTemplateImage(self): self._nameTemplateImage = None
    nameTemplateImage = property(getNameTemplateImage, setNameTemplateImage, delNameTemplateImage, "Property for nameTemplateImage")

    def export(self, outfile, level, name_='XSDataDozorInput'):
        showIndent(outfile, level)
        outfile.write(unicode('<%s>\n' % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode('</%s>\n' % name_))
    def exportChildren(self, outfile, level, name_='XSDataDozorInput'):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._detectorType is not None:
            self.detectorType.export(outfile, level, name_='detectorType')
        else:
            warnEmptyAttribute("detectorType", "XSDataString")
        if self._exposureTime is not None:
            self.exposureTime.export(outfile, level, name_='exposureTime')
        else:
            warnEmptyAttribute("exposureTime", "XSDataDouble")
        if self._spotSize is not None:
            self.spotSize.export(outfile, level, name_='spotSize')
        else:
            warnEmptyAttribute("spotSize", "XSDataInteger")
        if self._detectorDistance is not None:
            self.detectorDistance.export(outfile, level, name_='detectorDistance')
        else:
            warnEmptyAttribute("detectorDistance", "XSDataDouble")
        if self._wavelength is not None:
            self.wavelength.export(outfile, level, name_='wavelength')
        else:
            warnEmptyAttribute("wavelength", "XSDataDouble")
        if self._fractionPolarization is not None:
            self.fractionPolarization.export(outfile, level, name_='fractionPolarization')
        if self._orgx is not None:
            self.orgx.export(outfile, level, name_='orgx')
        else:
            warnEmptyAttribute("orgx", "XSDataDouble")
        if self._orgy is not None:
            self.orgy.export(outfile, level, name_='orgy')
        else:
            warnEmptyAttribute("orgy", "XSDataDouble")
        if self._oscillationRange is not None:
            self.oscillationRange.export(outfile, level, name_='oscillationRange')
        else:
            warnEmptyAttribute("oscillationRange", "XSDataDouble")
        if self._imageStep is not None:
            self.imageStep.export(outfile, level, name_='imageStep')
        if self._startingAngle is not None:
            self.startingAngle.export(outfile, level, name_='startingAngle')
        if self._firstImageNumber is not None:
            self.firstImageNumber.export(outfile, level, name_='firstImageNumber')
        else:
            warnEmptyAttribute("firstImageNumber", "XSDataInteger")
        if self._numberImages is not None:
            self.numberImages.export(outfile, level, name_='numberImages')
        else:
            warnEmptyAttribute("numberImages", "XSDataInteger")
        if self._nameTemplateImage is not None:
            self.nameTemplateImage.export(outfile, level, name_='nameTemplateImage')
        else:
            warnEmptyAttribute("nameTemplateImage", "XSDataString")
            
    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'detectorType':
            obj_ = XSDataString()
            obj_.build(child_)
            self.setDetectorType(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'exposureTime':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setExposureTime(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'spotSize':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setSpotSize(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'detectorDistance':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setDetectorDistance(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'wavelength':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setWavelength(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'fractionPolarization':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setFractionPolarization(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'orgx':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setOrgx(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'orgy':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setOrgy(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'oscillationRange':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setOscillationRange(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'imageStep':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setImageStep(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'startingAngle':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setStartingAngle(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'firstImageNumber':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setFirstImageNumber(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'numberImages':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setNumberImages(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'nameTemplateImage':
            obj_ = XSDataString()
            obj_.build(child_)
            self.setNameTemplateImage(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)
    #Method for marshalling an object
    def marshal( self ):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export( oStreamString, 0, name_="XSDataDozorInput" )
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML
    #Only to export the entire XML tree to a file stream on disk
    def exportToFile( self, _outfileName ):
        outfile = open( _outfileName, "w" )
        outfile.write(unicode('<?xml version=\"1.0\" ?>\n'))
        self.export( outfile, 0, name_='XSDataDozorInput' )
        outfile.close()
    #Deprecated method, replaced by exportToFile
    def outputFile( self, _outfileName ):
        print("WARNING: Method outputFile in class XSDataDozorInput is deprecated, please use instead exportToFile!")
        self.exportToFile(_outfileName)
    #Method for making a copy in a new instance
    def copy( self ):
        return XSDataDozorInput.parseString(self.marshal())
    #Static method for parsing a string
    def parseString( _inString ):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataDozorInput()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export( oStreamString, 0, name_="XSDataDozorInput" )
        oStreamString.close()
        return rootObj
    parseString = staticmethod( parseString )
    #Static method for parsing a file
    def parseFile( _inFilePath ):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataDozorInput()
        rootObj.build(rootNode)
        return rootObj
    parseFile = staticmethod( parseFile )
# end class XSDataDozorInput


class XSDataInputControlDozor(XSDataInput):
    def __init__(self, configuration=None, keepCbfTmpDirectory=None, radiationDamage=None, wedgeNumber=None, 
                hdf5BatchSize=None,   batchSize=None, endNo=None, startNo=None, template=None, directory=None, image=None, processDirectory=None, dataCollectionId=None,
                doISPyBUpload=None
    ):
        XSDataInput.__init__(self, configuration)
        if dataCollectionId is None:
            self._dataCollectionId = None
        elif dataCollectionId.__class__.__name__ == "XSDataInteger":
            self._dataCollectionId = dataCollectionId
        else:
            strMessage = "ERROR! XSDataInputControlDozor constructor argument 'dataCollectionId' is not XSDataInteger but %s" % self._dataCollectionId.__class__.__name__
            raise BaseException(strMessage)
        if processDirectory is None:
            self._processDirectory = None
        elif processDirectory.__class__.__name__ == "XSDataFile":
            self._processDirectory = processDirectory
        else:
            strMessage = "ERROR! XSDataInputControlDozor constructor argument 'processDirectory' is not XSDataFile but %s" % self._processDirectory.__class__.__name__
            raise BaseException(strMessage)
        if image is None:
            self._image = []
        elif image.__class__.__name__ == "list":
            self._image = image
        else:
            strMessage = "ERROR! XSDataInputControlDozor constructor argument 'image' is not list but %s" % self._image.__class__.__name__
            raise BaseException(strMessage)
        if directory is None:
            self._directory = None
        elif directory.__class__.__name__ == "XSDataFile":
            self._directory = directory
        else:
            strMessage = "ERROR! XSDataInputControlDozor constructor argument 'directory' is not XSDataFile but %s" % self._directory.__class__.__name__
            raise BaseException(strMessage)
        if template is None:
            self._template = None
        elif template.__class__.__name__ == "XSDataString":
            self._template = template
        else:
            strMessage = "ERROR! XSDataInputControlDozor constructor argument 'template' is not XSDataString but %s" % self._template.__class__.__name__
            raise BaseException(strMessage)
        if startNo is None:
            self._startNo = None
        elif startNo.__class__.__name__ == "XSDataInteger":
            self._startNo = startNo
        else:
            strMessage = "ERROR! XSDataInputControlDozor constructor argument 'startNo' is not XSDataInteger but %s" % self._startNo.__class__.__name__
            raise BaseException(strMessage)
        if endNo is None:
            self._endNo = None
        elif endNo.__class__.__name__ == "XSDataInteger":
            self._endNo = endNo
        else:
            strMessage = "ERROR! XSDataInputControlDozor constructor argument 'endNo' is not XSDataInteger but %s" % self._endNo.__class__.__name__
            raise BaseException(strMessage)
        if batchSize is None:
            self._batchSize = None
        elif batchSize.__class__.__name__ == "XSDataInteger":
            self._batchSize = batchSize
        else:
            strMessage = "ERROR! XSDataInputControlDozor constructor argument 'batchSize' is not XSDataInteger but %s" % self._batchSize.__class__.__name__
            raise BaseException(strMessage)
        if hdf5BatchSize is None:
            self._hdf5BatchSize = None
        elif hdf5BatchSize.__class__.__name__ == "XSDataInteger":
            self._hdf5BatchSize = hdf5BatchSize
        else:
            strMessage = "ERROR! XSDataInputControlDozor constructor argument 'hdf5BatchSize' is not XSDataInteger but %s" % self._hdf5BatchSize.__class__.__name__
            raise BaseException(strMessage)
        if wedgeNumber is None:
            self._wedgeNumber = None
        elif wedgeNumber.__class__.__name__ == "XSDataInteger":
            self._wedgeNumber = wedgeNumber
        else:
            strMessage = "ERROR! XSDataInputControlDozor constructor argument 'wedgeNumber' is not XSDataInteger but %s" % self._wedgeNumber.__class__.__name__
            raise BaseException(strMessage)
        if radiationDamage is None:
            self._radiationDamage = None
        elif radiationDamage.__class__.__name__ == "XSDataBoolean":
            self._radiationDamage = radiationDamage
        else:
            strMessage = "ERROR! XSDataInputControlDozor constructor argument 'radiationDamage' is not XSDataBoolean but %s" % self._radiationDamage.__class__.__name__
            raise BaseException(strMessage)
        if keepCbfTmpDirectory is None:
            self._keepCbfTmpDirectory = None
        elif keepCbfTmpDirectory.__class__.__name__ == "XSDataBoolean":
            self._keepCbfTmpDirectory = keepCbfTmpDirectory
        else:
            strMessage = "ERROR! XSDataInputControlDozor constructor argument 'keepCbfTmpDirectory' is not XSDataBoolean but %s" % self._keepCbfTmpDirectory.__class__.__name__
            raise BaseException(strMessage)
        if doISPyBUpload is None:
            self._doISPyBUpload = None
        elif doISPyBUpload.__class__.__name__ == "XSDataBoolean":
            self._doISPyBUpload = doISPyBUpload
        else:
            strMessage = (
                "ERROR! XSDataControlImageDozor constructor argument 'doISPyBUpload' is not XSDataBoolean but %s"
                % self._doISPyBUpload.__class__.__name__
            )
            raise Exception(strMessage)
    # Methods and properties for the 'dataCollectionId' attribute
    def getDataCollectionId(self): return self._dataCollectionId
    def setDataCollectionId(self, dataCollectionId):
        if dataCollectionId is None:
            self._dataCollectionId = None
        elif dataCollectionId.__class__.__name__ == "XSDataInteger":
            self._dataCollectionId = dataCollectionId
        else:
            strMessage = "ERROR! XSDataInputControlDozor.setDataCollectionId argument is not XSDataInteger but %s" % dataCollectionId.__class__.__name__
            raise BaseException(strMessage)
    def delDataCollectionId(self): self._dataCollectionId = None
    dataCollectionId = property(getDataCollectionId, setDataCollectionId, delDataCollectionId, "Property for dataCollectionId")
    # Methods and properties for the 'processDirectory' attribute
    def getProcessDirectory(self): return self._processDirectory
    def setProcessDirectory(self, processDirectory):
        if processDirectory is None:
            self._processDirectory = None
        elif processDirectory.__class__.__name__ == "XSDataFile":
            self._processDirectory = processDirectory
        else:
            strMessage = "ERROR! XSDataInputControlDozor.setProcessDirectory argument is not XSDataFile but %s" % processDirectory.__class__.__name__
            raise BaseException(strMessage)
    def delProcessDirectory(self): self._processDirectory = None
    processDirectory = property(getProcessDirectory, setProcessDirectory, delProcessDirectory, "Property for processDirectory")
    # Methods and properties for the 'image' attribute
    def getImage(self): return self._image
    def setImage(self, image):
        if image is None:
            self._image = []
        elif image.__class__.__name__ == "list":
            self._image = image
        else:
            strMessage = "ERROR! XSDataInputControlDozor.setImage argument is not list but %s" % image.__class__.__name__
            raise BaseException(strMessage)
    def delImage(self): self._image = None
    image = property(getImage, setImage, delImage, "Property for image")
    def addImage(self, value):
        if value is None:
            strMessage = "ERROR! XSDataInputControlDozor.addImage argument is None"
            raise BaseException(strMessage)            
        elif value.__class__.__name__ == "XSDataFile":
            self._image.append(value)
        else:
            strMessage = "ERROR! XSDataInputControlDozor.addImage argument is not XSDataFile but %s" % value.__class__.__name__
            raise BaseException(strMessage)
    def insertImage(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataInputControlDozor.insertImage argument 'index' is None"
            raise BaseException(strMessage)            
        if value is None:
            strMessage = "ERROR! XSDataInputControlDozor.insertImage argument 'value' is None"
            raise BaseException(strMessage)            
        elif value.__class__.__name__ == "XSDataFile":
            self._image[index] = value
        else:
            strMessage = "ERROR! XSDataInputControlDozor.addImage argument is not XSDataFile but %s" % value.__class__.__name__
            raise BaseException(strMessage)
    # Methods and properties for the 'directory' attribute
    def getDirectory(self): return self._directory
    def setDirectory(self, directory):
        if directory is None:
            self._directory = None
        elif directory.__class__.__name__ == "XSDataFile":
            self._directory = directory
        else:
            strMessage = "ERROR! XSDataInputControlDozor.setDirectory argument is not XSDataFile but %s" % directory.__class__.__name__
            raise BaseException(strMessage)
    def delDirectory(self): self._directory = None
    directory = property(getDirectory, setDirectory, delDirectory, "Property for directory")
    # Methods and properties for the 'template' attribute
    def getTemplate(self): return self._template
    def setTemplate(self, template):
        if template is None:
            self._template = None
        elif template.__class__.__name__ == "XSDataString":
            self._template = template
        else:
            strMessage = "ERROR! XSDataInputControlDozor.setTemplate argument is not XSDataString but %s" % template.__class__.__name__
            raise BaseException(strMessage)
    def delTemplate(self): self._template = None
    template = property(getTemplate, setTemplate, delTemplate, "Property for template")
    # Methods and properties for the 'startNo' attribute
    def getStartNo(self): return self._startNo
    def setStartNo(self, startNo):
        if startNo is None:
            self._startNo = None
        elif startNo.__class__.__name__ == "XSDataInteger":
            self._startNo = startNo
        else:
            strMessage = "ERROR! XSDataInputControlDozor.setStartNo argument is not XSDataInteger but %s" % startNo.__class__.__name__
            raise BaseException(strMessage)
    def delStartNo(self): self._startNo = None
    startNo = property(getStartNo, setStartNo, delStartNo, "Property for startNo")
    # Methods and properties for the 'endNo' attribute
    def getEndNo(self): return self._endNo
    def setEndNo(self, endNo):
        if endNo is None:
            self._endNo = None
        elif endNo.__class__.__name__ == "XSDataInteger":
            self._endNo = endNo
        else:
            strMessage = "ERROR! XSDataInputControlDozor.setEndNo argument is not XSDataInteger but %s" % endNo.__class__.__name__
            raise BaseException(strMessage)
    def delEndNo(self): self._endNo = None
    endNo = property(getEndNo, setEndNo, delEndNo, "Property for endNo")
    # Methods and properties for the 'batchSize' attribute
    def getBatchSize(self): return self._batchSize
    def setBatchSize(self, batchSize):
        if batchSize is None:
            self._batchSize = None
        elif batchSize.__class__.__name__ == "XSDataInteger":
            self._batchSize = batchSize
        else:
            strMessage = "ERROR! XSDataInputControlDozor.setBatchSize argument is not XSDataInteger but %s" % batchSize.__class__.__name__
            raise BaseException(strMessage)
    def delBatchSize(self): self._batchSize = None
    batchSize = property(getBatchSize, setBatchSize, delBatchSize, "Property for batchSize")
    # Methods and properties for the 'hdf5BatchSize' attribute
    def getHdf5BatchSize(self): return self._hdf5BatchSize
    def setHdf5BatchSize(self, hdf5BatchSize):
        if hdf5BatchSize is None:
            self._hdf5BatchSize = None
        elif hdf5BatchSize.__class__.__name__ == "XSDataInteger":
            self._hdf5BatchSize = hdf5BatchSize
        else:
            strMessage = "ERROR! XSDataInputControlDozor.setHdf5BatchSize argument is not XSDataInteger but %s" % hdf5BatchSize.__class__.__name__
            raise BaseException(strMessage)
    def delHdf5BatchSize(self): self._hdf5BatchSize = None
    hdf5BatchSize = property(getHdf5BatchSize, setHdf5BatchSize, delHdf5BatchSize, "Property for hdf5BatchSize")
    # Methods and properties for the 'wedgeNumber' attribute
    def getWedgeNumber(self): return self._wedgeNumber
    def setWedgeNumber(self, wedgeNumber):
        if wedgeNumber is None:
            self._wedgeNumber = None
        elif wedgeNumber.__class__.__name__ == "XSDataInteger":
            self._wedgeNumber = wedgeNumber
        else:
            strMessage = "ERROR! XSDataInputControlDozor.setWedgeNumber argument is not XSDataInteger but %s" % wedgeNumber.__class__.__name__
            raise BaseException(strMessage)
    def delWedgeNumber(self): self._wedgeNumber = None
    wedgeNumber = property(getWedgeNumber, setWedgeNumber, delWedgeNumber, "Property for wedgeNumber")
    # Methods and properties for the 'radiationDamage' attribute
    def getRadiationDamage(self): return self._radiationDamage
    def setRadiationDamage(self, radiationDamage):
        if radiationDamage is None:
            self._radiationDamage = None
        elif radiationDamage.__class__.__name__ == "XSDataBoolean":
            self._radiationDamage = radiationDamage
        else:
            strMessage = "ERROR! XSDataInputControlDozor.setRadiationDamage argument is not XSDataBoolean but %s" % radiationDamage.__class__.__name__
            raise BaseException(strMessage)
    def delRadiationDamage(self): self._radiationDamage = None
    radiationDamage = property(getRadiationDamage, setRadiationDamage, delRadiationDamage, "Property for radiationDamage")
    # Methods and properties for the 'keepCbfTmpDirectory' attribute
    def getKeepCbfTmpDirectory(self): return self._keepCbfTmpDirectory
    def setKeepCbfTmpDirectory(self, keepCbfTmpDirectory):
        if keepCbfTmpDirectory is None:
            self._keepCbfTmpDirectory = None
        elif keepCbfTmpDirectory.__class__.__name__ == "XSDataBoolean":
            self._keepCbfTmpDirectory = keepCbfTmpDirectory
        else:
            strMessage = "ERROR! XSDataInputControlDozor.setKeepCbfTmpDirectory argument is not XSDataBoolean but %s" % keepCbfTmpDirectory.__class__.__name__
            raise BaseException(strMessage)
    def delKeepCbfTmpDirectory(self): self._keepCbfTmpDirectory = None
    keepCbfTmpDirectory = property(getKeepCbfTmpDirectory, setKeepCbfTmpDirectory, delKeepCbfTmpDirectory, "Property for keepCbfTmpDirectory")
    # Methods and properties for the 'doISPyBUpload' attribute
    def getDoISPyBUpload(self):
        return self._doISPyBUpload

    def setDoISPyBUpload(self, doISPyBUpload):
        if doISPyBUpload is None:
            self._doISPyBUpload = None
        elif doISPyBUpload.__class__.__name__ == "XSDataBoolean":
            self._doISPyBUpload = doISPyBUpload
        else:
            strMessage = (
                "ERROR! XSDataInputControlDozor.setDoISPyBUpload argument is not XSDataBoolean but %s"
                % doISPyBUpload.__class__.__name__
            )
            raise Exception(strMessage)
    def delDoISPyBUpload(self):
        self._doISPyBUpload = None
    doISPyBUpload = property(
        getDoISPyBUpload,
        setDoISPyBUpload,
        delDoISPyBUpload,
        "Property for doISPyBUpload",
    )

    def export(self, outfile, level, name_='XSDataInputControlDozor'):
        showIndent(outfile, level)
        outfile.write(unicode('<%s>\n' % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode('</%s>\n' % name_))
    def exportChildren(self, outfile, level, name_='XSDataInputControlDozor'):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._dataCollectionId is not None:
            self.dataCollectionId.export(outfile, level, name_='dataCollectionId')
        if self._processDirectory is not None:
            self.processDirectory.export(outfile, level, name_='processDirectory')
        for image_ in self.getImage():
            image_.export(outfile, level, name_='image')
        if self._directory is not None:
            self.directory.export(outfile, level, name_='directory')
        if self._template is not None:
            self.template.export(outfile, level, name_='template')
        if self._startNo is not None:
            self.startNo.export(outfile, level, name_='startNo')
        if self._endNo is not None:
            self.endNo.export(outfile, level, name_='endNo')
        if self._batchSize is not None:
            self.batchSize.export(outfile, level, name_='batchSize')
        if self._hdf5BatchSize is not None:
            self.hdf5BatchSize.export(outfile, level, name_='hdf5BatchSize')
        if self._wedgeNumber is not None:
            self.wedgeNumber.export(outfile, level, name_='wedgeNumber')
        if self._radiationDamage is not None:
            self.radiationDamage.export(outfile, level, name_='radiationDamage')
        if self._keepCbfTmpDirectory is not None:
            self.keepCbfTmpDirectory.export(outfile, level, name_='keepCbfTmpDirectory')
        if self._doISPyBUpload is not None:
            self.doISPyBUpload.export(outfile, level, name_="doISPyBUpload")
    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'dataCollectionId':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setDataCollectionId(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'processDirectory':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setProcessDirectory(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'image':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.image.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'directory':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setDirectory(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'template':
            obj_ = XSDataString()
            obj_.build(child_)
            self.setTemplate(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'startNo':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setStartNo(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'endNo':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setEndNo(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'batchSize':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setBatchSize(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'hdf5BatchSize':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setHdf5BatchSize(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'wedgeNumber':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setWedgeNumber(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'radiationDamage':
            obj_ = XSDataBoolean()
            obj_.build(child_)
            self.setRadiationDamage(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'keepCbfTmpDirectory':
            obj_ = XSDataBoolean()
            obj_.build(child_)
            self.setKeepCbfTmpDirectory(obj_)
        elif (
            child_.nodeType == Node.ELEMENT_NODE 
            and nodeName_ == "doISPyBUpload"
        ):
            obj_ = XSDataBoolean()
            obj_.build(child_)
            self.setScore(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)
    #Method for marshalling an object
    def marshal( self ):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export( oStreamString, 0, name_="XSDataInputControlDozor" )
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML
    #Only to export the entire XML tree to a file stream on disk
    def exportToFile( self, _outfileName ):
        outfile = open( _outfileName, "w" )
        outfile.write(unicode('<?xml version=\"1.0\" ?>\n'))
        self.export( outfile, 0, name_='XSDataInputControlDozor' )
        outfile.close()
    #Deprecated method, replaced by exportToFile
    def outputFile( self, _outfileName ):
        print("WARNING: Method outputFile in class XSDataInputControlDozor is deprecated, please use instead exportToFile!")
        self.exportToFile(_outfileName)
    #Method for making a copy in a new instance
    def copy( self ):
        return XSDataInputControlDozor.parseString(self.marshal())
    #Static method for parsing a string
    def parseString( _inString ):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputControlDozor()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export( oStreamString, 0, name_="XSDataInputControlDozor" )
        oStreamString.close()
        return rootObj
    parseString = staticmethod( parseString )
    #Static method for parsing a file
    def parseFile( _inFilePath ):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputControlDozor()
        rootObj.build(rootNode)
        return rootObj
    parseFile = staticmethod( parseFile )
# end class XSDataInputControlDozor


class XSDataResultControlDozor(XSDataResult):
    def __init__(self, status=None, pngPlots=None, pathToCbfDirectory=None, dozorPlot=None, halfDoseTime=None, inputDozor=None, imageDozor=None):
        XSDataResult.__init__(self, status)
        if imageDozor is None:
            self._imageDozor = []
        elif imageDozor.__class__.__name__ == "list":
            self._imageDozor = imageDozor
        else:
            strMessage = "ERROR! XSDataResultControlDozor constructor argument 'imageDozor' is not list but %s" % self._imageDozor.__class__.__name__
            raise BaseException(strMessage)
        if inputDozor is None:
            self._inputDozor = None
        elif inputDozor.__class__.__name__ == "XSDataDozorInput":
            self._inputDozor = inputDozor
        else:
            strMessage = "ERROR! XSDataResultControlDozor constructor argument 'inputDozor' is not XSDataDozorInput but %s" % self._inputDozor.__class__.__name__
            raise BaseException(strMessage)
        if halfDoseTime is None:
            self._halfDoseTime = None
        elif halfDoseTime.__class__.__name__ == "XSDataDouble":
            self._halfDoseTime = halfDoseTime
        else:
            strMessage = "ERROR! XSDataResultControlDozor constructor argument 'halfDoseTime' is not XSDataDouble but %s" % self._halfDoseTime.__class__.__name__
            raise BaseException(strMessage)
        if dozorPlot is None:
            self._dozorPlot = None
        elif dozorPlot.__class__.__name__ == "XSDataFile":
            self._dozorPlot = dozorPlot
        else:
            strMessage = "ERROR! XSDataResultControlDozor constructor argument 'dozorPlot' is not XSDataFile but %s" % self._dozorPlot.__class__.__name__
            raise BaseException(strMessage)
        if pathToCbfDirectory is None:
            self._pathToCbfDirectory = None
        elif pathToCbfDirectory.__class__.__name__ == "XSDataFile":
            self._pathToCbfDirectory = pathToCbfDirectory
        else:
            strMessage = "ERROR! XSDataResultControlDozor constructor argument 'pathToCbfDirectory' is not XSDataFile but %s" % self._pathToCbfDirectory.__class__.__name__
            raise BaseException(strMessage)
        if pngPlots is None:
            self._pngPlots = []
        elif pngPlots.__class__.__name__ == "list":
            self._pngPlots = pngPlots
        else:
            strMessage = "ERROR! XSDataResultControlDozor constructor argument 'pngPlots' is not list but %s" % self._pngPlots.__class__.__name__
            raise BaseException(strMessage)
    # Methods and properties for the 'imageDozor' attribute
    def getImageDozor(self): return self._imageDozor
    def setImageDozor(self, imageDozor):
        if imageDozor is None:
            self._imageDozor = []
        elif imageDozor.__class__.__name__ == "list":
            self._imageDozor = imageDozor
        else:
            strMessage = "ERROR! XSDataResultControlDozor.setImageDozor argument is not list but %s" % imageDozor.__class__.__name__
            raise BaseException(strMessage)
    def delImageDozor(self): self._imageDozor = None
    imageDozor = property(getImageDozor, setImageDozor, delImageDozor, "Property for imageDozor")
    def addImageDozor(self, value):
        if value is None:
            strMessage = "ERROR! XSDataResultControlDozor.addImageDozor argument is None"
            raise BaseException(strMessage)            
        elif value.__class__.__name__ == "XSDataControlImageDozor":
            self._imageDozor.append(value)
        else:
            strMessage = "ERROR! XSDataResultControlDozor.addImageDozor argument is not XSDataControlImageDozor but %s" % value.__class__.__name__
            raise BaseException(strMessage)
    def insertImageDozor(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataResultControlDozor.insertImageDozor argument 'index' is None"
            raise BaseException(strMessage)            
        if value is None:
            strMessage = "ERROR! XSDataResultControlDozor.insertImageDozor argument 'value' is None"
            raise BaseException(strMessage)            
        elif value.__class__.__name__ == "XSDataControlImageDozor":
            self._imageDozor[index] = value
        else:
            strMessage = "ERROR! XSDataResultControlDozor.addImageDozor argument is not XSDataControlImageDozor but %s" % value.__class__.__name__
            raise BaseException(strMessage)
    # Methods and properties for the 'inputDozor' attribute
    def getInputDozor(self): return self._inputDozor
    def setInputDozor(self, inputDozor):
        if inputDozor is None:
            self._inputDozor = None
        elif inputDozor.__class__.__name__ == "XSDataDozorInput":
            self._inputDozor = inputDozor
        else:
            strMessage = "ERROR! XSDataResultControlDozor.setInputDozor argument is not XSDataDozorInput but %s" % inputDozor.__class__.__name__
            raise BaseException(strMessage)
    def delInputDozor(self): self._inputDozor = None
    inputDozor = property(getInputDozor, setInputDozor, delInputDozor, "Property for inputDozor")
    # Methods and properties for the 'halfDoseTime' attribute
    def getHalfDoseTime(self): return self._halfDoseTime
    def setHalfDoseTime(self, halfDoseTime):
        if halfDoseTime is None:
            self._halfDoseTime = None
        elif halfDoseTime.__class__.__name__ == "XSDataDouble":
            self._halfDoseTime = halfDoseTime
        else:
            strMessage = "ERROR! XSDataResultControlDozor.setHalfDoseTime argument is not XSDataDouble but %s" % halfDoseTime.__class__.__name__
            raise BaseException(strMessage)
    def delHalfDoseTime(self): self._halfDoseTime = None
    halfDoseTime = property(getHalfDoseTime, setHalfDoseTime, delHalfDoseTime, "Property for halfDoseTime")
    # Methods and properties for the 'dozorPlot' attribute
    def getDozorPlot(self): return self._dozorPlot
    def setDozorPlot(self, dozorPlot):
        if dozorPlot is None:
            self._dozorPlot = None
        elif dozorPlot.__class__.__name__ == "XSDataFile":
            self._dozorPlot = dozorPlot
        else:
            strMessage = "ERROR! XSDataResultControlDozor.setDozorPlot argument is not XSDataFile but %s" % dozorPlot.__class__.__name__
            raise BaseException(strMessage)
    def delDozorPlot(self): self._dozorPlot = None
    dozorPlot = property(getDozorPlot, setDozorPlot, delDozorPlot, "Property for dozorPlot")
    # Methods and properties for the 'pathToCbfDirectory' attribute
    def getPathToCbfDirectory(self): return self._pathToCbfDirectory
    def setPathToCbfDirectory(self, pathToCbfDirectory):
        if pathToCbfDirectory is None:
            self._pathToCbfDirectory = None
        elif pathToCbfDirectory.__class__.__name__ == "XSDataFile":
            self._pathToCbfDirectory = pathToCbfDirectory
        else:
            strMessage = "ERROR! XSDataResultControlDozor.setPathToCbfDirectory argument is not XSDataFile but %s" % pathToCbfDirectory.__class__.__name__
            raise BaseException(strMessage)
    def delPathToCbfDirectory(self): self._pathToCbfDirectory = None
    pathToCbfDirectory = property(getPathToCbfDirectory, setPathToCbfDirectory, delPathToCbfDirectory, "Property for pathToCbfDirectory")
    # Methods and properties for the 'pngPlots' attribute
    def getPngPlots(self): return self._pngPlots
    def setPngPlots(self, pngPlots):
        if pngPlots is None:
            self._pngPlots = []
        elif pngPlots.__class__.__name__ == "list":
            self._pngPlots = pngPlots
        else:
            strMessage = "ERROR! XSDataResultControlDozor.setPngPlots argument is not list but %s" % pngPlots.__class__.__name__
            raise BaseException(strMessage)
    def delPngPlots(self): self._pngPlots = None
    pngPlots = property(getPngPlots, setPngPlots, delPngPlots, "Property for pngPlots")
    def addPngPlots(self, value):
        if value is None:
            strMessage = "ERROR! XSDataResultControlDozor.addPngPlots argument is None"
            raise BaseException(strMessage)            
        elif value.__class__.__name__ == "XSDataFile":
            self._pngPlots.append(value)
        else:
            strMessage = "ERROR! XSDataResultControlDozor.addPngPlots argument is not XSDataFile but %s" % value.__class__.__name__
            raise BaseException(strMessage)
    def insertPngPlots(self, index, value):
        if index is None:
            strMessage = "ERROR! XSDataResultControlDozor.insertPngPlots argument 'index' is None"
            raise BaseException(strMessage)            
        if value is None:
            strMessage = "ERROR! XSDataResultControlDozor.insertPngPlots argument 'value' is None"
            raise BaseException(strMessage)            
        elif value.__class__.__name__ == "XSDataFile":
            self._pngPlots[index] = value
        else:
            strMessage = "ERROR! XSDataResultControlDozor.addPngPlots argument is not XSDataFile but %s" % value.__class__.__name__
            raise BaseException(strMessage)
    def export(self, outfile, level, name_='XSDataResultControlDozor'):
        showIndent(outfile, level)
        outfile.write(unicode('<%s>\n' % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode('</%s>\n' % name_))
    def exportChildren(self, outfile, level, name_='XSDataResultControlDozor'):
        XSDataResult.exportChildren(self, outfile, level, name_)
        for imageDozor_ in self.getImageDozor():
            imageDozor_.export(outfile, level, name_='imageDozor')
        if self._inputDozor is not None:
            self.inputDozor.export(outfile, level, name_='inputDozor')
        if self._halfDoseTime is not None:
            self.halfDoseTime.export(outfile, level, name_='halfDoseTime')
        if self._dozorPlot is not None:
            self.dozorPlot.export(outfile, level, name_='dozorPlot')
        if self._pathToCbfDirectory is not None:
            self.pathToCbfDirectory.export(outfile, level, name_='pathToCbfDirectory')
        for pngPlots_ in self.getPngPlots():
            pngPlots_.export(outfile, level, name_='pngPlots')
    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'imageDozor':
            obj_ = XSDataControlImageDozor()
            obj_.build(child_)
            self.imageDozor.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'inputDozor':
            obj_ = XSDataDozorInput()
            obj_.build(child_)
            self.setInputDozor(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'halfDoseTime':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setHalfDoseTime(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'dozorPlot':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setDozorPlot(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'pathToCbfDirectory':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setPathToCbfDirectory(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'pngPlots':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.pngPlots.append(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)
    #Method for marshalling an object
    def marshal( self ):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export( oStreamString, 0, name_="XSDataResultControlDozor" )
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML
    #Only to export the entire XML tree to a file stream on disk
    def exportToFile( self, _outfileName ):
        outfile = open( _outfileName, "w" )
        outfile.write(unicode('<?xml version=\"1.0\" ?>\n'))
        self.export( outfile, 0, name_='XSDataResultControlDozor' )
        outfile.close()
    #Deprecated method, replaced by exportToFile
    def outputFile( self, _outfileName ):
        print("WARNING: Method outputFile in class XSDataResultControlDozor is deprecated, please use instead exportToFile!")
        self.exportToFile(_outfileName)
    #Method for making a copy in a new instance
    def copy( self ):
        return XSDataResultControlDozor.parseString(self.marshal())
    #Static method for parsing a string
    def parseString( _inString ):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultControlDozor()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export( oStreamString, 0, name_="XSDataResultControlDozor" )
        oStreamString.close()
        return rootObj
    parseString = staticmethod( parseString )
    #Static method for parsing a file
    def parseFile( _inFilePath ):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultControlDozor()
        rootObj.build(rootNode)
        return rootObj
    parseFile = staticmethod( parseFile )
# end class XSDataResultControlDozor



# End of data representation classes.


