import gevent
from datetime import datetime
import time
import logging

from sample_changer.GenericSampleChanger import *

class SampleChangerMockup(SampleChanger):

    __TYPE__ = "Mockup"
    NO_OF_BASKETS = 17
    def __init__(self, *args, **kwargs):
        super(SampleChangerMockup, self).__init__(self.__TYPE__,False, *args, **kwargs)

    def init(self):
        self._selected_sample = 2
        self._selected_basket = 9
        self._scIsCharging = None

        for i in range(SampleChangerMockup.NO_OF_BASKETS):
            basket = Basket(self,i+1)
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
        for step in range(3 * 100):
            self.emit("progressStep", int(step / 5.))
            if step > 200:
                raise Exception ("Test exc")
            time.sleep(0.01)

        mounted_sample = self.getComponentByAddress(Pin.getSampleAddress(basket, sample))
        mounted_sample._setLoaded(True, False)
        #self._setState(SampleChangerState.Ready)
        self._setLoadedSample(mounted_sample)
        self.updateInfo()
        logging.getLogger("user_level_log").info("Sample changer: Sample loaded")
        self.emit("progressStop", ())

        return self.getLoadedSample()

    def unload(self, sample_slot=None, wait=None):
        logging.getLogger("user_level_log").info("Unloading sample")
        sample = self.getLoadedSample()
        sample._setLoaded(False, True)
        self._selected_basket = -1
        self._selected_sample = -1
        self._triggerLoadedSampleChangedEvent(self.getLoadedSample())
 
    def getLoadedSample(self):
        return self.getComponentByAddress(Pin.getSampleAddress(\
             self._selected_basket, self._selected_sample))

    def is_mounted_sample(self, sample):
        if isinstance(sample, tuple):
            sample = "%s:%s" % sample
        
        return sample == self.getLoadedSample()

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
        basket_list= [('', 4)] * 5

        for basket_index in range(SampleChangerMockup.NO_OF_BASKETS):
            basket=self.getComponents()[basket_index]
            datamatrix = None
            present = True
            scanned = False
            basket._setInfo(present, datamatrix, scanned)

        sample_list=[]
        for basket_index in range(SampleChangerMockup.NO_OF_BASKETS):
            for sample_index in range(10):
                sample_list.append(("", basket_index+1, sample_index+1, 1, Pin.STD_HOLDERLENGTH))
        for spl in sample_list:
            sample = self.getComponentByAddress(Pin.getSampleAddress(spl[1], spl[2]))
            datamatrix = "matr%d_%d" %(spl[1], spl[2])
            present = scanned = loaded = has_been_loaded = False
            sample._setInfo(present, datamatrix, scanned)
            sample._setLoaded(loaded, has_been_loaded)
            sample._setHolderLength(spl[4])

        mounted_sample = self.getComponentByAddress(Pin.getSampleAddress(1,1))
        mounted_sample._setLoaded(True, False)  
        self._setState(SampleChangerState.Ready)
