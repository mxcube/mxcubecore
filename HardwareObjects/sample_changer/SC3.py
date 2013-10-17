from GenericSampleChanger import *

import xml.sax
from xml.sax import SAXParseException
from xml.sax.handler import ContentHandler
import PyTango
import string


class Pin(Sample):        
    def __init__(self,basket,basket_no,sample_no):
        super(Pin, self).__init__(basket, Pin._getSampleAddress(basket_no,sample_no), True)
        self._setHolderLength(22.0)

    def getBasketNo(self):
        return self.getContainer().getIndex()+1

    def getVialNo(self):
        return self.getIndex()+1

    @staticmethod
    def _getSampleAddress(basket_number, sample_number):
        return str(basket_number) + ":" + "%02d" % (sample_number)


class Basket(Container):
    __TYPE__ = "Puck"    
    def __init__(self,container,number):
        super(Basket, self).__init__(self.__TYPE__,container,Basket._getBasketAddress(number),True)
        for i in range(10):
            slot = Pin(self,number,i+1)
            self._addComponent(slot)
                            
    @staticmethod
    def _getBasketAddress(basket_number):
        return str(basket_number)
            
            
class XMLDataMatrixReadingHandler(ContentHandler):
    def __init__(self):
        ContentHandler.__init__(self)
        self.dataMatrixList = []
        self.basketDataMatrixList = [('',4)] *5
        self.dataMatrix = ''
        self.basketLocation = -1
        self.sampleLocation = -1
        self.flag = 0
        self.holder_length=22.0

    def startElement(self, name, attrs):
        self.addBasketLocation = name == "BasketLocation"
        self.addSampleLocation = name == "Location"
        self.addDataMatrix = name == "DataMatrix"
        self.addFlag = name in ("SampleFlag","BasketFlag")
        self.addHolderLength = name == "HolderLength"        

    def characters(self, content):
        if self.addDataMatrix:          self.dataMatrix = str(content)
        elif self.addBasketLocation:    self.basketLocation = int(content)
        elif self.addSampleLocation:    self.sampleLocation = int(content)
        elif self.addFlag:              self.flag = int(content)
        elif self.addHolderLength:      self.holder_length =  float(content)

    def endElement(self, name):
        if name == "Sample":
            self.dataMatrixList.append((self.dataMatrix,self.basketLocation,self.sampleLocation,self.flag,self.holder_length))
            self.dataMatrix = ''
            self.basketLocation = -1
            self.sampleLocation = -1
            self.flag = 0
            self.holder_length=22.0
        elif name == "Basket":
            if len(self.dataMatrix) > 0:
                self.basketDataMatrixList[self.sampleLocation-1]=(self.dataMatrix,self.flag)
            self.dataMatrix = ''
            self.basketLocation = -1
            self.sampleLocation = -1
            self.flag = 0
            self.holder_length=22.0
        elif name == "BasketLocation":              self.addBasketLocation = None
        elif name == "Location":                    self.addSampleLocation = None
        elif name == "DataMatrix":                  self.addDataMatrix = None        
        elif name in ("SampleFlag","BasketFlag"):   self.addFlag = None
        elif name == "HolderLength":                self.addHolderLength = None
            
    
class SC3(SampleChanger):
    __TYPE__ = "SC3"    

    """
    Concrete implementation of SC3 Sample Changer
    """    
    def __init__(self, *args, **kwargs):
        super(SC3, self).__init__(self.__TYPE__,True, *args, **kwargs)
        for i in range(5):
            basket = Basket(self,i+1)
            self._addComponent(basket)
            
    def init(self):                 
        self._state = self.addChannel({"type":self.channel_type, "name":self.channel_state}, self.channel_state)        
        self._selected_basket = self.addChannel({"type":self.channel_type, "name":self.channel_selected_basket}, self.channel_selected_basket)
        self._selected_sample = self.addChannel({"type":self.channel_type, "name":self.channel_selected_sample}, self.channel_selected_sample)
        
        self._abort = self.addCommand({"type":self.channel_type, "name":self.command_abort}, self.command_abort)
        self._getInfo = self.addCommand({"type":self.channel_type, "name":self.command_info}, self.command_info)
        self._is_task_running = self.addCommand({"type":self.channel_type, "name":self.command_is_task_running}, self.command_is_task_running)
        self._check_task_result = self.addCommand({"type":self.channel_type, "name":self.command_check_task_result}, self.command_check_task_result)
        self._load = self.addCommand({"type":self.channel_type, "name":self.command_load}, self.command_load)
        self._unload = self.addCommand({"type":self.channel_type, "name":self.command_unload}, self.command_unload)
        self._chained_load = self.addCommand({"type":self.channel_type, "name":self.command_chained_load}, self.command_chained_load)
        self._set_sample_charge = self.addCommand({"type":self.channel_type, "name":self.command_set_sample_charge}, self.command_set_sample_charge)        
        self._scan_basket = self.addCommand({"type":self.channel_type, "name":self.command_scan_basket}, self.command_scan_basket)
        self._scan_samples = self.addCommand({"type":self.channel_type, "name":self.command_scan_samples}, self.command_scan_samples)
        self._select_sample = self.addCommand({"type":self.channel_type, "name":self.command_select_sample}, self.command_select_sample)
        self._select_basket = self.addCommand({"type":self.channel_type, "name":self.command_select_basket}, self.command_select_basket)
        self._reset = self.addCommand({"type":self.channel_type, "name":self.command_reset}, self.command_reset)
                
        SampleChanger.init(self)   
            
            
    def getSampleProperties(self):
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)
            
        

