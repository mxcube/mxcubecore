from .GenericSampleChanger import *
from PyTango.gevent import DeviceProxy
import gevent
import cPickle
import base64
import logging

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
    def __init__(self,container,cell_no,basket_no, unipuck=False):
        super(Basket, self).__init__(self.__TYPE__,container,Basket.getBasketAddress(cell_no,basket_no),True)
        for i in range(16 if unipuck else 10):
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
        self._addComponent(Basket(self,number,i+1, unipuck=1-(number%2)))
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

class FlexHCD(SampleChanger):
    __TYPE__ = "HCD"

    def __init__(self, *args, **kwargs):
        super(FlexHCD, self).__init__(self.__TYPE__, True, *args, **kwargs)

        for i in range(8):
            cell = Cell(self, i+1)
            self._addComponent(cell)


    def init(self):
        self.robot = DeviceProxy(self.getProperty('tango_device'))
        self.controller = self.getObjectByRole("controller")
        self.prepareLoad = self.getCommandObject("moveToLoadingPosition")
        return SampleChanger.init(self)

    @task
    def prepare_load(self):
        if self.controller:
            self.controller.prepare_flex(load=True)
        else:
            self.prepareLoad()

    def prepareCentring(self):
        if self.controller:
            self.controller.prepare_flex(load=False)
        else:
            gevent.sleep(2)
            self.getCommandObject("unlockMinidiffMotors")(wait=True)
            self.getCommandObject("prepareCentring")(wait=True)

    def getSampleProperties(self):
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)

    def getBasketList(self):
        basket_list = []
        for cell in self.getComponents():
            for basket in cell.getComponents(): 
                if isinstance(basket, Basket):
                    basket_list.append(basket)
        return basket_list


    def _doChangeMode(self, *args, **kwargs):
        return

    def _doUpdateInfo(self):
        self._updateSelection()
        self._updateState()

    def _doScan(self, component, recursive=True, saved={"barcodes":None}):
        return
 
    def _execute_cmd(self, cmd, *args, **kwargs):
        timeout = kwargs.pop('timeout', None)
        if args:
            cmd_str = 'flex.%s(%s)' % (cmd, ",".join(map(repr, args)))
        else:
            cmd_str = 'flex.%s()' % cmd
        cmd_id = self.robot.eval(cmd_str)
        with gevent.Timeout(timeout, RuntimeError("Timeout while executing %s" % repr(cmd_str))):
          while True:
            if self.robot.is_finished(cmd_id):
              break 
            gevent.sleep(0.2)  
        res = self.robot.get_result(cmd_id)
        if res:
          res = cPickle.loads(base64.decodestring(res))
          if isinstance(res, Exception):
              raise res
          else:
              return res

    def _doSelect(self, component): 
        if isinstance(component, Cell):
          cell_pos = component.getIndex()+1
        elif isinstance(component, Basket) or isinstance(component, Pin):
          cell_pos = component.getCellNo()
        
        self._execute_cmd('moveDewar', cell_pos)
         
        self._updateSelection()

    @task
    def load_sample(self, holderLength, sample_id=None, sample_location=None, sampleIsLoadedCallback=None, failureCallback=None, prepareCentring=True):
        cell, basket, sample = sample_location
        sample = self.getComponentByAddress(Pin.getSampleAddress(cell, basket, sample))
        return self.load(sample)

    def chained_load(self, old_sample, sample):
        unload_load_task = gevent.spawn(self._execute_cmd, 'chainedUnldLd', [old_sample.getCellNo(), old_sample.getBasketNo(), old_sample.getVialNo()], [sample.getCellNo(), sample.getBasketNo(), sample.getVialNo()])

        gevent.sleep(15)
        while not unload_load_task.ready():
           if self._execute_cmd("get_robot_cache_variable", "SampleCentringReady") == "True":
              self._setLoadedSample(sample)
              return True
           gevent.sleep(1)

        logging.getLogger('HWR').info("unload load task done")
        for msg in self.get_robot_exceptions():
            logging.getLogger("HWR").error(msg)

        if not self._execute_cmd("pin_on_gonio"):
            logging.getLogger('HWR').info("reset loaded sample")
            self._resetLoadedSample()
        logging.getLogger('HWR').info("return False")
        return False

    def reset_loaded_sample(self):
        self._execute_cmd("reset_loaded_position")
        self._resetLoadedSample()

    def get_robot_exceptions(self):
        return self._execute_cmd("getRobotExceptions")

    @task
    def load(self, sample):
        #warning_task = gevent.spawn(self._execute_cmd, "PSS_light")
        self.prepare_load(wait=True)
        self.enable_power()
        #warning_task.kill()
        try:
            res = SampleChanger.load(self, sample)
        finally:
            for msg in self.get_robot_exceptions():
                logging.getLogger("HWR").error(msg)
       
        if res:
            self.prepareCentring()
        return res
        
    @task
    def unload_sample(self, holderLength, sample_id=None, sample_location=None, successCallback=None, failureCallback=None):
        cell, basket, sample = sample_location
        sample = self.getComponentByAddress(Pin.getSampleAddress(cell, basket, sample))
        return self.unload(sample)

    @task
    def unload(self, sample):
        #warning_task = gevent.spawn(self._execute_cmd, "PSS_light")
        self.prepare_load(wait=True)
        self.enable_power()
        #warning_task.kill()
        try:
            SampleChanger.unload(self, sample)
        finally:
            for msg in self.get_robot_exceptions():
                logging.getLogger("HWR").error(msg)

    def get_gripper(self):
        gripper_type = "SPINE" if self._execute_cmd("get_gripper_type") == 3 else "UNIPUCK"
        return gripper_type

    @task
    def change_gripper(self):
        self.enable_power()
        self._execute_cmd("changeGripper") 

    @task
    def home(self):
        #warning_task = gevent.spawn(self._execute_cmd, "PSS_light")
        self.prepare_load(wait=True)
        self.enable_power()
        #warning_task.kill()
        self._execute_cmd("homeClear")

    @task
    def enable_power(self):
        self._execute_cmd("enablePower", 1)

    @task
    def defreeze(self):
        self._execute_cmd("defreezeGripper")

    def _doLoad(self, sample=None):
        self._doSelect(sample.getCell())

        load_task = gevent.spawn(self._execute_cmd, 'loadSample', sample.getCellNo(), sample.getBasketNo(), sample.getVialNo())
        gevent.sleep(5)
        while not load_task.ready():
           if self._execute_cmd("get_robot_cache_variable", "SampleCentringReady") == "True":
              self._setLoadedSample(sample)
              return True
           gevent.sleep(1)
         
        if self._execute_cmd("get_loaded_sample") == (sample.getCellNo(), sample.getBasketNo(), sample.getVialNo()):
          self._setLoadedSample(sample)
          return True
        if not self._execute_cmd("pin_on_gonio"):
            self._resetLoadedSample()
        return False

    def _doUnload(self, sample=None):
        loaded_sample = self.getLoadedSample()
        if loaded_sample is not None and loaded_sample != sample:
          raise RuntimeError("Can't unload another sample")

        self._execute_cmd('unloadSample', sample.getCellNo(), sample.getBasketNo(), sample.getVialNo())
        if self._execute_cmd("get_loaded_sample") == (-1,-1,-1):
            self._resetLoadedSample()
            return True
        return False

    def _doAbort(self):
        self._execute_cmd('abort')

    def _doReset(self):
        self._execute_cmd('homeClear')

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
      
    def isSequencerReady(self):
        if self.prepareLoad:
            cmdobj = self.getCommandObject
            return all([cmd.isSpecReady() for cmd in (cmdobj("moveToLoadingPosition"),)])
        return True
            
 
    def _readState(self):
        # should read state from robot
        state = "RUNNING" if self._execute_cmd("robot.isBusy") else "STANDBY"
        if state == 'STANDBY' and not self.isSequencerReady():
          state = 'RUNNING'
        state_converter = { "ALARM": SampleChangerState.Alarm,
                            "FAULT": SampleChangerState.Fault,
                            "RUNNING": SampleChangerState.Moving,
                            "READY": SampleChangerState.Ready,
                            "STANDBY": SampleChangerState.Ready }
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
        cell, puck = self._execute_cmd('get_cell_position')
        sample_cell, sample_puck, sample = self._execute_cmd('get_loaded_sample')

        for c in self.getComponents():
          i = c.getIndex()
          if cell == i + 1:
            self._setSelectedComponent(c)
            break

        # find sample
        for s in self.getSampleList():
          if s.getCoords() == (sample_cell, sample_puck, sample):
            self._setLoadedSample(s)
            #self._setSelectedSample(s)
            return

        self._resetLoadedSample()
        self._setSelectedSample(None)
 
