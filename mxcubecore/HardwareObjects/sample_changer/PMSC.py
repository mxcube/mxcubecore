from GenericSampleChanger import *
import Crims

import PyTango

def char_range(c1, c2):
    for c in xrange(ord(c1), ord(c2)+1): yield chr(c)


class Xtal(Sample):
    __NAME_PROPERTY__ = "Name"
    __LOGIN_PROPERTY__ = "Login"
    
    def __init__(self,drop, index):
        super(Xtal, self).__init__(drop, Xtal._getXtalAddress(drop, index), False)
        self._setImageX(None)
        self._setImageY(None)
        self._setImageURL(None)
        self._setName(None)
        self._setLogin(None)        
        self._setInfoURL(None)        

    def _setName(self,value):
        self._setProperty(self.__NAME_PROPERTY__,value)
    
    def getName(self):
        return self.getProperty(self.__NAME_PROPERTY__)

    def _setLogin(self,value):
        self._setProperty(self.__LOGIN_PROPERTY__,value)
    
    def getLogin(self):
        return self.getProperty(self.__LOGIN_PROPERTY__)

    def getDrop(self):
        return self.getContainer()

    def getCell(self):
        return self.getDrop().getCell()

    @staticmethod
    def _getXtalAddress(well, index):
        return str(well.getAddress()) + "-" + str(index)    

class Drop(Container):
    __TYPE__ = "Drop" 
    def __init__(self,cell, well_no):
        super(Drop, self).__init__(self.__TYPE__,cell, Drop._getWellAddress(cell, well_no), False)
        
    @staticmethod
    def _getWellAddress(cell, well_no):
        return str(cell.getAddress()) + ":" + str(well_no)    

    def getCell(self):
        return self.getContainer()

    def getWellNo(self):
        return self.getIndex()+1

class Cell(Container):
    __TYPE__ = "Cell"    
    def __init__(self,container,row,col,wells):
        super(Cell, self).__init__(self.__TYPE__,container,Cell._getCellAddress(row,col),False)
        self._row=row
        self._col=col
        self._wells=wells
        for i in range(wells):
            well = Drop(self,i+1)
            self._addComponent(well)
        self._transient=True
    
    def getRow(self):
        return self._row

    def getRowIndex(self):
        return ord(self._row.upper()) - ord('A')

    def getCol(self):
        return self._col

    def getWellsNo(self):
        return self._wells

    @staticmethod
    def _getCellAddress(row,col):
        return row + str(col) 
                            
            
    
class PMSC(SampleChanger):
    __TYPE__ = "PlateSupport"    

    """
    Concrete implementation of SC3 Sample Changer
    """    
    def __init__(self, *args, **kwargs):
        super(PMSC, self).__init__(self.__TYPE__,True, *args, **kwargs)
        self._initializeData()    
        self.current_phase=None
        self._setTransient(True)  
    
    def init(self):                 
        #exporter_address is propagated to chanels??? Id so why not type????        
        #self._state = self.addChannel({"type":self.channel_type, "name":self.channel_state , 'polling':200}, self.channel_state)   
        self._state = self.addChannel({"type":self.channel_type, "name":self.channel_state}, self.channel_state)
        self._phase = self.addChannel({"type":self.channel_type, "name":self.channel_phase , }, self.channel_phase)   
        self._taskInfo = self.addChannel({"type":self.channel_type, "name":self.channel_task_info , }, self.channel_task_info)   

        self._state.connectSignal("update", self._onStateChanged)
        self._set_phase = self.addCommand({"type":self.channel_type, "name":self.command_set_phase }, self.command_set_phase)
        self._select_sample = self.addCommand ({"type":self.channel_type, "name": self.command_select_sample }, self.command_select_sample)
        self._abort = self.addCommand({"type":self.channel_type, "name":self.command_abort }, self.command_abort)
        self._reset = self.addCommand({"type":self.channel_type, "name":self.command_reset }, self.command_reset)
        if self.type==CHANNEL_TANGO:
            self._image = self.addCommand({"type":self.channel_type, "name":"get"+self.channel_image ,"timeout":5}, "get"+self.channel_image)        
        else:
            self._image = self.addChannel({"type":self.channel_type, "name":self.channel_image ,"timeout":5}, self.channel_image)
        SampleChanger.init(self)   
                
        #self.setToken("JZ005320")
        #self.scan()    

    def getSampleProperties(self):
        return (Xtal.__LOGIN_PROPERTY__ , Xtal.__NAME_PROPERTY__,)

