"""
[Name] PlateManipulator

[Description]
Plate manipulator hardware object is used to use diffractometer in plate mode.
It is compatable with md2, md3 diffractometers. Class is based on
SampleChanger, so it has all the sample changed functionalities, like
mount, unmount sample (in this case move to plate position).
Plate is organized in rows and columns. Each cell (Cell) contains drop (Drop).
Each drop could contain several crystals (Xtal). If CRIMS is available then
each drop could have several crystals.

[Channels]

 - self.chan_current_phase   : diffractometer phase
 - self.chan_plate_location  : plate location (col, row)
 - self.chan_drop_location   : plate location (col, row, drop)
 - self.chan_state           : diffractometer state

[Commands]

 - self.cmd_move_to_location : move to plate location

[Emited signals]

 - emited signals defined in SampleChanger class

[Included Hardware Objects]
-----------------------------------------------------------------------
| name            | signals          | functions
-----------------------------------------------------------------------
-----------------------------------------------------------------------
"""

import time
import gevent
import logging

from mxcubecore.HardwareObjects.abstract.sample_changer import Crims
from mxcubecore.HardwareObjects.abstract.AbstractSampleChanger import (
    SampleChanger,
    SampleChangerState,
    SampleChangerMode
)
from mxcubecore.HardwareObjects.abstract.sample_changer.Container import (
    Container,
    Sample,
    Basket,
)


class Xtal(Sample):
    __NAME_PROPERTY__ = "Name"
    __LOGIN_PROPERTY__ = "Login"

    def __init__(self, drop, index):
        super(Xtal, self).__init__(drop, Xtal._get_xtal_address(drop, index), False)
        self._drop = drop
        self._index = index
        self._set_image_x(None)
        self._set_image_y(None)
        self._set_image_url(None)
        self._set_name(None)
        self._set_login(None)
        self._set_info_url(None)

        self._set_info(False, False, False)
        self._set_loaded(False, False)
        self.present = True

    def _set_name(self, value):
        self._set_property(self.__NAME_PROPERTY__, value)

    def get_name(self):
        return self.get_property(self.__NAME_PROPERTY__)

    def _set_login(self, value):
        self._set_property(self.__LOGIN_PROPERTY__, value)

    def get_login(self):
        return self.get_property(self.__LOGIN_PROPERTY__)

    def get_drop(self):
        return self._drop

    def get_cell(self):
        return self.get_drop().get_cell()
    
    def get_basket_no(self):
        """
        In this cas we assume a drop is a basket or puck
        """
        return self.get_drop().get_index() + 1
    
    def get_cell_no(self):
        """
        In this cas we assume wells in the row is a cell
        """
        return  self.get_cell().get_row_index() + 1

    @staticmethod
    def _get_xtal_address(drop, index):
        return str(drop.get_address()) + "-" + str(index)

    def get_index(self):
        """
        Descript. : Sample index is calculated relaive to the row (Basket)
                    In this case we assume that in drop is one xtal
                    This should be changed to various num of xtals in the drop
        """
        cell_index = self.get_cell().get_index()
        drops_in_cell_num = self.get_cell().get_drops_no()
        drop_index = self._drop.get_index()
        return cell_index * drops_in_cell_num + drop_index

    def get_container(self):
        return self.get_cell().get_container()

    def get_name(self):
        return "%s%d:%d" % (
            self.get_cell().get_row_chr(),
            self.get_cell().get_index() + 1,
            self._drop.get_index() + 1,
        )


class Drop(Container):
    __TYPE__ = "Drop"

    def __init__(self, cell, drops_num):
        super(Drop, self).__init__(
            self.__TYPE__, cell, Drop._get_drop_address(cell, drops_num), False
        )
        self._cell = cell
        self._drops_num = drops_num

    @staticmethod
    def _get_drop_address(cell, drop_num):
        return str(cell.get_address()) + ":" + str(drop_num)

    def get_cell(self):
        return self._cell

    def get_well_no(self):
        return self.get_index() + 1

    def is_loaded(self):
        """
        Returns if the sample is currently loaded for data collection
        :rtype: bool
        """
        sample = self.get_sample()
        return sample.is_loaded()

    def get_sample(self):
        """
        In this cas we assume that there is one crystal per drop
        """
        sample = self.get_components()
        return sample[0]



