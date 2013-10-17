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
            
    
class SC3b(SampleChanger):
    __TYPE__ = "SC3b"    

    """
    Concrete implementation of SC3 Sample Changer
    """    
    def __init__(self, *args, **kwargs):
        super(SC3b, self).__init__(self.__TYPE__,True, *args, **kwargs)
        for i in range(5):
            basket = Basket(self,i+1)
            self._addComponent(basket)
            
    def getSampleProperties(self):
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)
            
        

#########################           TASKS           #########################
    def _doAbort(self):
        self._callMethod("abort")            
            

    def _doUpdateInfo(self):       
        try:
            sxml = self._callMethod("GetInformationAsXML")
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
            self._executeServerTask("SetBasketTransferMode", True)
        elif mode==SampleChangerMode.Normal:
            self._executeServerTask("SetBasketTransferMode", False)
    
    def _doScan(self,component, recursive):
        selected_basket = self.getSelectedComponent()
        if isinstance(component, Sample):            
            if (selected_basket is None) or (selected_basket != component.getContainer()):
                self._doSelect(component)            
            self._executeServerTask("ScanSamplesForDatamatrix", [component.getIndex()+1,])
        elif isinstance(component, Container) and ( component.getType() == Basket.__TYPE__):
            if recursive:
                self._executeServerTask("ScanBasketForDatamatrix", (component.getIndex()+1))
            else:
                if (selected_basket is None) or (selected_basket != component):
                    self._doSelect(component)            
                self._executeServerTask("ScanSamplesForDatamatrix", (0,)) 
        elif isinstance(component, Container) and ( component.getType() == SC3b.__TYPE__):
            for basket in self.getComponents():
                self._doScan(basket, True)
    
    def _doSelect(self,component):
        if isinstance(component, Sample):
            selected_basket = self.getSelectedComponent()
            if (selected_basket is None) or (selected_basket != component.getContainer()):
                self._executeServerTask("MoveBasketLocation", component.getBasketNo()) 
            self._executeServerTask("MoveSampleLocation", component.getIndex()+1)
        elif isinstance(component, Container) and ( component.getType() == Basket.__TYPE__):
            self._executeServerTask("MoveBasketLocation", component.getIndex()+1)

    def _doLoad(self,sample=None):
        selected=self.getSelectedSample()            
        if self.hasLoadedSample():
            if (sample is None) or (sample==self.getLoadedSample()):
                raise Exception("The sample " + str(self.getLoadedSample().getAddress()) + " is already loaded")
            self._executeServerTask("ChainedLoadSample",[sample.getBasketNo(), sample.getVialNo(), sample.getHolderLength()])
        else:
            if (sample is None):
                if (selected == None):
                    raise Exception("No sample selected")
                else:
                    sample=selected
            elif (sample is not None) and (sample!=selected):
                self._doSelect(sample)                
            self._executeServerTask("LoadSample",sample.getHolderLength())

    def _doUnload(self,sample_slot=None):
        if (sample_slot is not None):
            self._doSelect(sample_slot)
        self._executeServerTask("UnLoadSample")

    def _doReset(self):
        return self._executeServerTask("Reset")
        
        
#########################           PRIVATE           #########################        
    def _getDevice(self):
        tango_name=self.getProperty("tangoname")
        if tango_name is None:
            tango_name = "tango://pc445.embl.fr:17100/EMBL/MXSC/1#dbase=no"
        return PyTango.DeviceProxy(string.strip(tango_name))
        
    def _executeServerTask(self, task_name, *args):
        self._waitDeviceReady(3.0)
        device = self._getDevice()
        method = getattr(device, task_name)
        task_id = method(*args)
        ret=None
        if task_id is None: #Reset
            while self._isDeviceBusy():
                gevent.sleep(0.1)
        else:
            while device.isTaskRunning(task_id): #If sync end with task_id must sync start with state    
            #while self._isDeviceBusy():  
                gevent.sleep(0.1)            
            try:
                ret = device.checkTaskResult(task_id)
            except PyTango.DevFailed, traceback:
                task_error = traceback[0]
                error_msg = str(task_error.desc).replace("Task error: ", "")
                raise Exception(error_msg) 
            except Exception,err:
                raise Exception(str(err)) 
            #self._updateState()
        return ret

    def _readAttribute(self,attribute):        
        try:
            device = self._getDevice()
            return device.read_attribute(attribute).value
        except:
            return None        
        
    def _callMethod(self,method):
        device = self._getDevice()
        return device.command_inout(method)
                
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
        return self._readAttribute("State")
         
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
        basket_no = self._readAttribute("SelectedBasketLocation")                    
        changed=False
        basket=None
        sample=None
        if basket_no is not None and basket_no>0 and basket_no <=5:
            basket = self.getComponentByAddress(Basket._getBasketAddress(basket_no))
            sample_no = self._readAttribute("SelectedSampleLocation")
            if sample_no is not None and sample_no>0 and sample_no <=10:
                sample = self.getComponentByAddress(Pin._getSampleAddress(basket_no, sample_no))            
        self._setSelectedComponent(basket)
        self._setSelectedSample(sample)
                
                            
                
        
if __name__ == "__main__":    
    def onStateChanged(state,former):
        print "State Change:  " + str(former) + " => " + str(state)
    def onInfoChanged():
        print "Info Changed"
        
    sc = SC3b()    
    sc.connect(sc, sc.__STATE_CHANGED_EVENT__, onStateChanged)
    sc.connect(sc, sc.__INFO_CHANGED_EVENT__, onInfoChanged)
    sc.init()

    
    """
    print "Before"
    
    sample = sc.getSampleList()[0]
    sample._setHolderLength(22.0)
    sc.updateInfo()
    print "After"
    """        
    while(True):
        try:
            sc.abort()               
            sc.reset()
            sc.changeMode(SampleChangerMode.Normal)
            #sc.changeMode(SampleChangerMode.Charging)
            
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
            
    
