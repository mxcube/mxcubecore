from .GenericSampleChanger import *
import gevent

class Pin(Sample):        
    def __init__(self,basket,basket_no,sample_no):
        super(Pin, self).__init__(basket, Pin.getSampleAddress(basket_no,sample_no), True)
        self._setHolderLength(22.0)

    def getBasketNo(self):
        return self.getContainer().getIndex()+1

    def getVialNo(self):
        return self.getIndex()+1

    @staticmethod
    def getSampleAddress(basket_number, sample_number):
        return str(basket_number) + ":" + "%02d" % (sample_number)


class Basket(Container):
    __TYPE__ = "Puck"    
    def __init__(self,container,number):
        super(Basket, self).__init__(self.__TYPE__,container,Basket.getBasketAddress(number),True)
        for i in range(10):
            slot = Pin(self,number,i+1)
            self._addComponent(slot)
                            
    @staticmethod
    def getBasketAddress(basket_number):
        return str(basket_number)

    def clearInfo(self):
	self.getContainer()._reset_basket_info(self.getIndex()+1)
        self.getContainer()._triggerInfoChangedEvent()


class Robodiff(SampleChanger):
    __TYPE__ = "Robodiff"

    def __init__(self, *args, **kwargs):
        super(Robodiff, self).__init__(self.__TYPE__, True, *args, **kwargs)

        for i in range(24):
            basket = Basket(self, i+1)
            self._addComponent(basket)

    def init(self):
        controller = self.getObjectByRole("controller")
        self.dm_reader = getattr(controller, "dm_reader")
        
        return SampleChanger.init(self)

    def getSampleProperties(self):
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)

    def _doAbort(self):
        self._abort()

    def _doUpdateInfo(self):
        dm_list = self.dm_reader.get_list()

        for b in range(24):
            basket = self.getComponents()[b]
            basket._setInfo(present_bool, datamatrix, scanned_bool)
        for s in sample_list:
            sample = self.getComponentByAddress(Pin.getSampleAddress(s[1], s[2]))
            sample._setInfo(present_bool, datamatrix, scanned_bool)
            sample._setLoaded(loaded_bool, has_been_loaded_bool)
            sample._setHolderLength(22)

        self._updateSelection()
        self._updateState()

    def _doScan(self, component, recursive):
        pass

    def _doSelect(self, component):
        if isinstance(component, Sample):
            selected_basket = self.getSelectedComponent()
            if (selected_basket is None) or (selected_basket != component.getContainer()):
                self._select_basket(component.getBasketNo())
            self._select_sample(component.getIndex()+1)
        elif isinstance(component, Container) and ( component.getType() == Basket.__TYPE__):
            self._select_basket(component.getIndex()+1)

    def _select_basket(self, basket_no):
        pass

    def _select_sample(self, sample_no):
        pass

    def _doLoad(self, sample=None):
        selected=self.getSelectedSample()
        if self.hasLoadedSample():
            if (sample is None) or (sample==self.getLoadedSample()):
                raise Exception("The sample " + str(self.getLoadedSample().getAddress()) + " is already loaded")
            self._chained_load(sample.getBasketNo(), sample.getVialNo(), sample.getHolderLength())
        else:
            if (sample is None):
                if (selected == None):
                    raise Exception("No sample selected")
                else:
                    sample=selected
            elif (sample is not None) and (sample!=selected):
                self._doSelect(sample)
            self._load(sample.getHolderLength())

    def _load(self, holderlength):
        pass

    def _doUnload(self, sample_slot=None):
        if (sample_slot is not None):
            self._doSelect(sample_slot)        
        self._unload()

    def _unload(self):
        pass

    def _doReset(self):
        return self._reset()

    def _reset(self):
        pass

    def clearBasketInfo(self, basket):
        return self._reset_basket_info(basket)

     def _updateState(self):
        try:
          state = self._readState()
        except:
          state = SampleChangerState.Unknown
        if state == SampleChangerState.Moving and self._isDeviceBusy(self.getState()):
            return          
        self._setState(state)
       
    def _readState(self):
        state = str(self._state.getValue() or "").upper()
        state_converter = { "ALARM": SampleChangerState.Alarm,
                            "FAULT": SampleChangerState.Fault,
                            "MOVING": SampleChangerState.Moving,
                            "STANDBY": SampleChangerState.Ready,
                            "READY": SampleChangerState.Ready,
                            "RUNNING": SampleChangerState.Moving,
                            "LOADING": SampleChangerState.Charging,
                            "INIT": SampleChangerState.Initializing }
        return state_converter.get(state, SampleChangerState.Unknown)
                        
    def _isDeviceBusy(self, state=None):
        if state is None:
            state = self._readState()
        return state not in (SampleChangerState.Ready, SampleChangerState.Loaded, SampleChangerState.Alarm, 
                             SampleChangerState.Disabled, SampleChangerState.Fault, SampleChangerState.StandBy)

    def _isDeviceReady(self):
        state = self._readState()
        return state in (SampleChangerState.Ready, SampleChangerState.Charging)              

    def _waitDeviceReady(self,timeout=None):
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self._isDeviceReady():
                gevent.sleep(0.01)
            
    def _updateSelection(self):    
        basket=None
        sample=None
        try:
          basket_no = self._selected_basket.getValue()                    
          if basket_no is not None and basket_no>0 and basket_no <=24:
            basket = self.getComponentByAddress(Basket.getBasketAddress(basket_no))
            sample_no = self._selected_sample.getValue()
            if sample_no is not None and sample_no>0 and sample_no <=10:
                sample = self.getComponentByAddress(Pin.getSampleAddress(basket_no, sample_no))            
        except:
          pass
        self._setSelectedComponent(basket)
        self._setSelectedSample(sample)
