#!/usr/bin/env python

#
# Generated Mon Feb 5 08:54::10 2018 by EDGenerateDS.
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
}

try:
    from XSDataCommon import XSDataBoolean
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



class XalocXSDataInputXia2DIALS(XSDataInput):
    def __init__(self, 
                 configuration=None, 
                 cell=None, 
                 symm=None, 
                 doAnomAndNonanom=None, 
                 processDirectory=None, 
                 toN=None, 
                 fromN=None, 
                 templateN=None, 
                 dirN=None, 
                 dataCollectionId=None, 
                 diffractionImage = None, 
                 small_molecule_3dii = None,
                 detector_max_res=None
                ):
        XSDataInput.__init__(self, configuration)
        if dataCollectionId is None:
            self._dataCollectionId = None
        elif dataCollectionId.__class__.__name__ == "XSDataInteger":
            self._dataCollectionId = dataCollectionId
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS constructor argument 'dataCollectionId' is not XSDataInteger but %s" % self._dataCollectionId.__class__.__name__
            raise BaseException(strMessage)
        if diffractionImage is None:
            self._diffractionImage = None
        elif diffractionImage.__class__.__name__ == "XSDataBoolean":
            self._diffractionImage = diffractionImage
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'diffractionImage' is not XSDataBoolean but %s" % diffractionImage.__class__.__name__
            raise BaseException(strMessage)
        if dirN is None:
            self._dirN = None
        elif dirN.__class__.__name__ == "XSDataFile":
            self._dirN = dirN
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS constructor argument 'dirN' is not XSDataFile but %s" % self._dirN.__class__.__name__
            raise BaseException(strMessage)
        if templateN is None:
            self._templateN = None
        elif templateN.__class__.__name__ == "XSDataString":
            self._templateN = templateN
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS constructor argument 'templateN' is not XSDataString but %s" % self._templateN.__class__.__name__
            raise BaseException(strMessage)
        if fromN is None:
            self._fromN = None
        elif fromN.__class__.__name__ == "XSDataInteger":
            self._fromN = fromN
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS constructor argument 'fromN' is not XSDataInteger but %s" % self._fromN.__class__.__name__
            raise BaseException(strMessage)
        if toN is None:
            self._toN = None
        elif toN.__class__.__name__ == "XSDataInteger":
            self._toN = toN
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS constructor argument 'toN' is not XSDataInteger but %s" % self._toN.__class__.__name__
            raise BaseException(strMessage)
        if processDirectory is None:
            self._processDirectory = None
        elif processDirectory.__class__.__name__ == "XSDataFile":
            self._processDirectory = processDirectory
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS constructor argument 'processDirectory' is not XSDataFile but %s" % self._processDirectory.__class__.__name__
            raise BaseException(strMessage)
        if doAnomAndNonanom is None:
            self._doAnomAndNonanom = None
        elif doAnomAndNonanom.__class__.__name__ == "XSDataBoolean":
            self._doAnomAndNonanom = doAnomAndNonanom
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS constructor argument 'doAnomAndNonanom' is not XSDataBoolean but %s" % self._doAnomAndNonanom.__class__.__name__
            raise BaseException(strMessage)
        if symm is None:
            self._symm = None
        elif symm.__class__.__name__ == "XSDataString":
            self._symm = symm
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS constructor argument 'symm' is not XSDataString but %s" % self._symm.__class__.__name__
            raise BaseException(strMessage)
        if cell is None:
            self._cell = None
        elif cell.__class__.__name__ == "XSDataString":
            self._cell = cell
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS constructor argument 'cell' is not XSDataString but %s" % self._cell.__class__.__name__
            raise BaseException(strMessage)
        if small_molecule_3dii is None:
            self._small_molecule_3dii = None
        elif small_molecule_3dii.__class__.__name__ == "XSDataBoolean":
            self._small_molecule_3dii = small_molecule_3dii
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC constructor argument 'small_molecule_3dii' is not XSDataBoolean but %s" % small_molecule_3dii.__class__.__name__
            raise BaseException(strMessage)
        if detector_max_res is None:
            self._detector_max_res = None
        elif detector_max_res.__class__.__name__ == "XSDataDouble":
            self._detector_max_res = detector_max_res
        else:
            strMessage = (
                "ERROR! XSDataAutoprocInput constructor argument 'detector_max_res' is not XSDataDouble but %s"
                % self._detector_max_res.__class__.__name__
            )
            raise Exception(strMessage)

        
    # Methods and properties for the 'small_molecule_3dii' attribute, used for xia2 small molecule processing
    def get_small_molecule_3dii(self): return self._small_molecule_3dii
    def set_small_molecule_3dii(self, small_molecule_3dii):
        if small_molecule_3dii is None:
            self._small_molecule_3dii = None
        elif small_molecule_3dii.__class__.__name__ == "XSDataBoolean":
            self._small_molecule_3dii = small_molecule_3dii
        else:
            strMessage = "ERROR! XSDataInputControlAutoPROC.set_small_molecule_3dii argument is not XSDataBoolean but %s" % small_molecule_3dii.__class__.__name__
            raise BaseException(strMessage)
    def del_small_molecule_3dii(self): self._small_molecule_3dii = None

    # Methods and properties for the 'dataCollectionId' attribute
    def getDataCollectionId(self): return self._dataCollectionId
    def setDataCollectionId(self, dataCollectionId):
        if dataCollectionId is None:
            self._dataCollectionId = None
        elif dataCollectionId.__class__.__name__ == "XSDataInteger":
            self._dataCollectionId = dataCollectionId
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS.setDataCollectionId argument is not XSDataInteger but %s" % dataCollectionId.__class__.__name__
            raise BaseException(strMessage)
    def delDataCollectionId(self): self._dataCollectionId = None
    dataCollectionId = property(getDataCollectionId, setDataCollectionId, delDataCollectionId, "Property for dataCollectionId")
    # Methods and properties for the 'image' attribute
    def getDiffractionImage(self): return self._diffractionImage
    def setDiffractionImage(self, image):
        if image is None:
            self._diffractionImage = None
        elif image.__class__.__name__ == "XSDataString":
            self._diffractionImage = image
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS.setDiffractionImage argument is not XSDataString but %s" % image.__class__.__name__
            raise BaseException(strMessage)
    def delDiffractionImage(self): self._diffractionImage = None
    diffractionImage = property(getDiffractionImage, setDiffractionImage, delDiffractionImage, "Property for diffractionImage")
    # Methods and properties for the 'dirN' attribute
    def getDirN(self): return self._dirN
    def setDirN(self, dirN):
        if dirN is None:
            self._dirN = None
        elif dirN.__class__.__name__ == "XSDataFile":
            self._dirN = dirN
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS.setDirN argument is not XSDataFile but %s" % dirN.__class__.__name__
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
            strMessage = "ERROR! XalocXSDataInputXia2DIALS.setTemplateN argument is not XSDataString but %s" % templateN.__class__.__name__
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
            strMessage = "ERROR! XalocXSDataInputXia2DIALS.setFromN argument is not XSDataInteger but %s" % fromN.__class__.__name__
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
            strMessage = "ERROR! XalocXSDataInputXia2DIALS.setToN argument is not XSDataInteger but %s" % toN.__class__.__name__
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
            strMessage = "ERROR! XalocXSDataInputXia2DIALS.setProcessDirectory argument is not XSDataFile but %s" % processDirectory.__class__.__name__
            raise BaseException(strMessage)
    def delProcessDirectory(self): self._processDirectory = None
    processDirectory = property(getProcessDirectory, setProcessDirectory, delProcessDirectory, "Property for processDirectory")
    # Methods and properties for the 'doAnomAndNonanom' attribute
    def getDoAnomAndNonanom(self): return self._doAnomAndNonanom
    def setDoAnomAndNonanom(self, doAnomAndNonanom):
        if doAnomAndNonanom is None:
            self._doAnomAndNonanom = None
        elif doAnomAndNonanom.__class__.__name__ == "XSDataBoolean":
            self._doAnomAndNonanom = doAnomAndNonanom
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS.setDoAnomAndNonanom argument is not XSDataBoolean but %s" % doAnomAndNonanom.__class__.__name__
            raise BaseException(strMessage)
    def delDoAnomAndNonanom(self): self._doAnomAndNonanom = None
    doAnomAndNonanom = property(getDoAnomAndNonanom, setDoAnomAndNonanom, delDoAnomAndNonanom, "Property for doAnomAndNonanom")
    # Methods and properties for the 'symm' attribute
    def getSpaceGroup(self): return self._symm
    def setSpaceGroup(self, symm):
        if symm is None:
            self._symm = None
        elif symm.__class__.__name__ == "XSDataString":
            self._symm = symm
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS.setSymm argument is not XSDataString but %s" % symm.__class__.__name__
            raise BaseException(strMessage)
    def delSpaceGroup(self): self._symm = None
    spacegroup = property(getSpaceGroup, setSpaceGroup, delSpaceGroup, "Property for symm")
    # Methods and properties for the 'cell' attribute
    def getUnit_cell(self): return self._cell
    def setUnit_cell(self, cell):
        if cell is None:
            self._cell = None
        elif cell.__class__.__name__ == "XSDataString":
            self._cell = cell
        else:
            strMessage = "ERROR! XalocXSDataInputXia2DIALS.setCell argument is not XSDataString but %s" % cell.__class__.__name__
            raise BaseException(strMessage)
    def delUnit_cell(self): self._cell = None
    unit_cell = property(getUnit_cell, setUnit_cell, delUnit_cell, "Property for cell")
    # Methods and properties for the 'detector_max_res' attribute

    def getDetector_max_res(self):
        return self._detector_max_res

    def setDetector_max_res(self, detector_max_res):
        if detector_max_res is None:
            self._detector_max_res = None
        elif detector_max_res.__class__.__name__ == "XSDataDouble":
            self._detector_max_res = detector_max_res
        else:
            strMessage = (
                "ERROR! XSDataAutoprocInput.setDetector_max_res argument is not XSDataDouble but %s"
                % detector_max_res.__class__.__name__
            )
            raise Exception(strMessage)

    def delDetector_max_res(self):
        self._detector_max_res = None

    detector_max_res = property(
        getDetector_max_res,
        setDetector_max_res,
        delDetector_max_res,
        "Property for detector_max_res",
    )
    
    def export(self, outfile, level, name_='XSDataInputXIA2'):
        showIndent(outfile, level)
        outfile.write(unicode('<%s>\n' % name_))
        self.exportChildren(outfile, level + 1, name_)
        showIndent(outfile, level)
        outfile.write(unicode('</%s>\n' % name_))
    def exportChildren(self, outfile, level, name_='XSDataInputXIA2'):
        XSDataInput.exportChildren(self, outfile, level, name_)
        if self._dataCollectionId is not None:
            self.dataCollectionId.export(outfile, level, name_='dataCollectionId')
            #self.dataCollectionId.export(outfile, level, name_='data_collection_id')
        if self._dirN is not None:
            self.dirN.export(outfile, level, name_='dirN')
        if self._templateN is not None:
            self.templateN.export(outfile, level, name_='templateN')
        if self._fromN is not None:
            self.fromN.export(outfile, level, name_='startFrame')
        if self._toN is not None:
            self.toN.export(outfile, level, name_='endFrame')
        if self._processDirectory is not None:
            self.processDirectory.export(outfile, level, name_='processDirectory')
        if self._doAnomAndNonanom is not None:
            self.doAnomAndNonanom.export(outfile, level, name_='doAnomAndNonanom')
        if self._symm is not None:
            self.symm.export(outfile, level, name_='symm')
        if self._cell is not None:
            self._cell.export(outfile, level, name_='cell')
        if self._small_molecule_3dii is not None:
            self._small_molecule_3dii.export(outfile, level, name_='small_molecule_3dii')
        #TODO: implement this properly using children
        if self._diffractionImage is not None:
            showIndent(outfile, level)
            outfile.write(unicode('<image>\n'))
            self._diffractionImage.export(outfile, level+1, name_='path')
            showIndent(outfile, level)
            outfile.write(unicode('</image>\n'))
        if self._detector_max_res is not None:
            self._detector_max_res.export(outfile, level, name_="d_min")
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
            nodeName_ == 'detector_max_res':
            obj_ = XSDataDouble()
            obj_.build(child_)
            self.setDetector_max_res(obj_)

        XSDataInput.buildChildren(self, child_, nodeName_)
    #Method for marshalling an object
    def marshal( self ):
        oStreamString = StringIO()
        oStreamString.write(unicode('<?xml version="1.0" ?>\n'))
        self.export( oStreamString, 0, name_="XSDataInputXIA2" )
        oStringXML = oStreamString.getvalue()
        oStreamString.close()
        return oStringXML
    #Only to export the entire XML tree to a file stream on disk
    def exportToFile( self, _outfileName ):
        outfile = open( _outfileName, "w" )
        outfile.write(unicode('<?xml version=\"1.0\" ?>\n'))
        self.export( outfile, 0, name_='XSDataInputXIA2' )
        outfile.close()
    #Deprecated method, replaced by exportToFile
    def outputFile( self, _outfileName ):
        print("WARNING: Method outputFile in class XalocXSDataInputXia2DIALS is deprecated, please use instead exportToFile!")
        self.exportToFile(_outfileName)
    #Method for making a copy in a new instance
    def copy( self ):
        return XalocXSDataInputXia2DIALS.parseString(self.marshal())
    #Static method for parsing a string
    def parseString( _inString ):
        doc = minidom.parseString(_inString)
        rootNode = doc.documentElement
        rootObj = XalocXSDataInputXia2DIALS()
        rootObj.build(rootNode)
        # Check that all minOccurs are obeyed by marshalling the created object
        oStreamString = StringIO()
        rootObj.export( oStreamString, 0, name_="XSDataInputXIA2" )
        oStreamString.close()
        return rootObj
    parseString = staticmethod( parseString )
    #Static method for parsing a file
    def parseFile( _inFilePath ):
        doc = minidom.parse(_inFilePath)
        rootNode = doc.documentElement
        rootObj = XalocXSDataInputXia2DIALS()
        rootObj.build(rootNode)
        return rootObj
    parseFile = staticmethod( parseFile )
# end class XalocXSDataInputXia2DIALS


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



# End of data representation classes.


