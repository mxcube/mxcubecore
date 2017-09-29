"""
CATS sample changer hardware object.

Implements the abstract interface of the GenericSampleChanger for the CATS
sample changer model.
Derived from Alexandre Gobbo's implementation for the EMBL SC3 sample changer.

PX2Cats sample changer hardware object inherit of PX1Cats.

Support for the CATS sample changer at SOLEIL PX1.  Using the 
device server CryoTong by Patrick Gourhant transfert it in PROXIMA 2

Implements the abstract interface of the GenericSampleChanger for the CATS
sample changer model.

This object includes both the SampleChanger interface and the Maintenance features 
as initially developed by Michael Hellmig for BESSY beamlines

"""
from GenericSampleChanger import *
import time
import logging

__author__ = "Gadea Laurent"
__credits__ = ["The MxCuBE collaboration"]

__email__ = "laurent.gadea@synchrotron-soleil.fr"
__status__ = "Beta from cryotong PX1"

class Pin(Sample):        
    STD_HOLDERLENGTH = 22.0

    def __init__(self,basket,basket_no,sample_no):
        super(Pin, self).__init__(basket, Pin.getSampleAddress(basket_no,sample_no), True)
        self._setHolderLength(Pin.STD_HOLDERLENGTH)

    def getBasketNo(self):
        return self.getContainer().getIndex()+1

    def getVialNo(self):
        return self.getIndex()+1

    @staticmethod
    def getSampleAddress(basket_number, sample_number):
        return str(basket_number) + ":" + "%02d" % (sample_number)


class Basket(Container):
    __TYPE__ = "Puck"    
    NO_OF_SAMPLES_PER_PUCK = 16

    def __init__(self,container,number):
        super(Basket, self).__init__(self.__TYPE__,container,Basket.getBasketAddress(number),True)
        for i in range(Basket.NO_OF_SAMPLES_PER_PUCK):
            slot = Pin(self,number,i+1)
            self._addComponent(slot)
                            
    @staticmethod
    def getBasketAddress(basket_number):
        return str(basket_number)

    def clearInfo(self):
        self.getContainer()._reset_basket_info(self.getIndex()+1)
        self.getContainer()._triggerInfoChangedEvent()

#identique a Cats90
class PX2Cats(SampleChanger):
    """
    Actual implementation of the CATS Sample Changer,
    SOLEIL PX2A installation with 3 lids and 144 samples
    """
    logging.info(">>>>............ INIT PX2Cats    .....<<<<<<<<<<<<<")    
    __TYPE__ = "CATS"    
    NO_OF_LIDS = 3
    NO_OF_BASKETS = 9
    TOOL = "1"

    def __init__(self, *args, **kwargs):
        super(PX2Cats, self).__init__(self.__TYPE__,False, *args, **kwargs)
            
    def init(self): 
        self._selected_sample = None
        self._selected_basket = None
        self._scIsCharging = None
        #detector object egq lqu PX1environment
        self.detector = None
        self.distanceToLoad = 200
#==============================================================================
#       PX1CatsCryoton  Catsmqin
        self.task_started = 0
        self.task_name = None
        self.last_state_emit = 0

        self._lidState = None
        self._poweredState = None
        self._toolState = None
        self._safeNeeded = None
        self._ln2regul = None
        self._last_status = None
        self._sc_state = None
        self._global_state = None

        #self.currentBasketDataMatrix = "this-is-not-a-matrix"
        #self.currentSample = -1
        #self.currentBasket = -1
