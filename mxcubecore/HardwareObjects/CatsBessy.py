from HardwareRepository.HardwareObjects.abstract.AbstractSampleChanger import *
import time


class Pin(Sample):
    STD_HOLDERLENGTH = 22.0

    def __init__(self, basket, basket_no, sample_no):
        super(Pin, self).__init__(
            basket, Pin.get_sample_address(basket_no, sample_no), True
        )
        self._set_holder_length(Pin.STD_HOLDERLENGTH)

    def get_basket_no(self):
        return self.get_container().get_index() + 1

    def get_vial_no(self):
        return self.get_index() + 1

    @staticmethod
    def get_sample_address(basket_number, sample_number):
        return str(basket_number) + ":" + "%02d" % (sample_number)


class Basket(Container):
    __TYPE__ = "Puck"
    NO_OF_SAMPLES_PER_PUCK = 10

    def __init__(self, container, number):
        super(Basket, self).__init__(
            self.__TYPE__, container, Basket.get_basket_address(number), True
        )
        for i in range(Basket.NO_OF_SAMPLES_PER_PUCK):
            slot = Pin(self, number, i + 1)
            self._add_component(slot)

    @staticmethod
    def get_basket_address(basket_number):
        return str(basket_number)

    def clear_info(self):
        self.get_container()._reset_basket_info(self.get_index() + 1)
        self.get_container()._trigger_info_changed_event()


