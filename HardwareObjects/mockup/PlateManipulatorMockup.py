"""
[Name] PlateManipulatorMockup

[Description]
Plate manipulator hardware object is used to use diffractometer in plate mode.
It is compatable with md2, md3 diffractometers. Class is based on
SampleChanger, so it has all the sample changed functionalities, like
mount, unmount sample (in this case move to plate position).
Plate is organized in rows and columns. Each cell (Cell) contains drop (Drop).
Each drop could contain several crystals (Xtal). If CRIMS is available then
each drop could have several crystals.

[Channels]

[Commands]

[Emited signals]

 - emited signals defined in SampleChanger class

[Included Hardware Objects]
-----------------------------------------------------------------------
| name            | signals          | functions
-----------------------------------------------------------------------
-----------------------------------------------------------------------
"""

import os
import time
import gevent
import tempfile
from datetime import datetime

from HardwareRepository.HardwareObjects.abstract import AbstractSampleChanger
from HardwareRepository.HardwareObjects.abstract.sample_changer import Container, Crims, Sample


class Xtal(Sample.Sample):
    __NAME_PROPERTY__ = "Name"
    __LOGIN_PROPERTY__ = "Login"

    def __init__(self, drop, index):
        # Sample.__init__(self, drop, Xtal._getXtalAddress(drop, index), False)
        super(Xtal, self).__init__(drop, Xtal._getXtalAddress(drop, index), False)
        self._drop = drop
        self._index = index
        self._setImageX(None)
        self._setImageY(None)
        self._setImageURL(None)
        self._setName(None)
        self._setLogin(None)
        self._setInfoURL(None)

        self._setInfo(False, False, False)
        self._setLoaded(False, False)

    def _setName(self, value):
        self._setProperty(self.__NAME_PROPERTY__, value)

    def getName(self):
        return self.getProperty(self.__NAME_PROPERTY__)

    def _setLogin(self, value):
        self._setProperty(self.__LOGIN_PROPERTY__, value)

    def getLogin(self):
        return self.getProperty(self.__LOGIN_PROPERTY__)

    def getDrop(self):
        return self._drop

    def getCell(self):
        return self.getDrop().getCell()

    @staticmethod
    def _getXtalAddress(drop, index):
        return str(drop.getAddress()) + "-" + str(index)

    def getIndex(self):
        """
        Descript. : Sample index is calculated relaive to the row (Basket)
                    In this case we assume that in drop is one xtal
                    This should be changed to various num of xtals in the drop
        """
        cell_index = self.getCell().getIndex()
        drops_in_cell_num = self.getCell().getDropsNo()
        drop_index = self._drop.getIndex()
        return cell_index * drops_in_cell_num + drop_index

    def getContainer(self):
        return self.getCell().getContainer()

    def getName(self):
        return "%s%d:%d" % (
            self.getCell().getRowChr(),
            self.getCell().getIndex() + 1,
            self._drop.getIndex() + 1,
        )


class Drop(Container.Container):
    __TYPE__ = "Drop"

    def __init__(self, cell, drops_num):
        super(Drop, self).__init__(
            self.__TYPE__, cell, Drop._getDropAddress(cell, drops_num), False
        )
        self._cell = cell
        self._drops_num = drops_num

    @staticmethod
    def _getDropAddress(cell, drop_num):
        return str(cell.getAddress()) + ":" + str(drop_num)

    def getCell(self):
        return self._cell

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

    # def getIndex(self):
    #    """
    #    Descript. Drop index is relative to the row
    #    """
    #    return self._well_no


class Cell(Container.Container):
    __TYPE__ = "Cell"

    def __init__(self, row, row_chr, col_index, drops_num):
        Container.Container.__init__(
            self, self.__TYPE__, row, Cell._getCellAddress(row_chr, col_index), False
        )
        self._row = row
        self._row_chr = row_chr
        self._col_index = col_index
        self._drops_num = drops_num
        for drop_index in range(self._drops_num):
            drop = Drop(self, drop_index + 1)
            self._addComponent(drop)
            xtal = Xtal(drop, drop.getNumberOfComponents())
            drop._addComponent(xtal)
        self._transient = True

    def getRow(self):
        return self._row

    def getRowChr(self):
        return self._row_chr

    def getRowIndex(self):
        return ord(self._row_chr.upper()) - ord("A")

    def getCol(self):
        return self._col_index

    def getDropsNo(self):
        return self._drops_num

    @staticmethod
    def _getCellAddress(row, col):
        return str(row) + str(col)


