"""
CATS sample changer hardware object.

Implements the abstract interface of the GenericSampleChanger for the CATS
sample changer model.

Derived from Alexandre Gobbo's implementation for the EMBL SC3 sample changer.
Derived from Michael Hellmig's implementation for the BESSY CATS sample changer

 - fix the Abort Bug
 - enable setondiff for the catsmaint object 
 - fix the bug of MD2 jam during exchange or unload
"""
from .GenericSampleChanger import *
import time
import PyTango
import logging

__author__ = "Michael Hellmig, Jie Nan, Bixente Rey"
__credits__ = ["The MXCuBE collaboration"]

__email__ = "jie.nan@maxlab.lu.se"

class Basket(Container):
    __TYPE__ = "Puck"

    def __init__(self, container, number, samples_num=10, name="Puck"):
        super(Basket, self).__init__(self.__TYPE__,container,Basket.getBasketAddress(number),True)

        self._name = name
        self.samples_num = samples_num
        for i in range(samples_num):
            slot = Pin(self,number,i+1)
            self._addComponent(slot)

    @staticmethod
    def getBasketAddress(basket_number):
        return str(basket_number)

    def getNumberOfSamples(self):
        return self.samples_num

    def clearInfo(self):
        #self.getContainer()._reset_basket_info(self.getIndex()+1)
        self.getContainer()._triggerInfoChangedEvent()

class Pin(Sample):
    STD_HOLDERLENGTH = 22.0

    def __init__(self,basket,basket_no,sample_no):
        super(Pin, self).__init__(basket, Pin.getSampleAddress(basket_no,sample_no), False)
        self._setHolderLength(Pin.STD_HOLDERLENGTH)

    def getBasketNo(self):
        return self.getContainer().getIndex()+1

    def getVialNo(self):
        return self.getIndex()+1

    @staticmethod
    def getSampleAddress(basket_number, sample_number):
        return str(basket_number) + ":" + "%02d" % (sample_number)