#########################           TASKS           #########################
    def _doAbort(self):
        self._abort()            
            

    def _doUpdateInfo(self):       
        try:
            sxml = self._getInfo()
            handler = XMLDataMatrixReadingHandler()        
            sxml=sxml.replace(' encoding="utf-16"','')
            xml.sax.parseString(sxml, handler)
            sample_list = handler.dataMatrixList
            basket_list = handler.basketDataMatrixList
        except Exception,ex:
            logging.error("Error retrieving sample info: %s" % str(ex))
            basket_list= [('',4)] * 5
            sample_list=[]
            for b in range(5):
                for s in range(10):
                    sample_list.append(("",b+1,s+1,1,22.0)) 
        
        for b in range(5):            
            datamatrix = basket_list[b][0]
            if (len(datamatrix)==0):    datamatrix=None
            flags=basket_list[b][1]
            present =   (flags & 3) != 0
            scanned =   (flags& 8) != 0
            basket=self.getComponents()[b]
            basket._setInfo(present,datamatrix,scanned)
        for s in sample_list:
            datamatrix = s[0]
            if (len(datamatrix)==0):    datamatrix=None
            flags = s[3]
            present =   (flags & 6) != 0
            scanned =   present
            loaded =   (flags & 8) != 0
            has_been_loaded =   (flags & 16) != 0
            sample = self.getComponentByAddress(Pin._getSampleAddress(s[1], s[2]))
            sample._setInfo(present,datamatrix,scanned)     
            sample._setLoaded(loaded,has_been_loaded)
            sample._setHolderLength(s[4])            
        self._updateSelection()
        self._updateState()               
                    

    def _doChangeMode(self,mode):
        if mode==SampleChangerMode.Charging:
            self._executeServerTask(self._set_sample_charge, True)                    
        elif mode==SampleChangerMode.Normal:
            self._executeServerTask(self._set_sample_charge, False)
    
    def _doScan(self,component, recursive):
        selected_basket = self.getSelectedComponent()
        if isinstance(component, Sample):            
            if (selected_basket is None) or (selected_basket != component.getContainer()):
                self._doSelect(component)            
            self._executeServerTask(self._scan_samples, [component.getIndex()+1,])
            
        elif isinstance(component, Container) and ( component.getType() == Basket.__TYPE__):
            if recursive:
                self._executeServerTask(self._scan_basket, (component.getIndex()+1))                
            else:
                if (selected_basket is None) or (selected_basket != component):
                    self._doSelect(component)            
                self._executeServerTask(self._scan_samples, (0,))                
        elif isinstance(component, Container) and ( component.getType() == SC3.__TYPE__):
            for basket in self.getComponents():
                self._doScan(basket, True)
    
    def _doSelect(self,component):
        if isinstance(component, Sample):
            selected_basket = self.getSelectedComponent()
            if (selected_basket is None) or (selected_basket != component.getContainer()):
                self._executeServerTask(self._select_basket , component.getBasketNo())
            self._executeServerTask(self._select_sample, component.getIndex()+1)
        elif isinstance(component, Container) and ( component.getType() == Basket.__TYPE__):
            self._executeServerTask(self._select_basket, component.getIndex()+1)
            
    def _doLoad(self,sample=None):
        selected=self.getSelectedSample()            
        if self.hasLoadedSample():
            if (sample is None) or (sample==self.getLoadedSample()):
                raise Exception("The sample " + str(self.getLoadedSample().getAddress()) + " is already loaded")
            self._executeServerTask(self._chained_load,[sample.getBasketNo(), sample.getVialNo(), sample.getHolderLength()])
        else:
            if (sample is None):
                if (selected == None):
                    raise Exception("No sample selected")
                else:
                    sample=selected
            elif (sample is not None) and (sample!=selected):
                self._doSelect(sample)                
            self._executeServerTask(self._load,sample.getHolderLength())

    def _doUnload(self,sample_slot=None):
        if (sample_slot is not None):
            self._doSelect(sample_slot)
        self._executeServerTask(self._unload)

    def _doReset(self):
        self._executeServerTask(self._reset)
        
