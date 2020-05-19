from HardwareRepository.HardwareObjects.abstract.AbstractSampleChanger import *
import gevent


class Pin(Sample):
    def __init__(self, basket, cell_no, basket_no, sample_no):
        super(Pin, self).__init__(
            basket, Pin.get_sample_address(cell_no, basket_no, sample_no), True
        )
        self._set_holder_length(22.0)

    def get_basket_no(self):
        return self.get_container().get_index() + 1

    def get_vial_no(self):
        return self.get_index() + 1

    def get_cell_no(self):
        return self.get_container().get_container().get_index() + 1

    def get_cell(self):
        return self.get_container().get_container()

    @staticmethod
    def get_sample_address(cell_number, basket_number, sample_number):
        return (
            str(cell_number) + ":" + str(basket_number) + ":" + "%02d" % (sample_number)
        )


class Basket(Container):
    __TYPE__ = "Puck"

    def __init__(self, container, cell_no, basket_no):
        super(Basket, self).__init__(
            self.__TYPE__,
            container,
            Basket.get_basket_address(cell_no, basket_no),
            True,
        )
        for i in range(10):
            slot = Pin(self, cell_no, basket_no, i + 1)
            self._add_component(slot)

    @staticmethod
    def get_basket_address(cell_number, basket_number):
        return str(cell_number) + ":" + str(basket_number)

    def get_cell_no(self):
        return self.get_container().get_index() + 1

    def get_cell(self):
        return self.get_container()

    def clear_info(self):
        self.get_container()._reset_basket_info(self.get_index() + 1)
        self.get_container()._trigger_info_changed_event()


class Cell(Container):
    __TYPE__ = "Cell"

    def __init__(self, container, number):
        super(Cell, self).__init__(
            self.__TYPE__, container, Cell.get_cell_address(number), True
        )
        for i in range(3):
            self._add_component(Basket(self, number, i + 1))

    @staticmethod
    def get_cell_address(cell_number):
        return str(cell_number)

    def _reset_basket_info(self, basket_no):
        pass

    def clear_info(self):
        self.get_container()._reset_cell_info(self.get_index() + 1)
        self.get_container()._trigger_info_changed_event()

    def get_cell(self):
        return self


