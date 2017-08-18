"""
CATS sample changer hardware object.

Implements the abstract interface of the GenericSampleChanger for the CATS
sample changer model.

Derived from Alexandre Gobbo's implementation for the EMBL SC3 sample changer.
Derived from Michael Hellmig's implementation for the BESSY CATS sample changer

History:
   - adds support for ISARA Model

Know Catalog of MXCuBE sites and CATS
   BESSY - 
       BL14. (CATS) 3lid * 3puck (SPINE) * 10 = 90 samples  
   ALBA - 
       XALOC. (CATS) 3lid * 3puck (UNIPUCK) * 16 = 144 samples 
   MAXIV -
       BIOMAX. (ISARA) 1 lid * 10puck (SPINE) * 10 + 19puck (UNIPUCK) * 16 = 404 samples
   SOLEIL
       PX1. (CATS)
       PX2. (CATS)
"""
from GenericSampleChanger import *

import time
import PyTango
import logging

__author__ = "Michael Hellmig, Jie Nan, Bixente Rey"
__credits__ = ["The MXCuBE collaboration"]

__email__ = "txo@txolutions.com"

#  
# Attention. Numbers here correspond to values returned by CassetteType of device server
#  
BASKET_UNKNOWN, BASKET_SPINE, BASKET_UNIPUCK = (0,1,2)

#
# Number of samples per puck type
#
SAMPLES_SPINE = 10
SAMPLES_UNIPUCK = 16

TOOL_FLANGE, TOOL_UNIPUCK, TOOL_SPINE, TOOL_PLATE, \
    TOOL_LASER, TOOL_DOUBLE_GRIPPER = (0,1,2,3,4,5)

class Basket(Container):
    __TYPE__ = "Puck"

    def __init__(self, container, number, samples_num=10, name="Puck"):
        super(Basket, self).__init__(self.__TYPE__,container,Basket.getBasketAddress(number),True)

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

class SpineBasket(Basket):
    def __init__(self, container, number, name="SpinePuck"):
        super(SpineBasket, self).__init__(container,Basket.getBasketAddress(number), SAMPLES_SPINE, True)

class UnipuckBasket(Basket):
    def __init__(self, container, number, name="UniPuck"):
        super(UnipuckBasket, self).__init__(container,Basket.getBasketAddress(number), SAMPLES_UNIPUCK, True)

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
        if basket_number is not None and sample_number is not None:
            return str(basket_number) + ":" + "%02d" % (sample_number)
        else:
            return ""


