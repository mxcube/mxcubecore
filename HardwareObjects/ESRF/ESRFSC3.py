"""ESRF SC3 Sample Changer Hardware Object
"""
from HardwareRepository.TaskUtils import *
from sample_changer import SC3
import functools

class ESRFSC3(SC3.SC3):
    (FLAG_SC_IN_USE,FLAG_MINIDIFF_CAN_MOVE,FLAG_SC_CAN_LOAD,FLAG_SC_NEVER) = (1,2,4,8)
    (STATE_BASKET_NOTPRESENT,STATE_BASKET_UNKNOWN,STATE_BASKET_PRESENT) = (-1,0,1)

    def __init__(self, *args, **kwargs):
        SC3.SC3.__init__(self, *args, **kwargs)

        self.lastOperationalFlags = ESRFSC3.FLAG_SC_NEVER

    def init(self):
        SC3.SC3.init(self)

        try:
            operationalChan = self.getChannelObject("OperationalFlags")
            chan = operationalChan.getValue()
            operationalChan.connectSignal("update", self.operationalFlagsChanged)
        except:
            operationalChan = self.getProperty("OperationalFlags")
            chan = operationalChan
        
        try:
            self.operationalFlagsChanged(chan)
        except:
            logging.getLogger("HWR").exception("%s: error getting SC vs MD operational flags" % self.name())

        try:
            self.microdiff
        except AttributeError:
            self.prepareCentringAfterLoad=True
        else:
            self.prepareCentringAfterLoad=False


    def __getSample(self, sample_id, sample_location):
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

        return sample


    def chained_load(self, sample_to_unload, sample_to_load):
        SC3.SC3.unload(self, sample_to_unload)
        return SC3.SC3.load(self, sample_to_load)

 
    @task
    def load(self, holderLength, sample_id=None, sample_location=None, sampleIsLoadedCallback=None, failureCallback=None, prepareCentring=True):
        loaded = False

        with error_cleanup(functools.partial(self.emit, "stateChanged", SC3.SampleChangerState.Alarm), failureCallback):
          with cleanup(functools.partial(self.emit, "stateChanged", SC3.SampleChangerState.Ready)):
            with cleanup(self.unlockMinidiffMotors, wait=True, timeout=3):
                loaded = self.__loadSample(holderLength, sample_id, sample_location)
        
            if loaded:
                logging.getLogger("HWR").debug("%s: sample is loaded", self.name())

                if self.prepareCentringAfterLoad and prepareCentring:
                    logging.getLogger("HWR").debug("%s: preparing minidiff for sample centring", self.name())
                    self.emit("stateChanged", SC3.SampleChangerState.Moving)
                    self.emit("statusChanged", "Preparing minidiff for sample centring")
                    self.prepareCentring(wait=True, timeout=1000)
              
                self.emit("statusChanged", "Ready")
 
                if callable(sampleIsLoadedCallback):
                    sampleIsLoadedCallback()


    def _getLoadingState(self):
        # if needed, should wait for SC to be able to load (loading state)
        pass


    def __loadSample(self, holderLength, sample_id, sample_location):
        logging.getLogger("HWR").debug("%s: in loadSample", self.name())

        sample = self.__getSample(sample_id, sample_location)

        if self.getLoadedSample() == sample:
            return True

        if not holderLength:
            holderLength = 22
            logging.getLogger("HWR").debug("%s: loading sample: using default holder length (%d mm)", self.name(), holderLength)

        sample._setHolderLength(holderLength)

        self.emit("stateChanged", SC3.SampleChangerState.Moving)
        self.emit("statusChanged", "Moving diffractometer to loading position")
        self._moveToLoadingPosition(holderLength, wait=True, timeout=10000)

        try:
            SC3.SC3.load(self, sample, wait=True)
        except Exception, err:
            self.emit("statusChanged", str(err))
            raise

        self._getLoadingState()
        return self.getLoadedSample() == sample

    def load_sample(self, *args, **kwargs):
      kwargs["wait"] = True
      return self.load(*args, **kwargs)

    @task
    def unload(self, holderLength, sample_id=None, sample_location=None, sampleIsUnloadedCallback=None, failureCallback=None):
        unloaded = False

        with error_cleanup(functools.partial(self.emit, "stateChanged", SC3.SampleChangerState.Alarm), failureCallback):
          with cleanup(functools.partial(self.emit, "stateChanged", SC3.SampleChangerState.Ready)):
            with cleanup(self.unlockMinidiffMotors, wait=True, timeout=3):
                unloaded = self.__unloadSample(holderLength, sample_id, sample_location)

            if unloaded:
                logging.getLogger("HWR").debug("%s: sample has been unloaded", self.name())

                self.emit("statusChanged", "Ready")

                if callable(sampleIsUnloadedCallback):
                    sampleIsUnloadedCallback()


    def __unloadSample(self, holderLength, sample_id, sample_location):   
        sample = self.__getSample(sample_id, sample_location)

        if not holderLength:
            holderLength = 22
            logging.getLogger("HWR").debug("%s: unloading sample: using default holder length (%d mm)", self.name(), holderLength)

        sample._setHolderLength(holderLength)

        self.emit("stateChanged", SC3.SampleChangerState.Moving)
        self.emit("statusChanged", "Moving diffractometer to unloading position")

        self._moveToUnloadingPosition(holderLength, wait=True, timeout=10000)
        SC3.SC3.unload(self, sample, wait=True)
 
        self._getLoadingState()
        return not self.hasLoadedSample()

    def moveCryoIn(self):
        cryoDevice = self.getDeviceByRole("Cryo")
        if cryoDevice is not None:
            cryoDevice.wagoIn()
   
    def moveLightIn(self):
        lightDevice = self.getDeviceByRole("Light")
        if lightDevice is not None:
            lightDevice.wagoIn()

    #def getSCHolderLength(self):
    #    return 

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

    """
    def sampleChangerToLoadingPosition(self):
        try:
            r=self._moveToLoadingPosition()
        except:
            logging.getLogger("HWR").exception("%s: error moving sample changer to loading position" % self.name())
            return False
        return True
    """
