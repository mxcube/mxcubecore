"""Sample Changer Hardware Object
"""
from HardwareRepository.TaskUtils import *
from sample_changer import SC3
import gevent 

class ESRFSC3(SC3.SC3):
    (FLAG_SC_IN_USE,FLAG_MINIDIFF_CAN_MOVE,FLAG_SC_CAN_LOAD,FLAG_SC_NEVER) = (1,2,4,8)
    (STATE_BASKET_NOTPRESENT,STATE_BASKET_UNKNOWN,STATE_BASKET_PRESENT) = (-1,0,1)
    USE_SPEC_LOADED_SAMPLE = False
    ALWAYS_ALLOW_MOUNTING  = True

    def __init__(self, *args, **kwargs):
        SC3.SC3.__init__(self, *args, **kwargs)

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
        self.lastOperationalFlags = ESRFSC3.FLAG_SC_NEVER
        self.loadedSampleDict={}
        self.scannedMatrices=None

    def init(self):
        SC3.SC3.init(self)

        moveToLoadingPositionCmd = self.addCommand({ 'type': 'spec', 'name': '_moveToLoadingPosition' }, "SCMoveToLoadingPos")
        moveToUnloadingPositionCmd = self.addCommand({'type': 'spec', 'name': '_moveToUnloadingPosition'}, "SCMoveToUnloadingPos")
        unlockMinidiffMotorsCmd = self.addCommand({ 'type': 'spec', 'name': 'unlockMinidiffMotors'}, "SCMinidiffGetControl")
        unlockMinidiffMotorsCleanupCmd = self.addCommand({ 'type': 'spec', 'name': 'unlockMinidiffMotorsCleanup'}, "SCMinidiffGetControl")
        prepareCentringCmd = self.addCommand({ 'type': 'spec', 'name': 'prepareCentring'}, "minidiff_prepare_centring")
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

    # Called when spec is disconnected
    #def specDisconnected(self):
    #    self.isSpecConnected=False
    #    self.sampleChangerStateChanged("DISABLE")

    # Called when spec is connected
    #def specConnected(self):
    #    self.isSpecConnected=True
    #    self.sampleChangerStateChanged(self.getState())

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

    @task
    def loadSample(self, holderLength, sample_id=None, sample_location=None, sampleIsLoadedCallback=None, failureCallback=None, prepareCentring=None, prepareCentringMotors={}):
        logging.getLogger("HWR").debug("%s: in loadSample", self.name())

        self.procedurePrepare(failureCallback)

        if sample_id and sample_location:
            logging.getLogger("HWR").debug("%s: both sample barcode and location provided, discarding barcode...", self.name())
            sample_id = None

        if sample_id:
            sample = self.getComponentById(sample_id)
        else:
            if sample_location:
              basket_number, sample_number = sample_location
              sample = self.getComponentByAddress(SC3.Pin.getSampleAddress(basket_number, sample_number))
            else:
              sample = self.getSelectedSample()            

        if not holderLength:
            holderLength = 22
            logging.getLogger("HWR").debug("%s: loading sample: using default holder length (%d mm)", self.name(), holderLength)

        sample._setHolderLength(holderLength)

        if self.getLoadedSample() == sample:
            return True

        #self.sampleChangerStateChanged("RUNNING")
        #self.emit("statusChanged", ("Moving minidiff to loading position", ))
        self._moveToLoadingPosition(holderLength, wait=True, timeout=30)

        self.loadSampleProcedure = self.load(sample, wait=True)

        if self.hasLoadedSample():
              logging.getLogger("HWR").debug("%s: sample is loaded", self.name())

              self.unlockMinidiffMotors(wait=True, timeout=3)

              if self.prepareCentringAfterLoad is True and prepareCentring is not False:
                  logging.getLogger("HWR").debug("%s: preparing the sample for centring", self.name())
                  #self.sampleChangerStateChanged("RUNNING")
                  self.emit("statusChanged", ("Preparing minidiff for sample centring", ))

                  motors_pos_str=";".join(["%s %f" % (MP[0],MP[1]) for MP in prepareCentringMotors.iteritems()])
                  self.prepareCentring(motors_pos_str, wait=True, timeout=30)

              if callable(sampleIsLoadedCallback):
                  sampleIsLoadedCallback(True)
        else:
            self.sampleLoadStateChanged(False)
            raise Exception("Load failed")


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

        try:
          self.executeJavaDeviceServerTask("UnLoadSample")
        except:
          pass
     
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

    def getSCHolderLength(self):
        sc_holderlength_cmd = self.getCommandObject("holderlength")
        try:
            sc_holderlength = sc_holderlength_cmd((self.currentBasket, self.currentSample))
        except  Exception,diag:        
            logging.getLogger("HWR").error("%s: error getting holder length (%s)", self.name(), str(diag))
            sc_holderlength = None
        return sc_holderlength

    def isMicrodiff(self):
        return not self.prepareCentringAfterLoad

    def operationalFlagsChanged(self,val):
        try:
            val=int(val)
        except:
            logging.getLogger("HWR").exception("%s: error reading operational flags" % self.name())
            return

        old_sc_can_load = self.lastOperationalFlags & ESRFSC3.FLAG_SC_CAN_LOAD
        new_sc_can_load = val & ESRFSC3.FLAG_SC_CAN_LOAD
        if old_sc_can_load != new_sc_can_load:
            self.emit("sampleChangerCanLoad", (new_sc_can_load>0, ))

        old_md_can_move = self.lastOperationalFlags & ESRFSC3.FLAG_MINIDIFF_CAN_MOVE
        new_md_can_move = val & ESRFSC3.FLAG_MINIDIFF_CAN_MOVE
        if old_md_can_move != new_md_can_move:
            self.emit("minidiffCanMove", (new_md_can_move>0, ))

        old_sc_in_use = self.lastOperationalFlags & ESRFSC3.FLAG_SC_IN_USE
        new_sc_in_use = val & ESRFSC3.FLAG_SC_IN_USE
        if old_sc_in_use != new_sc_in_use:
            self.emit("sampleChangerInUse", (new_sc_in_use>0, ))

        self.lastOperationalFlags = val

    def sampleChangerInUse(self):
        sc_in_use = self.lastOperationalFlags & ESRFSC3.FLAG_SC_IN_USE
        return sc_in_use>0

    def sampleChangerCanLoad(self):
        sc_can_load = self.lastOperationalFlags & ESRFSC3.FLAG_SC_CAN_LOAD
        return sc_can_load>0

    def minidiffCanMove(self):
        md_can_move= self.lastOperationalFlags & ESRFSC3.FLAG_MINIDIFF_CAN_MOVE
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
