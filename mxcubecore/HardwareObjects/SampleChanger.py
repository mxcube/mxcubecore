"""Sample Changer Hardware Object

template:
<equipment class = "SampleChanger">
  <username>label for users</username>   
  <specversion>host:port string of the Spec version running SC macros</specversion>
  <tangoname>full Tango name of the SC Device Server</tangoname>
  <!-- <device hwrid="/wago/cryo" role="Cryo"/>
       <device hwrid="/wago/swpermit" role="SoftwarePermit"/>
       <microdiff/>
  -->
</equipment>
"""
from HardwareRepository.TaskUtils import *
import Queue
import logging
from HardwareRepository.BaseHardwareObjects import Equipment
import xml.sax
from xml.sax import SAXParseException
from xml.sax.handler import ContentHandler
try:
  from SpecClient_gevent import SpecConnectionsManager
  from SpecClient_gevent import SpecEventsDispatcher
except ImportError:
  from SpecClient import SpecConnectionsManager
  from SpecClient import SpecEventsDispatcher
import gevent 
import time
import types
import PyTango

class XMLDataMatrixReadingHandler(ContentHandler):
    def __init__(self):
        ContentHandler.__init__(self)

        self.dataMatrixList = []
        self.basketDataMatrixList = [None, "", "", "", "", ""]
        self.dataMatrix = ''
        self.basketLocation = -1
        self.sampleLocation = -1
        self.sampleFlag = 0


    def startElement(self, name, attrs):
        self.addBasketLocation = name == "BasketLocation"
        self.addSampleLocation = name == "Location"
        self.addDataMatrix = name == "DataMatrix"
        self.addSampleFlag = name == "SampleFlag"


    def characters(self, content):
        if self.addDataMatrix:
            self.dataMatrix = str(content)
        elif self.addBasketLocation:
            self.basketLocation = int(content)
        elif self.addSampleLocation:
            self.sampleLocation = int(content)
        elif self.addSampleFlag:
            self.sampleFlag = int(content)


    def endElement(self, name):
        if name == "Sample":
            self.dataMatrixList.append((self.dataMatrix,\
                    self.basketLocation,\
                    self.sampleLocation,\
                    self.sampleFlag))
            self.dataMatrix = ''
            self.basketLocation = -1
            self.sampleLocation = -1
            self.sampleFlag = 0
        elif name == "Basket":
            if len(self.dataMatrix) > 0:
                self.basketDataMatrixList[self.sampleLocation]=self.dataMatrix
            self.dataMatrix = ''
            self.basketLocation = -1
            self.sampleLocation = -1
            self.sampleFlag = 0
        elif name == "BasketLocation":
            self.addBasketLocation = None
        elif name == "Location":
            self.addSampleLocation = None
        elif name == "DataMatrix":
            self.addDataMatrix = None
        elif name == "SampleFlag":
            self.addSampleFlag = None


def getDataMatricesList(sxml):
    #logging.getLogger("HWR").debug("XML data received from Sample Changer : %s", sxml)
    handler = XMLDataMatrixReadingHandler()

    sxml=sxml.replace(' encoding="utf-16"','')

    try:
        xml.sax.parseString(sxml, handler)
    except TypeError,diag:
        logging.getLogger("HWR").error("Error parsing XML data: %s" % str(diag))
        return []

    data_matrices=[]
    sc_sample_matrices=handler.dataMatrixList
    sc_basket_matrices=handler.basketDataMatrixList
    for sc_sample in sc_sample_matrices:
        try:
            basket_code=sc_basket_matrices[sc_sample[1]]
        except:
            sc_sample_ok=(sc_sample[0],sc_sample[1],sc_sample[2],"",sc_sample[3])
        else:
            sc_sample_ok=(sc_sample[0],sc_sample[1],sc_sample[2],basket_code,sc_sample[3])
        data_matrices.append(sc_sample_ok)

    return data_matrices


