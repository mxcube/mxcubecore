"""
"""
import time
import functools
from sample_changer.GenericSampleChanger import *

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

        self._setInfo(False, False, False)
        self._setLoaded(False, False)

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
        return self.getIndex() + 1

    def isLoaded(self):
        """
        Returns if the sample is currently loaded for data collection 
        :rtype: bool
        """
        sample = self.getSample()
        return sample.isLoaded()  
 
    def getSample(self):
        """
        In this cas we assume that there is one crystal per drop
        """ 
        sample = self.getComponents()
        return sample[0]
 

class Cell(Container):
    __TYPE__ = "Cell"
    def __init__(self, container, row, col, wells):
        super(Cell, self).__init__(self.__TYPE__,container,Cell._getCellAddress(row,col),False)
        self._row=row
        self._col=col
        self._wells=wells
        for i in range(wells):
            drop = Drop(self, i + 1)
            self._addComponent(drop)
            xtal = Xtal(drop,drop.getNumberOfComponents())
            drop._addComponent(xtal)
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
    def _getCellAddress(row, col):
        return str(row) + str(col)


class PlateManipulator(SampleChanger):
    """
    """    
    __TYPE__ = "Plate manipulator"    

    def __init__(self, *args, **kwargs):
        super(PlateManipulator, self).__init__(self.__TYPE__,False, *args, **kwargs)

        self.num_coll = None
        self.num_row = None
        self.current_phase = None
        #self._setTransient(True)
            
    def init(self):      
        """
        Descript. :
        """
        self.num_coll = self.getProperty("numColls")
        self.num_row = self.getProperty("numRows")
        self.num_drops = self.getProperty("numDrops")
        self.reference_pos_x = self.getProperty("referencePosX") 

        self._initSCContents()
        self.cmd_move_to_location = self.getCommandObject("cmd_move_plate_to_location")
        self.chan_current_phase = self.getChannelObject("chan_current_phase")
        self.chan_plate_location = self.getChannelObject("chan_plate_location")
        self.chan_state = self.getChannelObject("chan_state")
        if self.chan_state is not None:
            self.chan_state.connectSignal("update", self._onStateChanged)
       
        SampleChanger.init(self) 

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

    def _initSCContents(self):
        """
        Descript. :
        """
        self._setInfo(False, None, False)
        self._clearComponents()
        for row in range(self.num_row):
            for col in range(self.num_coll):
                cell = Cell(self, chr(65 + row), col + 1, self.num_drops)
                self._addComponent(cell)

    def _doAbort(self):
        """
        Descript. :
        """
        self._abort()

    def _doChangeMode(self,mode):
        """
        Descript. :
        """
        if mode==SampleChangerMode.Charging:
            self._set_phase("Transfer")
        elif mode==SampleChangerMode.Normal:
            self._set_phase("Centring")

    def _doLoad(self,sample=None):
        """
        Descript. :
        """
        selected=self.getSelectedSample()
        if (sample is None):
            sample = self.getSelectedSample()
        if (sample is not None):
            if (sample!=selected):
                self._doSelect(sample)
            self._setLoadedSample(sample)
        #TODO: Add pre-positioning and image matching

    def load_sample(self, sample_location=None):
        pos_y = float(sample_location[2]) / (self.num_drops + 1)   
        self.cmd_move_to_location(sample_location[0], sample_location[1] - 1, self.reference_pos_x, pos_y) 
        
    def _doUnload(self,sample_slot=None):
        """
        Descript. :
        """
        self._resetLoadedSample()

    def _doReset(self):
        """
        Descript. :
        """
        self._reset(False)
        self._waitDeviceReady()

    def _doScan(self,component, recursive):
        """
        Descript. :
        """
        if not isinstance(component, PlateManipulator):
            raise Exception ("Not supported")
        self._initializeData()
        if self.getToken() is None:
            raise Exception ("No plate barcode defined")
        self._loadData(self.getToken())

    def _doSelect(self,component):
        """
        Descript. :
        """
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

    def _doUpdateInfo(self):
        """
        Descript. :
        """
        self._updateState()
        self._updateLoadedSample()

    def _updateState(self):
        """
        Descript. :
        """ 
        return "Ready"
        state = self.chan_state.getValue()
        if (state == "Ready") or (self.current_phase is None):
            self.current_phase =  self.chan_current_phase.getValue()
        self._onStateChanged(state)
        return state

    def _updateLoadedSample(self):
        """
        Descript. :
        """
        #plate_location = self.chan_plate_location.getValue()
        """row = int(plate_location[0])
        col = int(plate_location[1])
        y_pos = float(plate_location[3])
        drop_index = abs(y_pos * self.num_drops) + 1
        if drop_index > self.num_drops:
            drop_index = self.num_drops"""

        row = 2
        col = 2
        drop_index = 2

        cell = self.getComponentByAddress("%s%d" %(chr(65 + row), col + 1))
        old_sample = self.getLoadedSample()
        drop = cell.getComponentByAddress("%s%d:%d" %(chr(65 + row), col + 1, drop_index))
        new_sample = drop.getSample()

        if old_sample != new_sample:
            if old_sample is not None:
                # there was a sample on the gonio
                loaded = False
                has_been_loaded = True
                old_sample._setLoaded(loaded, has_been_loaded)
            if new_sample is not None:
                #self._updateSampleBarcode(new_sample)
                loaded = True
                has_been_loaded = True
                new_sample._setLoaded(loaded, has_been_loaded)    

    def getSampleList(self):
        """
        Descript. :
        """
        sample_list = []
        for c in self.getComponents():
            if isinstance(c, Cell):
                for drop in c.getComponents():
                    #sample_list.append(drop)
                    sample_list.append(drop.getSample())
        return sample_list