class PlateManipulatorMockup(AbstractSampleChanger.SampleChanger):
    """
    """

    __TYPE__ = "PlateManipulator"

    def __init__(self, *args, **kwargs):
        super(PlateManipulatorMockup, self).__init__(
            self.__TYPE__, False, *args, **kwargs
        )

        self.num_cols = None
        self.num_rows = None
        self.num_drops = None
        self.current_phase = None
        self.reference_pos_x = None
        self.timeout = 3  # default timeout
        self.plate_location = None
        self.crims_url = None

    def init(self):
        """
        Descript. :
        """
        self.num_cols = self.getProperty("numCols")
        self.num_rows = self.getProperty("numRows")
        self.num_drops = self.getProperty("numDrops")
        self.reference_pos_x = self.getProperty("referencePosX")
        if not self.reference_pos_x:
            self.reference_pos_x = 0.5

        self._initSCContents()

        AbstractSampleChanger.SampleChanger.init(self)

    def _onStateChanged(self, state):
        """
        Descript. : state change callback. Based on diffractometer state
                    sets PlateManipulatorMockup state.
        """
        if state is None:
            self._setState(SampleChangerState.Unknown)
        else:
            if state == "Alarm":
                self._setState(SampleChangerState.Alarm)
            elif state == "Fault":
                self._setState(SampleChangerState.Fault)
            elif state == "Moving" or state == "Running":
                self._setState(SampleChangerState.Moving)
            elif state == "Ready":
                if self.current_phase == "Transfer":
                    self._setState(SampleChangerState.Charging)
                elif self.current_phase == "Centring":
                    self._setState(SampleChangerState.Ready)
                else:
                    self._setState(SampleChangerState.StandBy)
            elif state == "Initializing":
                self._setState(SampleChangerState.Initializing)

    def _initSCContents(self):
        """
        Descript. : Initializes content of plate.
        """
        if self.num_rows is None:
            return
        self._setInfo(False, None, False)
        self._clearComponents()
        for row in range(self.num_rows):
            # row is like a basket
            basket = Container.Basket(self, row + 1, samples_num=0, name="Row")
            present = True
            datamatrix = ""
            scanned = False
            basket._setInfo(present, datamatrix, scanned)
            self._addComponent(basket)

            for col in range(self.num_cols):
                cell = Cell(basket, chr(65 + row), col + 1, self.num_drops)
                basket._addComponent(cell)

    def _doAbort(self):
        """
        Descript. :
        """
        self._abort()

    def _doChangeMode(self, mode):
        """
        Descript. :
        """
        if mode == SampleChangerMode.Charging:
            self._set_phase("Transfer")
        elif mode == SampleChangerMode.Normal:
            self._set_phase("Centring")

    def _doLoad(self, sample=None):
        """
        Descript. :
        """
        selected = self.getSelectedSample()
        if sample is None:
            sample = self.getSelectedSample()
        if sample is not None:
            if sample != selected:
                self._doSelect(sample)
            self._setLoadedSample(sample)

    def load_sample(self, sample_location=None):
        """
        Descript. : function to move to plate location.
                    Location is estimated by sample location and reference positions.
        """
        gevent.spawn(self.load_sample_task, sample_location)

    def load_sample_task(self, sample_location):
        row = sample_location[0] - 1
        col = (sample_location[1] - 1) / self.num_drops
        drop = sample_location[1] - self.num_drops * col
        pos_y = float(drop) / (self.num_drops + 1)

        self.plate_location = [row, col, self.reference_pos_x, pos_y]
        col += 1
        cell = self.getComponentByAddress("%s%d" % (chr(65 + row), col))
        drop = cell.getComponentByAddress("%s%d:%d" % (chr(65 + row), col, drop))
        new_sample = drop.getSample()
        old_sample = self.getLoadedSample()
        new_sample = drop.getSample()
        if old_sample != new_sample:
            if old_sample is not None:
                old_sample._setLoaded(False, True)
            if new_sample is not None:
                new_sample._setLoaded(True, True)

    def _doUnload(self, sample_slot=None):
        """
        Descript. :
        """
        self._resetLoadedSample()
        self._onStateChanged("Ready")

    def _doReset(self):
        """
        Descript. :
        """
        self._reset(False)
        self._waitDeviceReady()

    def _doScan(self, component, recursive):
        """
        Descript. :
        """
        if not isinstance(component, PlateManipulatorMockup):
            raise Exception("Not supported")
        self._initializeData()
        if self.getToken() is None:
            raise Exception("No plate barcode defined")
        self._loadData(self.getToken())

    def _doSelect(self, component):
        """
        Descript. :
        """
        pos_x = self.reference_pos_x
        pos_y = 0.5

        if isinstance(component, Xtal):
            self._select_sample(
                component.getCell().getRowIndex(),
                component.getCell().getCol() - 1,
                component.getDrop().getWellNo() - 1,
            )
            self._setSelectedSample(component)
            component.getContainer()._setSelected(True)
            component.getContainer().getContainer()._setSelected(True)
        elif isinstance(component, Crims.CrimsXtal):
            col = component.Column - 1
            row = ord(component.Row.upper()) - ord("A")
            pos_x = component.offsetX
            pos_y = component.offsetY
            cell = self.getComponentByAddress(
                Cell._getCellAddress(component.Row, component.Column)
            )
            drop = self.getComponentByAddress(
                Drop._getDropAddress(cell, component.Shelf)
            )
            drop._setSelected(True)
            drop.getContainer()._setSelected(True)
        elif isinstance(component, Drop):
            self._select_sample(
                component.getCell().getRowIndex(),
                component.getCell().getCol() - 1,
                component.getWellNo() - 1,
            )
            component._setSelected(True)
            component.getContainer().getContainer()._setSelected(True)
        elif isinstance(component, Cell):
            self._select_sample(component.getRowIndex(), component.getCol() - 1, 0)
            component._setSelected(True)
        elif isinstance(component, list):
            row = component[0]
            col = component[1]
            if len(component > 2):
                pos_x = component[2]
                pos_y = component[3]
            cell = self.getComponentByAddress(Cell._getCellAddress(row, column))
            cell._setSelected(True)
        else:
            raise Exception("Invalid selection")
        self._resetLoadedSample()
        self._waitDeviceReady()

    def _loadData(self, barcode):
        processing_plan = Crims.get_processing_plan(barcode, self.crims_url)

        if processing_plan is None:
            msg = "No information about plate with barcode %s found in CRIMS" % barcode
            logging.getLogger("user_level_log").error(msg)
        else:
            msg = "Information about plate with barcode %s found in CRIMS" % barcode
            logging.getLogger("user_level_log").info(msg)
            self._setInfo(True, processing_plan.plate.barcode, True)

            for x in processing_plan.plate.xtal_list:
                cell = self.getComponentByAddress(Cell._getCellAddress(x.row, x.column))
                cell._setInfo(True, "", True)
                drop = self.getComponentByAddress(Drop._getDropAddress(cell, x.shelf))
                drop._setInfo(True, "", True)
                xtal = Xtal(drop, drop.getNumberOfComponents())
                xtal._setInfo(True, x.pin_id, True)
                xtal._setImageURL(x.image_url)
                xtal._setImageX(x.offset_x)
                xtal._setImageY(x.offset_y)
                xtal._setLogin(x.login)
                xtal._setName(x.sample)
                xtal._setInfoURL(x.summary_url)
                drop._addComponent(xtal)
            return processing_plan

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
        return "ready"

    def _updateLoadedSample(self):
        """Updates plate location"""
        old_sample = self.getLoadedSample()
        # plate_location = None
        # if self.chan_plate_location is not None:
        #    plate_location = self.chan_plate_location.getValue()

        if self.plate_location is not None:
            new_sample = self.get_sample(self.plate_location)

            if old_sample != new_sample:
                if old_sample is not None:
                    # there was a sample on the gonio
                    loaded = False
                    has_been_loaded = True
                    old_sample._setLoaded(loaded, has_been_loaded)
                if new_sample is not None:
                    # self._updateSampleBarcode(new_sample)
                    loaded = True
                    has_been_loaded = True
                    new_sample._setLoaded(loaded, has_been_loaded)

    def get_sample(self, plate_location):
        row = int(plate_location[0])
        col = int(plate_location[1])
        y_pos = float(plate_location[3])
        drop_index = abs(y_pos * self.num_drops) + 1
        if drop_index > self.num_drops:
            drop_index = self.num_drops

        cell = self.getComponentByAddress("%s%d" % (chr(65 + row), col + 1))
        if cell:
            old_sample = self.getLoadedSample()
            drop = cell.getComponentByAddress(
                "%s%d:%d" % (chr(65 + row), col + 1, drop_index)
            )
            return drop.getSample()

    def getSampleList(self):
        """
        Descript. : This is ugly
        """
        sample_list = []
        for basket in self.getComponents():
            if isinstance(basket, Container.Basket):
                for cell in basket.getComponents():
                    if isinstance(cell, Cell):
                        for drop in cell.getComponents():
                            sample_list.append(drop.getSample())
        return sample_list

    def is_mounted_sample(self, sample_location):
        row = sample_location[0] - 1
        col = (sample_location[1] - 1) / self.num_drops
        drop = sample_location[1] - self.num_drops * col
        pos_y = float(drop) / (self.num_drops + 1)
        sample = self.get_sample((row, col, drop, pos_y))
        return sample.loaded

    def _ready(self):
        if self._updateState() == "Ready":
            return True
        return False

    def _wait_ready(self, timeout=None):
        if timeout <= 0:
            timeout = self.timeout
        tt1 = time.time()
        while time.time() - tt1 < timeout:
            if self._ready():
                break
            else:
                gevent.sleep(0.5)

    def get_plate_info(self):
        """
        Descript. : returns dict with plate info
        """
        plate_info_dict = {}
        plate_info_dict["num_cols"] = self.num_cols
        plate_info_dict["num_rows"] = self.num_rows
        plate_info_dict["num_drops"] = self.num_drops
        plate_info_dict["plate_label"] = "Demo plate label"
        return plate_info_dict

    def get_plate_location(self):
        # if self.chan_plate_location is not None:
        #    self.plate_location = self.chan_plate_location.getValue()
        return self.plate_location

    def sync_with_crims(self, barcode):
        return self._loadData(barcode)
