import gevent
from datetime import datetime
import time
import logging

from sample_changer.GenericSampleChanger import *

class SampleChangerMockup(SampleChanger):

    __TYPE__ = "Mockup"
    NO_OF_BASKETS = 17
    NO_OF_SAMPLES_IN_BASKET = 10
    
    def __init__(self, *args, **kwargs):
        super(SampleChangerMockup, self).__init__(self.__TYPE__,False, *args, **kwargs)

    def init(self):
        self._selected_sample = -1
        self._selected_basket = -1
        self._scIsCharging = None
    
        self.no_of_baskets = self.getProperty('no_of_baskets', SampleChangerMockup.NO_OF_BASKETS)
        
        self.no_of_samples_in_basket = self.getProperty('no_of_samples_in_basket', SampleChangerMockup.NO_OF_SAMPLES_IN_BASKET)
        
        for i in range(self.no_of_baskets):
            basket = Basket(self, i+1, samples_num=self.no_of_samples_in_basket)
            self._addComponent(basket)

        self._initSCContents()
        self.signal_wait_task = None
        SampleChanger.init(self)

        self.log_filename = self.getProperty("log_filename")

    def get_log_filename(self):
        return self.log_filename

    def load_sample(self, holder_length, sample_location=None, wait=False):
        self.load(sample_location, wait)

    def load(self, sample, wait=False):
        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", True)
        self._setState(SampleChangerState.Loading)
        self._resetLoadedSample()
        if isinstance(sample, tuple):
            basket, sample = sample
        else:
            basket, sample = sample.split(":")

        self._selected_basket = basket
        self._selected_sample = sample

        msg = "Loading sample %d:%d" %(int(basket), int(sample))
        logging.getLogger("user_level_log").info(\
            "Sample changer: %s. Please wait..." % msg)

        self.emit("progressInit", (msg, 100))
        for step in range(2 * 100):
            self.emit("progressStep", int(step / 2.))
            time.sleep(0.01)

        mounted_sample = self.getComponentByAddress(Pin.getSampleAddress(basket, sample))
        mounted_sample._setLoaded(True, False)
        self._setState(SampleChangerState.Ready)

        self._setLoadedSample(mounted_sample)
        self.updateInfo()
        logging.getLogger("user_level_log").info("Sample changer: Sample loaded")
        self.emit("progressStop", ())

        self.emit("fsmConditionChanged", "sample_is_loaded", True)
        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", False)

        return self.getLoadedSample()

    def unload(self, sample_slot=None, wait=None):
        logging.getLogger("user_level_log").info("Unloading sample")
        sample = self.getLoadedSample()
        sample._setLoaded(False, True)
        self._selected_basket = -1
        self._selected_sample = -1
        self._triggerLoadedSampleChangedEvent(self.getLoadedSample())
        self.emit("fsmConditionChanged", "sample_is_loaded", False)
 
    def getLoadedSample(self):
        return self.getComponentByAddress(Pin.getSampleAddress(\
             self._selected_basket, self._selected_sample))

    def is_mounted_sample(self, sample):
        return self.getComponentByAddress(\
                  Pin.getSampleAddress(sample[0], sample[1]))== \
                  self.getLoadedSample()

    def _doAbort(self):
        return

    def _doChangeMode(self):
        return

    def _doUpdateInfo(self):
        return

    def _doSelect(self,component):
        return

    def _doScan(self,component,recursive):
        return

    def _doLoad(self, sample=None):
        return

    def _doUnload(self,sample_slot=None):
        return

    def _doReset(self):
        return

    def _initSCContents(self):
        """
        Initializes the sample changer content with default values.

        :returns: None
        :rtype: None
        """
        named_samples = {}
        if self.hasObject('test_sample_names'):
            for tag, val in self['test_sample_names'].getProperties().items():
                named_samples[val] = tag

        for basket_index in range(self.no_of_baskets):
            basket=self.getComponents()[basket_index]
            datamatrix = None
            present = True
            scanned = False
            basket._setInfo(present, datamatrix, scanned)

        sample_list=[]
        for basket_index in range(self.no_of_baskets):
            for sample_index in range(self.no_of_samples_in_basket):
                sample_list.append(("", basket_index+1, sample_index+1, 1, Pin.STD_HOLDERLENGTH))
        for spl in sample_list:
            address = Pin.getSampleAddress(spl[1], spl[2])
            sample = self.getComponentByAddress(address)
            sample_name = named_samples.get(address)
            if sample_name is not None:
                sample._name = sample_name
            datamatrix = "matr%d_%d" %(spl[1], spl[2])
            present = scanned = loaded = has_been_loaded = False
            sample._setInfo(present, datamatrix, scanned)
            sample._setLoaded(loaded, has_been_loaded)
            sample._setHolderLength(spl[4])

        #mounted_sample = self.getComponentByAddress(Pin.getSampleAddress(1,1))
        #mounted_sample._setLoaded(True, False)  
        self._setState(SampleChangerState.Ready)