class Cats90(SampleChanger):
    """
    Actual implementation of the CATS Sample Changer,
    BESSY BL14.1 installation with 3 lids and 90 samples
    """    
    __TYPE__ = "CATS"    

    default_no_lids = 3
    baskets_per_lid = 3
    default_samples_per_basket = 10

    def __init__(self, *args, **kwargs):
        super(Cats90, self).__init__(self.__TYPE__,False, *args, **kwargs)
            
    def init(self):      
        self._selected_sample = None
        self._selected_basket = None
        self._scIsCharging = None
        self._startLoad = False # add flag to disable Load or UnLoad/Exchange Button immediately after 1 click (Avoid Click multiple times)

        self.cats_datamatrix = ""
        self.cats_loaded_lid = None
        self.cats_loaded_num = None

        # Default values
        self.cats_powered = False
        self.cats_status = ""
        self.cats_running = False
        self.cats_state = PyTango.DevState.UNKNOWN
        self.cats_lids_closed = False

        self._minidiff_type = None

        # add support for CATS dewars with variable number of lids
        
        self._minidiff_type = self.getProperty("minidiff_type")

        no_of_lids = self.getProperty('no_of_lids')
        no_of_baskets = self.getProperty('no_of_baskets')
        samples_per_basket = self.getProperty('samples_per_basket')

        if no_of_lids is None:
            self.number_of_lids = self.default_no_lids
        else:
            self.number_of_lids = int(no_of_lids)

        if no_of_baskets is None:
            self.number_of_baskets = self.baskets_per_lid * self.number_of_lids
        else:
            self.number_of_baskets = int(no_of_baskets)

        self.basket_presence = [None,] * self.number_of_baskets
        self.basket_channels = [None,] * self.number_of_baskets
        
        if samples_per_basket is None:
            self.samples_per_basket = self.default_samples_per_basket
        else:
            self.samples_per_basket = samples_per_basket

        for i in range(self.number_of_baskets):
            basket = Basket(self,i+1, samples_num=self.samples_per_basket)
            self._addComponent(basket)

        # Create channels from XML
        self._chnState = self.getChannelObject("_chnState")
        self._chnStatus = self.getChannelObject("_chnStatus")
        self._chnPowered = self.getChannelObject("_chnPowered")
        self._chnPathRunning = self.getChannelObject("_chnPathRunning")
        self._chnNumLoadedSample = self.getChannelObject("_chnNumLoadedSample")
        self._chnLidLoadedSample = self.getChannelObject("_chnLidLoadedSample")
        self._chnSampleBarcode = self.getChannelObject("_chnSampleBarcode")
        self._chnSampleIsDetected = self.getChannelObject("_chnSampleIsDetected")

        for command_name in ("_cmdAbort", "_cmdLoad", "_cmdUnload", "_cmdChainedLoad"):
            setattr(self, command_name, self.getCommandObject(command_name))

        for basket_index in range(self.number_of_baskets):            
            channel_name = "_chnBasket%dState" % (basket_index + 1)
            self.basket_channels[basket_index] = self.getChannelObject(channel_name) 

        self._chnAllLidsClosed = self.getChannelObject("_chnTotalLidState")

        if self._minidiff_type == "MD2":
            self._chnCurrentPhase = self.getChannelObject("_chnCurrentPhase")
            self._chnTransferMode = self.getChannelObject("_chnTransferMode")

        self._initSCContents()

        # SampleChanger.init must be called _after_ initialization of the Cats because it starts the update methods which access
        # the device server's status attributes
        #  in fact.. no.  If SampleChanger.init() is called reception of signals at connection time is not done.  
        #
        #  In the case of Cats90 we do not use an update_timer... update is done by signals from Tango channels 
        #  Simply call updateInfo() to get information of which baskets are loaded

        # SampleChanger.init(self)   

        # useUpdateTimer 
        #
        # if True:
        #   update of state is done by calling _doUpdateInfo()
        # 
        # if False: 
        #   we should connect to signals from channels and send info out

        self.use_update_timer = False  # do not use update_timer for Cats 

        if self.use_update_timer is False:
             logging.getLogger("HWR").info("Cats: connecting signals")
             self._chnState.connectSignal("update", self.cats_state_changed)
             self._chnStatus.connectSignal("update", self.cats_status_changed)
             self._chnPathRunning.connectSignal("update", self.cats_pathrunning_changed) 
             self._chnPowered.connectSignal("update", self.cats_powered_changed) 
             self._chnAllLidsClosed.connectSignal("update", self.cats_lids_closed_changed)
             self._chnLidLoadedSample.connectSignal("update", self.cats_loaded_lid_changed)
             self._chnNumLoadedSample.connectSignal("update", self.cats_loaded_num_changed)

             for basket_index in range(self.number_of_baskets):
                 channel = self.basket_channels[basket_index]                 
                 channel.connectSignal("update", lambda value, \
                     this=self,idx=basket_index:Cats90.cats_basket_presence_changed(this,idx,value))

        self.updateInfo()

    def getSampleProperties(self):
        """
        Get the sample's holder length

        :returns: sample length [mm]
        :rtype: double
        """
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)

    def getBasketList(self):
        basket_list = []
        for basket in self.getComponents():
            if isinstance(basket, Basket):
                basket_list.append(basket)
        return basket_list

        
    def isPowered(self):
        return self._chnPowered.getValue()
    def isPathRunning(self):
        return self._chnPathRunning.getValue()

    #########################           TASKS           #########################

    def _doUpdateInfo(self):       
        """
        Updates the sample changers status: mounted pucks, state, currently loaded sample

        :returns: None
        :rtype: None
        """
        self._doUpdateCatsContents()
        self._doUpdateState()               
        self._doUpdateLoadedSample()
                    
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
          if basket_no is not None and basket_no>0 and basket_no <=self.number_of_baskets:
            basket = self.getComponentByAddress(Basket.getBasketAddress(basket_no))
            if sample_no is not None and sample_no>0 and sample_no <= basket.getNumberOfSamples():
                sample = self.getComponentByAddress(Pin.getSampleAddress(basket_no, sample_no))            
        except:
          pass
        self._setSelectedComponent(basket)
        self._setSelectedSample(sample)

    def _doSelect(self,component):
        """
        Selects a new component (basket or sample).
	Uses method >_directlyUpdateSelectedComponent< to actually search and select the corrected positions.

        :returns: None
        :rtype: None
        """
        logging.info("selecting component %s / type=%s" % (str(component), type(component)))

        if isinstance(component, Sample):
            selected_basket_no = component.getBasketNo()
            selected_sample_no = component.getIndex()+1
        elif isinstance(component, Container) and ( component.getType() == Basket.__TYPE__):
            selected_basket_no = component.getIndex()+1
            selected_sample_no = None
        elif isinstance(component,tuple) and len(component) == 2:
            selected_basket_no = component[0]
            selected_sample_no = component[1]
        self._directlyUpdateSelectedComponent(selected_basket_no, selected_sample_no)

