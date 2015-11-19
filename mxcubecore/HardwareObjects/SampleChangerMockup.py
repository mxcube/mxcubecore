from sample_changer.GenericSampleChanger import *

"""
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
        self.getContainer()._triggerInfoChangedEvent()
"""

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
        SampleChanger.init(self)

    def load_sample(self, holder_length, sample_location, wait):
        return

    def load(self, sample, wait):
        self._setState(SampleChangerState.Ready)  
        return sample

    def unload(self, sample_slot, wait):
        return

    def getBasketList(self):
        basket_list = []
        for basket in self.components:
            if isinstance(basket, Basket):
                basket_list.append(basket)
        return basket_list

    def _doAbort(self):
        return

    def _doChangeMode(self):
        return

    def _doUpdateInfo(self):
        return

    def _doChangeMode(self,mode):
        return

    def _doSelect(self,component):
        return

    def _doScan(self,component,recursive):
        return

    def _doLoad(self,sample=None):
        return

    def _doUnload(self,sample_slot=None):
        return

    def _doAbort(self):
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
            present = scanned = False
            basket._setInfo(present, datamatrix, scanned)

        sample_list=[]
        for basket_index in range(5):
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