#########################           PRIVATE           #########################        
    def _executeServerTask(self, method, *args):
        self._waitDeviceReady(3.0)
        task_id = method(*args)
        ret=None
        if task_id is None: #Reset
            while self._isDeviceBusy():
                gevent.sleep(0.1)
        else:
            while self._is_task_running(task_id): #If sync end with task_id must sync start with state        
            #while self._isDeviceBusy():  
                gevent.sleep(0.1)            
            try:
                ret = self._check_task_result(task_id)                
            except PyTango.DevFailed, traceback:
                task_error = traceback[0]
                error_msg = str(task_error.desc).replace("Task error: ", "")
                raise Exception(error_msg) 
            except Exception,err:
                raise Exception(str(err)) 
            #self._updateState()
        return ret

    def _updateState(self):
        state = self._readState()
                     
        if state is None: 
            self._setState(SampleChangerState.Unknown)
        else:
            if state == PyTango.DevState.ALARM: self._setState(SampleChangerState.Alarm)
            if state == PyTango.DevState.FAULT: self._setState(SampleChangerState.Fault)                        
            if not self.isExecutingTask():
                if state == PyTango.DevState.MOVING: self._setState(SampleChangerState.Charging)
                if state == PyTango.DevState.STANDBY:   self._setState(SampleChangerState.Ready)
                if state == PyTango.DevState.RUNNING:   self._setState(SampleChangerState.Moving)                        
                if state == PyTango.DevState.INIT: self._setState(SampleChangerState.Initializing)
                    

    def _readState(self):
        return  self._state.getValue()
         
    def _isDeviceBusy(self):
        state = self._readState()
        return state in (PyTango.DevState.RUNNING, PyTango.DevState.INIT)              

    def _isDeviceReady(self):
        state = self._readState()
        return state in (PyTango.DevState.STANDBY, PyTango.DevState.MOVING)              

    def _waitDeviceReady(self,timeout=-1):
        start=time.clock()
        while not self._isDeviceReady():
            if timeout>0:
                if (time.clock() - start) > timeout:
                    raise Exception("Timeout waiting device ready")
            gevent.sleep(0.01)
            
    def _updateSelection(self):    
        basket_no = self._selected_basket.getValue()                    
        changed=False
        basket=None
        sample=None
        if basket_no is not None and basket_no>0 and basket_no <=5:
            basket = self.getComponentByAddress(Basket._getBasketAddress(basket_no))
            sample_no = self._selected_sample.getValue()
            if sample_no is not None and sample_no>0 and sample_no <=10:
                sample = self.getComponentByAddress(Pin._getSampleAddress(basket_no, sample_no))            
        self._setSelectedComponent(basket)
        self._setSelectedSample(sample)
                
                            
                
        
if __name__ == "__main__":    
    def onStateChanged(state,former):
        print "State Change:  " + str(former) + " => " + str(state)
    def onInfoChanged():
        print "Info Changed"
        
    sc = SC3()
    sc.channel_type="tango"
    sc.tangoname="tango://pc445.embl.fr:17100/EMBL/MXSC/1#dbase=no"  
    sc.channel_state="State"
    sc.channel_selected_basket="SelectedBasketLocation"
    sc.channel_selected_sample="SelectedSampleLocation"
    sc.command_abort="abort"
    sc.command_info="GetInformationAsXML"
    sc.command_is_task_running="isTaskRunning"  
    sc.command_check_task_result="checkTaskResult"
    sc.command_load="LoadSample"
    sc.command_unload="UnLoadSample"
    sc.command_chained_load="ChainedLoadSample"
    sc.command_set_sample_charge="SetBasketTransferMode"
    sc.command_scan_basket="ScanBasketForDatamatrix"
    sc.command_scan_samples="ScanSamplesForDatamatrix"
    sc.command_select_sample="MoveSampleLocation"
    sc.command_select_basket="MoveBasketLocation"
    sc.command_reset="Reset"

    
    
    sc.connect(sc, sc.__STATE_CHANGED_EVENT__, onStateChanged)
    sc.connect(sc, sc.__INFO_CHANGED_EVENT__, onInfoChanged)
    sc.init()

    while(True):
        try:
            sc.abort()               
            sc.reset()
            sc.changeMode(SampleChangerMode.Normal)
            sc.select('1', wait=True) # or else sc.select(sc.getComponentByAddress('1'), wait=True)
            sc.unload(wait=True)
            sc.load(None, wait=True)
            sc.load('3:04', wait=True)
            sc.unload('4:01',wait=True)
            sc.scan('1:01', wait=True)        
            sc.scan('1:02', wait=True)
            sc.scan('1:03', wait=True)
            sc.scan('2:02', wait=True)
            sc.scan('3', wait=True)
            sc.scan('4', recursive=True, wait=True)
        except:
            print sys.exc_info()[1]      
            
    