#==============================================================================

        # add support for CATS dewars with variable number of lids
        # assumption: each lid provides access to three baskets
        self._propNoOfLids       = self.getProperty('no_of_lids')
        self._propSamplesPerPuck = self.getProperty('samples_per_puck')
        self._propHolderLength   = self.getProperty('holder_length')

        self.currentBasketDataMatrix = "this-is-not-a-matrix"
        self.currentSample = -1 
        self.currentBasket = -1

        if self._propNoOfLids is not None:
            try:
                PX2Cats.NO_OF_LIDS = int(self._propNoOfLids)
            except ValueError:
                pass
            else:
                PX2Cats.NO_OF_BASKETS = 3 * PX2Cats.NO_OF_LIDS

        if self._propSamplesPerPuck is not None:
            try:
                Basket.NO_OF_SAMPLES_PER_PUCK = int(self._propSamplesPerPuck)
            except ValueError:
                pass
 
        if self._propHolderLength is not None:
            try:
                Pin.STD_HOLDERLENGTH = int(self._propHolderLength)
            except ValueError:
                pass
        
        
        # initialize the sample changer components, moved here from __init__ after allowing
        # variable number of lids
        for i in range(PX2Cats.NO_OF_BASKETS):
            basket = Basket(self,i+1)
            self._addComponent(basket)
        
        for channel_name in ("_chnState","_chnStatus", \
                             "_chnNumLoadedSample", "_chnLidLoadedSample",\
                             "_chnSampleBarcode", "_chnPathRunning",\
                             "_chnSampleIsDetected",\
                             "_chnPowered", "_chnSafeNeeded", \
                             "_chnLN2RegulationDewar1","_chnMessage", \
                             "_chnSoftAuth", "_chnhomeOpened", "_chnDryAndSoakNeeded", "_chnIncoherentGonioSampleState"):
            setattr(self, channel_name, self.getChannelObject(channel_name))
        
        self._chnSampleOnDiff = self.getChannelObject("_sampleOnDiff")
        #self._chnSampleOnDiff.connectSignal("update", self._updateRunningState) -> not used

        #self._chnLidState.connectSignal("update", self._updateLidState) -> PX1 connect to isLidClosed 
        self._chnPowered.connectSignal("update", self._updatePoweredState)
        #self._chnSafeNeeded.connectSignal("update", self._updateSafeNeeded) -> cryotong PX1
        self._chnLN2RegulationDewar1.connectSignal("update", self._updateRegulationState)
        #self._chnToolOpen.connectSignal("update", self._updateToolOpen) 
        #self._chnSoftAuth.connectSignal("update", self._softwareAuthorization) -> -> cryotong PX1
        self._chnPathRunning.connectSignal("update", self._updateRunningState)
        self._chnMessage.connectSignal("update", self._updateMessage)
        #self._chnIncoherentGonioSampleState.connectSignal("update", self._updateAckSampleMemory)
        #self._chnDryAndSoakNeeded.connectSignal("update",self._dryAndSoakNeeded) -> cryotong PX1
        self._chnSampleIsDetected.connectSignal("update",self._updateSampleIsDetected)
        
        for basket_index in range(PX2Cats.NO_OF_BASKETS):            
            channel_name = "_chnBasket%dState" % (basket_index + 1)
            setattr(self, channel_name, self.getChannelObject(channel_name))
            
        for lid_index in range(PX2Cats.NO_OF_LIDS):            
            channel_name = "_chnLid%dState" % (lid_index + 1)
            setattr(self, channel_name, self.getChannelObject(channel_name))
            if getattr(self, channel_name) is not None:
                getattr(self, channel_name).connectSignal("update", getattr(self, "_updateLid%dState" % (lid_index + 1)))
                   
        for command_name in ("_cmdAbort", "_cmdLoad", "_cmdUnload", "_cmdChainedLoad",\
                             "_cmdReset", "_cmdBack", "_cmdSafe", "_cmdHome", "_cmdDry",\
                             "_cmdDrySoak", "_cmdSoak", "_cmdClearMemory",\
                             "_cmdAckSampleMemory", "_cmdOpenTool", "_cmdToolCal", "_cmdPowerOn", "_cmdPowerOff", \
                             "_cmdOpenLid1", "_cmdCloseLid1", "_cmdOpenLid2", "_cmdCloseLid2", "_cmdOpenLid3", "_cmdCloseLid3", \
                             "_cmdRegulOn"):
            setattr(self, command_name, self.getCommandObject(command_name))
        
        # "_cmdRegulOff" from PX1 not used
           
        #
        self._lidStatus = self.getChannelObject("_chnTotalLidState")
        if self._lidStatus is not None:
            self._lidStatus.connectSignal("update", self._updateOperationMode)
        #    
        try:
            self.detector= self.getObjectByRole("detectordistance")
            if self.detector is not None :
                logging.info("Detector Distance %s" % self.detector.getChannelObject("position").getValue())
                
        except :
            logging.getLogger("HWR").error('CatsPX2 detectordistance tangopssDevice is not defined ')
            
        #guillotin PX2    
        self.guillotine  = self.getObjectByRole("guillotine")

        self._initSCContents()

        # SampleChanger.init must be called _after_ initialization of the Cats because it starts the update methods which access
        # the device server's status attributes
        SampleChanger.init(self)
        logging.info(">>>>>........ INIT PX2CatsMockup  DONE  ...<<<<")

    def getSampleProperties(self):
        """
        Get the sample's holder length

        :returns: sample length [mm]
        :rtype: double
        """
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)#WASA
        
    def can_wash(self):
        return True

    # a tester from PX1 si util !!!!
    def is_mounted_sample(self, sample_location):        
        try:
            if sample_location == tuple(map(str,self.getLoadedSample().getCoords())):
                return True
            else:
                return False
        except AttributeError:
            logging.warning("PX1Cats. is_mounted_sample error.")
            return False 
    
    #from cats90
    def getBasketList(self):
        basket_list = []
        for basket in self.components:
            if isinstance(basket, Basket):
                basket_list.append(basket)
        return basket_list
     
     
    #########################           TASKS           #########################

    def getLoadedSampleDataMatrix(self):
        return "-not-a-matrix-"
        
    def _doUpdateInfo(self):       
        """
        Updates the sample changers status: mounted pucks, state, currently loaded sample

        :returns: None
        :rtype: None
        """
        """
        self._updateSCContents()
        # periodically updating the selection is not needed anymore, because each call to _doSelect
        # updates the selected component directly:
        # self._updateSelection()
        """
        self._updateSCContents()
        self._updateState()
        self._updateLoadedSample()           
        """        
        self._updateLoadedSample()
        
        #self._updateStatus()
        #self._updateLidState() # updateLid%dState
        #self._updatePoweredState()
        #self._updateSafeNeeded() PX1 ?
        #self._updateToolOpen() no used in PX1 r

        self._updateRegulationState()

        #self._updateGlobalState()
        """            
    def _doChangeMode(self,mode):
        """
        Changes the SC operation mode, not implemented for the CATS system

        :returns: None
        :rtype: None
        """
        pass

    def _directlyUpdateSelectedComponent(self, basket_no, sample_no):    
        basket = None
        sample = None
        try:
          if basket_no is not None and basket_no>0 and basket_no <=PX2Cats.NO_OF_BASKETS:
            basket = self.getComponentByAddress(Basket.getBasketAddress(basket_no))
            if sample_no is not None and sample_no>0 and sample_no <=Basket.NO_OF_SAMPLES_PER_PUCK:
                sample = self.getComponentByAddress(Pin.getSampleAddress(basket_no, sample_no))            
        except:
          pass
        self._setSelectedComponent(basket)
        self._setSelectedComponent(basket)
        self._setSelectedSample(sample)

    def _doSelect(self,component):
        """
        Selects a new component (basket or sample).
	Uses method >_directlyUpdateSelectedComponent< to actually search and select the corrected positions.

        :returns: None
        :rtype: None
        """
        if isinstance(component, Sample):
            selected_basket_no = component.getBasketNo()
            selected_sample_no = component.getIndex()+1
        elif isinstance(component, Container) and ( component.getType() == Basket.__TYPE__):
            selected_basket_no = component.getIndex()+1
            selected_sample_no = None
        self._directlyUpdateSelectedComponent(selected_basket_no, selected_sample_no)
            
    def _doScan(self,component,recursive):
        """
        Scans the barcode of a single sample, puck or recursively even the complete sample changer.
        Basket.NO_OF_SAMPLES_PER_PUCK = 16 MAX IV = 10
        :returns: None
        :rtype: None
        """
        selected_basket = self.getSelectedComponent()
        if isinstance(component, Sample):            
            # scan a single sample
            if (selected_basket is None) or (selected_basket != component.getContainer()):
                self._doSelect(component)            
            selected=self.getSelectedSample()            
            # self._executeServerTask(self._scan_samples, [component.getIndex()+1,])
            lid = ((selected.getBasketNo() - 1) / 3) + 1
            sample = (((selected.getBasketNo() - 1) % 3) * Basket.NO_OF_SAMPLES_PER_PUCK) + selected.getVialNo()
            argin = [PX2Cats.TOOL, str(lid), str(sample), "1", "0"]
            self._executeServerTask(self._cmdScanSample, argin)
            self._updateSampleBarcode(component)
        elif isinstance(component, Container) and ( component.getType() == Basket.__TYPE__):
            # component is a basket
            if recursive:
                pass
            else:
                if (selected_basket is None) or (selected_basket != component):
                    self._doSelect(component)            
                # self._executeServerTask(self._scan_samples, (0,))                
                selected=self.getSelectedSample()            
                for sample_index in range(Basket.NO_OF_SAMPLES_PER_PUCK):
                    lid = ((selected.getBasketNo() - 1) / 3) + 1
                    sample = (((selected.getBasketNo() - 1) % 3) * Basket.NO_OF_SAMPLES_PER_PUCK) + (sample_index+1)
                    argin = [PX2Cats.TOOL, str(lid), str(sample), "1", "0"]
                    self._executeServerTask(self._cmdScanSample, argin)
        elif isinstance(component, Container) and ( component.getType() == SC3.__TYPE__):
            for basket in self.getComponents():
                self._doScan(basket, True)
    
    def _doLoad(self,sample=None):
        """
        Loads a sample on the diffractometer. Performs a simple put operation if the diffractometer is empty, and 
        a sample exchange (unmount of old + mount of new sample) if a sample is already mounted on the diffractometer.

        :returns: None
        :rtype: None
        """
        
        if not self._chnPowered.getValue():
            raise Exception("CATS power is not enabled. Please switch on arm power before transferring samples.")
        selected=self.getSelectedSample()            
        if sample is not None:
            if sample != selected:
                self._doSelect(sample)
                selected=self.getSelectedSample()            
        else:
            if selected is not None:
                 sample = selected
            else:
               raise Exception("No sample selected")
               
        # calculate CATS specific lid/sample number
        lid = ((selected.getBasketNo() - 1) / 3) + 1
        sample = (((selected.getBasketNo() - 1) % 3) * Basket.NO_OF_SAMPLES_PER_PUCK) + selected.getVialNo()
        argin = [PX2Cats.TOOL, str(lid), str(sample), "1", "0", "-1000", "-700", "250"]
        """
        #check distance detector PX1
        distance = self.detector.getChannelObject("position").getValue()
        
        flag = False
        tempDistance = distance
        if distance < self.distanceToLoad :            
            flag = True
            self.detector.move(self.distanceToLoad)
            time.sleep(2.0)
            while self.detector.motorIsMoving():
                time.sleep(0.5)
        
        if not self.guillotine.isInsert():
            self.guillotine.setIn()
            
        """
        if self.hasLoadedSample():
            if selected==self.getLoadedSample():
                raise Exception("The sample " + str(self.getLoadedSample().getAddress()) + " is already loaded")
            else:
                self._executeServerTask(self._cmdChainedLoad, argin)
        else:
            #logging.debug("CATS executing server task command load.")
            self._executeServerTask(self._cmdLoad, argin)
            logging.debug("CATS executing server task command load done.")
        """  
        if flag :
            self.detector.move(tempDistance)
            time.sleep(2.0)
            while self.detector.motorIsMoving():
                time.sleep(0.5)
        """  
        #self._waitDeviceReady()
            
    def _doUnload(self,sample_slot=None):
        """
        Unloads a sample from the diffractometer.

        :returns: None
        :rtype: None
        """
        if not self._chnPowered.getValue():
            raise Exception("CATS power is not enabled. Please switch on arm power before transferring samples.")

        """#check distance detector
        distance = self.detector.getChannelObject("position").getValue()
        
        flag = False
        tempDistance = distance
        if distance < self.distanceToLoad :            
            flag = True
            self.detector.move(self.distanceToLoad)
            time.sleep(2.0)
            while self.detector.motorIsMoving():
                time.sleep(0.5)
        
        if not self.guillotine.isInsert():
            self.guillotine.setIn()
        """    
        if (sample_slot is not None):
            self._doSelect(sample_slot)
        argin = [PX2Cats.TOOL, "0", "-1000", "-700", "250"]
        self._executeServerTask(self._cmdUnload, argin)
        """
        if flag :
            self.detector.move(tempDistance)
            time.sleep(2.0)
            while self.detector.motorIsMoving():
                time.sleep(0.5)
        """
        
    def clearBasketInfo(self, basket):
        pass

    #########################           PRIVATE           ########################
    """CATSBRICKMAIN"""
    
    def backTraj(self):    
        """
        Moves a sample from the gripper back into the dewar to its logged position.
        """    
        return self._executeTask2(False,self._doBack)     

    def safeTraj(self):    
        """
        Safely Moves the robot arm and the gripper to the home position
        """    
        return self._executeTask2(False,self._doSafe)     

    ###MS 2014-11-18
    def homeTraj(self):    
        """
        Moves the robot arm to the home position
        """    
        return self._executeTask2(False,self._doHome)  
        
    def dryTraj(self):    
        """
        Drying the gripper
        """    
        return self._executeTask2(False,self._doDry)  
        
    def drySoakTraj(self):    
        """
        Dry and Soak the gripper
        """    
        return self._executeTask2(False,self._doDrySoak)
        
    def soakTraj(self):    
        """
        Soaking the gripper
        """    
        return self._executeTask2(False,self._doSoak)  
        
    def clearMemory(self):    
        """
        Clears the memory
        """    
        return self._executeTask2(False,self._doClearMemory)  
    
    def ackSampleMemory(self):    
        """
        Acknowledge incoherence between memorized and actual sample status -- e.g. if robot executed put trajectory but no sample was mounted on the gonio -- either because of empty position or problem with gripper.
        """    
        return self._executeTask2(False,self._doAckSampleMemory) 
        
    def opentool(self):    
        """
        Drying the gripper
        """    
        return self._executeTask2(False,self._doOpentool)  
        
    def toolcalTraj(self):    
        """
        Soaking the gripper
        """    
        return self._executeTask2(False,self._doToolCal)
    