class Cats90(SampleChanger):
    """

    Actual implementation of the CATS Sample Changer,
       BESSY BL14.1 installation with 3 lids and 90 samples

    """    
    __TYPE__ = "CATS"    

    default_no_lids = 3
    baskets_per_lid = 3

    default_basket_type = BASKET_SPINE

    def __init__(self, *args, **kwargs):
        super(Cats90, self).__init__(self.__TYPE__,False, *args, **kwargs)
            
    def init(self):      

        #  
        # DO NOT CALL SampleChanger.init()
        #  If SampleChanger.init() is called reception of signals at connection time is not done.  
        #
        #  In the case of Cats90 we do not use an update_timer... update is done by signals from Tango channels 
        #  

        self._selected_sample = None
        self._selected_basket = None
        self._scIsCharging = None

        self.read_datamatrix = False
        self.unipuck_tool = TOOL_UNIPUCK

        self.former_loaded = None
        self.cats_device = None

        self.cats_datamatrix = ""
        self.cats_loaded_lid = None
        self.cats_loaded_num = None

        # Default values
        self.cats_powered = False
        self.cats_status = ""
        self.cats_running = False
        self.cats_state = PyTango.DevState.UNKNOWN
        self.cats_lids_closed = False

        self.basket_types = None
        self.number_of_baskets = None

        # add support for CATS dewars with variable number of lids

        # Create channels from XML

        self.cats_device = PyTango.DeviceProxy(self.getProperty("tangoname"))

        no_of_lids = self.getProperty('no_of_lids')
        if no_of_lids is None:
            self.number_of_lids = self.default_no_lids
        else:
            self.number_of_lids = int(no_of_lids)

        # Create channels
        self._chnState = self.getChannelObject("_chnState")
        if self._chnState is None:
            self._chnState = self.addChannel({
                    "type": "tango", "name": "_chnState",
                    "tangoname": self.tangoname, "polling": 300,
                }, "State")

        self._chnStatus = self.getChannelObject("_chnStatus")
        if self._chnStatus is None:
            self._chnStatus = self.addChannel({
                    "type": "tango", "name": "_chnStatus",
                    "tangoname": self.tangoname, "polling": 300,
                }, "Status")

        self._chnPowered = self.getChannelObject("_chnPowered")
        if self._chnPowered is None:
            self._chnPowered = self.addChannel({
                    "type": "tango", "name": "_chnPowered",
                    "tangoname": self.tangoname, "polling": 300,
                }, "Powered")

        self._chnPathRunning = self.getChannelObject("_chnPathRunning")
        if self._chnPathRunning is None:
            self._chnPathRunning = self.addChannel({
                    "type": "tango", "name": "_chnPathRunning",
                    "tangoname": self.tangoname, "polling": 1000,
                }, "PathRunning")

        self._chnNumLoadedSample = self.getChannelObject("_chnNumLoadedSample")
        if self._chnNumLoadedSample is None:
            self._chnNumLoadedSample = self.addChannel({
                    "type": "tango", "name": "_chnNumLoadedSample",
                    "tangoname": self.tangoname, "polling": 1000,
                }, "NumSampleOnDiff")

        self._chnLidLoadedSample = self.getChannelObject("_chnLidLoadedSample")
        if self._chnLidLoadedSample is None:
            self._chnLidLoadedSample = self.addChannel({
                    "type": "tango", "name": "_chnLidLoadedSample",
                    "tangoname": self.tangoname, "polling": 1000,
                }, "LidSampleOnDiff")

        self._chnSampleBarcode = self.getChannelObject("_chnSampleBarcode")
        if self._chnSampleBarcode is None:
            self._chnSampleBarcode = self.addChannel({
                    "type": "tango", "name": "_chnSampleBarcode",
                    "tangoname": self.tangoname, "polling": 1000,
                }, "Barcode")

        self._chnSampleIsDetected = self.getChannelObject("_chnSampleIsDetected")
        if self._chnSampleIsDetected is None:
            self._chnSampleIsDetected = self.addChannel({
                    "type": "tango", "name": "_chnSampleIsDetected",
                    "tangoname": self.tangoname, 
                }, "di_PRI_SOM")

        self._chnAllLidsClosed = self.getChannelObject("_chnTotalLidState")
        if self._chnAllLidsClosed is None:
            self._chnAllLidsClosed = self.addChannel({
                    "type": "tango", "name": "_chnAllLidsClosed",
                    "tangoname": self.tangoname, "polling": 1000,
                }, "di_AllLidsClosed")

        # commands
        self._cmdLoad = self.getCommandObject("_cmdLoad")
        if self._cmdLoad is None:
            self._cmdLoad = self.addCommand({
                    "type": "tango",
                    "name": "_cmdLoad",
                    "tangoname": self.tangoname,
                }, "put")

        self._cmdUnload = self.getCommandObject("_cmdUnload")
        if self._cmdUnload is None:
            self._cmdUnload = self.addCommand({
                    "type": "tango",
                    "name": "_cmdUnload",
                    "tangoname": self.tangoname,
                }, "get")

        self._cmdChainedLoad = self.getCommandObject("_cmdChainedLoad")
        if self._cmdChainedLoad is None:
            self._cmdChainedLoad = self.addCommand({
                    "type": "tango",
                    "name": "_cmdChainedLoad",
                    "tangoname": self.tangoname,
                }, "getput")

        self._cmdAbort = self.getCommandObject("_cmdAbort")
        if self._cmdAbort is None:
            self._cmdAbort = self.addCommand({
                    "type": "tango",
                    "name": "_cmdAbort",
                    "tangoname": self.tangoname,
                }, "abort")

        self._cmdLoadBarcode = self.getCommandObject("_cmdLoadBarcode")
        if self._cmdLoadBarcode is None:
            self._cmdLoadBarcode = self.addCommand({
                    "type": "tango",
                    "name": "_cmdLoadBarcode",
                    "tangoname": self.tangoname,
                }, "put_bcrd")

        self._cmdChainedLoadBarcode = self.getCommandObject("_cmdChainedLoadBarcode")
        if self._cmdChainedLoadBarcode is None:
            self._cmdChainedLoadBarcode = self.addCommand({
                    "type": "tango",
                    "name": "_cmdChainedLoadBarcode",
                    "tangoname": self.tangoname,
                }, "getput_bcrd")

        self._cmdScanSample = self.getCommandObject("_cmdScanSample")
        if self._cmdScanSample is None:
            self._cmdScanSample = self.addCommand({
                    "type": "tango",
                    "name": "_cmdScanSample",
                    "tangoname": self.tangoname,
                }, "barcode")


        # see if we can find model from devserver. Otherwise... CATS
        try:
            self.cats_model = self.cats_device.read_attribute("CatsModel").value
        except PyTango.DevError:
            self.cats_model = "CATS"
            
        # see if the device server can return CassetteTypes (and then number of cassettes/baskets)
        try:
            self.basket_types = self.cats_device.read_attribute("CassetteType").value
            self.number_of_baskets = len(self.basket_types)
        except PyTango.DevError:
            pass

        # find number of baskets and number of samples per basket 
        if self.number_of_baskets is not None: 
            if self.is_cats():
                # if CATS... uniform type of baskets. the first number in CassetteType is used for all
                basket_type = self.basket_types[0]
                if basket_type is BASKET_UNIPUCK:
                    self.samples_per_basket = SAMPLES_UNIPUCK
                else:
                    self.samples_per_basket = SAMPLES_SPINE
            else:
                self.samples_per_basket = None
        else:
            # ok. it does not. use good old way (xml or default) to find nb baskets and samples
            no_of_baskets = self.getProperty('no_of_baskets')
            samples_per_basket = self.getProperty('samples_per_basket')

            if no_of_baskets is None:
                self.number_of_baskets = self.baskets_per_lid * self.number_of_lids
            else:
                self.number_of_baskets = int(no_of_baskets)

            self.basket_types = [None,] * self.number_of_baskets

            if samples_per_basket is None:
                self.samples_per_basket = SAMPLES_SPINE
            else:
                self.samples_per_basket = int(samples_per_basket)

        # declare channels to detect basket presence changes
        if self.is_isara():
            self.basket_channels = None
            self._chnBasketPresence = self.getChannelObject("_chnBasketPresence")
            if self._chnBasketPresence is None:
                self._chnBasketPresence = self.addChannel({
                        "type": "tango", "name": "_chnBasketPresence",
                        "tangoname": self.tangoname, "polling": 1000,
                    }, "CassettePresence")
            self.samples_per_basket = None
        else:
            self.basket_channels = [None,] * self.number_of_baskets

            for basket_index in range(self.number_of_baskets):            
                channel_name = "_chnBasket%dState" % (basket_index + 1)
                chan = self.getChannelObject(channel_name)
                if chan is None:
                   chan = self.addChannel({
                        "type": "tango", "name": channel_name,
                        "tangoname": self.tangoname, "polling": 1000,
                      }, "Cassette%dPresence" % (basket_index+1))
                self.basket_channels[basket_index] = chan

        #
        # determine Cats geometry and prepare objects
        #
        self._initSCContents()

        #
        # connect channel signals to update info
        #

        self.use_update_timer = False  # do not use update_timer for Cats 

        self._chnState.connectSignal("update", self.cats_state_changed)
        self._chnStatus.connectSignal("update", self.cats_status_changed)
        self._chnPathRunning.connectSignal("update", self.cats_pathrunning_changed) 
        self._chnPowered.connectSignal("update", self.cats_powered_changed) 
        self._chnAllLidsClosed.connectSignal("update", self.cats_lids_closed_changed)
        self._chnLidLoadedSample.connectSignal("update", self.cats_loaded_lid_changed)
        self._chnNumLoadedSample.connectSignal("update", self.cats_loaded_num_changed)
        self._chnSampleBarcode.connectSignal("update", self.cats_barcode_changed)

        # connect presence channels
        if self.basket_channels is not None:  # old device server
            for basket_index in range(self.number_of_baskets):
                channel = self.basket_channels[basket_index]                 
                channel.connectSignal("update", lambda value, \
                     this=self,idx=basket_index:Cats90.cats_basket_presence_changed(this,idx,value))
        else: # new device server with global CassettePresence attribute
            self._chnBasketPresence.connectSignal("update", self.cats_baskets_changed)

        # Read other XML properties
        read_datamatrix = self.getProperty("read_datamatrix")
        if read_datamatrix: 
            self.setReadBarcode(True)
         
        unipuck_tool = self.getProperty("unipuck_tool")
        try:
            unipuck_tool = int(unipuck_tool)
            if unipuck_tool:
               self.setUnipuckTool(unipuck_tool) 
        except:
            pass
 
        self.updateInfo()

    def is_isara(self):
        return self.cats_model == "ISARA"

    def is_cats(self):
        return self.cats_model != "ISARA"

    def _initSCContents(self):
        """
        Initializes the sample changer content with default values.

        :returns: None
        :rtype: None
        """
        logging.getLogger("HWR").warning("Cats90:  initializing contents")

        self.basket_presence = [None,] * self.number_of_baskets
        
        for i in range(self.number_of_baskets):
            if self.basket_types[i] == BASKET_SPINE:
                basket = SpineBasket(self,i+1)
            elif self.basket_types[i] == BASKET_UNIPUCK:
                basket = UnipuckBasket(self,i+1)
            else:
                basket = Basket(self,i+1, samples_num=self.samples_per_basket)

            self._addComponent(basket)

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

    def setReadBarcode(self, value):
        """
        Activates reading of barcode during load or chained load trajectory
        Internally it will use put() or put_bcrd() in PyCats dev. server

        :value:  boolean argument
        """
        self.read_datamatrix = value

    def setUnipuckTool(self, value):
        if value in [TOOL_UNIPUCK, TOOL_DOUBLE_GRIPPER]:
            self.unipuck_tool = value
        else:
            logging.warning("wrong unipuck tool selected %s (valid: %s/%s). Selection IGNORED" % (value, TOOL_UNIPUCK, TOOL_DOUBLE_GRIPPER))

    #########################           TASKS           #########################

    def _doUpdateInfo(self):       
        """
        Updates the sample changers status: mounted pucks, state, currently loaded sample

        :returns: None
        :rtype: None
        """
        logging.info("doUpdateInfo should not be called for cats. only for update timer type of SC")
        return

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
            lid, sample = self.basketsample_to_lidsample(selected.getBasketNo(), selected.getVialNo())
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
                    basket = selected.getBasketNo()
                    num = sample_index+1
                    lid, sample = self.basketsample_to_lidsample(basket,num)
                    argin = ["2", str(lid), str(sample), "0", "0"]
                    self._executeServerTask(self._cmdScanSample, argin)
    
    def load(self, sample=None, wait=True):
        """
        Load a sample. 
            overwrite original load() from GenericSampleChanger to allow finer decision 
            on command to use (with or without barcode / or allow for wash in some cases)
            Implement that logic in _doLoad()
            Add initial verification about the Powered:
            (NOTE) In fact should be already as the power is considered in the state handling
        """
        if not self._chnPowered.getValue():
            raise Exception("CATS power is not enabled. Please switch on arm power before transferring samples.")
            return 

        self._updateState() # remove software flags like Loading.
        logging.getLogger("HWR").debug("  ***** ISARA *** load cmd .state is:  %s " % (self.state))

        sample = self._resolveComponent(sample)
        self.assertNotCharging()

        self._executeTask(SampleChangerState.Loading, wait, self._doLoad, sample)

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

        basketno = selected.getBasketNo()
        sampleno = selected.getVialNo() 

        lid, sample = self.basketsample_to_lidsample(basketno,sampleno)

        if self.is_isara():
            stype = "1"
        else:
            stype = "0"

        tool = self.tool_for_basket(basketno)

        # we should now check basket type on diffr to see if tool is different... then decide what to do
     
        if shifts is None:
            xshift, yshift, zshift = ["0", "0", "0" ]
        else:
            xshift, yshift, zshift = map(str,shifts)

        # prepare argin values
        argin = [str(tool), str(lid), str(sample), stype, "0", xshift, yshift, zshift]
        logging.getLogger("HWR").debug("  ***** ISARA *** doLoad argin:  %s / %s:%s" % (argin, basketno, sampleno))
            
        if self.hasLoadedSample():
            if selected==self.getLoadedSample():
                raise Exception("The sample " + str(self.getLoadedSample().getAddress()) + " is already loaded")
            else:
                if self.read_datamatrix and self._cmdChainedLoadBarcode is not None:
                    logging.getLogger("HWR").warning("  ==========CATS=== chained load sample (brcd), sending to cats:  %s" % argin)
                    self._executeServerTask(self._cmdChainedLoadBarcode, argin)
                else:
                    logging.getLogger("HWR").warning("  ==========CATS=== chained load sample, sending to cats:  %s" % argin)
                    self._executeServerTask(self._cmdChainedLoad, argin)
        else:
            if self.cats_sample_on_diffr():
                logging.getLogger("HWR").warning("  ==========CATS=== trying to load sample, but sample detected on diffr. aborting") 
                self._updateState() # remove software flags like Loading.
            else:
                if self.read_datamatrix and self._cmdLoadBarcode is not None:
                    logging.getLogger("HWR").warning("  ==========CATS=== load sample (bcrd), sending to cats:  %s" % argin)
                    self._executeServerTask(self._cmdLoadBarcode, argin)
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
            
        if not self.hasLoadedSample() or not self._chnSampleIsDetected.getValue():
            logging.getLogger("HWR").warning("  Trying do unload sample, but it does not seem to be any on diffr:  %s" % argin)

        if (sample_slot is not None):
            self._doSelect(sample_slot)

        if shifts is None:
            xshift, yshift, zshift = ["0", "0", "0" ]
        else:
            xshift, yshift, zshift = map(str,shifts)

        loaded_lid = self._chnLidLoadedSample.getValue()
        loaded_num = self._chnNumLoadedSample.getValue()
        loaded_basket, loaded_sample = self.lidsample_to_basketsample(loaded_lid, loaded_num)
        
        tool = self.tool_for_basket(loaded_basket)

        argin = [str(tool), "0", xshift, yshift, zshift]

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

        # hack for transient states
        trials = 0
        while value in [PyTango.DevState.ALARM, PyTango.DevState.ON]:
            time.sleep(0.1)
            trials += 1
            logging.getLogger("HWR").warning("SAMPLE CHANGER could be in transient state. trying again")
            value = self._chnState.getValue()
            if trials > 4:
               break

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
        self.cats_lids_closed = value
        self._updateState()
    
    def cats_basket_presence_changed(self,basket_index,value):
        self.basket_presence[basket_index] = value
        self._updateCatsContents()

    def cats_baskets_changed(self,value):
        logging.getLogger("HWR").warning("Baskets changed. %s" % value)
        for idx,val in enumerate(value):
            self.basket_presence[idx] = val
        self._updateCatsContents()
        self._updateLoadedSample()

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

        scanned = (len(value) != 0)

        lid_on_tool = self.cats_device.read_attribute("LidSampleOnTool").value
        sample_on_tool = self.cats_device.read_attribute("NumSampleOnTool").value

        if -1 in [lid_on_tool, sample_on_tool]: 
            return

        basketno, sampleno = self.lidsample_to_basketsample(lid_on_tool,sample_on_tool)
        logging.getLogger("HWR").warning("Barcode %s read. Assigning it to sample %s:%s" % (value, basketno, sampleno))

        sample = self.getComponentByAddress(Pin.getSampleAddress(basketno, sampleno))
        sample._setInfo(sample.isPresent(), value, scanned)

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
        self.cats_running = self._chnPathRunning.getValue()
        self.cats_powered = self._chnPowered.getValue()
        self.cats_lids_closed = self._chnAllLidsClosed.getValue() 
        self.cats_status = self._chnStatus.getValue()
        self.cats_state = self._chnState.getValue()

    def _updateState(self):

        has_loaded = self.hasLoadedSample()
        on_diff = self._chnSampleIsDetected.getValue()


        state = self._decideState(self.cats_state, self.cats_powered, self.cats_lids_closed, has_loaded, on_diff)

        status = SampleChangerState.tostring(state)
        self._setState(state, status)
       
    def _readState(self):
        """
        Read the state of the Tango DS and translate the state to the SampleChangerState Enum

        :returns: Sample changer state
        :rtype: GenericSampleChanger.SampleChangerState
        """
        _state = self._chnState.getValue()
        _powered = self._chnPowered.getValue()
        _lids_closed = self._chnAllLidsClosed.getValue()
        _has_loaded = self.hasLoadedSample()
        _on_diff = self._chnSampleIsDetected.getValue()

        # hack for transient states
        trials = 0
        while  _state in [PyTango.DevState.ALARM, PyTango.DevState.ON]:
            time.sleep(0.1)
            trials += 1
            logging.getLogger("HWR").warning("SAMPLE CHANGER could be in transient state. trying again")
            _state = self._chnState.getValue()
            if trials > 2:
               break

        state =  self._decideState(_state, _powered, _lids_closed, _has_loaded, _on_diff)
      
        return state
                        
    def _decideState(self, dev_state, powered, lids_closed, has_loaded, on_diff):

        if dev_state == PyTango.DevState.ALARM: 
            _state = SampleChangerState.Alarm 
        elif not powered:
            _state = SampleChangerState.Disabled
        elif dev_state == PyTango.DevState.RUNNING: 
            if self.state not in [SampleChangerState.Loading, SampleChangerState.Unloading]: 
               _state = SampleChangerState.Moving 
            else:
               _state = self.state
        elif dev_state == PyTango.DevState.UNKNOWN: 
            _state = SampleChangerState.Unknown
        elif has_loaded ^ on_diff:
            # go to Unknown state if a sample is detected on the gonio but not registered in the internal database
            # or registered but not on the gonio anymore
            logging.getLogger("HWR").warning("SAMPLE CHANGER Unknown 2 (hasLoaded: %s / detected: %s)" % (self.hasLoadedSample(), self._chnSampleIsDetected.getValue()))
            _state = SampleChangerState.Unknown 
        #elif not lids_closed: 
            #_state = SampleChangerState.Charging
        elif dev_state == PyTango.DevState.ON:
            _state = SampleChangerState.Ready
        else:
            _state = SampleChangerState.Unknown 

        return _state

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

    def lidsample_to_basketsample(self, lid, num):
        if self.is_isara():
            return lid,num
        else:
           lid_base = (lid - 1) * self.baskets_per_lid
           lid_offset = ((num - 1) / self.samples_per_basket) + 1
           sample_pos = ((num - 1) % self.samples_per_basket) + 1
           basket = lid_base + lid_offset
           return basket, sample_pos

    def basketsample_to_lidsample(self, basket, num):
        if self.is_isara():
           return basket,num
        else:
           lid = ((basket - 1) / self.baskets_per_lid) + 1
           sample = (((basket - 1) % self.basket_per_lid) * self.samples_per_basket) + num
           return lid,sample

    def tool_for_basket(self, basketno):

        basket_type = self.basket_types[basketno-1]

        if basket_type == BASKET_SPINE:
            tool = TOOL_SPINE
        elif basket_type == BASKET_UNIPUCK:
            tool = self.unipuck_tool # configurable (xml and command setUnipuckTool()  
        return tool

    def _updateLoadedSample(self):
      
        loadedSampleLid = self.cats_loaded_lid
        loadedSampleNum = self.cats_loaded_num

        logging.getLogger("HWR").info("Updating loaded sample %s:%s" % (loadedSampleLid, loadedSampleNum)) 

        if -1 not in [loadedSampleLid, loadedSampleNum]:
            basket, sample = self.lidsample_to_basketsample(loadedSampleLid,loadedSampleNum)
            new_sample = self.getComponentByAddress(Pin.getSampleAddress(basket, sample))
        else:
            basket, sample = None, None
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
                logging.getLogger("HWR").info("  setting sample %s (%s) as currently loaded. %s" % (new_sample.getAddress(), id(new_sample), new_sample.isLoaded()))

            if (old_sample is None) or (new_sample is None) or (old_sample.getAddress()!=new_loaded.getAddress()):
                self._triggerLoadedSampleChangedEvent(new_sample)


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

        self._triggerContentsUpdatedEvent()

def test_hwo(hwo):
    basket_list = hwo.getBasketList()
    sample_list = hwo.getSampleList()
    print("Baskets/Samples in CATS: %s/%s" % ( len(basket_list), len(sample_list)))
    gevent.sleep(2)
    sample_list = hwo.getSampleList()

    for s in sample_list:
        if s.isLoaded():
            print "Sample %s loaded" % s.getAddress()
            break

    if hwo.hasLoadedSample():
        print "Currently loaded (%s): %s" % (hwo.hasLoadedSample(),hwo.getLoadedSample().getAddress())
    print "CATS state is: ", hwo.state
    print "Sample on Magnet : ", hwo.cats_sample_on_diffr()
    print "All lids closed: ", hwo._chnAllLidsClosed.getValue()
    
    print "Sample Changer State is: ", hwo.getStatus()
    for basketno in range(hwo.number_of_baskets):
        no = basketno +1
        print "Tool for basket %d is: %d" % (no, hwo.tool_for_basket(no))
