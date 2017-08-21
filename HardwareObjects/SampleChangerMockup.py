import gevent
from datetime import datetime
import time

from sample_changer.GenericSampleChanger import *

class SampleChangerMockup(SampleChanger):

    __TYPE__ = "SC3"
    NO_OF_BASKETS = 17
    def __init__(self, *args, **kwargs):
        super(SampleChangerMockup, self).__init__(self.__TYPE__,False, *args, **kwargs)

    def init(self):
        self._selected_sample = 1
        self._selected_basket = 1
        self._scIsCharging = None

        for i in range(5):
            basket = Basket(self,i+1)
            self._addComponent(basket)

        self._initSCContents()
        self.signal_wait_task = None
        SampleChanger.init(self)

    def load_sample(self, holder_length, sample_location=None, wait=False):
        self.load(sample_location, wait)

    def load(self, sample, wait=False):
        current = self.getLoadedSample()
        if current != None:
            self.unload(None, wait=True)

        try:
            self._setState(SampleChangerState.Loading)
            if isinstance(sample, tuple):
                basket, sample = sample
            else:
                basket, sample = sample.split(":")

            time.sleep(2)

            self._setState(SampleChangerState.Ready)
            self._triggerLoadedSampleChangedEvent(self.getLoadedSample())
        except:
            basket, sample = (None, None)
            self._setState(SampleChangerState.Error)
        finally:
            self._selected_basket = int(basket)
            self._selected_sample = int(sample)

        loaded_sample = self.getLoadedSample()
        loaded_sample._setLoaded(True)
        return loaded_sample

    def unload(self, sample_slot, wait):
        logging.getLogger('HWR').info('Unloading sample %s' %sample_slot)
        self._setState(SampleChangerState.Unloading)
        current = self.getLoadedSample()
        current._setLoaded(False)

        self._selected_basket = None
        self._selected_sample = None
        time.sleep(2)
        self._triggerLoadedSampleChangedEvent(None)
        self._setState(SampleChangerState.Ready)

    def getBasketList(self):
        basket_list = []
        for basket in self.components:
            if isinstance(basket, Basket):
                basket_list.append(basket)
        return basket_list

    def getLoadedSample(self):
        if self._selected_basket != None and self._selected_sample != None:
            return self.getComponentByAddress(Pin.getSampleAddress(self._selected_basket, self._selected_sample))
        else:
            return None

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

        for basket_index in range(5):
            basket=self.getComponents()[basket_index]
            datamatrix = None
            scanned = False
            present = True
            basket._setInfo(present, datamatrix, scanned)

        sample_list=[]
        for basket_index in range(5):
            for sample_index in range(10):
                sample_list.append(("", basket_index+1, sample_index+1, 1, Pin.STD_HOLDERLENGTH))
        for spl in sample_list:
            sample = self.getComponentByAddress(Pin.getSampleAddress(spl[1], spl[2]))
            datamatrix = "matr%d_%d" %(spl[1], spl[2])
            scanned = loaded = has_been_loaded = False
            sample._setInfo(present, datamatrix, scanned)
            sample._setLoaded(loaded, has_been_loaded)
            sample._setHolderLength(spl[4])

        mounted_sample = self.getComponentByAddress(Pin.getSampleAddress(1,1))
        mounted_sample._setLoaded(True, False)  
        self._setState(SampleChangerState.Ready)