# JN 20150324, load for CATS GUI, no timer and the window will not freeze
    def load_cats(self, sample=None, wait=True):
        """
        Load a sample. 
        """
        sample = self._resolveComponent(sample)
        self.assertNotCharging()
        logging.info("call load without a timer")
        if not self._chnPowered.getValue():
            return

        # JN, 20150512, make sure MD2 TransferMode is "SAMPLE_CHANGER"
        if self._minidiff_type == "MD2":
            if not self._chnTransferMode.getValue()=="SAMPLE_CHANGER":
                return
       
        return self._executeTask(SampleChangerState.Loading,wait,self._doLoad,sample)

# JN 20150324, add load for queue mount, sample centring can start after MD2 in Centring phase instead of waiting for CATS finishes completely
    def load(self, sample=None, wait=True):
        """
        Load a sample. 
        """
        if not self._chnPowered.getValue():
            raise Exception("CATS power is not enabled. Please switch on arm power before transferring samples.")
            return 

        # JN, 20150512, make sure MD2 TransferMode is "SAMPLE_CHANGER"
        if self._minidiff_type == "MD2":
            if not self._chnTransferMode.getValue()=="SAMPLE_CHANGER":
                raise Exception("TransferMode is %s. Please set the value to SAMPLE_CHANGER in MD2 software." % str(self._chnTransferMode.getValue()))
                return 

        sample = self._resolveComponent(sample)
        self.assertNotCharging()

        self._executeTask(SampleChangerState.Loading,False,self._doLoad,sample)

        if self._minidiff_type == "MD2":
            timeout=0
            time.sleep(20) # in case MD2 starts with Centring phase before loading the new sample
            while self._chnCurrentPhase.getValue() != 'Centring':
                if timeout > 60:
                    logging.info("waited for too long, change to centring mode manually")
                    return
                time.sleep(1)
                timeout+=1
                logging.info("current phase is " + self._chnCurrentPhase.getValue())
   
    def _doScan(self,component,recursive):
        """
        Scans the barcode of a single sample, puck or recursively even the complete sample changer.

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
            sample = (((selected.getBasketNo() - 1) % 3) * 10) + selected.getVialNo()
            argin = ["2", str(lid), str(sample), "0", "0"]
            self._executeServerTask(self._cmdScanSample, argin)
            self._updateSampleBarcode(component)
        elif isinstance(component, Container) and ( component.getType() == Basket.__TYPE__):
            # component is a basket
            basket = component
            if recursive:
                pass
            else:
                if (selected_basket is None) or (selected_basket != basket):
                    self._doSelect(basket)            

                selected=self.getSelectedSample()            

                for sample_index in range(basket.getNumberOfSamples()):
                    lid = ((selected.getBasketNo() - 1) / 3) + 1
                    sample = (((selected.getBasketNo() - 1) % 3) * 10) + (sample_index+1)
                    argin = ["2", str(lid), str(sample), "0", "0"]
                    self._executeServerTask(self._cmdScanSample, argin)
    
    def _doLoad(self,sample=None, shifts=None):
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
        sample = (((selected.getBasketNo() - 1) % 3) * 10) + selected.getVialNo()

        if shifts is None:
            xshift, yshift, zshift = ["0", "0", "0" ]
        else:
            xshift, yshift, zshift = map(str,shifts)

        argin = ["2", str(lid), str(sample), "0", "0", xshift, yshift, zshift]
            
        if self.hasLoadedSample():
            if selected==self.getLoadedSample():
                raise Exception("The sample " + str(self.getLoadedSample().getAddress()) + " is already loaded")
            else:
                if self._minidiff_type == "MD2":
                    self._startLoad = True
                    self._cmdRestartMD2(0) # fix the bug of waiting for MD2 by a hot restart, JN,20140708
                    time.sleep(5) # wait for the MD2 restart
                    self._startLoad = False

                logging.getLogger("HWR").warning("  ==========CATS=== chained load sample, sending to cats:  %s" % argin)
                self._executeServerTask(self._cmdChainedLoad, argin)
        else:
            if self.cats_sample_on_diffr():
                logging.getLogger("HWR").warning("  ==========CATS=== trying to load sample, but sample detected on diffr. aborting") 
                self._updateState() # remove software flags like Loading.
            else:
                logging.getLogger("HWR").warning("  ==========CATS=== load sample, sending to cats:  %s" % argin)
                self._executeServerTask(self._cmdLoad, argin)

    def _doUnload(self,sample_slot=None, shifts=None):
        """
        Unloads a sample from the diffractometer.

        :returns: None
        :rtype: None
        """
        if not self._chnPowered.getValue():
            raise Exception("CATS power is not enabled. Please switch on arm power before transferring samples.")
            
        if (sample_slot is not None):
            self._doSelect(sample_slot)

        if shifts is None:
            xshift, yshift, zshift = ["0", "0", "0" ]
        else:
            xshift, yshift, zshift = map(str,shifts)

        argin = ["2", "0", xshift, yshift, zshift]

        if self._minidiff_type == "MD2":
            self._startLoad = True
            self._cmdRestartMD2(0) # fix the bug of waiting for MD2 by a hot restart, JN,20140708
            time.sleep(5) # wait for the MD2 restart
            self._startLoad = False

        logging.getLogger("HWR").warning("  ==========CATS=== unload sample, sending to cats:  %s" % argin)
        self._executeServerTask(self._cmdUnload, argin)

    def clearBasketInfo(self, basket):
        pass

    ################################################################################

    def _doAbort(self):
        """
        Aborts a running trajectory on the sample changer.

        :returns: None
        :rtype: None
        """
        self._cmdAbort()            
        self._updateState() # remove software flags like Loading.. reflects current hardware state 

    def _doReset(self):
        pass

    #########################           CATS EVENTS           #########################        

    def cats_state_changed(self, value):
        self.cats_state = value
        self._updateState()

    def cats_status_changed(self, value):
        self.cats_status = value
        self._updateState()

    def cats_pathrunning_changed(self, value):
        self.cats_running = value
        self._updateState()
        self.emit('runningStateChanged', (value, ))

    def cats_powered_changed(self, value):
        self.cats_powered = value
        self._updateState()
        self.emit('powerStateChanged', (value, ))

    def cats_lids_closed_changed(self, value):
        logging.getLogger("HWR").warning("Operation mode changed. All LIDs closed" + str(value))
        self.cats_lids_closed = value
        self._updateState()
    
    def cats_basket_presence_changed(self,basket_index,value):
        self.basket_presence[basket_index] = value
        self._updateCatsContents()

    def cats_loaded_lid_changed(self,value):
        self.cats_loaded_lid = value
        self.cats_loaded_num = self._chnNumLoadedSample.getValue()
        self._updateLoadedSample() 

    def cats_loaded_num_changed(self, value):
        self.cats_loaded_lid = self._chnLidLoadedSample.getValue()
        self.cats_loaded_num = value
        self._updateLoadedSample() 

    def cats_barcode_changed(self, value):
        self.cats_datamatrix = value
        self._updateLoadedSample() 

    def cats_sample_on_diffr(self):
        return self._chnSampleIsDetected.getValue()

    #########################           PRIVATE           #########################        

    def _executeServerTask(self, method, *args):
        """
        Executes a task on the CATS Tango device server

        :returns: None
        :rtype: None
        """
        self._waitDeviceReady(3.0)
        task_id = method(*args)
        print "Cats90._executeServerTask", task_id
        ret=None
        if task_id is None: #Reset
            while self._isDeviceBusy():
                gevent.sleep(0.1)
        else:
            # introduced wait because it takes some time before the attribute PathRunning is set
            # after launching a transfer
            time.sleep(2.0)
            while str(self._chnPathRunning.getValue()).lower() == 'true': 
                gevent.sleep(0.1)            
            ret = True
        return ret

    def _doUpdateState(self):
        """
        Updates the state of the hardware object

        :returns: None
        :rtype: None
        """
        try:
            self.cats_state = self._readState()
        except:
            self.cats_state = PyTango.DevState.UNKNOWN

        self.cats_running = self._chnPathRunning.getValue()
        self.cats_powered = self._chnPowered.getValue()
        self.cats_lids_closed = self._chnAllLidsClosed.getValue() 
        self.cats_status = self._chnStatus.getValue()

    def _updateState(self):

        # PyCats only returns three states (ON, RUNNING or ALARM)

        if not self.cats_powered:
            state = SampleChangerState.Disabled
        elif self.cats_state == PyTango.DevState.UNKNOWN: 
            state = SampleChangerState.Unknown
        elif self.cats_state == PyTango.DevState.RUNNING: 
            state = SampleChangerState.Moving 
        elif self.cats_state == PyTango.DevState.ALARM: 
            state = SampleChangerState.Alarm 
        elif self.hasLoadedSample() ^ self._chnSampleIsDetected.getValue():
            # go to Unknown state if a sample is detected on the gonio but not registered in the internal database
            # or registered but not on the gonio anymore
            logging.getLogger("HWR").warning("SAMPLE CHANGER Unknown 2 (hasLoaded: %s / detected: %s)" % (self.hasLoadedSample(), self._chnSampleIsDetected.getValue()))
            state = SampleChangerState.Unknown 
        elif not self.cats_lids_closed: 
            state = SampleChangerState.Charging
        else:
            state = SampleChangerState.Ready

        logging.getLogger("HWR").warning("SAMPLE CHANGER state updated poweron=%s / cats_state=%s / cats_status=%s " % (self.cats_powered, self.cats_state, self.cats_status))
        #status = self.cats_status
        status = SampleChangerState.tostring(state)
        self._setState(state, status)
       
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
        
        state_converter = { "ALARM": SampleChangerState.Alarm,
                            "ON": SampleChangerState.Ready,
                            "RUNNING": SampleChangerState.Moving }

        if stateStr not in state_converter:
            logging.getLogger("HWR").warning("SAMPLE CHANGER Unknown 3 %s" % stateStr)

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
            
    def _doUpdateLoadedSample(self):
        """
        Reads the currently mounted sample basket and pin indices from the CATS Tango DS,
        translates the lid/sample notation into the basket/sample notation and marks the 
        respective sample as loaded.

        :returns: None
        :rtype: None
        """
        self.cats_loaded_lid = self._chnLidLoadedSample.getValue()
        self.cats_loaded_num = self._chnNumLoadedSample.getValue()
        self.cats_datamatrix = str(self._chnSampleBarcode.getValue())
        self._updateLoadedSample()

    def _updateLoadedSample(self):
      
        loadedSampleLid = self.cats_loaded_lid
        loadedSampleNum = self.cats_loaded_num

        if loadedSampleLid != -1 or loadedSampleNum != -1:
            lidBase = (loadedSampleLid - 1) * 3
            lidOffset = ((loadedSampleNum - 1) / 10) + 1
            samplePos = ((loadedSampleNum - 1) % 10) + 1
            basket = lidBase + lidOffset
        else:
            basket = None
            samplePos = None
 
        if basket is not None and samplePos is not None:
            new_sample = self.getComponentByAddress(Pin.getSampleAddress(basket, samplePos))
        else:
            new_sample = None

        if self.getLoadedSample() != new_sample:
            # remove 'loaded' flag from old sample but keep all other information
            old_sample = self.getLoadedSample()

            if old_sample is not None:
                # there was a sample on the gonio
                loaded = False
                has_been_loaded = True
                old_sample._setLoaded(loaded, has_been_loaded)

            if new_sample is not None:
                loaded = True
                has_been_loaded = True
                new_sample._setLoaded(loaded, has_been_loaded)

        #if new_sample is not None:
        self._updateSampleBarcode(new_sample)

    def _updateSampleBarcode(self, sample):
        """
        Updates the barcode of >sample< in the local database after scanning with
        the barcode reader.

        :returns: None
        :rtype: None
        """
        # update information of recently scanned sample
        if sample is None:
            return 

        scanned = (len(self.cats_datamatrix) != 0)
        if not scanned:    
           datamatrix = '----------'   
        else:
           datamatrix = self.cats_datamatrix
        sample._setInfo(sample.isPresent(), datamatrix, scanned)

    def _initSCContents(self):
        """
        Initializes the sample changer content with default values.

        :returns: None
        :rtype: None
        """
        logging.getLogger("HWR").warning("Cats90:  initializing contents")

        # write the default basket information into permanent Basket objects 
        for basket_index in range(self.number_of_baskets):            
            basket=self.getComponents()[basket_index]
            datamatrix = None
            present = scanned = False
            basket._setInfo(present, datamatrix, scanned)

        # create temporary list with default sample information and indices
        sample_list=[]
        for basket_index in range(self.number_of_baskets):            
            basket = self.getComponents()[basket_index]
            for sample_index in range(basket.getNumberOfSamples()):
                sample_list.append(("", basket_index+1, sample_index+1, 1, Pin.STD_HOLDERLENGTH)) 

        # write the default sample information into permanent Pin objects 
        for spl in sample_list:
            sample = self.getComponentByAddress(Pin.getSampleAddress(spl[1], spl[2]))
            datamatrix = None
            present = scanned = loaded = has_been_loaded = False
            sample._setInfo(present, datamatrix, scanned)
            sample._setLoaded(loaded, has_been_loaded)
            sample._setHolderLength(spl[4])    

        logging.getLogger("HWR").warning("Cats90:  initializing contents done")

    def _doUpdateCatsContents(self):
        """
        Updates the sample changer content. The state of the puck positions are
        read from the respective channels in the CATS Tango DS.
        The CATS sample sample does not have an detection of each individual sample, so all
        samples are flagged as 'Present' if the respective puck is mounted.

        :returns: None
        :rtype: None
        """

        for basket_index in range(self.number_of_baskets):            
            # get presence information from the device server
            channel = self.basket_channels[basket_index]
            is_present = channel.getValue()
            self.basket_presence[basket_index] = is_present

        self._updateCatsContents()
           
    def _updateCatsContents(self):
 
        for basket_index in range(self.number_of_baskets):            
            # get saved presence information from object's internal bookkeeping
            basket=self.getComponents()[basket_index]
            is_present = self.basket_presence[basket_index]

            # check if the basket presence has changed
            if is_present ^ basket.isPresent():
                # a mounting action was detected ...
                if is_present:
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
                for sample_index in range(basket.getNumberOfSamples()):
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


def test_hwo(hwo):
    print("Baskets in CATS:", hwo.getBasketList())

if __name__ == '__main__':    
    test()
