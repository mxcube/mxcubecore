"""
"""
import time
import functools
import MySQLdb
from sample_changer.GenericSampleChanger import *

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


class Basket(Container):
    __TYPE__ = "Puck"    
    NO_OF_SAMPLES_PER_PUCK = 10

    def __init__(self,container,number):
        super(Basket, self).__init__(self.__TYPE__,container,Basket.getBasketAddress(number),True)
        for i in range(Basket.NO_OF_SAMPLES_PER_PUCK):
            slot = Pin(self,number,i+1)
            self._addComponent(slot)
                            
    @staticmethod
    def getBasketAddress(basket_number):
        return str(basket_number)

    def clearInfo(self):
        #self.getContainer()._reset_basket_info(self.getIndex()+1)
        print "EMBLSC clearinfo self.getContainer()._reset_basket_info(self.getIndex()+1) - TODO"
        self.getContainer()._triggerInfoChangedEvent()

class EMBLSC(SampleChanger):
    """
    """    
    __TYPE__ = "SC"    
    NO_OF_BASKETS = 17

    def __init__(self, *args, **kwargs):
        super(EMBLSC, self).__init__(self.__TYPE__,False, *args, **kwargs)
            
    def init(self):      
        self._selected_sample = None
        self._selected_basket = None
        self._scIsCharging = None

        # initialize the sample changer components, moved here from __init__ after allowing
        # variable number of lids
        for i in range(EMBLSC.NO_OF_BASKETS):
            basket = Basket(self,i+1)
            self._addComponent(basket)

        """self.chan_puck_switches = self.getChannelObject("chanPuckSwitches")       
        self.chan_selected_puck = self.getChannelObject("chanSelectedPuck")
        self.chan_selected_sample = self.getChannelObject("chanSelectedSample") """
 
        """self.chan_status = self.getChannelObject("chanStatus")
        self.chan_door_switch = self.getChannelObject("chanDoorSwitch") 
        self.chan_puck_switches = self.getChannelObject("chanPuckSwitch")   

        self.cmd_open_lid = self.getCommandObject("cmdOpenLid")
        self.cmd_close_lid = self.getCommandObject("cmdCloseLid")
        self.cmd_mount_sample = self.getCommandObject("cmdMountSample")
        self.cmd_unmount_sample = self.getCommandObject("cmdUnmountSample")"""
        self._mounted_sample_index = None

        self._initSCContents()

        # SampleChanger.init must be called _after_ initialization of the Cats because it starts the update methods which access
        # the device server's status attributes
        SampleChanger.init(self)  
     
       
        #self._initSCCintentsFromDB() 

    def getBasketList(self):
        basket_list = []
        for basket in self.components:
            if isinstance(basket, Basket):
                basket_list.append(basket)
        return basket_list

    def _openLid(self):
        return
        #self.cmd_open_lid(1)
    
    def _closeLid(self): 
        return
        #self.cmd_close_lid(1)

    def _mountSample(self, sample_index):      
        return
        """self.cmd_mount_sample(sample_index)
        self._mounted_sample_index = sample_index
        logging.getLogger("HWR").debug("Sample changer: mounting sample no. %d" 
                    %self._mounted_sample_index)  """

    def _unmountSample(self):
        return
        """if self._mounted_sample_index: 
            self.cmd_unmount_sample(self._mounted_sample_index) 
            logging.getLogger("HWR").debug("Sample changer: unmounting sample no. %d" 
                    %self._mounted_sample_index)
        else:
            logging.getLogger("HWR").debug("Sample Changer: no sample mounted on minidiff")"""

    def getSampleProperties(self):
        """
        Get the sample's holder length

        :returns: sample length [mm]
        :rtype: double
        """
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)
        
    #########################           TASKS           #########################

    def _doUpdateInfo(self):       
        """
        Updates the sample changers status: mounted pucks, state, currently loaded sample

        :returns: None
        :rtype: None
        """
        self._updateSCContents()
        # periodically updating the selection is not needed anymore, because each call to _doSelect
        # updates the selected component directly:
        # self._updateSelection()
        self._updateState()               
        #self._updateLoadedSample()
                    
    def _doChangeMode(self,mode):
        """
        Changes the SC operation mode, not implemented for the CATS system

        :returns: None
        :rtype: None
        """
        pass

    def _directlyUpdateSelectedComponent(self, basket_no, sample_no):    
        print "_directlyUpdateSelectedComponent"
        basket = None
        sample = None
        try:
          if basket_no is not None and basket_no>0 and basket_no <=EMBLSC.NO_OF_BASKETS:
            basket = self.getComponentByAddress(Basket.getBasketAddress(basket_no))
            if sample_no is not None and sample_no>0 and sample_no <=Basket.NO_OF_SAMPLES_PER_PUCK:
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
            if recursive:
                pass
            else:
                if (selected_basket is None) or (selected_basket != component):
                    self._doSelect(component)            
                # self._executeServerTask(self._scan_samples, (0,))                
                selected=self.getSelectedSample()            
                for sample_index in range(Basket.NO_OF_SAMPLES_PER_PUCK):
                    lid = ((selected.getBasketNo() - 1) / 3) + 1
                    sample = (((selected.getBasketNo() - 1) % 3) * 10) + (sample_index+1)
                    argin = ["2", str(lid), str(sample), "0", "0"]
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
        #if not self._chnPowered.getValue():
        #    raise Exception("Sample changer power is not enabled. Please switch on arm power before transferring samples.")
            
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
        basket = selected.getBasketNo() 
        sample = selected.getBasketNo() * 10 + selected.getVialNo()
        argin = ["2", str(basket), str(sample), "0", "0", "0", "0", "0"]
           
        
 
        if self.hasLoadedSample():
            if selected==self.getLoadedSample():
                raise Exception("The sample " + str(self.getLoadedSample().getAddress()) + " is already loaded")
            else:
                print 'self._executeServerTask(self._cmdChainedLoad, argin) : IK TODO'
                #self._executeServerTask(self._cmdChainedLoad, argin)
        else:
            print argin
            print "self._executeServerTask(self._cmdLoad, argin): IK TODO" 
            #self._executeServerTask(self._cmdLoad, argin)
            
    def _doUnload(self,sample_slot=None):
        """
        Unloads a sample from the diffractometer.

        :returns: None
        :rtype: None
        """
        if not self._chnPowered.getValue():
            raise Exception("CATS power is not enabled. Please switch on arm power before transferring samples.")
            
        if (sample_slot is not None):
            self._doSelect(sample_slot)
        argin = ["2", "0", "0", "0", "0"]
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

    def _doReset(self):
        """
        Clean all sample info
        Move sample to his position
        move puck from center to base
        """
        self._initSCContents() 

    #########################           PRIVATE           #########################        

    def _updateOperationMode(self, value):
        self._scIsCharging = not value

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
            time.sleep(2.0)
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
        #try:
        state = self._readState()
        #except:
        #  state = SampleChangerState.Unknown
        if state == SampleChangerState.Moving and self._isDeviceBusy(self.getState()):
            #print "*** _updateState return"
            return          

        """sampleIsDetected = 0b0000000001 
        #if self.hasLoadedSample() ^ self._chnSampleIsDetected.getValue():
        if self.hasLoadedSample() ^ sampleIsDetected:
            # go to Unknown state if a sample is detected on the gonio but not registered in the internal database
            # or registered but not on the gonio anymore
            state = SampleChangerState.Unknown
        elif self._chnPathRunning.getValue() and not (state in [SampleChangerState.Loading, SampleChangerState.Unloading]):
            state = SampleChangerState.Moving
        elif self._scIsCharging and not (state in [SampleChangerState.Alarm, SampleChangerState.Moving, SampleChangerState.Loading, SampleChangerState.Unloading]):
            state = SampleChangerState.Charging"""
        #print "*** _updateState: ", state

        #state = SampleChangerState.Ready

        self._setState(state)
       
    def _readState(self):
        """
        Read the state of the Tango DS and translate the state to the SampleChangerState Enum

        :returns: Sample changer state
        :rtype: GenericSampleChanger.SampleChangerState
        """
        #state = self._chnState.getValue()
        state = "ON"
        #print "*** _readState: ", state
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
        print "_updateSelection" 
        #import pdb; pdb.set_trace()
        basket=None
        sample=None
        # print "_updateSelection: saved selection: ", self._selected_basket, self._selected_sample
        try:
          basket_no = self._selected_basket
          if basket_no is not None and basket_no>0 and basket_no <=EMBLSC.NO_OF_BASKETS:
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

        loadedSampleLid = 1
        loadedSampleNum = 1
        #loadedSampleLid = self._chnLidLoadedSample.getValue()
        #loadedSampleNum = self._chnNumLoadedSample.getValue()

        try:
           loadedSampleLid = int(self.chan_selected_puck.getValue())
           loadedSampleNum = int(self.chan_selected_sample.getValue())
        except:
           pass

        if loadedSampleLid != -1 or loadedSampleNum != -1:
            #lidBase = (loadedSampleLid - 1) * 3
            lidBase = loadedSampleLid
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
        #datamatrix = str(self._chnSampleBarcode.getValue())
         

        datamatrix = "NotAvailable"

        scanned = (len(datamatrix) != 0)
        if not scanned:    
           datamatrix = '----------'   
        sample._setInfo(sample.isPresent(), datamatrix, scanned)

    def _initSCContents(self):
        """
        Initializes the sample changer content with default values.

        :returns: None
        :rtype: None
        """
        # create temporary list with default basket information
        basket_list= [('', 4)] * EMBLSC.NO_OF_BASKETS
        # write the default basket information into permanent Basket objects 

        for basket_index in range(EMBLSC.NO_OF_BASKETS):            
            basket=self.getComponents()[basket_index]
            datamatrix = None
            present = scanned = False
            basket._setInfo(present, datamatrix, scanned)

        # create temporary list with default sample information and indices
        sample_list=[]
        for basket_index in range(EMBLSC.NO_OF_BASKETS):            
            for sample_index in range(Basket.NO_OF_SAMPLES_PER_PUCK):
                sample_list.append(("", basket_index+1, sample_index+1, 1, Pin.STD_HOLDERLENGTH)) 
        # write the default sample information into permanent Pin objects 
        for spl in sample_list:
            sample = self.getComponentByAddress(Pin.getSampleAddress(spl[1], spl[2]))
            datamatrix = None
            present = scanned = loaded = has_been_loaded = False
            sample._setInfo(present, datamatrix, scanned)
            sample._setLoaded(loaded, has_been_loaded)
            sample._setHolderLength(spl[4])    

    def _initSCCintentsFromDB(self):
    
        print '_initSCCintentsFromDB'

        return
        content_str = self._getLastSCContentFromDB()
        content = eval(content_str)
        for basket_index in range(len(content)):
            basket=self.getComponents()[basket_index]
            present = True
            scanned = False
            datamatrix = None
            basket._setInfo(present, datamatrix, scanned) 
            for sample_index in range(len(content[basket_index])):
                 sample = self.getComponentByAddress(Pin.getSampleAddress((basket_index + 1), (sample_index + 1)))
                 present = sample.getContainer().isPresent()
                 
                 scanned = False
                 datamatrix = None
                 loaded = has_been_loaded = False
                 if content[basket_index][sample_index] == 0:
                     pass
                 elif content[basket_index][sample_index] == 1:
                     scanned = True
                 elif content[basket_index][sample_index] == 2:
                     scanned = True 
                     loaded = has_been_loaded = True 
                 elif content[basket_index][sample_index] == 3:
                     scanned = True
                     loaded = has_been_loaded = False
                     datamatrix = "barcode%d:%d" %(basket_index, sample_index)                     
                 elif content[basket_index][sample_index] == 4:   
                     scanned = True
                     loaded = has_been_loaded = True
                     datamatrix = "barcode%d:%d" %(basket_index, sample_index)

                 sample._setInfo(present, datamatrix, scanned)
                 sample._setLoaded(loaded, has_been_loaded)


    def _updateSCContents(self):
        """
        Updates the sample changer content. The state of the puck positions are
        read from the respective channels in the CATS Tango DS.
        The CATS sample sample does not have an detection of each individual sample, so all
        samples are flagged as 'Present' if the respective puck is mounted.

        :returns: None
        :rtype: None
        """
        #self._extractStatus()
        #puck_switches = int(self.chan_puck_switches.getValue())
        #IK TODO
        puck_switches = -1
        for basket_index in range(EMBLSC.NO_OF_BASKETS):            
            basket=self.getComponents()[basket_index]
            if puck_switches & pow(2, basket_index) > 0:
            #f puck_switches & (1 << basket_index):
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
                    datamatrix = '%d:%d - Not defined' %(basket_index,sample_index)
                else:
                    datamatrix = None
                datamatrix = None
                scanned = False
                sample._setInfo(present, datamatrix, scanned)
                # forget about any loaded state in newly mounted or removed basket)
                loaded = has_been_loaded = False
                sample._setLoaded(loaded, has_been_loaded)

    def _extractStatus(self):
        """
        Reads sample changer status string and extracts it as a 
        status dictionary. Available status tags:
          lid    : LidCls, LidOpn, LidBus
          magnet : MagOff, MagOn
          cryo   : CryoErr
          centralPuck  : None, no.
          isSample : SmpleYes, SmplNo 
        """
        return 
        #IK TODO 
        status_string = self.chan_status.getValue() 
        status_dict = {}
        status_list = status_string.split("|")
        status_list = filter(None, status_list)

        status_dict = {}
        status_dict["lid"] = status_list[0].lower()
        status_dict["magnet"] = status_list[1].lower()         
        status_dict["cryo"] = status_list[2].lower()
        status_dict["centralPuck"] = eval(status_list[3].replace("CPuck:", ""))
        #status_dict["vialStatus"] = status_list[4].lower()
        #status_dict["vial = status_list[5].lower()

        status_dict["dryGrip"] = status_list[6].lower()
        status_dict["isSample"] = status_list[7].lower() 
        status_dict["scPosition"] = status_list[8]
        status_dict["prgs"] = eval(status_list[9].replace("Prgs:", ""))
        status_dict["door"] = self.chan_door_switch.getValue() == 0 
        
        self.emit("stausDictChanged", status_dict)

    def _getLastSCContentFromDB(self):
        """
        Decript: Updates sample changer content from Database. It is done 
                 once at init. From the brick there should be possibility 
                 to "clear memory" and start from the beginning      
        Returns: a list with sample status (as m x n list). For example:
                 [["mounted", "collected", "notmounted ...        
        """
        """cur = self.db_connection.cursor()
        sql_string = "SELECT `activityState` FROM activity ORDER BY  activityID DESC LIMIT 1;"
        cur.execute(sql_string)
        res = cur.fetchone()[0]
        cur.close()
        return res"""
        return 

    def _storeLastSCContentFromDB(self, puck, sample, activity):     
	"""
        Descript: stores last SC situation in DB. 
        Args    : puck, sample, activity: integers
                  puckID, sampleID, activity: 
                  0 - empty,  
                  1 - without barcode, not mounted 
                  2 - without barcode, mounted
                  3 - with barcode, not mounted
                  4 - with bracode, mounted   
        """       
        """cur = self.db_connection.cursor()
        sql_string = "[%d, %d, %d]" %(puck, sample, activity)
        sql_string = "INSERT INTO `activity` (`activityState`) VALUES ('%s');" %sql_string
        cur.execute(sql_string)
        self.db_connection.commit()
        cur.close() """
        return

    @task
    def load(self, holderLength, sample_id=None, sample_location=None, sampleIsLoadedCallback=None, failureCallback=None, prepareCentring=True):
        loaded = False

        with error_cleanup(functools.partial(self.emit, "stateChanged", SampleChangerState.Alarm), failureCallback):
	  with cleanup(functools.partial(self.emit, "stateChanged", SampleChangerState.Ready)):
	    #IK spec command
			
            #with cleanup(self.unlockMinidiffMotors, wait=True, timeout=3):
            loaded = self.__loadSample(holderLength, sample_id, sample_location)
        
            if loaded:
                logging.getLogger("HWR").debug("%s: sample is loaded", self.name())

                if self.prepareCentringAfterLoad and prepareCentring:
                    logging.getLogger("HWR").debug("%s: preparing minidiff for sample centring", self.name())
                    self.emit("stateChanged", SampleChangerState.Moving)
                    self.emit("statusChanged", "Preparing minidiff for sample centring")

                    #if not self.prepareCentring.isSpecConnected():
                        # this is not to wait for 30 seconds if spec is not running, in fact
                    #    raise RuntimeError("spec is not connected")

                    self.prepareCentring(wait=True, timeout=30)
              
                self.emit("statusChanged", "Ready")
 
                if callable(sampleIsLoadedCallback):
                    sampleIsLoadedCallback()

    def __loadSample(self, holderLength, sample_id, sample_location):
        logging.getLogger("HWR").debug("%s: in loadSample", self.name())

        sample = self.__getSample(sample_id, sample_location)

        if self.getLoadedSample() == sample:
            return True

        if not holderLength:
            holderLength = 22
            logging.getLogger("HWR").debug("%s: loading sample: using default holder length (%d mm)", self.name(), holderLength)

        sample._setHolderLength(holderLength)

        self.emit("stateChanged", SampleChangerState.Moving)
        self.emit("statusChanged", "Moving diffractometer to loading position")
        #if self._moveToLoadingPosition.isSpecConnected():


	#IK move minidiff to load position
        #self._moveToLoadingPosition(holderLength, wait=True, timeout=30)
        #else:
        #  raise RuntimeError("spec is not connected")

        try:
            SampleChanger.load(self, sample, wait=True)
        except Exception, err:
            self.emit("statusChanged", str(err))
            raise

        return self.getLoadedSample() == sample

    def load_sample(self, *args, **kwargs):
        kwargs["wait"] = True
        return self.load(*args, **kwargs)

    @task
    def unload(self, holderLength, sample_id=None, sample_location=None, sampleIsUnloadedCallback=None, failureCallback=None):
        unloaded = False

        with error_cleanup(functools.partial(self.emit, "stateChanged", SampleChangerState.Alarm), failureCallback):
          with cleanup(functools.partial(self.emit, "stateChanged", SampleChangerState.Ready)):
	    #IK
            #with cleanup(self.unlockMinidiffMotors, wait=True, timeout=3):
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

        self.emit("stateChanged", SampleChangerState.Moving)
        self.emit("statusChanged", "Moving diffractometer to unloading position")
        #if self._moveToUnloadingPosition.isSpecConnected():
        self._moveToUnloadingPosition(holderLength, wait=True, timeout=30)
        #else:
        #  raise RuntimeError("spec is not connected")

        EMBLSC.EMBLSC.unload(self, sample, wait=True)
 
        return not self.hasLoadedSample()

    def __getSample(self, sample_id, sample_location):
        if sample_id and sample_location:
            logging.getLogger("HWR").debug("%s: both sample barcode and location provided, discarding barcode...", self.name())
            sample_id = None

        if sample_id:
            sample = self.getComponentById(sample_id)
        else:
            if sample_location:
              basket_number, sample_number = sample_location
              sample = self.getComponentByAddress(Pin.getSampleAddress(basket_number, sample_number))
            else:
              sample = self.getSelectedSample()

        return sample
