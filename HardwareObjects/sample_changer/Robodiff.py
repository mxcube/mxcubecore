from .GenericSampleChanger import *
import gevent

class Pin(Sample):        
    def __init__(self,basket,cell_no,basket_no,sample_no):
        super(Pin, self).__init__(basket, Pin.getSampleAddress(cell_no,basket_no,sample_no), True)
        self._setHolderLength(22.0)

    def getBasketNo(self):
        return self.getContainer().getIndex()+1

    def getVialNo(self):
        return self.getIndex()+1

    def getCellNo(self):
        return self.getContainer().getContainer().getIndex()+1

    def getCell(self):
        return self.getContainer().getContainer()

    @staticmethod
    def getSampleAddress(cell_number,basket_number, sample_number):
        return str(cell_number)+":"+str(basket_number) + ":" + "%02d" % (sample_number)


class Basket(Container):
    __TYPE__ = "Puck"    
    def __init__(self,container,cell_no,basket_no):
        super(Basket, self).__init__(self.__TYPE__,container,Basket.getBasketAddress(cell_no,basket_no),True)
        for i in range(10):
            slot = Pin(self,cell_no,basket_no,i+1)
            self._addComponent(slot)
                            
    @staticmethod
    def getBasketAddress(cell_number,basket_number):
        return str(cell_number)+":"+str(basket_number)

    def getCellNo(self):
        return self.getContainer().getIndex()+1

    def getCell(self):
        return self.getContainer()

    def clearInfo(self):
	self.getContainer()._reset_basket_info(self.getIndex()+1)
        self.getContainer()._triggerInfoChangedEvent()


class Cell(Container):
    __TYPE__ = "Cell"
    def __init__(self, container, number):
      super(Cell, self).__init__(self.__TYPE__,container,Cell.getCellAddress(number),True)
      for i in range(3):
        self._addComponent(Basket(self,number,i+1))
    @staticmethod
    def getCellAddress(cell_number):
      return str(cell_number)
    def _reset_basket_info(self, basket_no):
      pass
    def clearInfo(self):
      self.getContainer()._reset_cell_info(self.getIndex()+1)
      self.getContainer()._triggerInfoChangedEvent()
    def getCell(self):
      return self

class Robodiff(SampleChanger):
    __TYPE__ = "Robodiff"

    def __init__(self, *args, **kwargs):
        super(Robodiff, self).__init__(self.__TYPE__, True, *args, **kwargs)

        for i in range(8):
            cell = Cell(self, i+1)
            self._addComponent(cell)

    def init(self):
        controller = self.getObjectByRole("controller")
        self.dm_reader = getattr(controller, "dm_reader")
        self.dw = getattr(controller, "dw")
        self.robot = controller
        self.detector_translation = self.getObjectByRole("detector_translation")
        
        return SampleChanger.init(self)

    def getSampleProperties(self):
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)

    def _doChangeMode(self, *args, **kwargs):
        return

    def _doUpdateInfo(self):
        self._updateSelection()
        self._updateState()

    def _doScan(self, component, recursive=True, saved={"barcodes":None}):
        def read_barcodes():
            try:
              logging.info("Datamatrix reader: Scanning barcodes")
              barcodes = self.dm_reader.get_barcode()
            except:
              saved["barcodes"]=[[None]*11]*3
            else:
              saved["barcodes"]=barcodes
            logging.info("Scanning completed.")
        def get_barcodes():
            if None in saved.values():
                read_barcodes()
            return saved["barcodes"]
       
        selected_cell = self.getSelectedComponent()
        if (selected_cell is None) or (selected_cell != component.getCell()):
            self._doSelect(component)
            read_barcodes()  

        if isinstance(component, Sample):
            barcodes = get_barcodes()

            # read one sample dm
            sample_index = component.getIndex()
            basket_index = component.getContainer().getIndex()
            sample_dm = barcodes[basket_index][sample_index]
            sample_present_bool = self.dm_reader.sample_is_present(basket_index,sample_index)

            component._setInfo(sample_present_bool, sample_dm, True)
        elif isinstance(component, Container) and (component.getType() == Basket.__TYPE__):
            barcodes = get_barcodes()
            
            if recursive:
                # scan one basket dm
                for sample in component.getComponents():
                  self._doScan(sample)
            
            # get basket dm 
            basket_dm = ""
            basket_present_bool = any(barcodes[component.getIndex()])
            if basket_present_bool:
                basket_dm = barcodes[component.getIndex()][-1]
            component._setInfo(basket_present_bool, basket_dm, True)
        elif isinstance(component, Container) and (component.getType() == Cell.__TYPE__):
            for basket in component.getComponents():
                self._doScan(basket, True) 
        elif isinstance(component, Container) and (component.getType() == Robodiff.__TYPE__):
            for cell in self.getComponents():
              self._doScan(cell, True)
 
    def _doSelect(self, component):
        if isinstance(component, Cell):
          cell_pos = component.getIndex()
          self.dw.move(cell_pos+1)
          self._updateSelection()

    def _doLoad(self, sample=None):
        self._doSelect(sample.getCell())
        basket_index = sample.getBasketNo()-1
        vial_index = sample.getVialNo()
        sample_to_load = basket_index*10+vial_index
        # move detector to high software limit, without waiting end of move
        self.detector_translation.move(self.detector_translation.getLimits()[1])
        # now call load procedure
        self.robot.load_sample(sample_to_load)
        self._setLoadedSample(sample)

    def _doUnload(self, sample=None):
        loaded_sample = self.getLoadedSample()
        if loaded_sample is not None and loaded_sample != sample:
          raise RuntimeError("Can't unload another sample")
        basket_index = sample.getBasketNo()-1
        vial_index = sample.getVialNo()
        sample_to_unload = basket_index*10+vial_index
        self.robot.unload_sample(sample_to_unload)
        self._setLoadedSample(None)

    def _doAbort(self):
        return

    def _doReset(self):
        pass

    def clearBasketInfo(self, basket):
        return self._reset_basket_info(basket)

    def _reset_basket_info(self, basket):
        pass

    def clearCellInfo(self, cell):
        return self._reset_cell_info(cell)

    def _reset_cell_info(self, cell):
        pass

    def _updateState(self):
        try:
          state = self._readState()
        except:
          state = SampleChangerState.Unknown
        if state == SampleChangerState.Moving and self._isDeviceBusy(self.getState()):
            return          
        self._setState(state)
       
    def _readState(self):
        # should read state from robot
        state = self.robot.state() 
        state_converter = { "ALARM": SampleChangerState.Alarm,
                            "FAULT": SampleChangerState.Fault,
                            "MOVING": SampleChangerState.Moving,
                            "READY": SampleChangerState.Ready,
                            "LOADING": SampleChangerState.Charging }
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
        dw_pos = int(self.dw.position())-1
        for cell in self.getComponents():
          i = cell.getIndex()
          if dw_pos == i:
            self._setSelectedComponent(cell)
            break
        self._setSelectedSample(0)