#########################           EVENTS           #########################    
    def _onStateChanged(self,state):
        if state is None: 
            self._setState(SampleChangerState.Unknown)
        else:
            if   state == "Alarm": self._setState(SampleChangerState.Alarm)
            elif state == "Fault": self._setState(SampleChangerState.Fault)                                    
            elif state == "Moving" or state == "Running": self._setState(SampleChangerState.Moving)
            elif state == "Ready":
                if self.current_phase == "Transfer":    self._setState(SampleChangerState.Charging)
                elif self.current_phase == "Centring":  self._setState(SampleChangerState.Ready)
                else:                                   self._setState(SampleChangerState.StandBy)
            elif state == "Initializing": self._setState(SampleChangerState.Initializing)        
        

#########################           TASKS           #########################
    def _doAbort(self):
        self._abort()
        
    def _doUpdateInfo(self):
        self._updateState()        
                         
    def _doChangeMode(self,mode):
        if mode==SampleChangerMode.Charging:
            self._set_phase("Transfer")
        elif mode==SampleChangerMode.Normal:
            self._set_phase("Centring")
    
    def _doScan(self,component, recursive):
        if not isinstance(component, PMSC):
            raise Exception ("Not supported")
        self._initializeData()
        if self.getToken() is None:
            raise Exception ("No plate barcode defined")
        self._loadData(self.getToken())        
    
    def _doSelect(self,component):    
        if isinstance(component, Xtal):                             
            self._select_sample(component.getCell().getRowIndex(),component.getCell().getCol()-1,component.getDrop().getWellNo()-1)
            self._setSelectedSample(component)
            component.getContainer()._setSelected(True)
            component.getContainer().getContainer()._setSelected(True)
        elif isinstance(component, Drop):                             
            self._select_sample(component.getCell().getRowIndex(),component.getCell().getCol()-1,component.getWellNo()-1)
            component._setSelected(True)
            component.getContainer().getContainer()._setSelected(True)
        elif isinstance(component, Cell):
            self._select_sample(component.getRowIndex(),component.getCol()-1,0)
            component._setSelected(True)
        else:
            raise Exception ("Invalid selection")
        self._resetLoadedSample()
        self._waitDeviceReady()   
        
    def _doLoad(self,sample=None):
        selected=self.getSelectedSample()            
        if (sample is None):
            sample = self.getSelectedSample()
        if (sample is not None):
            if (sample!=selected):         
                self._doSelect(sample)  
            self._setLoadedSample(sample)              
        #TODO: Add pre-positioning and image matching
        

    def _doUnload(self,sample_slot=None):
        self._resetLoadedSample()
    
    def _doReset(self):
        self._reset(False)    
        self._waitDeviceReady()   
        
