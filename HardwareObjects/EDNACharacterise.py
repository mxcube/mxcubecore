from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository import EnhancedPopen
from HardwareRepository import HardwareRepository
from XSDataMXCuBEv1_3 import XSDataInputMXCuBE
from XSDataMXCuBEv1_3 import XSDataResultMXCuBE
from XSDataMXCuBEv1_3 import XSDataMXCuBEDataSet
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataFile
from XSDataCommon import XSDataString
from XSDataCommon import XSDataDouble
from XSDataMXv1 import XSDataBeam
from XSDataCommon import XSDataSize
from XSDataCommon import XSDataLength
#from XSDataMXv1 import XSDataCharacterisation
from lxml import etree
import subprocess
import qt
import logging
import copy
import time
import sys
import os
import atexit

DEBUG=0
TEST=0
EDNA_PROCESSES = []

def kill_edna():
  for edna_process in EDNA_PROCESSES:
    try:
      edna_process.kill()
    except:
      continue

#atexit.register(kill_edna)

class EDNACharacterise(Equipment):
    DEFAULTDICT={'comment': 'Image created for EDNA characterisation', \
              'dark': 1, 'phi': 0.0, \
              'oscillation_sequence': [{\
                                        'exposure_time': 1.0, \
                                        'start_image_number': 1, 'number_of_images': 1, \
                                        'range': 1.0,'overlap': -0.0, 'start': 0.0, \
                                        'number_of_passes': 1\
                                        }], \
                'write_input_files': 0, \
                'gshg': 2.0, 'gsvg': 2.0, \
                'tth': 0.0, 'kap': 0.0, 'kth': 0.0, \
                'wavelength': 1.0, \
                'fileinfo': {\
                             'directory': None ,'prefix': 'edna_', 'run_number': 1, \
                             'sub_directory': 'edna', 'suffix':'mccd'}, \
                             'resolution': {'upper': 1.0}, 'dezinger': 1}

    """ The following are the characterise methods
    The structure is an index to append to the image name (after the prefix),
    followed by a list of dictionaries containing particular parameters to set up in the data collection
    sequence which must respect the oscillation_sequence dictionary keywords.
    This means that any sequence of data collections can be defined with this structure.
    """
    REF_IMAGE_METHODS=[[1,[{'number_of_images':1}]],
                      [2,[{'number_of_images':2,'start':-45,'overlap':-90}]],
                      [3,[{'number_of_images':4,'start':0,'overlap':-90}]]
                       ]

    RADIATION_DAMAGE_DEFAULT_PROPS = ["forceSpaceGroup",\
          "strategyComplexity",\
          "maxExposureTimePerDataCollection",\
          "aimedIOverSigmaAtHighestResolution",\
          "minOscillationWidth",\
          "aimedCompleteness",\
          "aimedResolution",\
          "aimedMultiplicity",\
          "flux",\
          "minExposureTimePerImage",\
          "beamSizeX",\
          "beamSizeY",\
          "maxOscillationSpeed",\
          "minOscillationWidth",\
          "sampledimX",\
          "sampledimY",\
          "radiationSusceptibility"\
    ]



    def __init__(self,*args,**kwargs):
        Equipment.__init__(self,*args,**kwargs)

    def init(self):
        self.config=True
        self.default_exposure=None
        self.default_resolution=None
        self.selectedSample = None
        self.EDNAResultsFiles = {}
        self.EDNAWaitResultsTimers = {}
        self.imagePathProperties = {}

        """ D.S 20100216 all the defaults dictionary should be configured out of the code, say in the edna_config file.
        This is pending. """
        try:
            self.defaultDataCollectDict=self.DEFAULTDICT
        except:
            self.config=False

        self.ednaDefaultsInputFile = self.getProperty('edna_default_file')
        self.ednaInput = self.initialiseEDNAdefaults()
        if not self.config:
            logging.getLogger().error("Could not initialise default edna configuration,giving up. Check the ednaconf.xml")

        self.beamlinePars=self.getObjectByRole("beamline_pars")

        """ D.S 20090507 Get the edna start command """
        self.StartEdnaCommand=self.getProperty("StartEdnaCommand")
        
        try:
            self.fluxSource = self.getProperty("fluxSource")
            if self.fluxSource != 'lastImage' and self.fluxSource != 'currentFlux':
                self.fluxSource = 'default'
        except:
            self.fluxSource = "default"

    def safeEmit(self,signal,params):
        qt.qApp.lock()
        try:
            self.emit(signal,params)
            print "emitting",signal, params
        finally:
            qt.qApp.unlock()

    def initialiseEDNAdefaults(self):
        self.ednaInput = XSDataInputMXCuBE.parseFile(self.ednaDefaultsInputFile)
        self.ednaDefaultInput = copy.deepcopy(self.ednaInput)


    def buildEdnaCollectRefImagesDictList(self,dir,process_dir,run_number,prefix,exposure,osc_start,osc_range,wavelength,resolution,detector_mode,method):
        """ User selects how many images from combo box """
	""" The following naming convention was not chosen by mxcube. Must be careful to match the correct resulting images """
        self.ednaPollTimer = None

        method=self.REF_IMAGE_METHODS[method]
        dataCollectList=[]
        baseCollectDict=copy.deepcopy(self.defaultDataCollectDict)
        baseCollectDict['fileinfo']['process_directory']=process_dir
        baseCollectDict['oscillation_sequence'][0]['exposure_time']=exposure
        # GB: take osc_range from Collect, instead of using the 1 degree all the time 
        baseCollectDict['oscillation_sequence'][0]['range']=osc_range
        baseCollectDict['fileinfo']['run_number']=run_number
        baseCollectDict['wavelength']=wavelength
        baseCollectDict['resolution']['upper']=resolution
        baseCollectDict['fileinfo']['directory']=dir
        baseCollectDict['detector_mode']=detector_mode
        # GB: use DNA style reference image naming convention
        baseCollectDict['fileinfo']['prefix']="ref-"+prefix
        if self.selectedSample:
            sampleDbInfoList=copy.deepcopy(self.selectedSample[0])
            sampleGUIInfoList = copy.deepcopy(self.selectedSample[1])
        else:
            # Deal with if there is only one non-database and non-sample changer sample (unidentified)
            tmpDict = copy.deepcopy(baseCollectDict)
            tmpDict['sample_reference'] = None
            tmpDict['sample_info'] = None
            sampleDbInfoList = ['need one element']

        for sample in range(len(sampleDbInfoList)):
            i=0
            for sequence in method[1]:
                tmpDict=copy.deepcopy(baseCollectDict)
                for keyword in sequence.keys():
                    tmpDict['oscillation_sequence'][i][keyword]=sequence[keyword]
                tmpDict['oscillation_sequence'][i]['overlap']=tmpDict['oscillation_sequence'][i]['overlap']+osc_range
                tmpDict['oscillation_sequence'][i]['start']=osc_start
                """ Need to attribute an extra naming convention for each image in the sequence """
    #            tmpDict['fileinfo']['prefix']=baseCollectDict['fileinfo']['prefix']+str(method[0])
                if len(sampleDbInfoList) > 1:
                    blsampleid = sampleDbInfoList[sample].get('blSampleId')
                    if blsampleid is not None and blsampleid!="":
                        tmpDict['fileinfo']['prefix']="ref-%s-%s" % (sampleGUIInfoList[sample]['protein_acronym'],sampleGUIInfoList[sample]['name'])
                        tmpDict['fileinfo']['directory']=os.path.join(baseCollectDict['fileinfo']['directory'],sampleGUIInfoList[sample]['protein_acronym'],sampleGUIInfoList[sample]['name'])
                        tmpDict["fileinfo"]["process_directory"]=os.path.join(process_dir, sampleGUIInfoList[sample]['protein_acronym'],sampleGUIInfoList[sample]['name'])
                    else:
                        try:
                            prefix=str(sampleDbInfoList[sample]['code'])
                        except (KeyError,TypeError):
                            prefix=None
                        if prefix=="" or prefix==str(None) or prefix is None:
                            try:
                                basket=int(sampleGUIInfoList[sample]["basket"])
                            except KeyError:
                                prefix="yourprefix"
                            else:
                                try:
                                    vial=int(sampleGUIInfoList[sample]["vial"])
                                except KeyError:
                                    prefix="yourprefix"
                                else:
                                    prefix="b%ds%02d" % (basket,vial)

                        tmpDict['fileinfo']['prefix']=prefix
                        tmpDict['fileinfo']['directory']=os.path.join(baseCollectDict['fileinfo']['directory'],prefix)
                        tmpDict['fileinfo']['process_directory']=os.path.join(process_dir, prefix) 
                else:
                    tmpDict['fileinfo']['prefix']=baseCollectDict['fileinfo']['prefix']
                if self.selectedSample:
                    try:
                        tmpDict['sample_reference'] = sampleDbInfoList[sample]
                        tmpDict['sample_info'] = (sampleDbInfoList[sample].get('blSampleId'),sampleGUIInfoList[sample])
                    except Exception,msg:
                        logging.getLogger().warning("Selected sample has no database identification (%r)" % msg)
                dataCollectList.append(tmpDict)
                i += 1

        #logging.getLogger().debug(dataCollectList)
        self.process_dir=process_dir 
        self.current_method = method
        self.collectSeqList = dataCollectList

        return(dataCollectList)

    """ Should be able to directly use the edna input model """
    def characteriseWithXmlInput(self, data_collection_id, sampleCharacteriseIndex, beamsize):
        if data_collection_id is not None:
          self.ednaInput.setDataCollectionId(XSDataInteger(data_collection_id))
        else:
          self.ednaInput.setDataCollectionId(None)
          logging.getLogger().warning("The data collection ID is not known for this characterisation. Therefore the EDNA results cannot be put into the database")

        # build data set
        imageSuffix = self.beamlinePars["BCM_PARS"].getProperty("FileSuffix")
        dataSetObj = XSDataMXCuBEDataSet()
        self.ednaInput.setDataSet([])
        methodDCNo = len(self.current_method[1])
        for methodIndex in range(methodDCNo):
          number_of_images = self.current_method[1][methodIndex]['number_of_images']
          imageNameIdx = self.current_method[0]
          listIndex = sampleCharacteriseIndex * methodDCNo + methodIndex
          for imageno in range(int(number_of_images)):
              imageFileObj = XSDataFile()
              pathStrObj = XSDataString()
              pathStrObj.setValue(('%s/%s_%d_%04d.%s' % (self.collectSeqList[listIndex]['fileinfo']['directory'],\
                                                         self.collectSeqList[listIndex]['fileinfo']['prefix'],\
                                                         int(self.collectSeqList[listIndex]['fileinfo']['run_number']),\
                                                         imageno+1,imageSuffix)))
              imageFileObj.setPath(pathStrObj)
              dataSetObj.addImageFile(imageFileObj)
        self.ednaInput.addDataSet(dataSetObj)

        if TEST:
          self.ednaInput.getDataSet()[0].getImageFile()[0].getPath().setValue("/opt/pxsoft/DNA/TestCase/ref-testscale_1_001.img")
          self.ednaInput.getDataSet()[0].getImageFile()[1].getPath().setValue("/opt/pxsoft/DNA/TestCase/ref-testscale_1_002.img")
        path = self.process_dir
        suffix = '_%s.xml' % (self.ednaInput.getDataCollectionId().getValue() or id(self.ednaInput))
        ednaResultsFile = os.path.join(path, 'EDNAOutput%s' % suffix)
        ednaInputXMLFile = os.path.join(path, 'EDNAInput%s' % suffix)
        if not os.path.isdir(path):
            os.makedirs(path)

        beamObj = self.ednaInput.getExperimentalCondition().getBeam()
        beamObj.setSize(XSDataSize(x=XSDataLength(float(beamsize[0])),y=XSDataLength(float(beamsize[1]))))
        """ create an edna input file using the ednainput model """
        ednaInputXML = self.ednaInput.exportToFile(ednaInputXMLFile)

        logging.getLogger().info("Starting Edna using xml file, %s" % ednaInputXMLFile)

        # use an intermediate script to run edna with its command line options
        edna_args = "%s  %s %s" % (ednaInputXMLFile,ednaResultsFile,path)
        edna_cmd=self.StartEdnaCommand+" "+edna_args
        if self.ednaPollTimer is None:
            self.ednaPollTimer = qt.QTimer()
            qt.QObject.connect(self.ednaPollTimer,qt.SIGNAL("timeout()"), self.pollEDNA)

        logging.getLogger().debug(edna_cmd)
        EDNA_PROCESSES.append(EnhancedPopen.Popen(edna_cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,universal_newlines=True))
        self.EDNAResultsFiles[id(EDNA_PROCESSES[-1])]=ednaResultsFile
        # save image prefix,etc. for next step
        # only take first image, since we just want to have image prefix, run number, etc. :
        # it is the same within the whole collectSeqList (hopefully)
        imagePrefix = self.collectSeqList[0]['fileinfo']['prefix'][4:] #remove ref-
        self.imagePathProperties[id(EDNA_PROCESSES[-1])]={"imagePrefix":imagePrefix, "imageDir": self.collectSeqList[0]['fileinfo']['directory'], "lRunN": int(self.collectSeqList[0]['fileinfo']['run_number'])}
        self.ednaPollTimer.start(100)

    def pollEDNA(self):
        i = 0
        while i < len(EDNA_PROCESSES):
          ednaprocess = EDNA_PROCESSES[i]

          out=EnhancedPopen.recv_some(ednaprocess, e=0, stderr=0)

          if len(out):
              # add the edna errors to the mxcube log
              # those messages look like:
              # 20110711-181659  [ERROR]: Timeout when blablabla
              # use a brute force approach for now
              for line in out.split('\n'):
                  if line.find('[ERROR]') != -1:
                      logging.getLogger().error(line)

              self.emit("displayEdnaMessage", (out, self.EDNAResultsFiles[id(ednaprocess)]))

          if ednaprocess.poll() != None:
              logging.getLogger().info("finished polling %r" % ednaprocess.poll())
              edna_process_id = id(ednaprocess)
              del EDNA_PROCESSES[i]
              self.getEDNAResults(edna_process_id)
          else:
              i = i + 1
          if len(EDNA_PROCESSES) == 0:
              self.ednaPollTimer.stop()


    def getEDNAResults(self, edna_process_id):
        edna_results_file = self.EDNAResultsFiles[edna_process_id] 
        self.EDNAWaitResultsTimers[edna_process_id] = qt.QTimer()
        def reallyGetEDNAResults(edna_process_id=edna_process_id, edna_results_file=edna_results_file, storage_dict={"i":0}):
            storage_dict["i"]+=1
            if storage_dict["i"]>=3:
              logging.getLogger().error("Timeout: cannot open EDNA results file (%s)", edna_results_file)
              self.EDNAWaitResultsTimers[edna_process_id].stop()
              del self.EDNAWaitResultsTimers[edna_process_id]
              del self.imagePathProperties[edna_process_id]
            else:
              results = XSDataResultMXCuBE.parseFile(edna_results_file)
              self.EDNAWaitResultsTimers[edna_process_id].stop()
              del self.EDNAWaitResultsTimers[edna_process_id]
              imagePrefix = self.imagePathProperties[edna_process_id]["imagePrefix"]
              imageDir = self.imagePathProperties[edna_process_id]["imageDir"]
              lRunN = self.imagePathProperties[edna_process_id]["lRunN"] 
              del self.imagePathProperties[edna_process_id]
              try:
                  html_path = results.htmlPage.path.value
                  self.emit('newEDNAHTML', (html_path, imagePrefix, lRunN))
              except:
                  logging.getLogger().exception('EDNACharacterize: no html in results')
                 
              try:
                  screening_id = results.getScreeningId().getValue()
              except:
                  screening_id = None 
              self.readEDNAResults(results.getCharacterisationResult(), edna_results_file, imageDir,
                                   imagePrefix, lRunN, screeningId = screening_id)
              

        qt.QObject.connect(self.EDNAWaitResultsTimers[edna_process_id], qt.SIGNAL("timeout()"), reallyGetEDNAResults)
        self.EDNAWaitResultsTimers[edna_process_id]._cb = reallyGetEDNAResults
        self.EDNAWaitResultsTimers[edna_process_id].start(1000)
 
 
    def readEDNAResults(self, xsDataCharacterisation, results_file, imageDir,
                        imagePrefix, lRunN, process_dir=None, do_inducedraddam=None, screeningId = None): 
       if xsDataCharacterisation is None:
           logging.error("%s: no characterisation results !", self.name())
           self.emit("noEDNAStrategyResult",(None,))
           return
       else:
           if process_dir is not None:
               self.process_dir = process_dir
           if do_inducedraddam is not None:
               self.do_inducedraddam = do_inducedraddam
           real_results_file = ""
           root=etree.parse(results_file)                    
           for elt in root.findall("//listOfOutputFiles/value"):
             if elt.text.endswith("CharacterisationResult.xml"):
               real_results_file = elt.text
               break
       try:
           strategy = xsDataCharacterisation.getStrategyResult()
           try:
               collectionPlan = strategy.getCollectionPlan()
           except Exception,msg:
               logging.getLogger().error("No collection plan was returned by EDNA (%r). Probably, the images could not be processed correctly." )
               collectionPlan=[]
   
           """ Set any default beamline parameters """
           defaultNoOfPasses = self.beamlinePars["BCM_PARS"].getProperty("default_number_of_passes")
           
           defaultDetectorBinning = self.beamlinePars["SPEC_PARS"]["detector"].getProperty("binning")
           detectorModes =  ["Software binned","Unbinned","Hardware binned", "disable"]
           DetectorBinning = detectorModes[defaultDetectorBinning]
               
           """ Iterate through the subwedges and data collection plans. Currently this makes a wrong assumption that the order is correct in the 
               xml file
           """
           wedgeDictList = []

           for cSI in range(len(collectionPlan)):
               wedges = collectionPlan[cSI].getCollectionStrategy().getSubWedge()
               # Sort the list of strategies by wedgeNo
               wedges.sort(lambda x,y: cmp(x.getSubWedgeNumber().getValue(),y.getSubWedgeNumber().getValue()))

               # GB: try getting "collectionPlan.Summary.Attenuation first, as it was in Characterization 1_1
               try:
                   transmission = (collectionPlan[cSI].getStrategySummary().getAttenuation().getValue())
                   gotTransmission = 1
               except:
                   gotTransmission = 0
                   
               """ Deal with selected sample """
               barcode=''
               location=''
               if self.selectedSample is not None:
                   """ Temporary code to make edna work for one sample while develpoing multi samples """
                   sampleDbInfo = self.selectedSample[0]
                   if len(sampleDbInfo)==1:                                
                       try:
                           barcode=sampleDbInfo[0]["code"]
                       except KeyError:
                           barcode = ''
                       try:
                           location=sampleDbInfo[0]["sample_location"]
                       except KeyError:
                           location = ''
                                       
               imageCounter = 1

               for wegidx in range(len(wedges)):
                   subWedgeId = screeningId #wedges[wegidx].getSubWedgeId()
                   expCondition = wedges[wegidx].getExperimentalCondition()
                   goniostat = expCondition.getGoniostat()
                   beam = expCondition.getBeam()
                   osc_start = goniostat.getRotationAxisStart().getValue()
                   osc_end = goniostat.getRotationAxisEnd().getValue()
                   osc_width = goniostat.getOscillationWidth().getValue()
                   
                   #
                   # GB: images in a subwedge are numbered continuously
                   #
                   startImageNumber = imageCounter 
                   numberOfImages = int(abs(osc_end - osc_start)/osc_width)
                   imageCounter = startImageNumber + numberOfImages
                   
                   if numberOfImages == 0:
                      logging.getLogger().warning("EDNA strategy should not use 0 number of images, setting to 1.")
                      numberOfImages=1

                   thisDetectorBinning = DetectorBinning
                   if wedges[wegidx].getAction() is not None:
                       if wedges[wegidx].getAction().getValue() == 'burn':
                           thisDetectorBinning = 'disable'

                   # runNumber was a wedge number - this leads to redundant filenames
                   # runNumber = wedges[wegidx].getSubWedgeNumber().getValue()
                   #
                   # now  runNumber is a collectionPlan number.
                   runNumber = collectionPlan[cSI].getCollectionPlanNumber().getValue()
                   #
                   #GB: if there was no transmision asigned in Summary, try Beam transmission of inidvidual subwedges - as in Characterization 1_2
                   #GB: if nothing helps, set transmission 100%.
                   if not gotTransmission:
                       try:
                           transmission = beam.getTransmission().getValue()
                       except:
                           transmission = 100.0
                   ###    

                   try:
                       comments = collectionPlan[cSI].getStrategySummary().getResolutionReasoning().getValue()
                   except:
                       comments = "No comment"
                      
                   prefix = str(imagePrefix + 'w' + str(wegidx+1))
                   image_number_format="####"
                   template = "%s_%d_%s.%s" % (prefix, lRunN, image_number_format, self.beamlinePars["BCM_PARS"].getProperty("FileSuffix")) 
                   wedgeDict={
                       'process_directory':self.process_dir,
                       'exposure_time':    beam.getExposureTime().getValue(),
                       'osc_start':        osc_start,
                       'energy':           int(123984.0/beam.getWavelength().getValue())/10000.0,
                       'mad_1_energy':     (False, '', ''), 
                       'prefix':           prefix, 
                       'overlap':          '+0.00', 
                       'first_image':      str(startImageNumber),
                       'number_images':    numberOfImages,
                       'mad_energies':    'pk - ip - rm - rm2', 
                       'comments':         comments, 
                       'mad_2_energy':     (False, '', ''), 
                       'osc_range':        osc_width, 
                       'inverse_beam':     (False, '1'), 
                       'template':         template, 
                       'detector_mode':    str(thisDetectorBinning), 
                       'mad_3_energy':     (False, '', ''), 
                       'mad_4_energy':     (False, '', ''), 
                       'run_number':       str(runNumber), 
                       'transmission':     str(transmission), 
                       'number_passes':    str(defaultNoOfPasses),
                       'directory':        str(imageDir), 
                       'resolution':       collectionPlan[cSI].getStrategySummary().getResolution().getValue(),
                       'barcode':          barcode,
                       'location':         location,
                       'anomalous':        False,
                       'processing':       True,
                       'EDNA_files_dir':   os.path.dirname(real_results_file),
                       'do_inducedraddam': self.do_inducedraddam,
                       'screening_sub_wedge_id': subWedgeId
                       }

                   if self.selectedSample is not None:
                       try:
                           wedgeDict['sample_info'] = (self.selectedSample[0][0]['blSampleId'],self.selectedSample[1][0])
                       except Exception,msg:
                           logging.getLogger().debug("EDNACharacterise: Selected Sample error with database identification (%r)" % msg)
                   
                   """ Should be careful, inserting any missing default values
                       This could now be taken away """
                   for key in self.DEFAULTDICT.iterkeys():
                       if not wedgeDict.has_key(key):
                           wedgeDict[key]=self.DEFAULTDICT[key]

                   wedgeDictList.append(wedgeDict)

           self.emit("newEDNAStrategyCreated",(wedgeDictList,))
       except Exception,msg:
           logging.getLogger().error("An error occurred, trying to obtain the EDNA output. (%s)",msg)