class CatsBessy(SampleChanger):
    __TYPE__ = "CATS"
    NO_OF_BASKETS = 9

    """
    Actual implementation of the CATS Sample Changer, BESSY BL14.1 installation
    """

    def __init__(self, *args, **kwargs):
        super(CatsBessy, self).__init__(self.__TYPE__, False, *args, **kwargs)
        for i in range(CatsBessy.NO_OF_BASKETS):
            basket = Basket(self, i + 1)
            self._add_component(basket)

    def init(self):
        self._selected_sample = 1
        self._selected_basket = 1

        self._state = self.get_channel_object("_state")
        self._abort = self.get_command_object("_abort")

        self._basketChannels = []
        for basket_index in range(CatsBessy.NO_OF_BASKETS):
            self._basketChannels.append(
                self.add_channel(
                    {
                        "type": "tango",
                        "name": "di_basket",
                        "tangoname": self.tangoname,
                        "polling": "events",
                    },
                    ("di_Cassette%dPresence" % (basket_index + 1)),
                )
            )

        self._lidStatus = self.add_channel(
            {
                "type": "tango",
                "name": "di_AllLidsClosed",
                "tangoname": self.tangoname,
                "polling": "events",
            },
            "di_AllLidsClosed",
        )
        if self._lidStatus is not None:
            self._lidStatus.connect_signal("update", self._update_operation_mode)
        self._scIsCharging = None

        self._load = self.add_command(
            {"type": "tango", "name": "put_bcrd", "tangoname": self.tangoname},
            "put_bcrd",
        )
        self._unload = self.add_command(
            {"type": "tango", "name": "put_bcrd", "tangoname": self.tangoname}, "get"
        )
        self._chained_load = self.add_command(
            {"type": "tango", "name": "getput_bcrd", "tangoname": self.tangoname},
            "getput_bcrd",
        )
        self._barcode = self.add_command(
            {"type": "tango", "name": "barcode", "tangoname": self.tangoname}, "barcode"
        )
        self._reset = self.add_command(
            {"type": "tango", "name": "reset", "tangoname": self.tangoname}, "reset"
        )
        self._abort = self.add_command(
            {"type": "tango", "name": "abort", "tangoname": self.tangoname}, "abort"
        )

        self._numSampleOnDiff = self.add_channel(
            {
                "type": "tango",
                "name": "NumSampleOnDiff",
                "tangoname": self.tangoname,
                "polling": "events",
            },
            "NumSampleOnDiff",
        )
        self._lidSampleOnDiff = self.add_channel(
            {
                "type": "tango",
                "name": "LidSampleOnDiff",
                "tangoname": self.tangoname,
                "polling": "events",
            },
            "LidSampleOnDiff",
        )
        self._barcode = self.add_channel(
            {
                "type": "tango",
                "name": "Barcode",
                "tangoname": self.tangoname,
                "polling": "events",
            },
            "Barcode",
        )
        self._path_running = self.add_channel(
            {
                "type": "tango",
                "name": "PathRunning",
                "tangoname": self.tangoname,
                "polling": "events",
            },
            "PathRunning",
        )

        self._init_sc_contents()

        # SampleChanger.init must be called _after_ initialization of the Cats because it starts the update methods which access
        # the device server's status attributes
        SampleChanger.init(self)

    def get_sample_properties(self):
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)

    # ########################           TASKS           #########################
    def _do_update_info(self):
        self._updateSCContents()
        self._update_selection()
        self._update_state()
        self._update_loaded_sample()

    def _do_change_mode(self, mode):
        pass

    def get_selected_component(self):
        return self.get_components()[self._selected_basket - 1]

    def _do_select(self, component):
        if isinstance(component, Sample):
            selected_basket = self.get_selected_component()
            if (selected_basket is None) or (
                selected_basket != component.get_container()
            ):
                # self._execute_server_task(self._select_basket , component.get_basket_no())
                self._selected_basket = component.get_basket_no()
            # self._execute_server_task(self._select_sample, component.get_index()+1)
            self._selected_sample = component.get_index() + 1
        elif isinstance(component, Container) and (
            component.get_type() == Basket.__TYPE__
        ):
            # self._execute_server_task(self._select_basket, component.get_index()+1)
            self._selected_basket = component.get_index() + 1

    def _do_abort(self):
        self._abort()

    def _do_scan(self, component, recursive):
        selected_basket = self.get_selected_component()
        if isinstance(component, Sample):
            # scan a single sample
            if (selected_basket is None) or (
                selected_basket != component.get_container()
            ):
                self._do_select(component)
            # self._execute_server_task(self._scan_samples, [component.get_index()+1,])
            lid = ((self._selected_basket - 1) / 3) + 1
            sample = (((self._selected_basket - 1) % 3) * 10) + (
                component.get_index() + 1
            )
            argin = ["2", str(lid), str(sample), "0", "0"]
            self._execute_server_task(self._barcode, argin)
        elif isinstance(component, Container) and (
            component.get_type() == Basket.__TYPE__
        ):
            # component is a basket
            if recursive:
                pass
                # self._execute_server_task(self._scan_basket, (component.get_index()+1))
            else:
                if (selected_basket is None) or (selected_basket != component):
                    self._do_select(component)
                # self._execute_server_task(self._scan_samples, (0,))
                for sample_index in range(Basket.NO_OF_SAMPLES_PER_PUCK):
                    lid = ((self._selected_basket - 1) / 3) + 1
                    sample = (((self._selected_basket - 1) % 3) * 10) + (
                        sample_index + 1
                    )
                    argin = ["2", str(lid), str(sample), "0", "0"]
                    self._execute_server_task(self._barcode, argin)
        elif isinstance(component, Container) and (
            component.get_type() == SC3.__TYPE__
        ):
            for basket in self.get_components():
                self._do_scan(basket, True)

    def _do_load(self, sample=None):
        selected = self.get_selected_sample()
        if self.has_loaded_sample():
            if (sample is None) or (sample == self.get_loaded_sample()):
                raise Exception(
                    "The sample "
                    + str(self.get_loaded_sample().get_address())
                    + " is already loaded"
                )
            lid = ((self._selected_basket - 1) / 3) + 1
            sample = (((self._selected_basket - 1) % 3) * 10) + self._selected_sample
            argin = ["2", str(lid), str(sample), "0", "0", "0", "0", "0"]
            self._execute_server_task(self._chained_load, argin)
        else:
            if sample is None:
                if selected is None:
                    raise Exception("No sample selected")
                else:
                    sample = selected
            elif (sample is not None) and (sample != selected):
                self._do_select(sample)
            # self._execute_server_task(self._load,sample.get_holder_length())
            lid = ((self._selected_basket - 1) / 3) + 1
            sample = (((self._selected_basket - 1) % 3) * 10) + self._selected_sample
            argin = ["2", str(lid), str(sample), "0", "0", "0", "0", "0"]
            self._execute_server_task(self._load, argin)

    def _do_unload(self, sample_slot=None):
        if sample_slot is not None:
            self._do_select(sample_slot)
        argin = ["2", "0", "0", "0", "0"]
        self._execute_server_task(self._unload, argin)

    def _do_reset(self):
        self._execute_server_task(self._reset)

    def clear_basket_info(self, basket):
        self._reset_basket_info(basket)

    # ########################           PRIVATE           #########################
    def _update_operation_mode(self, value):
        self._scIsCharging = not value

    def _execute_server_task(self, method, *args):
        self._wait_device_ready(3.0)
        task_id = method(*args)
        # introduced wait because it takes some time before the attribute PathRunning is set
        # after launching a transfer
        time.sleep(2.0)
        ret = None
        if task_id is None:  # Reset
            while self._is_device_busy():
                gevent.sleep(0.1)
        else:
            while str(self._path_running.get_value()).lower() == "true":
                gevent.sleep(0.1)
            # try:
            #    ret = self._check_task_result(task_id)
            # except Exception,err:
            #    raise
            ret = True
        return ret

    def _update_state(self):
        try:
            state = self._read_state()
        except Exception:
            state = SampleChangerState.Unknown
        if state == SampleChangerState.Moving and self._is_device_busy(
            self.get_state()
        ):
            return
        if self._scIsCharging and not (state == SampleChangerState.Alarm):
            state = SampleChangerState.Charging
        self._set_state(state)

    def _read_state(self):
        state = self._state.get_value()
        if state is not None:
            stateStr = str(state).upper()
        else:
            stateStr = ""
        # state = str(self._state.get_value() or "").upper()
        state_converter = {
            "ALARM": SampleChangerState.Alarm,
            "ON": SampleChangerState.Ready,
            "RUNNING": SampleChangerState.Moving,
        }
        return state_converter.get(stateStr, SampleChangerState.Unknown)

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
        basket = None
        sample = None
        try:
            basket_no = self._selected_basket
            if (
                basket_no is not None
                and basket_no > 0
                and basket_no <= CatsBessy.NO_OF_BASKETS
            ):
                basket = self.get_component_by_address(
                    Basket.get_basket_address(basket_no)
                )
                sample_no = self._selected_sample
                if (
                    sample_no is not None
                    and sample_no > 0
                    and sample_no <= Basket.NO_OF_SAMPLES_PER_PUCK
                ):
                    sample = self.get_component_by_address(
                        Pin.get_sample_address(basket_no, sample_no)
                    )
        except Exception:
            pass
        self._set_selected_component(basket)
        self._set_selected_sample(sample)

    def _update_loaded_sample(self):
        loadedSampleLid = self._lidSampleOnDiff.get_value()
        loadedSampleNum = self._numSampleOnDiff.get_value()
        if loadedSampleLid != -1 or loadedSampleNum != -1:
            lidBase = (loadedSampleLid - 1) * 3
            lidOffset = ((loadedSampleNum - 1) / 10) + 1
            samplePos = ((loadedSampleNum - 1) % 10) + 1
            basket = lidBase + lidOffset
        else:
            basket = None
            samplePos = None

        if basket is not None and samplePos is not None:
            new_sample = self.get_component_by_address(
                Pin.get_sample_address(basket, samplePos)
            )
        else:
            new_sample = None

        if self.get_loaded_sample() != new_sample:
            # remove 'loaded' flag from old sample but keep all other information
            old_sample = self.get_loaded_sample()
            if old_sample is not None:
                # there was a sample on the gonio
                loaded = False
                has_been_loaded = True
                old_sample._set_loaded(loaded, has_been_loaded)
            if new_sample is not None:
                # update information of recently loaded sample
                datamatrix = str(self._barcode.get_value())
                scanned = len(datamatrix) != 0
                if not scanned:
                    datamatrix = "----------"
                loaded = True
                has_been_loaded = True
                new_sample._set_info(new_sample.is_present(), datamatrix, scanned)
                new_sample._set_loaded(loaded, has_been_loaded)

    def _init_sc_contents(self):
        # create temporary list with default basket information
        basket_list = [("", 4)] * CatsBessy.NO_OF_BASKETS
        # write the default basket information into permanent Basket objects
        for basket_index in range(CatsBessy.NO_OF_BASKETS):
            basket = self.get_components()[basket_index]
            datamatrix = None
            present = scanned = False
            basket._set_info(present, datamatrix, scanned)

        # create temporary list with default sample information and indices
        sample_list = []
        for basket_index in range(CatsBessy.NO_OF_BASKETS):
            for sample_index in range(Basket.NO_OF_SAMPLES_PER_PUCK):
                sample_list.append(
                    ("", basket_index + 1, sample_index + 1, 1, Pin.STD_HOLDERLENGTH)
                )
        # write the default sample information into permanent Pin objects
        for spl in sample_list:
            sample = self.get_component_by_address(
                Pin.get_sample_address(spl[1], spl[2])
            )
            datamatrix = None
            present = scanned = loaded = has_been_loaded = False
            sample._set_info(present, datamatrix, scanned)
            sample._set_loaded(loaded, has_been_loaded)
            sample._set_holder_length(spl[4])

    def _updateSCContents(self):
        for basket_index in range(CatsBessy.NO_OF_BASKETS):
            # get presence information from the device server
            newBasketPresence = self._basketChannels[basket_index].get_value()
            # get saved presence information from object's internal bookkeeping
            basket = self.get_components()[basket_index]

            # check if the basket was newly mounted or removed from the dewar
            if newBasketPresence ^ basket.is_present():
                # a mounting action was detected ...
                if newBasketPresence:
                    # basket was mounted
                    present = True
                    scanned = False
                    datamatrix = None
                    basket._set_info(present, datamatrix, scanned)
                else:
                    # basket was removed
                    present = False
                    scanned = False
                    datamatrix = None
                    basket._set_info(present, datamatrix, scanned)
                # set the information for all dependent samples
                for sample_index in range(Basket.NO_OF_SAMPLES_PER_PUCK):
                    sample = self.get_component_by_address(
                        Pin.get_sample_address((basket_index + 1), (sample_index + 1))
                    )
                    present = sample.get_container().is_present()
                    if present:
                        datamatrix = "          "
                    else:
                        datamatrix = None
                    scanned = False
                    sample._set_info(present, datamatrix, scanned)
                    # forget about any loaded state in newly mounted or removed basket)
                    loaded = has_been_loaded = False
                    sample._set_loaded(loaded, has_been_loaded)