#==============================================================================
#     def _doAbort(self):
#         """
#         Launch the "abort" trajectory on the CATS Tango DS
# 
#         :returns: None
#         :rtype: None
#         """
#         self._cmdAbort()            
# 
#     def _doReset(self):
#         """
#         Launch the "reset" command on the CATS Tango DS
# 
#         :returns: None
#         :rtype: None
#         """
#==============================================================================
#        self._cmdReset()

    def _doBack(self):
        """
        Launch the "back" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = 1
        self._executeServerTask(self._cmdBack, argin)

    def _doSafe(self):
        """
        Launch the "safe" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = 1
        self._executeServerTask(self._cmdSafe, argin)

    # MS 2014-11-18
    def _doHome(self):
        """
        Launch the "home" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = 1
        self._executeServerTask(self._cmdHome, argin)
    
    def _doDry(self):
        """
        Launch the "dry" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = 1
        self._executeServerTask(self._cmdDry, argin)
    
    def _doDrySoak(self):
        """
        Launch the "dry_soak" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = ('1', '2')
        self._executeServerTask(self._cmdDrySoak, argin)
        
    def _doSoak(self):
        """
        Launch the "soak" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = ('1', '2')
        self._executeServerTask(self._cmdSoak, argin)
        
    def _doClearMemory(self):
        """
        Execute "clear_memory" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        #argin = 1
        self._executeServerTask(self._cmdClearMemory)
        
    def _doAckSampleMemory(self):
        """
        Execute "clear_memory" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        #argin = 1
        self._executeServerTask(self._cmdAckSampleMemory)
    
    def _doOpentool(self):
        """
        Open tool via the CATS Tango DS

        :returns: None
        :rtype: None
        """
        #argin = 1
        self._executeServerTask(self._cmdOpenTool) #, argin)
        
    def _doToolCal(self):
        """
        Launch the "toolcal" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        #argin = 1
        self._executeServerTask(self._cmdToolCal)     
    ###
    
    def _doPowerState(self, state=False):
        """
        Switch on CATS power if >state< == True, power off otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._cmdPowerOn()
        else:
            self._cmdPowerOff()

    def _doEnableRegulation(self):
        """
        Switch on CATS regulation

        :returns: None
        :rtype: None
        """
        self._cmdRegulOn()

    def _doLid1State(self, state = True):
        """
        Opens lid 1 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._executeServerTask(self._cmdOpenLid1)
        else:
            self._executeServerTask(self._cmdCloseLid1)
           
    def _doLid2State(self, state = True):
        """
        Opens lid 2 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._executeServerTask(self._cmdOpenLid2)
        else:
            self._executeServerTask(self._cmdCloseLid2)
           
    def _doLid3State(self, state = True):
        """
        Opens lid 3 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._executeServerTask(self._cmdOpenLid3)
        else:
            self._executeServerTask(self._cmdCloseLid3)
    """CatsBricks"""
        
    def _doAbort(self):
        """
        Aborts a running trajectory on the sample changer.

        :returns: None
        :rtype: None
        """
        self._cmdAbort()            

    def _doReset(self):
        """
        Launch the "reset" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdReset()

    #     
    def _softwareAuthorization(self, value):
        self.emit("softwareAuthorizationChanged", (value,))   

    def _updateOperationMode(self, value):
        self._scIsCharging = not value
    
    def _pathRunning(self,timeout=None):
        """
        Waits until the pathRunning change value from false to true better than time.sleep !

        :returns: None
        :rtype: None
        """

        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self._chnPathRunning.getValue():
                gevent.sleep(0.01)
                
    def _executeServerTask(self, method, *args):
        """
        Executes a task on the CATS Tango device server

        :returns: None
        :rtype: None
        """
        self._waitDeviceReady(3.0)
        task_id = method(*args)
        ret=None
        if task_id is None: #Reset
            while self._isDeviceBusy():
                gevent.sleep(0.1)
        else:
            # introduced wait because it takes some time before the attribute PathRunning is set
            # after launching a transfer
            self._pathRunning(10.0)
            while str(self._chnPathRunning.getValue()).lower() == 'true': 
                gevent.sleep(0.1)
            ret = True
        return ret

    def _updateState(self):
        """
        Updates the state of the hardware object

        :returns: None
        :rtype: None
        """
        #logging.info("##############################_______ PX2Cats_Mokcup _updateState __####################")
        try:
          state = self._readState()
        except:
          state = SampleChangerState.Unknown
        if state == SampleChangerState.Moving and self._isDeviceBusy(self.getState()):
            return          
        if self.hasLoadedSample() ^ self._chnSampleIsDetected.getValue():
            # go to Unknown state if a sample is detected on the gonio but not registered in the internal database
            # or registered but not on the gonio anymore
            state = SampleChangerState.Ready
        elif self._chnPathRunning.getValue() and not (state in [SampleChangerState.Loading, SampleChangerState.Unloading]):
            state = SampleChangerState.Moving
        elif self._scIsCharging and not (state in [SampleChangerState.Alarm, SampleChangerState.Moving, SampleChangerState.Loading, SampleChangerState.Unloading]):
            state = SampleChangerState.Charging
            
        #logging.info("##############################_______ PX2Cats_Mokcup is %s __####################" % str(state))
        self._setState(state)
       
    def _readState(self):
        """
        Read the state of the Tango DS and translate the state to the SampleChangerState Enum

        :returns: Sample changer state
        :rtype: GenericSampleChanger.SampleChangerState
        """
        state = self._chnState.getValue()
        if state is not None:
            stateStr = str(state).upper()
        else:
            stateStr = ""
        #state = str(self._state.getValue() or "").upper()
        state_converter = { "ALARM": SampleChangerState.Alarm,
                            "ON": SampleChangerState.Ready,
                            "RUNNING": SampleChangerState.Moving }
        return state_converter.get(stateStr, SampleChangerState.Unknown)
                        
    def _isDeviceBusy(self, state=None):
        """
        Checks whether Sample changer HO is busy.

        :returns: True if the sample changer is busy
        :rtype: Bool
        """
        if state is None:
            state = self._readState()
        return state not in (SampleChangerState.Ready, SampleChangerState.Loaded, SampleChangerState.Alarm, 
                             SampleChangerState.Disabled, SampleChangerState.Fault, SampleChangerState.StandBy)

    def _isDeviceReady(self):
        """
        Checks whether Sample changer HO is ready.

        :returns: True if the sample changer is ready
        :rtype: Bool
        """
        state = self._readState()
        return state in (SampleChangerState.Ready, SampleChangerState.Charging)              

    def _waitDeviceReady(self,timeout=None):
        """
        Waits until the samle changer HO is ready.

        :returns: None
        :rtype: None
        """

        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self._isDeviceReady():
                gevent.sleep(0.01)
            
    def _updateSelection(self):    
        """
        Updates the selected basket and sample. NOT USED ANYMORE FOR THE CATS.
        Legacy method left from the implementation of the SC3 where the currently selected sample
        is always read directly from the SC3 Tango DS

        :returns: None
        :rtype: None
        """
        #import pdb; pdb.set_trace()
        basket=None
        sample=None
        # print "_updateSelection: saved selection: ", self._selected_basket, self._selected_sample
        try:
          basket_no = self._selected_basket
          if basket_no is not None and basket_no>0 and basket_no <=PX2Cats.NO_OF_BASKETS:
            basket = self.getComponentByAddress(Basket.getBasketAddress(basket_no))
            sample_no = self._selected_sample
            if sample_no is not None and sample_no>0 and sample_no <=Basket.NO_OF_SAMPLES_PER_PUCK:
                sample = self.getComponentByAddress(Pin.getSampleAddress(basket_no, sample_no))            
        except:
          pass
        #if basket is not None and sample is not None:
        #    print "_updateSelection: basket: ", basket, basket.getIndex()
        #    print "_updateSelection: sample: ", sample, sample.getIndex()
        self._setSelectedComponent(basket)
        self._setSelectedSample(sample)

    def _updateLoadedSample(self):
        """
        Reads the currently mounted sample basket and pin indices from the CATS Tango DS,
        translates the lid/sample notation into the basket/sample notation and marks the 
        respective sample as loaded.

        :returns: None
        :rtype: None
        """
        loadedSampleLid = self._chnLidLoadedSample.getValue()
        loadedSampleNum = self._chnNumLoadedSample.getValue()
        if loadedSampleLid != -1 or loadedSampleNum != -1:
            lidBase = (loadedSampleLid - 1) * 3
            lidOffset = ((loadedSampleNum - 1) / Basket.NO_OF_SAMPLES_PER_PUCK) + 1
            samplePos = ((loadedSampleNum - 1) % Basket.NO_OF_SAMPLES_PER_PUCK) + 1
            basket = lidBase + lidOffset
        else:
            basket = None
            samplePos = None
 
        if basket is not None and samplePos is not None:
            new_sample = self.getComponentByAddress(Pin.getSampleAddress(basket, samplePos))
        else:
            new_sample = None

        if self.getLoadedSample() != new_sample:
            # import pdb; pdb.set_trace()
            # remove 'loaded' flag from old sample but keep all other information
            old_sample = self.getLoadedSample()
            if old_sample is not None:
                # there was a sample on the gonio
                loaded = False
                has_been_loaded = True
                old_sample._setLoaded(loaded, has_been_loaded)
            if new_sample is not None:
                self._updateSampleBarcode(new_sample)
                loaded = True
                has_been_loaded = True
                new_sample._setLoaded(loaded, has_been_loaded)

    def _updateSampleBarcode(self, sample):
        """
        Updates the barcode of >sample< in the local database after scanning with
        the barcode reader.

        :returns: None
        :rtype: None
        """
        # update information of recently scanned sample
        datamatrix = str(self._chnSampleBarcode.getValue())
        scanned = (len(datamatrix) != 0)
        if not scanned:
           datamatrix = None
           #datamatrix = '----------'   
        sample._setInfo(sample.isPresent(), datamatrix, scanned)

    def _initSCContents(self):
        """
        Initializes the sample changer content with default values.

        :returns: None
        :rtype: None
        """
        # create temporary list with default basket information
        #basket_list= [('', 4)] * PX2Cats.NO_OF_BASKETS
        # write the default basket information into permanent Basket objects 
        for basket_index in range(PX2Cats.NO_OF_BASKETS):            
            basket=self.getComponents()[basket_index]
            datamatrix = None
            present = scanned = False
            basket._setInfo(present, datamatrix, scanned)

        # create temporary list with default sample information and indices
        sample_list=[]
        for basket_index in range(PX2Cats.NO_OF_BASKETS):            
            for sample_index in range(Basket.NO_OF_SAMPLES_PER_PUCK):
                sample_list.append(("", basket_index+1, sample_index+1, 1, Pin.STD_HOLDERLENGTH)) 
        # write the default sample information into permanent Pin objects 
        for spl in sample_list:
            sample = self.getComponentByAddress(Pin.getSampleAddress(spl[1], spl[2]))
            datamatrix = "matr%d_%d" %(spl[1], spl[2])
            present = scanned = loaded = has_been_loaded = False
            sample._setInfo(present, datamatrix, scanned)
            sample._setLoaded(loaded, has_been_loaded)
            sample._setHolderLength(spl[4])    

    def _updateSCContents(self):
        """
        Updates the sample changer content. The state of the puck positions are
        read from the respective channels in the CATS Tango DS.
        The CATS sample sample does not have an detection of each individual sample, so all
        samples are flagged as 'Present' if the respective puck is mounted.

        :returns: None
        :rtype: None
        """
        for basket_index in range(PX2Cats.NO_OF_BASKETS):            
            # get presence information from the device server
            newBasketPresence = getattr(self, "_chnBasket%dState" % (basket_index + 1)).getValue()
            # get saved presence information from object's internal bookkeeping
            basket=self.getComponents()[basket_index]
            # check if the basket was newly mounted or removed from the dewar
            if newBasketPresence ^ basket.isPresent():
                # import pdb; pdb.set_trace()
                # a mounting action was detected ...
                if newBasketPresence:
                    # basket was mounted
                    present = True
                    scanned = False
                    datamatrix = None
                    basket._setInfo(present, datamatrix, scanned)
                else:
                    # basket was removed
                    present = False
                    scanned = False
                    datamatrix = None
                    basket._setInfo(present, datamatrix, scanned)
                # set the information for all dependent samples
                for sample_index in range(Basket.NO_OF_SAMPLES_PER_PUCK):
                    sample = self.getComponentByAddress(Pin.getSampleAddress((basket_index + 1), (sample_index + 1)))
                    present = sample.getContainer().isPresent()
                    if present:
                        datamatrix = '          '   
                    else:
                        datamatrix = None
                    scanned = False
                    sample._setInfo(present, datamatrix, scanned)
                    # forget about any loaded state in newly mounted or removed basket)
                    loaded = has_been_loaded = False
                    sample._setLoaded(loaded, has_been_loaded)
                    
    #########################           PRIVATE CatsMain           ########################     

    def _executeTask2(self,wait,method,*args):
        ret= self._run2(method,wait=False,*args)
        if (wait):                        
            return ret.get()
        else:
            return ret    
        
    @task
    def _run2(self,method,*args):
        exception=None
        ret=None    
        try:            
            ret=method(*args)
        except Exception as ex:        
            exception=ex
        if exception is not None:
            raise exception
        return ret