class Robodiff(SampleChanger):
    __TYPE__ = "HCD"

    def __init__(self, *args, **kwargs):
        super(Robodiff, self).__init__(self.__TYPE__, True, *args, **kwargs)

        for i in range(8):
            cell = Cell(self, i + 1)
            self._add_component(cell)

    def init(self):
        controller = self.getObjectByRole("controller")
        self.dm_reader = getattr(controller, "dm_reader")
        self.dw = self.getObjectByRole("dewar")
        self.robot = controller
        self.detector_translation = self.getObjectByRole("detector_translation")

        return SampleChanger.init(self)

    def get_sample_properties(self):
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)

    def get_basket_list(self):
        basket_list = []
        for cell in self.get_components():
            for basket in cell.get_components():
                if isinstance(basket, Basket):
                    basket_list.append(basket)
        return basket_list

    def _do_change_mode(self, *args, **kwargs):
        return

    def _do_update_info(self):
        self._update_selection()
        self._update_state()

    def _do_scan(self, component, recursive=True, saved={"barcodes": None}):
        def read_barcodes():
            try:
                logging.info("Datamatrix reader: Scanning barcodes")
                barcodes = self.dm_reader.get_barcode()
            except BaseException:
                saved["barcodes"] = [[None] * 11] * 3
            else:
                saved["barcodes"] = barcodes
            logging.info("Scanning completed.")

        def get_barcodes():
            if None in saved.values():
                read_barcodes()
            return saved["barcodes"]

        selected_cell = self.get_selected_component()
        if (selected_cell is None) or (selected_cell != component.get_cell()):
            self._do_select(component)
            read_barcodes()

        if isinstance(component, Sample):
            barcodes = get_barcodes()

            # read one sample dm
            sample_index = component.get_index()
            basket_index = component.get_container().get_index()
            sample_dm = barcodes[basket_index][sample_index]
            sample_present_bool = self.dm_reader.sample_is_present(
                basket_index, sample_index
            )

            component._set_info(sample_present_bool, sample_dm, True)
        elif isinstance(component, Container) and (
            component.get_type() == Basket.__TYPE__
        ):
            barcodes = get_barcodes()

            if recursive:
                # scan one basket dm
                for sample in component.get_components():
                    self._do_scan(sample)

            # get basket dm
            basket_dm = ""
            basket_present_bool = any(barcodes[component.get_index()])
            if basket_present_bool:
                basket_dm = barcodes[component.get_index()][-1]
            component._set_info(basket_present_bool, basket_dm, True)
        elif isinstance(component, Container) and (
            component.get_type() == Cell.__TYPE__
        ):
            for basket in component.get_components():
                self._do_scan(basket, True)
        elif isinstance(component, Container) and (
            component.get_type() == Robodiff.__TYPE__
        ):
            for cell in self.get_components():
                self._do_scan(cell, True)

    def _do_select(self, component):
        if isinstance(component, Cell):
            cell_pos = component.get_index()
            self.dw.moveToPosition(cell_pos + 1)
            self.dw.waitEndOfMove()
            self._update_selection()

    @task
    def load_sample(
        self,
        holderLength,
        sample_id=None,
        sample_location=None,
        sampleIsLoadedCallback=None,
        failureCallback=None,
        prepareCentring=True,
    ):
        cell, basket, sample = sample_location
        sample = self.get_component_by_address(
            Pin.get_sample_address(cell, basket, sample)
        )
        return self.load(sample)

    @task
    def unload_sample(
        self,
        holderLength,
        sample_id=None,
        sample_location=None,
        successCallback=None,
        failureCallback=None,
    ):
        cell, basket, sample = sample_location
        sample = self.get_component_by_address(
            Pin.get_sample_address(cell, basket, sample)
        )
        return self.unload(sample)

    def chained_load(self, sample_to_unload, sample_to_load):
        try:
            self.robot.tg_device.setval3variable(["1", "n_UnloadLoad"])
            return SampleChanger.chained_load(self, sample_to_unload, sample_to_load)
        finally:
            self.robot.tg_device.setval3variable(["0", "n_UnloadLoad"])

    def _do_load(self, sample=None):
        self._do_select(sample.get_cell())
        # move detector to high software limit, without waiting end of move
        # self.detector_translation.set_value(self.detector_translation.get_limits()[1])
        self.prepare_detector()

        # now call load procedure
        load_successful = self.robot.load_sample(
            sample.get_cell_no(), sample.get_basket_no(), sample.get_vial_no()
        )
        if not load_successful:
            return False
        self._set_loaded_sample(sample)
        # update chi position and state
        self.robot.chi._update_channels()
        return True

    def prepare_detector(self):
        # DN to speedup load/unload
        self.robot.detcover.cover_ctrl.set(self.robot.detcover.keys["cover_out_cmd"], 0)
        # move detector to high software limit, without waiting end of move
        self.detector_translation.set_value(self.detector_translation.get_limits()[1])
        while not self.robot.detcover.status() == "IN":
            time.sleep(0.5)

    def _do_unload(self, sample=None):
        # DN to speedup load/unload
        # self.detector_translation.set_value(self.detector_translation.get_limits()[1])
        self.prepare_detector()

        loaded_sample = self.get_loaded_sample()
        if loaded_sample is not None and loaded_sample != sample:
            raise RuntimeError("Can't unload another sample")
        # sample_to_unload = basket_index*10+vial_index
        self.robot.unload_sample(
            sample.get_cell_no(), sample.get_basket_no(), sample.get_vial_no()
        )
        self._reset_loaded_sample()

    def _do_abort(self):
        return

    def _do_reset(self):
        pass

    def clear_basket_info(self, basket):
        return self._reset_basket_info(basket)

    def _reset_basket_info(self, basket):
        pass

    def clear_cell_info(self, cell):
        return self._reset_cell_info(cell)

    def _reset_cell_info(self, cell):
        pass

    def _update_state(self):
        try:
            state = self._read_state()
        except BaseException:
            state = SampleChangerState.Unknown
        if state == SampleChangerState.Moving and self._is_device_busy(
            self.get_state()
        ):
            return
        self._set_state(state)

    def _read_state(self):
        # should read state from robot
        state = self.robot.state()
        state_converter = {
            "ALARM": SampleChangerState.Alarm,
            "FAULT": SampleChangerState.Fault,
            "MOVING": SampleChangerState.Moving,
            "READY": SampleChangerState.Ready,
            "LOADING": SampleChangerState.Charging,
        }
        return state_converter.get(state, SampleChangerState.Unknown)

    def _is_device_busy(self, state=None):
        if state is None:
            state = self._read_state()
        return state not in (
            SampleChangerState.Ready,
            SampleChangerState.Loaded,
            SampleChangerState.Alarm,
            SampleChangerState.Disabled,
            SampleChangerState.Fault,
            SampleChangerState.StandBy,
        )

    def _is_device_ready(self):
        state = self._read_state()
        return state in (SampleChangerState.Ready, SampleChangerState.Charging)

    def _wait_device_ready(self, timeout=None):
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self._is_device_ready():
                gevent.sleep(0.01)

    def _update_selection(self):
        dw_pos = int(self.dw.get_current_position_name()) - 1
        for cell in self.get_components():
            i = cell.get_index()
            if dw_pos == i:
                self._set_selected_component(cell)
                break
        # read nSampleNumber
        robot_sample_no = int(
            self.robot.tg_device.getVal3DoubleVariable("nSampleNumber")
        )
        sample_no = 1 + ((robot_sample_no - 1) % 10)
        puck_no = 1 + ((robot_sample_no - 1) // 10)
        # find sample
        cell = self.get_selected_component()
        for sample in cell.get_sample_list():
            if sample.get_vial_no() == sample_no and sample.get_basket_no() == puck_no:
                self._set_loaded_sample(sample)
                self._set_selected_sample(sample)
                return
        self._set_loaded_sample(None)
        self._set_selected_sample(None)