#########################           PRIVATE           #########################        
    def _initializeData(self):        
        self._setInfo(False,None,False)
        self._clearComponents()
        for row in char_range('A', 'H'):
            for col in range(12):
                cell = Cell(self,row,col+1,0)
                self._addComponent(cell)    
    
    def _loadData(self,barcode):
        pp= Crims.getProcessingPlan(barcode)
        self._setInfo(True,pp.Plate.Barcode,True)  
        wells=1
        for x in pp.Plate.Xtal:
            if x.Shelf>1:
                wells=x.Shelf

        self._clearComponents()
        for row in char_range('A', 'H'):
            for col in range(12):
                cell = Cell(self,row,col+1,wells)
                self._addComponent(cell)            
                
        for x in pp.Plate.Xtal:
            cell = self.getComponentByAddress(Cell._getCellAddress(x.Row, x.Column))
            cell._setInfo(True,"",True)
            drop = self.getComponentByAddress(Drop._getWellAddress(cell,x.Shelf))
            drop._setInfo(True,"",True)
            xtal = Xtal(drop,drop.getNumberOfComponents())
            xtal._setInfo(True,x.PinID,True)
            xtal._setImageURL(x.IMG_URL)                    
            xtal._setImageX(x.offsetX)
            xtal._setImageY(x.offsetY)
            xtal._setLogin(x.Login)      
            xtal._setName(x.Sample)            
            xtal._setInfoURL(x.SUMMARY_URL) 
            drop._addComponent(xtal)  
         
    def _isDeviceBusy(self):
        return  self.getState() in (SampleChangerState.Moving, SampleChangerState.Initializing)              

    def _isDeviceReady(self):
        return self.getState()  in (SampleChangerState.Ready, SampleChangerState.Charging)     
    
    def _waitDeviceReady(self,timeout=-1):
        start=time.clock()
        while not self._isDeviceReady():
            if timeout>0:
                if (time.clock() - start) > timeout:
                    raise Exception("Timeout waiting device ready")
            gevent.sleep(0.01)
            
                
    def _updateState(self):
        #logging.getLogger("user_level_log").info("****  " + str(self._state.getValue()))        
        state =  self._state.getValue()
        if (state == "Ready") or (self.current_phase is None):
            self.current_phase =  self._phase.getValue()
        self._onStateChanged(state)
        return state    
    
    def _readImage(self):
        if self.type==CHANNEL_TANGO:
            return self._image()
        else:
            return self._image.getValue()
        
    def _readTaskInfo(self):
        return self._taskInfo.getValue()
    

                
CHANNEL_TANGO="tango"
CHANNEL_EXPORTER="exporter"
        
if __name__ == "__main__":    
    def onStateChanged(state,former):
        print "State Change:  " + str(former) + " => " + str(state)
    def onInfoChanged():
        print "Info Changed"
        
    sc = PMSC()    
    sc.connect(sc, sc.STATE_CHANGED_EVENT, onStateChanged)
    sc.connect(sc, sc.INFO_CHANGED_EVENT, onInfoChanged)
    
    #<username>PMSC</username>
  
    sc.channel_type=CHANNEL_EXPORTER
    sc.exporter_address="pc445.embl.fr:9001"
    sc.tangoname="tango://pc445.embl.fr:18001/embl/jaf/1#dbase=no"  
    sc.channel_state="State"
    sc.channel_image="ImageJPG"
    sc.channel_phase="CurrentPhase"
    sc.channel_task_info="LastTaskInfo"  

    sc.command_scan="startScan"
    sc.command_set_phase="startSetPhase"
    sc.command_abort="abort"
    sc.command_reset="restart"
    sc.command_select_sample="startMovePlateToShelf"
    
    sc.setToken("JZ005209")
    
    sc.init()

    
    """
    print "Before"
    
    sample = sc.getSampleList()[0]
    sample._setHolderLength(22.0)
    sc.updateInfo()
    print "After"
    """        
    #while(True):
    try:
        #gevent.sleep(50)
        sc.abort()               
        sc.reset()
        sc.changeMode(SampleChangerMode.Normal)
        #sc.select(sc.getComponentByAddress('C4'), wait=True)
        sc.scan()
        sc.select(sc.getComponentByAddress('C12:1-0'), wait=True)
        #sc.select(sc.getComponentByAddress('C12:1'), wait=True)
        #sc.select(sc.getComponentByAddress('C12'), wait=True)
    except:
        print sys.exc_info()[1]      
        

        