class Cell(Container):
    __TYPE__ = "Cell"

    def __init__(self, row, row_chr, col_index, drops_num):
        Container.__init__(
            self, self.__TYPE__, row, Cell._get_cell_address(row_chr, col_index), False
        )
        self._row = row
        self._row_chr = row_chr
        self._col_index = col_index
        self._drops_num = drops_num
        for drop_index in range(self._drops_num):
            drop = Drop(self, drop_index + 1)
            self._add_component(drop)
            xtal = Xtal(drop, drop.get_number_of_components())
            drop._add_component(xtal)
        self._transient = True

    def get_row(self):
        return self._row

    def get_row_chr(self):
        return self._row_chr

    def get_row_index(self):
        return ord(self._row_chr.upper()) - ord("A")

    def get_col(self):
        return self._col_index

    def get_drops_no(self):
        return self._drops_num

    @staticmethod
    def _get_cell_address(row, col):
        return str(row) + str(col)


class PlateManipulator(SampleChanger):
    """ """

    __TYPE__ = "PlateManipulator"

    def __init__(self, *args, **kwargs):
        super(PlateManipulator, self).__init__(self.__TYPE__, False, *args, **kwargs)

        self.plate_label = None
        self.num_cols = None
        self.num_rows = None
        self.num_drops = None
        self.current_phase = None
        self.reference_pos_x = None
        self.timeout = 3  # default timeout
        self.plate_location = None
        self.crims_url = None
        self.crims_user_agent = None
        self.plate_barcode = None
        self.harvester_key = None
        self.processing_plan = None

        self.stored_pos_x = None
        self.stored_pos_y = None

        self.cmd_move_to_drop = None
        self.cmd_move_to_location = None

        self.chan_state = None

    def init(self):
        """
        Descript. :
        """
        cmd_get_config = self.get_channel_object("GetPlateConfig", optional=True)
        if cmd_get_config:
            try:
                (
                    self.num_rows,
                    self.num_cols,
                    self.num_drops,
                ) = cmd_get_config.get_value()
            except Exception:
                pass
        else:
            self.num_cols = self.get_property("numCols")
            self.num_rows = self.get_property("numRows")
            self.num_drops = self.get_property("numDrops")

        self.reference_pos_x = self.get_property("referencePosX")        
        if not self.reference_pos_x:
            self.reference_pos_x = 0.5

        self.stored_pos_x = self.reference_pos_x
        self.stored_pos_y = 0.5
        self.plate_label = self.get_property("plateLabel")
        self.crims_url = self.get_property("crimsWsRoot")
        self.crims_user_agent = self.get_property("crimsUserAgent")
        self.plate_barcode = self.get_property("PlateBarcode")
        self.harvester_key = self.get_property("harvesterKey")

        self.cmd_move_to_drop = self.get_command_object("MoveToDrop")
        if not self.cmd_move_to_drop:
            self.cmd_move_to_location = self.get_command_object(
                "startMovePlateToLocation"
            )

        self.cmd_move_to_crystal_position = self.get_command_object("MoveToXtalPointing")
        self.cmd_get_omega_scan_limits = self.get_command_object("getOmegaMotorDynamicScanLimits")

        self.cmd_do_abort = self.get_command_object("AbortCurrentAction")

        self._init_sc_contents()

        self.chan_current_phase = self.get_channel_object("CurrentPhase")
        self.chan_drop_location = self.get_channel_object("DropLocation")
        self.chan_plate_location = self.get_channel_object("PlateLocation")
        if self.chan_plate_location is not None:
            self.chan_plate_location.connect_signal(
                "update", self.plate_location_changed
            )
            self.plate_location_changed(self.chan_plate_location.get_value())

        self.chan_state = self.get_channel_object("State")
        if self.chan_state is not None:
            self.chan_state.connect_signal("update", self.state_changed)

        SampleChanger.init(self)

    def change_plate_barcode(self, barcode):
        if self._load_data(barcode):
            self.plate_barcode = barcode
            return True
        else:
            raise Exception("barcode unknown")
        

    def hw_get_loaded_sample_location(self):
        loaded_sample = None
        if(self.chan_drop_location):
            loaded_sample = self.chan_drop_location.get_value()
        
            return (
                chr(65 + loaded_sample[0])
                + str(loaded_sample[1] +1)
                + ":"
                + str(loaded_sample[2] +1)
                + "-0"
            )
        return loaded_sample

    def plate_location_changed(self, plate_location):
        self.plate_location = plate_location
        self._update_loaded_sample()
        self.update_info()

    def state_changed(self, state):
        try:
            self.plate_location_changed(self.chan_plate_location.get_value())
            self._on_state_changed(state)
        except AttributeError:
            pass

    def _on_state_changed(self, state):
        """
        Descript. : state change callback. Based on diffractometer state
                    sets PlateManipulator state.
        """
        if state is None:
            self._set_state(SampleChangerState.Unknown)
        else:
            if state == "Alarm":
                self._set_state(SampleChangerState.Alarm)
            elif state == "Fault":
                self._set_state(SampleChangerState.Fault)
            elif state == "Moving" or state == "Running":
                self._set_state(SampleChangerState.Moving)
            elif state == "Ready":
                if self.current_phase == "Transfer":
                    self._set_state(SampleChangerState.Charging)
                elif self.current_phase == "Centring":
                    self._set_state(SampleChangerState.Ready)
                else:
                    self._set_state(SampleChangerState.StandBy)
            elif state == "Initializing":
                self._set_state(SampleChangerState.Initializing)

    def _init_sc_contents(self):
        """
        Descript. : Initializes content of plate.
        """
        if self.num_rows is None:
            return
        self._set_info(False, None, False)
        self._clear_components()
        for row in range(self.num_rows):
            # row is like a basket
            basket = Basket(self, row + 1, samples_num=0, name="Row")
            present = True
            datamatrix = ""
            scanned = False
            basket._set_info(present, datamatrix, scanned)
            self._add_component(basket)

            for col in range(self.num_cols):
                cell = Cell(basket, chr(65 + row), col + 1, self.num_drops)
                basket._add_component(cell)

    def _do_abort(self):
        """
        Descript. :
        """
        self.cmd_do_abort()

    def _do_change_mode(self, mode):
        """
        Descript. :
        """
        if mode == SampleChangerMode.Charging:
            self._set_phase("Transfer")
        elif mode == SampleChangerMode.Normal:
            self._set_phase("Centring")

    def _do_load(self, sample=None):
        """
        Descript. :
        """
        selected = self.get_selected_sample()
        if sample is None:
            sample = self.get_selected_sample()
        if sample is not None:
            if sample != selected:
                self._do_select(sample)
            self._set_loaded_sample(sample)

    def load(self, sample=None, wait=True):
        comp = self._resolve_component(sample)
        coords = comp.get_coords()
        res = self.load_sample(coords)
        if res:
            self._set_loaded_sample(comp)
            comp._set_loaded(True, True)
        return res

    def load_sample(self, sample_location=None, pos_x=None, pos_y=None, wait=True):
        """
        Location is estimated by sample location and reference positions.
        """
        try:
            row = sample_location[0] - 1
            col = int((sample_location[1] - 1) / self.num_drops)
            drop = sample_location[1] - self.num_drops * col

            if not pos_x:
                pos_x = self.stored_pos_x
            else:
                self.stored_pos_x = pos_x
            if not pos_y:
                pos_y = self.stored_pos_y
            else:
                self.stored_pos_y = pos_y
                # pos_y = float(drop) / (self.num_drops + 1)

            if self.cmd_move_to_location:
                self.cmd_move_to_location(row, col, pos_x, pos_y)
                if wait:
                    self._wait_ready(60)
            elif self.cmd_move_to_drop:
                self.cmd_move_to_drop(row, col, drop - 1)
                if wait:
                    self._wait_ready(60)
            else:
                # No actual move cmd defined. Act like a mockup
                self.plate_location = [row, col, self.stored_pos_x, pos_y]
                col += 1
                cell = self.get_component_by_address("%s%d" % (chr(65 + row), col))
                drop = cell.get_component_by_address("%s%d:%d" % (chr(65 + row), col, drop))
                new_sample = drop.get_sample()
                old_sample = self.get_loaded_sample()
                new_sample = drop.get_sample()
                if old_sample != new_sample:
                    if old_sample is not None:
                        old_sample._set_loaded(False, True)
                    if new_sample is not None:
                        new_sample._set_loaded(True, True)

            return True
        except:
             return False   

    def _do_unload(self, sample_slot=None):
        """
        Descript. :
        """
        self._reset_loaded_sample()
        self._on_state_changed("Ready")

    def _do_reset(self):
        """
        Descript. :
        """
        self._reset(False)
        self._wait_device_ready()

    def _do_scan(self, component, recursive):
        """
        Descript. :
        """
        if not isinstance(component, PlateManipulator):
            raise Exception("Not supported")
        self._initializeData()
        if self.get_token() is None:
            raise Exception("No plate barcode defined")
        self._load_data(self.get_token())
    
    def sync_with_crims(self):
        """
        Descript. :
        Get Crims information
        """
        self.processing_plan = self._load_data(self.plate_barcode)
        return self.processing_plan

    def _do_select(self, component):
        """
        Descript. :
        """
        pos_x = self.stored_pos_x
        pos_y = 0.5

        if isinstance(component, Xtal):
            self._select_sample(
                component.get_cell().get_row_index(),
                component.get_cell().get_col() - 1,
                component.get_drop().get_well_no() - 1,
            )
            self._set_selected_sample(component)
            component.get_container()._set_selected(True)
            component.get_container().get_container()._set_selected(True)
        elif isinstance(component, Crims.CrimsXtal):
            col = component.Column - 1
            row = ord(component.Row.upper()) - ord("A")
            pos_x = component.offsetX
            pos_y = component.offsetY
            cell = self.get_component_by_address(
                Cell._get_cell_address(component.Row, component.Column)
            )
            drop = self.get_component_by_address(
                Drop._get_drop_address(cell, component.Shelf)
            )
            drop._set_selected(True)
            drop.get_container()._set_selected(True)
        elif isinstance(component, Drop):
            self._select_sample(
                component.get_cell().get_row_index(),
                component.get_cell().get_col() - 1,
                component.get_well_no() - 1,
            )
            component._set_selected(True)
            component.get_container().get_container()._set_selected(True)
        elif isinstance(component, Cell):
            self._select_sample(component.get_row_index(), component.get_col() - 1, 0)
            component._set_selected(True)
        elif isinstance(component, list):
            row = component[0]
            col = component[1]
            if len(component > 2):
                pos_x = component[2]
                pos_y = component[3]
            cell = self.get_component_by_address(Cell._get_cell_address(row, col))
            cell._set_selected(True)
        else:
            raise Exception("Invalid selection")
        self._reset_loaded_sample()
        self._wait_device_ready()

    def _load_data(self, plate_barcode):
        processing_plan = Crims.get_processing_plan(plate_barcode, self.crims_url, self.crims_user_agent, self.harvester_key)
        if processing_plan is None:
            msg = "No information about plate with barcode %s found in CRIMS" % plate_barcode
            logging.getLogger("user_level_log").error(msg)
        else:
            msg = "Information about plate with barcode %s found in CRIMS" % plate_barcode
            logging.getLogger("user_level_log").info(msg)
            self._set_info(True, processing_plan.plate.barcode, True)

            for x in processing_plan.plate.xtal_list:
                cell = self.get_component_by_address(
                    Cell._get_cell_address(x.row, x.column)
                )
                cell._set_info(True, "", True)
                drop = self.get_component_by_address(
                    Drop._get_drop_address(cell, x.shelf)
                )
                drop._set_info(True, "", True)
                xtal = Xtal(drop, drop.get_number_of_components())
                xtal._set_info(True, x.pin_id, True)
                xtal._set_image_url(x.image_url)
                xtal._set_image_x(x.offset_x)
                xtal._set_image_y(x.offset_y)
                xtal._set_login(x.login)
                xtal._set_name(x.sample)
                xtal._set_info_url(x.summary_url)
                drop._add_component(xtal)
        return processing_plan

    def _do_update_info(self):
        """
        Descript. :
        """
        self._update_state()

    def _read_state(self):
        return self.chan_state.get_value()

    def _update_state(self):
        """
        Descript. :
        """
        state = None
        if self.chan_state is not None:
            state = self.chan_state.get_value()
            if (state == "Ready") or (self.current_phase is None):
                self.current_phase = self.chan_current_phase.get_value()
            self._on_state_changed(state)
        return state

    def _update_loaded_sample(self):
        """Updates plate location"""

        if self.plate_location is not None:
            new_sample = self.get_loaded_sample()
            if new_sample is not None:
                # self._update_sample_barcode(new_sample)
                loaded = True
                has_been_loaded = True
                new_sample._set_loaded(loaded, has_been_loaded)
                self._set_loaded_sample(new_sample)

    def get_loaded_sample(self):
        sample = None
        for s in self.get_sample_list():
            if s.get_address() == self.hw_get_loaded_sample_location():
                sample = s
        return sample

    def get_sample(self, plate_location):
        row = int(plate_location[0])
        col = int(plate_location[1])
        y_pos = float(plate_location[3])
        drop_index = abs(y_pos * self.num_drops) + 1
        if drop_index > self.num_drops:
            drop_index = self.num_drops

        cell = self.get_component_by_address("%s%d" % (chr(65 + row), col + 1))
        if cell:
            drop = cell.get_component_by_address(
                "%s%d:%d" % (chr(65 + row), col + 1, drop_index)
            )
            return drop.get_sample()

    def get_sample_list(self):
        """
        Descript. : This is ugly
        """
        sample_list = []
        for basket in self.get_components():
            if isinstance(basket, Basket):
                for cell in basket.get_components():
                    if isinstance(cell, Cell):
                        for drop in cell.get_components():
                            sample_list.append(drop.get_sample())
        return sample_list

    def is_mounted_sample(self, sample_location):
        row = sample_location[0] - 1
        col = (sample_location[1] - 1) / self.num_drops
        drop = sample_location[1] - self.num_drops * col
        pos_y = float(drop) / (self.num_drops + 1)
        sample = self.get_sample((row, col, drop, pos_y))
        return sample.loaded

    def _ready(self):
        if self._update_state() == "Ready":
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
        plate_info_dict["plate_label"] = self.plate_label or  "Demo plate label"
        plate_info_dict["plate_barcode"] = self.plate_barcode or  ""
        plate_info_dict["num_cols"] = self.num_cols
        plate_info_dict["num_rows"] = self.num_rows
        plate_info_dict["num_drops"] = self.num_drops
        return plate_info_dict

    def get_plate_location(self):
        if self.chan_plate_location is not None:
           self.plate_location = self.chan_plate_location.get_value()
        return self.plate_location

    def move_to_crystal_position(self, crystal_uuid):
        """
         Descript. : Move Diff to crystal position
         Get crystal_uuid from processing plan for loaded sample/drop 
        """
        ret = None
        if crystal_uuid in ["undefined", None]:
            loaded_sample = self.chan_drop_location.get_value()
            row = int(loaded_sample[0])
            col = int(loaded_sample[1])
            drop = int(loaded_sample[2])

            if self.processing_plan:
                for x in self.processing_plan.plate.xtal_list:
                    if (row == ord(x.row) - 65  and  col == x.column -1 and drop == x.shelf -1):
                        crystal_uuid = x.crystal_uuid
            else : raise Exception("No processing_plan OR Crystal Found in this well")
        

        if self.cmd_move_to_crystal_position and crystal_uuid:
                try:
                    # ret = self.cmd_move_to_crystal_position(row, col, drop, x.image_url, x.offset_x, x.offset_y, 0.0, 0.0, False)
                    ret = self.cmd_move_to_crystal_position(self.plate_barcode, crystal_uuid)
                except Exception as ex:
                    raise Exception("Could not move to crystal position %s" %str(ex))
        else:
            raise Exception("move_to_crystal_position command or crystal UUID not found")

        return ret

    def get_scan_limits(self, args):
        """
        get Omega Motor Dynamic Scan Limits
        """
        ret = ''
        if self.cmd_get_omega_scan_limits:
            try:
                ret = self.cmd_get_omega_scan_limits(args)
            except Exception:
                raise Exception("Could not get Omega Motor Dynamic Scan Limits")
        else:
            raise Exception("command not found")

        return ret