#==============================================================================
#     def safeTraj(self):    
#         """
#         Safely Moves the robot arm and the gripper to the home position
#         """    
#         return self._doSafe()
#==============================================================================

        
    def _updateSampleIsDetected(self, value):
        self.emit('sampleIsDetected', (value, ))
        
    def _updateRunningState(self, value):
        logging.info('CatsMaint _updateRunningState %s' % value)
        self.emit('runningStateChanged', (value, ))

    def _updatePoweredState(self, value):
        #logging.info("##############################_______ PX2Cats_Mokcup _updateState __####################")
        logging.info('CatsMaint _updatePoweredState emit %s' % value)
        self.emit('powerStateChanged', (value, ))

    def _updateMessage(self, value):
        logging.info('CatsMaint _updateMessage %s' % value)
        if 'incoherent' in value.lower():
            #value = '%s\nThe sample is not present on the gonio although robot thinks it should be.\nThis can happen in three cases:\n1. there was no sample in the specified position in the puck,\n2. the robot could not get it (rare)\n3. the gonio can not detect sample which is present (very rare).\nIf the sample is really not present on the gonio please click "abort" button\n and then "Missing sample" button below to be able to continue.' % value
            value = '%s\nThe sample is not present on the gonio although robot thinks it should be.\nPlease click "Missing sample" button below to be able to continue.' % value
        if 'trfgtd' in value.lower():
            value = '%s\nTransfer permission was not granted by the gonio.\n1. Please Abort the trajectory\n2. set gonio to Transfer phase from the pull down menu on the right\n3. Start the load/unload trajectory again.' % value
        if 'dback' in value.lower():
            value = '%s\nThe detector is too close (less then 195 mm from the sample)\nPlease move it to at least 195 mm.' % value
        if 'remote mode requested' in value.lower():
            value = '%s\nRemote operation not enabled.\nPlease turn the robot key to the remote position.\nThe key is located next to the experiment hutch door.' % value
        if 'splon' in value.lower():
            value = '%s\nSample not detected by the goniometer\nPlease click "Abort", then "Missing Sample".' % value
        if 'manual brake control' in value.lower():
            value = '%s\nPlease turn the manual brake knob at the base of the robot to position 0.' % value
        if 'collision detection' in value.lower():
            value = '%s\nPlease click Safe.A series of recovery procedures will be carried out to reset the robot.\nIf nothing happens there has been a hard collision call your LC or 9797 after 11 P.M.' % value
        if value != "":
            logging.getLogger("user_level_log").error(value)
        self.emit('messageChanged', (value, ))

    def _updateRegulationState(self, value):
        logging.info('CatsMaint _updateRegulationState %s' % value)
        self.emit('regulationStateChanged', (value, ))

    def _updateLid1State(self, value):
        logging.info('CatsMaint _updateLid1State %s' % value)
        self.emit('lid1StateChanged', (value, ))

    def _updateLid2State(self, value):
        logging.info('CatsMaint _updateLid2State %s' % value)
        self.emit('lid2StateChanged', (value, ))

    def _updateLid3State(self, value):
        logging.info('CatsMaint _updateLid3State %s' % value)
        self.emit('lid3StateChanged', (value, ))

    def _updateOperationMode(self, value):
        self._scIsCharging = not value
