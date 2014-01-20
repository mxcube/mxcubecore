from .GenericSampleChanger import *


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
	self.getContainer()._reset_basket_info(self.getIndex()+1)
        self.getContainer()._triggerInfoChangedEvent()


class CatsBessy(SampleChanger):
    __TYPE__ = "CATS"    
    NO_OF_BASKETS = 9

    """
    Actual implementation of the CATS Sample Changer, BESSY implementation
    """    
    def __init__(self, *args, **kwargs):
        super(CatsBessy, self).__init__(self.__TYPE__,False, *args, **kwargs)
        for i in range(CatsBessy.NO_OF_BASKETS):
            basket = Basket(self,i+1)
            self._addComponent(basket)
            
    def init(self):      
        self._selected_sample = 1
        self._selected_basket = 1

        self._state = self.getChannelObject("_state")
        self._abort = self.getCommandObject("_abort")

        self._basketChannels = []
        for b in range(CatsBessy.NO_OF_BASKETS):            
            self._basketChannels.append(self.addChannel({"type":"tango", "name":"di_basket", "tangoname": self.tangoname, "polling": 500}, ("di_Cassette%dPresence" % (b + 1))))

        self._lidStatus = self.addChannel({"type":"tango", "name":"di_AllLidsClosed", "tangoname": self.tangoname, "polling": 500}, "di_AllLidsClosed")
        if self._lidStatus is not None:
            self._lidStatus.connectSignal("update", self._updateOperationMode)

        self._load = self.addCommand({"type":"tango", "name":"put_bcrd", "tangoname": self.tangoname}, "put_bcrd")
        self._unload = self.addCommand({"type":"tango", "name":"put_bcrd", "tangoname": self.tangoname}, "get")
        self._chained_load = self.addCommand({"type":"tango", "name":"getput_bcrd", "tangoname": self.tangoname}, "getput_bcrd")
        self._reset = self.addCommand({"type":"tango", "name":"reset", "tangoname": self.tangoname}, "reset")
        self._abort = self.addCommand({"type":"tango", "name":"abort", "tangoname": self.tangoname}, "abort")

        self._numSampleOnDiff = self.addChannel({"type":"tango", "name":"NumSampleOnDiff", "tangoname": self.tangoname, "polling": 500}, "NumSampleOnDiff")
        self._lidSampleOnDiff = self.addChannel({"type":"tango", "name":"LidSampleOnDiff", "tangoname": self.tangoname, "polling": 500}, "LidSampleOnDiff")
        self._barcode = self.addChannel({"type":"tango", "name":"Barcode", "tangoname": self.tangoname, "polling": 500}, "Barcode")

        SampleChanger.init(self)   

    def getSampleProperties(self):
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)
        
    #########################           TASKS           #########################
    def _doAbort(self):
        self._abort()            

    def _doScan(self):
        pass

    def _doUpdateInfo(self):       
        basket_list= [('', 4)] * CatsBessy.NO_OF_BASKETS
        sample_list=[]

        for b in range(CatsBessy.NO_OF_BASKETS):
            for s in range(Basket.NO_OF_SAMPLES_PER_PUCK):
                sample_list.append(("", b+1, s+1, 1, Pin.STD_HOLDERLENGTH)) 
        
        for b in range(CatsBessy.NO_OF_BASKETS):            
            datamatrix = basket_list[b][0]
            if (len(datamatrix)==0):
                datamatrix=None
            flags=basket_list[b][1]
            present = self._basketChannels[b].getValue()
            scanned = False
            basket=self.getComponents()[b]
            basket._setInfo(present,datamatrix,scanned)

        for s in sample_list:
            sample = self.getComponentByAddress(Pin.getSampleAddress(s[1], s[2]))

            datamatrix = s[0]
            if (len(datamatrix)==0):    datamatrix=None
            flags = s[3]
            present = True
            present = sample.getContainer().isPresent()
            if present:
                datamatrix = '0000000000'   
            scanned = False
            loaded = False 
            has_been_loaded = False

            sample._setInfo(present,datamatrix,scanned)
            sample._setLoaded(loaded,has_been_loaded)
            sample._setHolderLength(s[4])    

        self._updateSelection()
        self._updateState()               
        self._updateLoadedSample()
                    
    def _doChangeMode(self,mode):
        if mode==SampleChangerMode.Charging:
            print "self._executeServerTask(self._set_sample_charge, True)"
            #self._executeServerTask(self._set_sample_charge, True)                    
        elif mode==SampleChangerMode.Normal:
            print "self._executeServerTask(self._set_sample_charge, False)"
            #self._executeServerTask(self._set_sample_charge, False)
    
    def getSelectedComponent(self):
        return self.getComponents()[self._selected_basket-1]
    
    def _doSelect(self,component):
        print "CatsBessy._doSelect: ok"
        #import pdb; pdb.set_trace()
        if isinstance(component, Sample):
            selected_basket = self.getSelectedComponent()
            if (selected_basket is None) or (selected_basket != component.getContainer()):
                #self._executeServerTask(self._select_basket , component.getBasketNo())
                self._selected_basket = component.getBasketNo()
            #self._executeServerTask(self._select_sample, component.getIndex()+1)
            self._selected_sample = component.getIndex()+1
        elif isinstance(component, Container) and ( component.getType() == Basket.__TYPE__):
            #self._executeServerTask(self._select_basket, component.getIndex()+1)
            self._selected_basket = component.getIndex()+1
            
    def _doLoad(self,sample=None):
        print "CatsBessy._doLoad"
        import pdb; pdb.set_trace()
        selected=self.getSelectedSample()            
        if self.hasLoadedSample():
            if (sample is None) or (sample==self.getLoadedSample()):
                raise Exception("The sample " + str(self.getLoadedSample().getAddress()) + " is already loaded")
            lid = ((self._selected_basket - 1) / 3) + 1
            sample = (((self._selected_basket - 1) % 3) * 10) + self._selected_sample
            argin = ["2", str(lid), str(sample), "0", "0", "0", "0", "0"]
            self._executeServerTask(self._chained_load, argin)
        else:
            if (sample is None):
                if (selected == None):
                    raise Exception("No sample selected")
                else:
                    sample=selected
            elif (sample is not None) and (sample!=selected):
                self._doSelect(sample)                
            #self._executeServerTask(self._load,sample.getHolderLength())
            #import pdb; pdb.set_trace()
            lid = ((self._selected_basket - 1) / 3) + 1
            sample = (((self._selected_basket - 1) % 3) * 10) + self._selected_sample
            argin = ["2", str(lid), str(sample), "0", "0", "0", "0", "0"]
            self._executeServerTask(self._load, argin)
            

    def _doUnload(self,sample_slot=None):
        print "CatsBessy._doUnload"
        if (sample_slot is not None):
            self._doSelect(sample_slot)
        argin = ["2", "0", "0", "0", "0"]
        self._executeServerTask(self._unload, argin)

    def _doReset(self):
        print "CatsBessy._doReset"
        self._executeServerTask(self._reset)

    def clearBasketInfo(self, basket):
	self._reset_basket_info(basket)

    #########################           PRIVATE           #########################        
    def _updateOperationMode(self, value):
        pass

    def _executeServerTask(self, method, *args):
        self._waitDeviceReady(3.0)
        task_id = method(*args)
        ret=None
        if task_id is None: #Reset
            while self._isDeviceBusy():
                gevent.sleep(0.1)
        else:
            while str(self._is_task_running(task_id)).lower() == 'true': 
                gevent.sleep(0.1)            
            try:
                ret = self._check_task_result(task_id)                
            except Exception,err:
                raise 
        return ret

    def _updateState(self):
        try:
          state = self._readState()
        except:
          state = SampleChangerState.Unknown
        if state == SampleChangerState.Moving and self._isDeviceBusy(self.getState()):
            return          
        self._setState(state)
       
    def _readState(self):
        state = self._state.getValue()
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
        #import pdb; pdb.set_trace()
        basket=None
        sample=None
        try:
          basket_no = self._selected_basket
          if basket_no is not None and basket_no>0 and basket_no <=CatsBessy.NO_OF_BASKETS:
            basket = self.getComponentByAddress(Basket.getBasketAddress(basket_no))
            sample_no = self._selected_sample
            if sample_no is not None and sample_no>0 and sample_no <=Basket.NO_OF_SAMPLES_PER_PUCK:
                sample = self.getComponentByAddress(Pin.getSampleAddress(basket_no, sample_no))            
        except:
          pass
        self._setSelectedComponent(basket)
        self._setSelectedSample(sample)

    def _updateLoadedSample(self):
        #import pdb; pdb.set_trace()
        loadedSampleLid = self._lidSampleOnDiff.getValue()
        loadedSampleNum = self._numSampleOnDiff.getValue()
        if loadedSampleLid != -1 or loadedSampleNum != -1:
            lidBase = (loadedSampleLid - 1) * 3
            lidOffset = ((loadedSampleNum - 1) / 10) + 1
            samplePos = ((loadedSampleNum - 1) % 10) + 1
            basket = lidBase + lidOffset
        else:
            basket = None
            samplePos = None
 
        if basket is not None and samplePos is not None:
            sample = self.getComponentByAddress(Pin.getSampleAddress(basket, samplePos))

            datamatrix = str(self._barcode.getValue())
            if (len(datamatrix)==0):    
                datamatrix = '0000000000'   
                scanned = False
            else:
                scanned = True
            loaded = True
            has_been_loaded = True

            sample._setInfo(True,datamatrix,scanned)
            sample._setLoaded(loaded,has_been_loaded)
