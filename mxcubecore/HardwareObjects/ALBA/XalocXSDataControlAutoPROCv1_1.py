#!/usr/bin/env python

#
# Generated Wed Jul 3 05:01::57 2019 by EDGenerateDS.
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



class XSDataInputControlAutoPROC(XSDataInput):
    def __init__(self, configuration=None, highResolutionLimit=None, lowResolutionLimit=None, reprocess=None, cell=None, symm=None, doAnomAndNonanom=None, doAnom=None, processDirectory=None, toN=None, fromN=None, templateN=None, dirN=None, dataCollectionId=None, configDef=None):
        XSDataInput.__init__(self, configuration)
        if dataCollectionId is None:
            self._dataCollectionId = None
        elif dataCollectionId.__class__.__name__ == "XSDataInteger":
            self._dataCollectionId = dataCollectionId
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'dataCollectionId' is not XSDataInteger but %s" % self._dataCollectionId.__class__.__name__
            raise BaseException(strMessage)
        if dirN is None:
            self._dirN = None
        elif dirN.__class__.__name__ == "XSDataFile":
            self._dirN = dirN
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'dirN' is not XSDataFile but %s" % self._dirN.__class__.__name__
            raise BaseException(strMessage)
        if templateN is None:
            self._templateN = None
        elif templateN.__class__.__name__ == "XSDataString":
            self._templateN = templateN
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'templateN' is not XSDataString but %s" % self._templateN.__class__.__name__
            raise BaseException(strMessage)
        if fromN is None:
            self._fromN = None
        elif fromN.__class__.__name__ == "XSDataInteger":
            self._fromN = fromN
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'fromN' is not XSDataInteger but %s" % self._fromN.__class__.__name__
            raise BaseException(strMessage)
        if toN is None:
            self._toN = None
        elif toN.__class__.__name__ == "XSDataInteger":
            self._toN = toN
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'toN' is not XSDataInteger but %s" % self._toN.__class__.__name__
            raise BaseException(strMessage)
        if processDirectory is None:
            self._processDirectory = None
        elif processDirectory.__class__.__name__ == "XSDataFile":
            self._processDirectory = processDirectory
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'processDirectory' is not XSDataFile but %s" % self._processDirectory.__class__.__name__
            raise BaseException(strMessage)
        if doAnom is None:
            self._doAnom = None
        elif doAnom.__class__.__name__ == "XSDataBoolean":
            self._doAnom = doAnom
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'doAnom' is not XSDataBoolean but %s" % self._doAnom.__class__.__name__
            raise BaseException(strMessage)
        if doAnomAndNonanom is None:
            self._doAnomAndNonanom = None
        elif doAnomAndNonanom.__class__.__name__ == "XSDataBoolean":
            self._doAnomAndNonanom = doAnomAndNonanom
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'doAnomAndNonanom' is not XSDataBoolean but %s" % self._doAnomAndNonanom.__class__.__name__
            raise BaseException(strMessage)
        if symm is None:
            self._symm = None
        elif symm.__class__.__name__ == "XSDataString":
            self._symm = symm
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'symm' is not XSDataString but %s" % self._symm.__class__.__name__
            raise BaseException(strMessage)
        if cell is None:
            self._cell = None
        elif cell.__class__.__name__ == "XSDataString":
            self._cell = cell
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'cell' is not XSDataString but %s" % self._cell.__class__.__name__
            raise BaseException(strMessage)
        if reprocess is None:
            self._reprocess = None
        elif reprocess.__class__.__name__ == "XSDataBoolean":
            self._reprocess = reprocess
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'reprocess' is not XSDataBoolean but %s" % self._reprocess.__class__.__name__
            raise BaseException(strMessage)
        if lowResolutionLimit is None:
            self._lowResolutionLimit = None
        elif lowResolutionLimit.__class__.__name__ == "XSDataDouble":
            self._lowResolutionLimit = lowResolutionLimit
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'lowResolutionLimit' is not XSDataDouble but %s" % self._lowResolutionLimit.__class__.__name__
            raise BaseException(strMessage)
        if highResolutionLimit is None:
            self._highResolutionLimit = None
        elif highResolutionLimit.__class__.__name__ == "XSDataDouble":
            self._highResolutionLimit = highResolutionLimit
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'highResolutionLimit' is not XSDataDouble but %s" % self._highResolutionLimit.__class__.__name__
            raise BaseException(strMessage)
        if configDef is None:
            self._configDef = None
        elif configDef.__class__.__name__ == "XSDataFile":
            self._configDef = configDef
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'configDef' is not XSDataFile but %s" % self._configDef.__class__.__name__
            raise BaseException(strMessage)

    # Methods and properties for the 'dataCollectionId' attribute
    def getDataCollectionId(self): return self._dataCollectionId
    def setDataCollectionId(self, dataCollectionId):
        if dataCollectionId is None:
            self._dataCollectionId = None
        elif dataCollectionId.__class__.__name__ == "XSDataInteger":
            self._dataCollectionId = dataCollectionId
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setDataCollectionId argument is not XSDataInteger but %s" % dataCollectionId.__class__.__name__
            raise BaseException(strMessage)
    def delDataCollectionId(self): self._dataCollectionId = None
    dataCollectionId = property(getDataCollectionId, setDataCollectionId, delDataCollectionId, "Property for dataCollectionId")
    # Methods and properties for the 'dirN' attribute
    def getDirN(self): return self._dirN
    def setDirN(self, dirN):
        if dirN is None:
            self._dirN = None
        elif dirN.__class__.__name__ == "XSDataFile":
            self._dirN = dirN
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setDirN argument is not XSDataFile but %s" % dirN.__class__.__name__
            raise BaseException(strMessage)
    def delDirN(self): self._dirN = None
    dirN = property(getDirN, setDirN, delDirN, "Property for dirN")
    # Methods and properties for the 'templateN' attribute
    def getTemplateN(self): return self._templateN
    def setTemplateN(self, templateN):
        if templateN is None:
            self._templateN = None
        elif templateN.__class__.__name__ == "XSDataString":
            self._templateN = templateN
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setTemplateN argument is not XSDataString but %s" % templateN.__class__.__name__
            raise BaseException(strMessage)
    def delTemplateN(self): self._templateN = None
    templateN = property(getTemplateN, setTemplateN, delTemplateN, "Property for templateN")
    # Methods and properties for the 'fromN' attribute
    def getFromN(self): return self._fromN
    def setFromN(self, fromN):
        if fromN is None:
            self._fromN = None
        elif fromN.__class__.__name__ == "XSDataInteger":
            self._fromN = fromN
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setFromN argument is not XSDataInteger but %s" % fromN.__class__.__name__
            raise BaseException(strMessage)
    def delFromN(self): self._fromN = None
    fromN = property(getFromN, setFromN, delFromN, "Property for fromN")
    # Methods and properties for the 'toN' attribute
    def getToN(self): return self._toN
    def setToN(self, toN):
        if toN is None:
            self._toN = None
        elif toN.__class__.__name__ == "XSDataInteger":
            self._toN = toN
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setToN argument is not XSDataInteger but %s" % toN.__class__.__name__
            raise BaseException(strMessage)
    def delToN(self): self._toN = None
    toN = property(getToN, setToN, delToN, "Property for toN")
    # Methods and properties for the 'processDirectory' attribute
    def getProcessDirectory(self): return self._processDirectory
    def setProcessDirectory(self, processDirectory):
        if processDirectory is None:
            self._processDirectory = None
        elif processDirectory.__class__.__name__ == "XSDataFile":
            self._processDirectory = processDirectory
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setProcessDirectory argument is not XSDataFile but %s" % processDirectory.__class__.__name__
            raise BaseException(strMessage)
    def delProcessDirectory(self): self._processDirectory = None
    processDirectory = property(getProcessDirectory, setProcessDirectory, delProcessDirectory, "Property for processDirectory")
    # Methods and properties for the 'doAnom' attribute
    def getDoAnom(self): return self._doAnom
    def setDoAnom(self, doAnom):
        if doAnom is None:
            self._doAnom = None
        elif doAnom.__class__.__name__ == "XSDataBoolean":
            self._doAnom = doAnom
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setDoAnom argument is not XSDataBoolean but %s" % doAnom.__class__.__name__
            raise BaseException(strMessage)
    def delDoAnom(self): self._doAnom = None
    doAnom = property(getDoAnom, setDoAnom, delDoAnom, "Property for doAnom")
    # Methods and properties for the 'doAnomAndNonanom' attribute
    def getDoAnomAndNonanom(self): return self._doAnomAndNonanom
    def setDoAnomAndNonanom(self, doAnomAndNonanom):
        if doAnomAndNonanom is None:
            self._doAnomAndNonanom = None
        elif doAnomAndNonanom.__class__.__name__ == "XSDataBoolean":
            self._doAnomAndNonanom = doAnomAndNonanom
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setDoAnomAndNonanom argument is not XSDataBoolean but %s" % doAnomAndNonanom.__class__.__name__
            raise BaseException(strMessage)
    def delDoAnomAndNonanom(self): self._doAnomAndNonanom = None
    doAnomAndNonanom = property(getDoAnomAndNonanom, setDoAnomAndNonanom, delDoAnomAndNonanom, "Property for doAnomAndNonanom")
    # Methods and properties for the 'symm' attribute
    def getSymm(self): return self._symm
    def setSymm(self, symm):
        if symm is None:
            self._symm = None
        elif symm.__class__.__name__ == "XSDataString":
            self._symm = symm
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setSymm argument is not XSDataString but %s" % symm.__class__.__name__
            raise BaseException(strMessage)
    def delSymm(self): self._symm = None
    symm = property(getSymm, setSymm, delSymm, "Property for symm")
    setSpacegroup = setSymm
    getSpacegroup = getSymm
    delSpacegroup = delSymm
    # Methods and properties for the 'configDef' attribute
    def getConfigDef(self): return self._configDef
    def setConfigDef(self, configDef):
        if configDef is None:
            self._configDef = None
        elif configDef.__class__.__name__ == "XSDataFile":
            self._configDef = configDef
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setDirN argument is not XSDataFile but %s" % configDef.__class__.__name__
            raise BaseException(strMessage)
    def delConfigDef(self): self._configDef = None
    configDef = property(getConfigDef, setConfigDef, delConfigDef, "Property for configDef")
    # Methods and properties for the 'cell' attribute
    def getCell(self): return self._cell
    def setCell(self, cell):
        if cell is None:
            self._cell = None
        elif cell.__class__.__name__ == "XSDataString":
            self._cell = cell
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setCell argument is not XSDataString but %s" % cell.__class__.__name__
            raise BaseException(strMessage)
    def delCell(self): self._cell = None
    cell = property(getCell, setCell, delCell, "Property for cell")
    # Methods and properties for the 'reprocess' attribute
    def getReprocess(self): return self._reprocess
    def setReprocess(self, reprocess):
        if reprocess is None:
            self._reprocess = None
        elif reprocess.__class__.__name__ == "XSDataBoolean":
            self._reprocess = reprocess
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setReprocess argument is not XSDataBoolean but %s" % reprocess.__class__.__name__
            raise BaseException(strMessage)
    def delReprocess(self): self._reprocess = None
    reprocess = property(getReprocess, setReprocess, delReprocess, "Property for reprocess")
    # Methods and properties for the 'lowResolutionLimit' attribute
    def getLowResolutionLimit(self): return self._lowResolutionLimit
    def setLowResolutionLimit(self, lowResolutionLimit):
        if lowResolutionLimit is None:
            self._lowResolutionLimit = None
        elif lowResolutionLimit.__class__.__name__ == "XSDataDouble":
            self._lowResolutionLimit = lowResolutionLimit
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setLowResolutionLimit argument is not XSDataDouble but %s" % lowResolutionLimit.__class__.__name__
            raise BaseException(strMessage)
    def delLowResolutionLimit(self): self._lowResolutionLimit = None
    lowResolutionLimit = property(getLowResolutionLimit, setLowResolutionLimit, delLowResolutionLimit, "Property for lowResolutionLimit")
    # Methods and properties for the 'highResolutionLimit' attribute
    def getHighResolutionLimit(self): return self._highResolutionLimit
    def setHighResolutionLimit(self, highResolutionLimit):
        if highResolutionLimit is None:
            self._highResolutionLimit = None
        elif highResolutionLimit.__class__.__name__ == "XSDataDouble":
            self._highResolutionLimit = highResolutionLimit
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.setHighResolutionLimit argument is not XSDataDouble but %s" % highResolutionLimit.__class__.__name__
            raise BaseException(strMessage)
    def delHighResolutionLimit(self): self._highResolutionLimit = None
    highResolutionLimit = property(getHighResolutionLimit, setHighResolutionLimit, delHighResolutionLimit, "Property for highResolutionLimit")
    def export(self, outfile, level, name_='XSDataInputControlAutoPROC'):
        showIndent(outfile, level)
        outfile.write(unicode('<%s>\n' % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode('</%s>\n' % name_))
    def exportChildren(self, outfile, level, name_='XSDataInputControlAutoPROC'):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._dataCollectionId is not None:
            self.dataCollectionId.export(outfile, level, name_='dataCollectionId')
        if self._dirN is not None:
            self.dirN.export(outfile, level, name_='dirN')
        if self._configDef is not None:
            self.configDef.export(outfile, level, name_='configDef')
        if self._templateN is not None:
            self.templateN.export(outfile, level, name_='templateN')
        if self._fromN is not None:
            self.fromN.export(outfile, level, name_='fromN')
        if self._toN is not None:
            self.toN.export(outfile, level, name_='toN')
        if self._processDirectory is not None:
            self.processDirectory.export(outfile, level, name_='processDirectory')
        if self._doAnom is not None:
            self.doAnom.export(outfile, level, name_='doAnom')
        if self._doAnomAndNonanom is not None:
            self.doAnomAndNonanom.export(outfile, level, name_='doAnomAndNonanom')
        if self._symm is not None:
            self.symm.export(outfile, level, name_='symm')
        if self._cell is not None:
            self.cell.export(outfile, level, name_='cell')
        if self._reprocess is not None:
            self.reprocess.export(outfile, level, name_='reprocess')
        if self._lowResolutionLimit is not None:
            self.lowResolutionLimit.export(outfile, level, name_='lowResolutionLimit')
        if self._highResolutionLimit is not None:
            self.highResolutionLimit.export(outfile, level, name_='highResolutionLimit')
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
            nodeName_ == 'dirN':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setDirN(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'configDef':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setConfigDef(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'templateN':
            obj_ = XSDataString()
            obj_.build(child_)
            self.setTemplateN(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'fromN':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setFromN(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'toN':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setToN(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'processDirectory':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setProcessDirectory(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'doAnom':
            obj_ = XSDataBoolean()
            obj_.build(child_)
            self.setDoAnom(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'doAnomAndNonanom':
            obj_ = XSDataBoolean()
            obj_.build(child_)
            self.setDoAnomAndNonanom(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'symm':
            obj_ = XSDataString()
            obj_.build(child_)
            self.setSymm(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'cell':
            obj_ = XSDataString()
            obj_.build(child_)
            self.setCell(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'reprocess':
            obj_ = XSDataBoolean()
            obj_.build(child_)
            self.setReprocess(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'lowResolutionLimit':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setLowResolutionLimit(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'highResolutionLimit':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setHighResolutionLimit(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)
    #Method for marshalling an object
    def marshal( self ):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export( oStreamString, 0, name_="XSDataInputControlAutoPROC" )
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML
    #Only to export the entire XML tree to a file stream on disk
    def exportToFile( self, _outfileName ):
        outfile = open( _outfileName, "w" )
        outfile.write(unicode('<?xml version=\"1.0\" ?>\n'))
        self.export( outfile, 0, name_='XSDataInputControlAutoPROC' )
        outfile.close()
    #Deprecated method, replaced by exportToFile
    def outputFile( self, _outfileName ):
        print("WARNING: Method outputFile in class XSDataInputControlAutoPROC is deprecated, please use instead exportToFile!")
        self.exportToFile(_outfileName)
    #Method for making a copy in a new instance
    def copy( self ):
        return XSDataInputControlAutoPROC.parseString(self.marshal())
    #Static method for parsing a string
    def parseString( _inString ):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputControlAutoPROC()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export( oStreamString, 0, name_="XSDataInputControlAutoPROC" )
        oStreamString.close()
        return rootObj
    parseString = staticmethod( parseString )
    #Static method for parsing a file
    def parseFile( _inFilePath ):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputControlAutoPROC()
        rootObj.build(rootNode)
        return rootObj
    parseFile = staticmethod( parseFile )
# end class XSDataInputControlAutoPROC


class XSDataResultControlAutoPROC(XSDataResult):
    def __init__(self, status=None):
        XSDataResult.__init__(self, status)
    def export(self, outfile, level, name_='XSDataResultControlAutoPROC'):
        showIndent(outfile, level)
        outfile.write(unicode('<%s>\n' % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode('</%s>\n' % name_))
    def exportChildren(self, outfile, level, name_='XSDataResultControlAutoPROC'):
        XSDataResult.exportChildren(self, outfile, level, name_)
    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildChildren(self, child_, nodeName_):
        pass
        XSDataResult.buildChildren(self, child_, nodeName_)
    #Method for marshalling an object
    def marshal( self ):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export( oStreamString, 0, name_="XSDataResultControlAutoPROC" )
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML
    #Only to export the entire XML tree to a file stream on disk
    def exportToFile( self, _outfileName ):
        outfile = open( _outfileName, "w" )
        outfile.write(unicode('<?xml version=\"1.0\" ?>\n'))
        self.export( outfile, 0, name_='XSDataResultControlAutoPROC' )
        outfile.close()
    #Deprecated method, replaced by exportToFile
    def outputFile( self, _outfileName ):
        print("WARNING: Method outputFile in class XSDataResultControlAutoPROC is deprecated, please use instead exportToFile!")
        self.exportToFile(_outfileName)
    #Method for making a copy in a new instance
    def copy( self ):
        return XSDataResultControlAutoPROC.parseString(self.marshal())
    #Static method for parsing a string
    def parseString( _inString ):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultControlAutoPROC()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export( oStreamString, 0, name_="XSDataResultControlAutoPROC" )
        oStreamString.close()
        return rootObj
    parseString = staticmethod( parseString )
    #Static method for parsing a file
    def parseFile( _inFilePath ):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultControlAutoPROC()
        rootObj.build(rootNode)
        return rootObj
    parseFile = staticmethod( parseFile )
# end class XSDataResultControlAutoPROC


class XSDataInputControlDimpleAP(XSDataInput):
    def __init__(self, configuration=None, resultsDirectory=None, autoProcProgramId=None, pdbDirectory=None, beamline=None, sessionDate=None, proposal=None, imagePrefix=None, pyarchPath=None, mtzFile=None, dataCollectionId=None):
        XSDataInput.__init__(self, configuration)
        if dataCollectionId is None:
            self._dataCollectionId = None
        elif dataCollectionId.__class__.__name__ == "XSDataInteger":
            self._dataCollectionId = dataCollectionId
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP constructor argument 'dataCollectionId' is not XSDataInteger but %s" % self._dataCollectionId.__class__.__name__
            raise BaseException(strMessage)
        if mtzFile is None:
            self._mtzFile = None
        elif mtzFile.__class__.__name__ == "XSDataFile":
            self._mtzFile = mtzFile
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP constructor argument 'mtzFile' is not XSDataFile but %s" % self._mtzFile.__class__.__name__
            raise BaseException(strMessage)
        if pyarchPath is None:
            self._pyarchPath = None
        elif pyarchPath.__class__.__name__ == "XSDataFile":
            self._pyarchPath = pyarchPath
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP constructor argument 'pyarchPath' is not XSDataFile but %s" % self._pyarchPath.__class__.__name__
            raise BaseException(strMessage)
        if imagePrefix is None:
            self._imagePrefix = None
        elif imagePrefix.__class__.__name__ == "XSDataString":
            self._imagePrefix = imagePrefix
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP constructor argument 'imagePrefix' is not XSDataString but %s" % self._imagePrefix.__class__.__name__
            raise BaseException(strMessage)
        if proposal is None:
            self._proposal = None
        elif proposal.__class__.__name__ == "XSDataString":
            self._proposal = proposal
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP constructor argument 'proposal' is not XSDataString but %s" % self._proposal.__class__.__name__
            raise BaseException(strMessage)
        if sessionDate is None:
            self._sessionDate = None
        elif sessionDate.__class__.__name__ == "XSDataString":
            self._sessionDate = sessionDate
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP constructor argument 'sessionDate' is not XSDataString but %s" % self._sessionDate.__class__.__name__
            raise BaseException(strMessage)
        if beamline is None:
            self._beamline = None
        elif beamline.__class__.__name__ == "XSDataString":
            self._beamline = beamline
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP constructor argument 'beamline' is not XSDataString but %s" % self._beamline.__class__.__name__
            raise BaseException(strMessage)
        if pdbDirectory is None:
            self._pdbDirectory = None
        elif pdbDirectory.__class__.__name__ == "XSDataFile":
            self._pdbDirectory = pdbDirectory
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP constructor argument 'pdbDirectory' is not XSDataFile but %s" % self._pdbDirectory.__class__.__name__
            raise BaseException(strMessage)
        if autoProcProgramId is None:
            self._autoProcProgramId = None
        elif autoProcProgramId.__class__.__name__ == "XSDataInteger":
            self._autoProcProgramId = autoProcProgramId
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP constructor argument 'autoProcProgramId' is not XSDataInteger but %s" % self._autoProcProgramId.__class__.__name__
            raise BaseException(strMessage)
        if resultsDirectory is None:
            self._resultsDirectory = None
        elif resultsDirectory.__class__.__name__ == "XSDataFile":
            self._resultsDirectory = resultsDirectory
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP constructor argument 'resultsDirectory' is not XSDataFile but %s" % self._resultsDirectory.__class__.__name__
            raise BaseException(strMessage)
    # Methods and properties for the 'dataCollectionId' attribute
    def getDataCollectionId(self): return self._dataCollectionId
    def setDataCollectionId(self, dataCollectionId):
        if dataCollectionId is None:
            self._dataCollectionId = None
        elif dataCollectionId.__class__.__name__ == "XSDataInteger":
            self._dataCollectionId = dataCollectionId
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP.setDataCollectionId argument is not XSDataInteger but %s" % dataCollectionId.__class__.__name__
            raise BaseException(strMessage)
    def delDataCollectionId(self): self._dataCollectionId = None
    dataCollectionId = property(getDataCollectionId, setDataCollectionId, delDataCollectionId, "Property for dataCollectionId")
    # Methods and properties for the 'mtzFile' attribute
    def getMtzFile(self): return self._mtzFile
    def setMtzFile(self, mtzFile):
        if mtzFile is None:
            self._mtzFile = None
        elif mtzFile.__class__.__name__ == "XSDataFile":
            self._mtzFile = mtzFile
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP.setMtzFile argument is not XSDataFile but %s" % mtzFile.__class__.__name__
            raise BaseException(strMessage)
    def delMtzFile(self): self._mtzFile = None
    mtzFile = property(getMtzFile, setMtzFile, delMtzFile, "Property for mtzFile")
    # Methods and properties for the 'pyarchPath' attribute
    def getPyarchPath(self): return self._pyarchPath
    def setPyarchPath(self, pyarchPath):
        if pyarchPath is None:
            self._pyarchPath = None
        elif pyarchPath.__class__.__name__ == "XSDataFile":
            self._pyarchPath = pyarchPath
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP.setPyarchPath argument is not XSDataFile but %s" % pyarchPath.__class__.__name__
            raise BaseException(strMessage)
    def delPyarchPath(self): self._pyarchPath = None
    pyarchPath = property(getPyarchPath, setPyarchPath, delPyarchPath, "Property for pyarchPath")
    # Methods and properties for the 'imagePrefix' attribute
    def getImagePrefix(self): return self._imagePrefix
    def setImagePrefix(self, imagePrefix):
        if imagePrefix is None:
            self._imagePrefix = None
        elif imagePrefix.__class__.__name__ == "XSDataString":
            self._imagePrefix = imagePrefix
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP.setImagePrefix argument is not XSDataString but %s" % imagePrefix.__class__.__name__
            raise BaseException(strMessage)
    def delImagePrefix(self): self._imagePrefix = None
    imagePrefix = property(getImagePrefix, setImagePrefix, delImagePrefix, "Property for imagePrefix")
    # Methods and properties for the 'proposal' attribute
    def getProposal(self): return self._proposal
    def setProposal(self, proposal):
        if proposal is None:
            self._proposal = None
        elif proposal.__class__.__name__ == "XSDataString":
            self._proposal = proposal
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP.setProposal argument is not XSDataString but %s" % proposal.__class__.__name__
            raise BaseException(strMessage)
    def delProposal(self): self._proposal = None
    proposal = property(getProposal, setProposal, delProposal, "Property for proposal")
    # Methods and properties for the 'sessionDate' attribute
    def getSessionDate(self): return self._sessionDate
    def setSessionDate(self, sessionDate):
        if sessionDate is None:
            self._sessionDate = None
        elif sessionDate.__class__.__name__ == "XSDataString":
            self._sessionDate = sessionDate
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP.setSessionDate argument is not XSDataString but %s" % sessionDate.__class__.__name__
            raise BaseException(strMessage)
    def delSessionDate(self): self._sessionDate = None
    sessionDate = property(getSessionDate, setSessionDate, delSessionDate, "Property for sessionDate")
    # Methods and properties for the 'beamline' attribute
    def getBeamline(self): return self._beamline
    def setBeamline(self, beamline):
        if beamline is None:
            self._beamline = None
        elif beamline.__class__.__name__ == "XSDataString":
            self._beamline = beamline
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP.setBeamline argument is not XSDataString but %s" % beamline.__class__.__name__
            raise BaseException(strMessage)
    def delBeamline(self): self._beamline = None
    beamline = property(getBeamline, setBeamline, delBeamline, "Property for beamline")
    # Methods and properties for the 'pdbDirectory' attribute
    def getPdbDirectory(self): return self._pdbDirectory
    def setPdbDirectory(self, pdbDirectory):
        if pdbDirectory is None:
            self._pdbDirectory = None
        elif pdbDirectory.__class__.__name__ == "XSDataFile":
            self._pdbDirectory = pdbDirectory
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP.setPdbDirectory argument is not XSDataFile but %s" % pdbDirectory.__class__.__name__
            raise BaseException(strMessage)
    def delPdbDirectory(self): self._pdbDirectory = None
    pdbDirectory = property(getPdbDirectory, setPdbDirectory, delPdbDirectory, "Property for pdbDirectory")
    # Methods and properties for the 'autoProcProgramId' attribute
    def getAutoProcProgramId(self): return self._autoProcProgramId
    def setAutoProcProgramId(self, autoProcProgramId):
        if autoProcProgramId is None:
            self._autoProcProgramId = None
        elif autoProcProgramId.__class__.__name__ == "XSDataInteger":
            self._autoProcProgramId = autoProcProgramId
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP.setAutoProcProgramId argument is not XSDataInteger but %s" % autoProcProgramId.__class__.__name__
            raise BaseException(strMessage)
    def delAutoProcProgramId(self): self._autoProcProgramId = None
    autoProcProgramId = property(getAutoProcProgramId, setAutoProcProgramId, delAutoProcProgramId, "Property for autoProcProgramId")
    # Methods and properties for the 'resultsDirectory' attribute
    def getResultsDirectory(self): return self._resultsDirectory
    def setResultsDirectory(self, resultsDirectory):
        if resultsDirectory is None:
            self._resultsDirectory = None
        elif resultsDirectory.__class__.__name__ == "XSDataFile":
            self._resultsDirectory = resultsDirectory
        else:
            strMessage = "ERROR! XSDataInputControlDimpleAP.setResultsDirectory argument is not XSDataFile but %s" % resultsDirectory.__class__.__name__
            raise BaseException(strMessage)
    def delResultsDirectory(self): self._resultsDirectory = None
    resultsDirectory = property(getResultsDirectory, setResultsDirectory, delResultsDirectory, "Property for resultsDirectory")
    def export(self, outfile, level, name_='XSDataInputControlDimpleAP'):
        showIndent(outfile, level)
        outfile.write(unicode('<%s>\n' % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode('</%s>\n' % name_))
    def exportChildren(self, outfile, level, name_='XSDataInputControlDimpleAP'):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._dataCollectionId is not None:
            self.dataCollectionId.export(outfile, level, name_='dataCollectionId')
        else:
            warnEmptyAttribute("dataCollectionId", "XSDataInteger")
        if self._mtzFile is not None:
            self.mtzFile.export(outfile, level, name_='mtzFile')
        else:
            warnEmptyAttribute("mtzFile", "XSDataFile")
        if self._pyarchPath is not None:
            self.pyarchPath.export(outfile, level, name_='pyarchPath')
        else:
            warnEmptyAttribute("pyarchPath", "XSDataFile")
        if self._imagePrefix is not None:
            self.imagePrefix.export(outfile, level, name_='imagePrefix')
        else:
            warnEmptyAttribute("imagePrefix", "XSDataString")
        if self._proposal is not None:
            self.proposal.export(outfile, level, name_='proposal')
        else:
            warnEmptyAttribute("proposal", "XSDataString")
        if self._sessionDate is not None:
            self.sessionDate.export(outfile, level, name_='sessionDate')
        else:
            warnEmptyAttribute("sessionDate", "XSDataString")
        if self._beamline is not None:
            self.beamline.export(outfile, level, name_='beamline')
        else:
            warnEmptyAttribute("beamline", "XSDataString")
        if self._pdbDirectory is not None:
            self.pdbDirectory.export(outfile, level, name_='pdbDirectory')
        if self._autoProcProgramId is not None:
            self.autoProcProgramId.export(outfile, level, name_='autoProcProgramId')
        if self._resultsDirectory is not None:
            self.resultsDirectory.export(outfile, level, name_='resultsDirectory')
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
            nodeName_ == 'mtzFile':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setMtzFile(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'pyarchPath':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setPyarchPath(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'imagePrefix':
            obj_ = XSDataString()
            obj_.build(child_)
            self.setImagePrefix(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'proposal':
            obj_ = XSDataString()
            obj_.build(child_)
            self.setProposal(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sessionDate':
            obj_ = XSDataString()
            obj_.build(child_)
            self.setSessionDate(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'beamline':
            obj_ = XSDataString()
            obj_.build(child_)
            self.setBeamline(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'pdbDirectory':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setPdbDirectory(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'autoProcProgramId':
            obj_ = XSDataInteger()
            obj_.build(child_)
            self.setAutoProcProgramId(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'resultsDirectory':
            obj_ = XSDataFile()
            obj_.build(child_)
            self.setResultsDirectory(obj_)
        XSDataInput.buildChildren(self, child_, nodeName_)
    #Method for marshalling an object
    def marshal( self ):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export( oStreamString, 0, name_="XSDataInputControlDimpleAP" )
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML
    #Only to export the entire XML tree to a file stream on disk
    def exportToFile( self, _outfileName ):
        outfile = open( _outfileName, "w" )
        outfile.write(unicode('<?xml version=\"1.0\" ?>\n'))
        self.export( outfile, 0, name_='XSDataInputControlDimpleAP' )
        outfile.close()
    #Deprecated method, replaced by exportToFile
    def outputFile( self, _outfileName ):
        print("WARNING: Method outputFile in class XSDataInputControlDimpleAP is deprecated, please use instead exportToFile!")
        self.exportToFile(_outfileName)
    #Method for making a copy in a new instance
    def copy( self ):
        return XSDataInputControlDimpleAP.parseString(self.marshal())
    #Static method for parsing a string
    def parseString( _inString ):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataInputControlDimpleAP()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export( oStreamString, 0, name_="XSDataInputControlDimpleAP" )
        oStreamString.close()
        return rootObj
    parseString = staticmethod( parseString )
    #Static method for parsing a file
    def parseFile( _inFilePath ):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataInputControlDimpleAP()
        rootObj.build(rootNode)
        return rootObj
    parseFile = staticmethod( parseFile )
# end class XSDataInputControlDimpleAP


class XSDataResultControlDimpleAP(XSDataResult):
    def __init__(self, status=None, dimpleExecutedSuccessfully=None):
        XSDataResult.__init__(self, status)
        if dimpleExecutedSuccessfully is None:
            self._dimpleExecutedSuccessfully = None
        elif dimpleExecutedSuccessfully.__class__.__name__ == "XSDataBoolean":
            self._dimpleExecutedSuccessfully = dimpleExecutedSuccessfully
        else:
            strMessage = "ERROR! XSDataResultControlDimpleAP constructor argument 'dimpleExecutedSuccessfully' is not XSDataBoolean but %s" % self._dimpleExecutedSuccessfully.__class__.__name__
            raise BaseException(strMessage)
    # Methods and properties for the 'dimpleExecutedSuccessfully' attribute
    def getDimpleExecutedSuccessfully(self): return self._dimpleExecutedSuccessfully
    def setDimpleExecutedSuccessfully(self, dimpleExecutedSuccessfully):
        if dimpleExecutedSuccessfully is None:
            self._dimpleExecutedSuccessfully = None
        elif dimpleExecutedSuccessfully.__class__.__name__ == "XSDataBoolean":
            self._dimpleExecutedSuccessfully = dimpleExecutedSuccessfully
        else:
            strMessage = "ERROR! XSDataResultControlDimpleAP.setDimpleExecutedSuccessfully argument is not XSDataBoolean but %s" % dimpleExecutedSuccessfully.__class__.__name__
            raise BaseException(strMessage)
    def delDimpleExecutedSuccessfully(self): self._dimpleExecutedSuccessfully = None
    dimpleExecutedSuccessfully = property(getDimpleExecutedSuccessfully, setDimpleExecutedSuccessfully, delDimpleExecutedSuccessfully, "Property for dimpleExecutedSuccessfully")
    def export(self, outfile, level, name_='XSDataResultControlDimpleAP'):
        showIndent(outfile, level)
        outfile.write(unicode('<%s>\n' % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode('</%s>\n' % name_))
    def exportChildren(self, outfile, level, name_='XSDataResultControlDimpleAP'):
        XSDataResult.exportChildren(self, outfile, level, name_)
        if self._dimpleExecutedSuccessfully is not None:
            self.dimpleExecutedSuccessfully.export(outfile, level, name_='dimpleExecutedSuccessfully')
        else:
            warnEmptyAttribute("dimpleExecutedSuccessfully", "XSDataBoolean")
    def build(self, node_):
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'dimpleExecutedSuccessfully':
            obj_ = XSDataBoolean()
            obj_.build(child_)
            self.setDimpleExecutedSuccessfully(obj_)
        XSDataResult.buildChildren(self, child_, nodeName_)
    #Method for marshalling an object
    def marshal( self ):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export( oStreamString, 0, name_="XSDataResultControlDimpleAP" )
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML
    #Only to export the entire XML tree to a file stream on disk
    def exportToFile( self, _outfileName ):
        outfile = open( _outfileName, "w" )
        outfile.write(unicode('<?xml version=\"1.0\" ?>\n'))
        self.export( outfile, 0, name_='XSDataResultControlDimpleAP' )
        outfile.close()
    #Deprecated method, replaced by exportToFile
    def outputFile( self, _outfileName ):
        print("WARNING: Method outputFile in class XSDataResultControlDimpleAP is deprecated, please use instead exportToFile!")
        self.exportToFile(_outfileName)
    #Method for making a copy in a new instance
    def copy( self ):
        return XSDataResultControlDimpleAP.parseString(self.marshal())
    #Static method for parsing a string
    def parseString( _inString ):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XSDataResultControlDimpleAP()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export( oStreamString, 0, name_="XSDataResultControlDimpleAP" )
        oStreamString.close()
        return rootObj
    parseString = staticmethod( parseString )
    #Static method for parsing a file
    def parseFile( _inFilePath ):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XSDataResultControlDimpleAP()
        rootObj.build(rootNode)
        return rootObj
    parseFile = staticmethod( parseFile )
# end class XSDataResultControlDimpleAP

# End of data representation classes.