class SampleChanger(Equipment):
    (FLAG_SC_IN_USE,FLAG_MINIDIFF_CAN_MOVE,FLAG_SC_CAN_LOAD,FLAG_SC_NEVER) = (1,2,4,8)
    (STATE_BASKET_NOTPRESENT,STATE_BASKET_UNKNOWN,STATE_BASKET_PRESENT) = (-1,0,1)

    USE_SPEC_LOADED_SAMPLE = False
    ALWAYS_ALLOW_MOUNTING  = True

    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)

        self.__timers = {}
        self.currentSample = None
        self.currentBasket = None
        self.currentSampleDataMatrix = None
        self.currentBasketDataMatrix = None
        self.scanAllBasketsProcedure = None
        self.scanCurrentBasketProcedure = None
        self.loadSampleProcedure = None
        self.unloadSampleProcedure = None
        self.failureCallback = None
        self.moveToPositionRetries = []
        self.stopScanAllBasketsFlag = None
        self.specConnection = None
        self.isSpecConnected = None
        self.lastOperationalFlags = SampleChanger.FLAG_SC_NEVER
        self.loadedSampleDict={}
        self.scannedMatrices=None

    def init(self):
        moveToLoadingPositionCmd = self.addCommand({ 'type': 'spec', 'name': '_moveToLoadingPosition' }, "SCMoveToLoadingPos")
        moveToUnloadingPositionCmd = self.addCommand({'type': 'spec', 'name': '_moveToUnloadingPosition'}, "SCMoveToUnloadingPos")
        unlockMinidiffMotorsCmd = self.addCommand({ 'type': 'spec', 'name': 'unlockMinidiffMotors'}, "SCMinidiffGetControl")
        unlockMinidiffMotorsCleanupCmd = self.addCommand({ 'type': 'spec', 'name': 'unlockMinidiffMotorsCleanup'}, "SCMinidiffGetControl")
        prepareCentringCmd = self.addCommand({ 'type': 'spec', 'name': 'prepareCentring'}, "minidiff_prepare_centring")

        abortCmd = self.addCommand({ 'type': 'tango', 'name': 'abort' }, "Abort")
        holderLengthCmd = self.addCommand( { 'type': 'tango', 'name': 'holderlength' }, "GetSampleHolderLength")
        isScanBasketForDataMatrixDoneCmd = self.addCommand({ 'type': 'tango', 'name':'isScanBasketForDataMatrixDone' }, "isScanBasketForDataMatrixDone")
        getInformationAsXmlCmd = self.addCommand({ 'type': 'tango', 'name': 'getInformationAsXml' }, 'GetInformationAsXml')
        statusChan = self.addChannel({ 'type': 'tango', 'name': 'status', 'polling':1000 }, "Status")
        stateChan = self.addChannel({ 'type': 'tango', 'name': 'state', 'polling':1000 }, "State")
        selectedBasketChan = self.addChannel({ 'type': 'tango', 'name':'selectedBasket', 'polling':1000 }, "SelectedBasketLocation")
        selectedSampleChan = self.addChannel({ 'type': 'tango', 'name': 'selectedSample', 'polling':1000 }, "SelectedSampleLocation")
        selectedBasketDataMatrixChan = self.addChannel({ 'type': 'tango', 'name': 'selectedBasketDataMatrix', 'polling':1000 }, "SelectedBasketDataMatrix")
        sampleIsLoadedChan = self.addChannel({"type":"tango", "name":"sampleIsLoaded", "polling":500 }, "SampleIsLoaded")
        basketTransferChan = self.addChannel({"type":"tango", "name":"transferMode", "polling":1000 }, "BasketTransferMode")
        self.addCommand({'type':'tango', 'name':'resetBasketInformation' }, "ResetBasketInformation")
        self.addCommand({"type":"tango", "name":"switchTransferMode"}, "SetBasketTransferMode")

        operationalChan = self.addChannel( { 'type': 'spec', 'name': 'OperationalFlags' }, "SC_MD_FLAGS")

        for cmd in self.getCommands():
            cmd.connectSignal("commandFailed", self.__commandFailed)
            cmd.connectSignal("commandAborted", self.__commandAborted)

        if self.getProperty('specversion') is None:
            logging.getLogger("HWR").error("%s: you must specify a spec version" % self.name())
        else:
            operationalChan.connectSignal("update", self.operationalFlagsChanged)
            try:
                self.operationalFlagsChanged(operationalChan.getValue())
            except:
                logging.getLogger("HWR").exception("%s: error getting SC vs MD operational flags" % self.name())

            self.specConnection=SpecConnectionsManager.SpecConnectionsManager().getConnection(self.specversion)
            SpecEventsDispatcher.connect(self.specConnection, 'connected', self.specConnected)
            SpecEventsDispatcher.connect(self.specConnection, 'disconnected', self.specDisconnected)

        statusChan.connectSignal("update", self.sampleChangerStatusChanged)
        stateChan.connectSignal("update", self.sampleChangerStateChanged)
        selectedSampleChan.connectSignal("update", self.selectedSampleChanged)
        selectedBasketChan.connectSignal("update", self.selectedBasketChanged)
        selectedBasketDataMatrixChan.connectSignal("update", self.selectedBasketDataMatrixChanged)
        basketTransferChan.connectSignal("update", self.basketTransferModeChanged)
        sampleIsLoadedChan.connectSignal("update", self.sampleLoadStateChanged)
 
        try:
            self.isSpecConnected=unlockMinidiffMotorsCmd.isSpecConnected()
        except:
            self.isSpecConnected=False

        try:
            self.microdiff
        except AttributeError:
            self.prepareCentringAfterLoad=True
        else:
            self.prepareCentringAfterLoad=False

    @task
    def executeJavaDeviceServerTask(self, task_name, *args):
        device = PyTango.DeviceProxy(self.getProperty("tangoname"))
        method = getattr(device, task_name)
        task_id = method(*args)

        while device.isTaskRunning(task_id):
          time.sleep(0.5)
        
        try:
          r = device.checkTaskResult(task_id)
        except PyTango.DevFailed, traceback:
          task_error = traceback[0]
          error_msg = str(task_error.desc).replace("Task error: ", "")
          raise Exception(error_msg) 
        except Exception,err:
          raise Exception(str(err)) 
        else:
          return r 
    

    # Called when spec is disconnected
    def specDisconnected(self):
        self.isSpecConnected=False
        self.sampleChangerStateChanged("DISABLE")


    # Called when spec is connected
    def specConnected(self):
        self.isSpecConnected=True
        self.sampleChangerStateChanged(self.getState())


    def connectNotify(self, signal):
        for channelName in self.getChannelNamesList():
            chan = self.getChannelObject(channelName)
            try:
                chan.update()
            except:
                pass
        try:
          if signal=="sampleChangerContentsUpdated":
             self.emit("sampleChangerContentsUpdated", (self.samples_presence, )) 
        except AttributeError:
          pass


    def getLoadedSample(self):
        return dict(self.loadedSampleDict)


    def setLoadedSample(self,loaded_sample_dict,extended=False):
        logging.getLogger("HWR").debug("%s: setLoadedSample %s" % (self.name(),str(loaded_sample_dict)))

        loaded_sample_dict["_timestamp"] = time.time()

        self.loadedSampleDict = loaded_sample_dict

        self.emit("loadedSampleChanged", (dict(self.loadedSampleDict), ))


    def displayErrorFromSampleChangerTask(self, task):
      try:
        e = task.get()
      except Exception, errmsg:
        logging.error("%s: error while executing sample changer task: %s", self.name(), errmsg)
        

    def reset(self):
        self.stopScanAllBasketsFlag = None
        self.executeJavaDeviceServerTask("Reset", wait=False).link(self.displayErrorFromSampleChangerTask)
        
  
    def resetBasketsInformation(self):
        cmd = self.getCommandObject("resetBasketInformation")
        for i in range(5):
          cmd(i+1)
        logging.info("%s: sample changer contents reset done", self.name()) 

 
    def setBasketSampleInformation(self, input):
        logging.debug("calling setBasketSampleInformation: %r", input)


    def extendLoadedSample(self, sample_info_dict):
        self.loadedSampleDict.update(sample_info_dict)


    def sampleLoadStateChanged(self, loaded, prev_load={"state":None}):
        if loaded is None:
            return
    	loaded=bool(loaded)
        if bool(prev_load["state"]) == loaded:
            return
        else:
            prev_load["state"] = loaded

        self.updateDataMatrices()

        if not loaded:
            loaded_sample_dict={"loaded":loaded,"barcode":None,"basket":None,"vial":None,"holderlength":None}
        else: 
            sample_basket, sample_vial = self.getLoadedSampleLocation()
            loaded_sample_dict={"loaded":loaded,"barcode":self.getLoadedSampleDataMatrix(),"basket":sample_basket,"vial":sample_vial,"holderlength":None}

        self.setLoadedSample(loaded_sample_dict)

        logging.getLogger("HWR").debug("%s: sampleLoadStateChanged %s" % (self.name(),loaded))
       
        # as soon as we know sample is loaded, move cryo in 
        if loaded and self.loadSampleProcedure is not None:
          self.moveCryoIn()

        self.emit("sampleIsLoaded", (loaded, ))


    def procedurePrepare(self,failureCallback):
        self.scanAllBasketsProcedure = None
        self.scanCurrentBasketProcedure = None
        self.unloadSampleProcedure = None
        self.loadSampleProcedure = None
        self.failureCallback = failureCallback


    def procedureExceptionCleanup(self,state,problem=None,md_get_ctrl=True, in_abort=False):
        if problem is not None:
            logging.getLogger("HWR").error("%s: error in procedure (%s)" % (self.name(),str(problem)))

        current_procedure=self.currentProcedureName()
        self.scanAllBasketsProcedure = None
        self.scanCurrentBasketProcedure = None
        self.unloadSampleProcedure = None
        self.loadSampleProcedure = None

        if current_procedure: 
            logging.error("%s could not be performed %s", current_procedure, problem is not None and "(%s)"%str(problem) or "")

        if md_get_ctrl:
            self.unlockMinidiffMotorsCleanup()

        if callable(self.failureCallback):
            if state == "ALARM":
                self.failureCallback("ALARM")
            else:
                self.failureCallback("FAULT")
                
        self.sampleChangerStateChanged(state=="ALARM" and state or "FAULT")
        self.failureCallback = None


    def currentProcedureName(self):
        loading = self.loadSampleProcedure is not None
        unloading = self.unloadSampleProcedure is not None
        scanning = (self.scanAllBasketsProcedure is not None) or (self.scanCurrentBasketProcedure is not None)
        moving = False
        return loading and "loading" or unloading and "unloading" or scanning and "scanning" or moving and "moving" or ""


    def sampleChangerStateChanged(self,state,old={"state":None}):
        if state == old["state"]:
            return
        old["state"]=state
        if state is None or str(state)=="":
            return
        if not self.isSpecConnected:
            state="DISABLE"
        state=str(state)
        self.updateDataMatrices()
        self.emit("stateChanged", (state, ))


    def sampleChangerStatusChanged(self, status):
        self.emit("statusChanged", (str(status), ))
        logging.info("%s: %s", self.name(), status)


    def sampleIsLoaded(self):
        sampleIsLoadedChan = self.getChannelObject("sampleIsLoaded")
        try:
            is_loaded=sampleIsLoadedChan.getValue()
        except:
            logging.getLogger("HWR").exception("%s: error getting smart magnet state" % self.name())
            is_loaded=None
        return is_loaded

        
    def scanBasket(self, basket = None, wait=False):
        if basket is None:
            basket = self.currentBasket

        logging.info("%s: scanning basket %s", self.name(), basket)
        
        self.scannedMatrices=[]
        ret = self.executeJavaDeviceServerTask("ScanBasketForDatamatrix", basket, wait=wait)
        if not wait:
          ret.link(self.displayErrorFromSampleChangerTask)
        return ret


    @task
    def __scanAllBasketsProcedure(self, baskets_to_scan, scanFinishedCallback=None):
        basket_presence = self.isScanBasketForDataMatrixDone()
        self.emit("basketPresenceChanged", (basket_presence, ))
        
        i = 0
        for scan in baskets_to_scan:
            i+=1
            if scan == 1:
                self.scanBasket(i, wait=True)                
                logging.info("%s: basket %s scanned", self.name(), i)

            if self.stopScanAllBasketsFlag:
                raise Exception("Scan stopped")

        logging.info("%s: basket(s) scan done", self.name())
        
        matrices=self.getMatrixCodes(force=True)
        if callable(scanFinishedCallback):
            scanFinishedCallback(matrices)
        self.updateDataMatrices()

        self.stopScanAllBasketsFlag = None


    def scanAllBaskets(self, scanFinishedCallback=None, failureCallback=None):
        return self.scanBaskets([1,1,1,1], scanFinishedCallback, failureCallback)


    def scanBaskets(self, baskets_to_scan, scanFinishedCallback=None, failureCallback=None):
        """Scan all the baskets

        If a callback function is given, it is called when scan is finished.
        The callback function must have an argument to receive data matrices.
        """
        self.stopScanAllBasketsFlag = False
        self.procedurePrepare(failureCallback)
        self.scanAllBasketsProcedure = self.__scanAllBasketsProcedure(baskets_to_scan, scanFinishedCallback, wait=False)

        def finished(procedure):
          self.scanAllBasketsProcedure = None
          
          try:
            procedure.get()
          except Exception, diag: 
            self.procedureExceptionCleanup("ALARM",str(diag))
          else:
            scanFinishedCallback()

        self.scanAllBasketsProcedure.link(finished)
        

    def stopScanAllBaskets(self):
        if self.scanAllBasketsProcedure is not None:
            self.scanAllBasketsProcedure.kill()

    @task
    def __scanCurrentBasketProcedure(self, scanFinishedCallback=None):
        basket = self.currentBasket
        logging.getLogger("HWR").debug("%s: going to scan basket %d", self.name(), basket)

        self.scanBasket(basket, wait=True)
               
        logging.getLogger("HWR").debug("%s: basket %s scanned", self.name(), basket)

        self.scanCurrentBasketProcedure = None

        matrices=self.getMatrixCodes(force=True)
        self.updateDataMatrices()
        if callable(scanFinishedCallback):
            scanFinishedCallback(matrices)
            

    def scanCurrentBasket(self, scanFinishedCallback=None, failureCallback=None):
        logging.getLogger("HWR").debug("%s: scanCurrentBasket", self.name())
        
        self.procedurePrepare(failureCallback)
        self.scanCurrentBasketProcedure = self.__scanCurrentBasketProcedure(scanFinishedCallback, wait=False)

        def finished(procedure):
          self.scanAllBasketsProcedure = None

          try:
            procedure.get()
          except Exception, diag:
            self.procedureExceptionCleanup("ALARM",str(diag))
          else:
            pass

        self.scanCurrentBasketProcedure.link(finished)


    def changeSelectedBasket(self, newBasket, wait=False):
      ret = self.executeJavaDeviceServerTask("MoveBasketLocation", newBasket, wait=wait)
      if not wait:
        ret.link(self.displayErrorFromSampleChangerTask)
      return ret
     

    def changeSelectedSample(self, newSample, wait=False):
      ret = self.executeJavaDeviceServerTask("MoveSampleLocation", newSample, wait=wait)
      if not wait:
        ret.link(self.displayErrorFromSampleChangerTask)
      return ret
        

    def selectedBasketChanged(self, basket):
        try:
            basket=int(basket)
        except:
            logging.getLogger("HWR").exception("%s: error updating basket position" % self.name())
        else:
            self.currentBasket = basket
            self.emit("basketChanged", (basket, ))

            scanned_matrices=self.getMatrixCodes()
            for scanned_matrix in scanned_matrices:
                if self.currentBasket==scanned_matrix[1] and self.currentSample==scanned_matrix[2]:
                    self.selectedSampleDataMatrixChanged(scanned_matrix[0])


    def selectedSampleChanged(self, sample):
        try:
            sample=int(sample)
        except:
            logging.getLogger("HWR").exception("%s: error updating sample position" % self.name())
        else:
            self.currentSample = sample
            self.emit("sampleChanged", (sample, ))

            scanned_matrices=self.getMatrixCodes()
            for scanned_matrix in scanned_matrices:
                if self.currentBasket==scanned_matrix[1] and self.currentSample==scanned_matrix[2]:
                    self.selectedSampleDataMatrixChanged(scanned_matrix[0])


    @task
    def __loadSampleProcedure(self, holderLength, sample_id = None, sample_location = None, sampleIsLoadedCallback = None, prepareCentring = None, prepareCentringMotors = {}):
        already_loaded=False
        if self.sampleIsLoaded():
            if sample_id and self.getLoadedSampleDataMatrix()==sample_id:
                already_loaded=True
            elif sample_location and self.getLoadedSampleLocation()==sample_location:
                already_loaded=True
            else:
                pass
        logging.getLogger("HWR").debug("%d %s %s %s", holderLength, sample_id, sample_location, self.sampleIsLoaded())

        if already_loaded:
          return True

        self.sampleChangerStateChanged("RUNNING")
        self.emit("statusChanged", ("Moving minidiff to loading position", ))

        self._moveToLoadingPosition(holderLength, wait=True, timeout=30)
                            
        if sample_id:
          matrices = self.getMatrixCodes()

          for sid, basket_loc, vial_loc, basket_barcode, s_flag in matrices:
            if sid==sample_id:
              sample_location = (basket_loc, vial_loc, sid)
              break

        if sample_location:
              try:
                  basket_loc=int(sample_location[0])
                  vial_loc=int(sample_location[1])
              except:
                  logging.getLogger("HWR").exception("%s: could not move to location %s" % (self.name(), sample_location))
                  raise Exception("Invalid sample location %s" % sample_location)

              self.executeJavaDeviceServerTask("ChainedLoadSample", [basket_loc, vial_loc, holderLength])
        else:
              self.executeJavaDeviceServerTask("LoadSample", holderLength)


        if self.sampleIsLoaded():
              logging.getLogger("HWR").debug("%s: sample is loaded", self.name())

              self.sampleLoadStateChanged(True) 

              self.unlockMinidiffMotors(wait=True, timeout=3)

              if self.prepareCentringAfterLoad is True and prepareCentring is not False:
                  logging.getLogger("HWR").debug("%s: preparing the sample for centring", self.name())
                  self.sampleChangerStateChanged("RUNNING")
                  self.emit("statusChanged", ("Preparing minidiff for sample centring", ))

                  motors_pos_str=";".join(["%s %f" % (MP[0],MP[1]) for MP in prepareCentringMotors.iteritems()])
                  self.prepareCentring(motors_pos_str, wait=True, timeout=30)

                  self.emit("statusChanged", (self.getStatus(), ))
                  self.emit("stateChanged", (self.getState(), ))

              if callable(sampleIsLoadedCallback):
                  sampleIsLoadedCallback(already_loaded)
        else:
          self.sampleLoadStateChanged(False)

          raise Exception("Load failed")


    def loadSample(self, holderLength, sample_id=None, sample_location=None, sampleIsLoadedCallback=None, failureCallback=None, prepareCentring=None, prepareCentringMotors={}, wait=False):
        logging.getLogger("HWR").debug("%s: in loadSample", self.name())

        self.procedurePrepare(failureCallback)

        if sample_id and sample_location:
            logging.getLogger("HWR").debug("%s: both sample barcode and location provided, discarding barcode...", self.name())
            sample_id=None

        if sample_id:
            found_location=None
            scanned_matrices=self.getMatrixCodes()

            for scanned_matrix in scanned_matrices:
                if sample_id==scanned_matrix[0]:
                    try:
                        found_location=(int(scanned_matrix[1]),int(scanned_matrix[2]))
                    except:
                        found_location=None
            if found_location is None:
                logging.getLogger("HWR").error("%s: couldn't find location for matrix code %s", self.name(), sample_id)
                self.procedureExceptionCleanup("ALARM")
                return
            sample_id=None
            sample_location=found_location

        if not holderLength:
            holderLength = 22
            logging.getLogger("HWR").debug("%s: loading sample: using default holder length (%d mm)", self.name(), holderLength)

        self.loadSampleProcedure = self.__loadSampleProcedure(holderLength, sample_id, sample_location, sampleIsLoadedCallback, prepareCentring, prepareCentringMotors, wait=False)

        if wait:
          try:
            already_mounted = self.loadSampleProcedure.get()
          except Exception, diag:
            self.procedureExceptionCleanup("ALARM",str(diag))
            self.loadSampleProcedure = None
            raise
          else:
            if already_mounted:
              logging.getLogger("HWR").debug("%s: sample already loaded nothing to do", self.name())

          self.loadSampleProcedure = None
        else:
          self.loadSampleProcedure.link(self.displayErrorFromSampleChangerTask)
          return self.loadSampleProcedure


    def load_sample(self, *args, **kwargs):
      kwargs["wait"] = True
      return self.loadSample(*args, **kwargs)

    
    @task
    def __unloadSampleProcedure(self, holderLength, sample_id = None, sample_location = None, sampleIsUnloadedCallback = None):   
        if sample_id and sample_location:
            self.unlockMinidiffMotors(wait=True)
            raise Exception("Unload failed")

        if sample_id:
            logging.getLogger("HWR").debug("%s: moving to data matrix %s", self.name(), sample_id)

            self.executeJavaDeviceServerTask("MoveToDataMatrixLocation", sample_id)
                
            logging.getLogger("HWR").debug("%s: successfully moved to data matrix %s", self.name(), self.currentSampleDataMatrix)
        elif sample_location:
            try:
                basket_loc=int(sample_location[0])
                vial_loc=int(sample_location[1])
            except:
                logging.getLogger("HWR").exception("%s: could not move to location %s" % (self.name(), sample_location))
                raise Exception("Invalid sample location %s" % sample_location)

            logging.getLogger("HWR").debug("%s: moving to basket position %d", self.name(), basket_loc)
            if not self.changeSelectedBasket(basket_loc, wait=True):
                raise Exception("Could not move to basket position %s (%s)" % (basket_loc, str(diag)))
                
            logging.getLogger("HWR").debug("%s: successfully moved to basket position %s", self.name(), self.currentBasket)

            logging.getLogger("HWR").debug("%s: moving to sample position %d", self.name(), vial_loc)
            if not self.changeSelectedSample(vial_loc, wait=True):
                raise Exception("Could not move to sample position %s (%s)" % (vial_loc, str(diag)))
            
            logging.getLogger("HWR").debug("%s: successfully moved to sample position %s", self.name(), self.currentSample)
        else:
            logging.getLogger("HWR").debug("%s: unloading to current location", self.name())

        self.sampleChangerStateChanged("RUNNING")
        self.emit("statusChanged", ("Moving minidiff to unloading position", ))
        self._moveToUnloadingPosition(holderLength, wait=True, timeout=30)
                
        logging.getLogger("HWR").debug("%s: unloading position reached", self.name())

        self.executeJavaDeviceServerTask("UnLoadSample")
             
        self.unlockMinidiffMotors(wait=True)

        #logging.getLogger("HWR").debug("%s: sample is %s", self.name(), self.sampleIsLoaded() and "loaded" or "unloaded")

        if not self.sampleIsLoaded():
            logging.getLogger("HWR").debug("%s: sample is unloaded", self.name())

            self.sampleLoadStateChanged(False)

            if callable(sampleIsUnloadedCallback):
                logging.getLogger("HWR").debug("%s: calling 'sample is unloaded' callback", self.name())
                sampleIsUnloadedCallback()
        else:
            self.sampleLoadStateChanged(True)

            logging.getLogger("HWR").debug("%s: sample was not unloaded", self.name())
            raise Exception("Unload failed")
          

    def unloadSample(self, holderLength, sample_id = None, sample_location = None, sampleIsUnloadedCallback = None, failureCallback = None, wait=False):
        logging.getLogger("HWR").debug("%s: in unloadSample", self.name())

        self.procedurePrepare(failureCallback)

        if sample_id and sample_location:
            logging.getLogger("HWR").debug("%s: both sample barcode and location provided, discarding barcode...", self.name())
            sample_id=None
            self.procedureExceptionCleanup("ALARM")
            return

        if sample_id:
            found_location=None
            scanned_matrices=self.getMatrixCodes()
            for scanned_matrix in scanned_matrices:
                if sample_id==scanned_matrix[0]:
                    try:
                        found_location=(int(scanned_matrix[1]),int(scanned_matrix[2]))
                    except:
                        found_location=None
            if found_location is None:
                logging.getLogger("HWR").error("%s: couldn't find location for matrix code %s", self.name(), sample_id)
                self.procedureExceptionCleanup("ALARM")
                return
            sample_id=None
            sample_location=found_location

        if holderLength is None or holderLength=="":
            holderLength = self.getSCHolderLength()
            logging.getLogger("HWR").debug("%s: unloading sample: using holder length from SC (%f)", self.name(), holderLength)

        self.unloadSampleProcedure = self.__unloadSampleProcedure(holderLength, sample_id, sample_location, sampleIsUnloadedCallback, wait=False)

        if wait:
          try:
            self.unloadSampleProcedure.get()
          except Exception, diag:
            self.procedureExceptionCleanup("ALARM",str(diag))
       
          self.unloadSampleProcedure = None
        else:
          self.unloadSampleProcedure.link(self.displayErrorFromSampleChangerTask)
          return self.unloadSampleProcedure
    

    def __commandFailed(self, err, cmd=None):
        logging.getLogger("HWR").error("%s: command %s failed (%s)", self.name(), cmd, err)

        """
        if cmd == '_moveToLoadingPosition' or cmd == '_moveToUnloadingPosition':
            retries=self.moveToPositionRetries[0]
            holderLength=self.moveToPositionRetries[1]
            if retries>0:
                logging.getLogger("HWR").error("%s: retrying command %s", self.name(), cmd)
                self.moveToPositionRetries[0]=retries-1
                if cmd == '_moveToLoadingPosition':
                    self._moveToLoadingPosition(holderLength)
                else:
                    self._moveToUnloadingPosition(holderLength)
                return
        """
        minidiff_get_control = cmd!='unlockMinidiffMotors'

        self.procedureExceptionCleanup("ALARM",err,minidiff_get_control)


    def __commandAborted(self, cmd):
        logging.getLogger("HWR").error("%s: command %s aborted", self.name(), cmd)
        minidiff_get_control = cmd!='unlockMinidiffMotors'
        self.procedureExceptionCleanup("ALARM","spec aborted",minidiff_get_control, in_abort=True)


    def moveCryoIn(self):
        cryoDevice = self.getDeviceByRole("Cryo")
        if cryoDevice is not None:
            cryoDevice.wagoIn()
   

    def moveLightIn(self):
        lightDevice = self.getDeviceByRole("Light")
        if lightDevice is not None:
            lightDevice.wagoIn()


    def updateDataMatrices(self,old={"matrices":None}):
        matrices = self.getMatrixCodes(force=True)
        logging.getLogger("HWR").debug("%s: data matrices updated: %s", self.name(), matrices)

        loaded_sample_barcode = self.getLoadedSampleDataMatrix()
        self.selectedSampleDataMatrixChanged(loaded_sample_barcode)
      
        if old["matrices"] != matrices:
          old["matrices"] = matrices
          self.emit('matrixCodesUpdate', (matrices,))
         

    def getMatrixCodes(self,force=False):
        if force or self.scannedMatrices is None:
            matrix_codes_list = []
            sc_xml = self.getInformationAsXml()
            if sc_xml is not None:
                matrix_codes_list = getDataMatricesList(sc_xml)
            self.scannedMatrices=matrix_codes_list
        return self.scannedMatrices


    def sampleInSampleChanger(self, sample_item):
      for sample in self.scannedMatrices:
        if sample[-1] in (2, 4):
          try:
            (basket, vial) = map(int, sample_item.locationStr.split(':'))
          except:
            (basket, vial) = (None, None)

          if (sample_item.barcode is sample[0]) or \
             (basket, vial) == (sample[1], sample[2]):
            return True
        
      return False

        
    def getState(self):
        if self.isSpecConnected:
                   try:
                      stateChan = self.getChannelObject("state")
                      val = str(stateChan.getValue())
                   except:
                      val = "DISABLED"
                   return val
        return "DISABLED"


    def getStatus(self):
        if self.isSpecConnected:
           try:
              statusChan = self.getChannelObject("status")
              val = str(statusChan.getValue())
           except:
              return "unknown" 
        return val


    def getSCHolderLength(self):
        sc_holderlength_cmd = self.getCommandObject("holderlength")
        try:
            sc_holderlength = sc_holderlength_cmd((self.currentBasket, self.currentSample))
        except  Exception,diag:        
            logging.getLogger("HWR").error("%s: error getting holder length (%s)", self.name(), str(diag))
            sc_holderlength = None
        return sc_holderlength


    def selectedSampleDataMatrixChanged(self, matrixCode):
        self.currentSampleDataMatrix = matrixCode or None
        self.emit("selectedSampleDataMatrixChanged", (matrixCode, ))


    def selectedBasketDataMatrixChanged(self, matrixCode):
        self.currentBasketDataMatrix = matrixCode or None
        self.emit("selectedBasketDataMatrixChanged", (matrixCode, ))


    def isMicrodiff(self):
        return not self.prepareCentringAfterLoad


    def getLoadedSampleDataMatrix(self):
      for code in self.getMatrixCodes():
        matrix=code[0]
        basket=code[1]
        vial=code[2]
        try:
          basket_code=str(code[3])
        except:
          basket_code=""

        flag = int(code[4])
        if flag & 8:
          return matrix
            
      
    def getLoadedSampleLocation(self):
      for code in self.getMatrixCodes():
        matrix=code[0]
        basket=code[1]
        vial=code[2]
        try:
          basket_code=str(code[3])
        except:
          basket_code=""

        flag = int(code[4])
        if flag & 8:
          return (basket, vial)
      return (None, None)



    def getLoadedHolderLength(self):
        try:
            loaded=self.loadedSampleDict["loaded"]
        except:
            loaded=False
        if loaded:
            try:
                holderlength=float(self.loadedSampleDict["holderlength"])
            except:
                holderlength=None
        else:
            holderlength=None
        return holderlength


    def getBasketPresence(self):
        return self.isScanBasketForDataMatrixDone()
      

    def canLoadSample(self,sample_code=None,sample_location=None,holder_lenght=None):
        can_load=False
        already_loaded=False

        something_is_loaded=self.sampleIsLoaded()
        sc_state=self.getState()

        if sc_state in ("STANDBY","ALARM"):
            if sample_code or sample_location:
                if something_is_loaded:
                    if self.getLoadedSampleDataMatrix() or self.getLoadedSampleLocation():
                        can_load=True
                else:
                    can_load=True

        if something_is_loaded:
            if sample_code and sample_code==self.getLoadedSampleDataMatrix():
                already_loaded=True
            elif sample_location and sample_location==self.getLoadedSampleLocation():
                already_loaded=True

        if SampleChanger.ALWAYS_ALLOW_MOUNTING:
            can_load=True
        return (can_load,already_loaded)


    def operationalFlagsChanged(self,val):
        try:
            val=int(val)
        except:
            logging.getLogger("HWR").exception("%s: error reading operational flags" % self.name())
            return

        old_sc_can_load = self.lastOperationalFlags & SampleChanger.FLAG_SC_CAN_LOAD
        new_sc_can_load = val & SampleChanger.FLAG_SC_CAN_LOAD
        if old_sc_can_load != new_sc_can_load:
            self.emit("sampleChangerCanLoad", (new_sc_can_load>0, ))

        old_md_can_move = self.lastOperationalFlags & SampleChanger.FLAG_MINIDIFF_CAN_MOVE
        new_md_can_move = val & SampleChanger.FLAG_MINIDIFF_CAN_MOVE
        if old_md_can_move != new_md_can_move:
            self.emit("minidiffCanMove", (new_md_can_move>0, ))

        old_sc_in_use = self.lastOperationalFlags & SampleChanger.FLAG_SC_IN_USE
        new_sc_in_use = val & SampleChanger.FLAG_SC_IN_USE
        if old_sc_in_use != new_sc_in_use:
            self.emit("sampleChangerInUse", (new_sc_in_use>0, ))

        self.lastOperationalFlags = val


    def sampleChangerInUse(self):
        sc_in_use = self.lastOperationalFlags & SampleChanger.FLAG_SC_IN_USE
        return sc_in_use>0


    def sampleChangerCanLoad(self):
        sc_can_load = self.lastOperationalFlags & SampleChanger.FLAG_SC_CAN_LOAD
        return sc_can_load>0


    def minidiffCanMove(self):
        md_can_move= self.lastOperationalFlags & SampleChanger.FLAG_MINIDIFF_CAN_MOVE
        return md_can_move>0


    def minidiffGetControl(self):
        try:
            self.unlockMinidiffMotors()
        except:
            logging.getLogger("HWR").exception("%s: error unlocking minidiff motors" % self.name())
            return False
        return True

    def sampleChangerToLoadingPosition(self):
        try:
            r=self._moveToLoadingPosition()
        except:
            logging.getLogger("HWR").exception("%s: error moving sample changer to loading position" % self.name())
            return False
        return True

    def basketTransferModeChanged(self, basket_transfer):
        logging.info(basket_transfer and "Sample Changer switched to basket transfer mode" or "Sample Changer switched to sample transfer mode")
        self.emit("sampleChangerBasketTransferModeChanged", (basket_transfer and True or False, ))

    def getBasketTransferMode(self):
        return self.getChannelObject("transferMode").getValue()

    def switchToSampleTransferMode(self):
        self.getCommandObject("switchTransferMode")(False)
        self.basketTransferModeChanged(False)
