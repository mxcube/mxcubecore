import xml.sax
from xml.sax.handler import ContentHandler

from mxcubecore.HardwareObjects.abstract.AbstractSampleChanger import (
    Container,
    Sample,
    SampleChanger,
    SampleChangerMode,
    SampleChangerState,
    gevent,
    sys,
)


class Pin(Sample):
    def __init__(self, basket, basket_no, sample_no):
        super(Pin, self).__init__(
            basket, Pin.get_sample_address(basket_no, sample_no), True
        )
        self._set_holder_length(22.0)

    def get_basket_no(self):
        return self.get_container().get_index() + 1

    def get_vial_no(self):
        return self.get_index() + 1

    @staticmethod
    def get_sample_address(basket_number, sample_number):
        return str(basket_number) + ":" + "%02d" % (sample_number)


class Basket(Container):
    __TYPE__ = "Puck"

    def __init__(self, container, number):
        super(Basket, self).__init__(
            self.__TYPE__, container, Basket.get_basket_address(number), True
        )
        for i in range(10):
            slot = Pin(self, number, i + 1)
            self._add_component(slot)

    @staticmethod
    def get_basket_address(basket_number):
        return str(basket_number)

    def clear_info(self):
        self.get_container()._reset_basket_info(self.get_index() + 1)
        self.get_container()._trigger_info_changed_event()


class XMLDataMatrixReadingHandler(ContentHandler):
    def __init__(self):
        ContentHandler.__init__(self)
        self.dataMatrixList = []
        self.basketDataMatrixList = [("", 4)] * 5
        self.dataMatrix = ""
        self.basketLocation = -1
        self.sampleLocation = -1
        self.flag = 0
        self.holder_length = 22.0

    def startElement(self, name, attrs):
        self.addBasketLocation = name == "BasketLocation"
        self.addSampleLocation = name == "Location"
        self.addDataMatrix = name == "DataMatrix"
        self.addFlag = name in ("SampleFlag", "BasketFlag")
        self.addHolderLength = name == "HolderLength"

    def characters(self, content):
        if self.addDataMatrix:
            self.dataMatrix = str(content)
        elif self.addBasketLocation:
            self.basketLocation = int(content)
        elif self.addSampleLocation:
            self.sampleLocation = int(content)
        elif self.addFlag:
            self.flag = int(content)
        elif self.addHolderLength:
            self.holder_length = float(content)

    def endElement(self, name):
        if name == "Sample":
            self.dataMatrixList.append(
                (
                    self.dataMatrix,
                    self.basketLocation,
                    self.sampleLocation,
                    self.flag,
                    self.holder_length,
                )
            )
            self.dataMatrix = ""
            self.basketLocation = -1
            self.sampleLocation = -1
            self.flag = 0
            self.holder_length = 22.0
        elif name == "Basket":
            self.basketDataMatrixList[self.sampleLocation - 1] = (
                self.dataMatrix,
                self.flag,
            )
            self.dataMatrix = ""
            self.basketLocation = -1
            self.sampleLocation = -1
            self.flag = 0
            self.holder_length = 22.0
        elif name == "BasketLocation":
            self.addBasketLocation = None
        elif name == "Location":
            self.addSampleLocation = None
        elif name == "DataMatrix":
            self.addDataMatrix = None
        elif name in ("SampleFlag", "BasketFlag"):
            self.addFlag = None
        elif name == "HolderLength":
            self.addHolderLength = None


class SC3(SampleChanger):
    __TYPE__ = "SC3"

    """
    Concrete implementation of SC3 Sample Changer
    """

    def __init__(self, *args, **kwargs):
        super(SC3, self).__init__(self.__TYPE__, True, *args, **kwargs)
        for i in range(5):
            basket = Basket(self, i + 1)
            self._add_component(basket)

    def init(self):
        for channel_name in ("_state", "_selected_basket", "_selected_sample"):
            setattr(self, channel_name, self.get_channel_object(channel_name))

        for command_name in (
            "_abort",
            "_getInfo",
            "_is_task_running",
            "_check_task_result",
            "_load",
            "_unload",
            "_chained_load",
            "_set_sample_charge",
            "_scan_basket",
            "_scan_samples",
            "_select_sample",
            "_select_basket",
            "_reset",
            "_reset_basket_info",
        ):
            setattr(self, command_name, self.get_command_object(command_name))

        SampleChanger.init(self)

    def get_sample_properties(self):
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)

    def get_basket_list(self):
        basket_list = []
        for basket in self.get_components():
            if isinstance(basket, Basket):
                basket_list.append(basket)
        return basket_list

    # ########    TASKS    ########
    def _do_abort(self):
        self._abort()

    def _do_update_info(self):
        try:
            sxml = self._getInfo()
            handler = XMLDataMatrixReadingHandler()
            sxml = sxml.replace(' encoding="utf-16"', "")
            xml.sax.parseString(sxml, handler)
            sample_list = handler.dataMatrixList
            basket_list = handler.basketDataMatrixList
        except Exception:
            basket_list = [("", 4)] * 5
            sample_list = []
            for b in range(5):
                for s in range(10):
                    sample_list.append(("", b + 1, s + 1, 1, 22.0))

        for b in range(5):
            datamatrix = basket_list[b][0]
            if len(datamatrix) == 0:
                datamatrix = None
            flags = basket_list[b][1]

            present = (flags & 3) != 0
            scanned = (flags & 8) != 0
            basket = self.get_components()[b]
            basket._set_info(present, datamatrix, scanned)
        for s in sample_list:
            datamatrix = s[0]
            if len(datamatrix) == 0:
                datamatrix = None
            flags = s[3]
            present = (flags & 6) != 0
            scanned = present
            loaded = (flags & 8) != 0
            has_been_loaded = (flags & 16) != 0
            sample = self.get_component_by_address(Pin.get_sample_address(s[1], s[2]))
            sample._set_info(present, datamatrix, scanned)
            sample._set_loaded(loaded, has_been_loaded)
            sample._set_holder_length(s[4])
        self._update_selection()
        self._update_state()

    def _do_change_mode(self, mode):
        if mode == SampleChangerMode.Charging:
            self._execute_server_task(self._set_sample_charge, True)
        elif mode == SampleChangerMode.Normal:
            self._execute_server_task(self._set_sample_charge, False)

    def _do_scan(self, component, recursive):
        selected_basket = self.get_selected_component()
        if isinstance(component, Sample):
            if (selected_basket is None) or (
                selected_basket != component.get_container()
            ):
                self._do_select(component)
            self._execute_server_task(self._scan_samples, [component.get_index() + 1])

        elif isinstance(component, Container) and (
            component.get_type() == Basket.__TYPE__
        ):
            if recursive:
                self._execute_server_task(
                    self._scan_basket, (component.get_index() + 1)
                )
            else:
                if (selected_basket is None) or (selected_basket != component):
                    self._do_select(component)
                self._execute_server_task(self._scan_samples, (0,))
        elif isinstance(component, Container) and (
            component.get_type() == SC3.__TYPE__
        ):
            for basket in self.get_components():
                self._do_scan(basket, True)

    def _do_select(self, component):
        if isinstance(component, Sample):
            selected_basket = self.get_selected_component()
            if (selected_basket is None) or (
                selected_basket != component.get_container()
            ):
                self._execute_server_task(
                    self._select_basket, component.get_basket_no()
                )
            self._execute_server_task(self._select_sample, component.get_index() + 1)
        elif isinstance(component, Container) and (
            component.get_type() == Basket.__TYPE__
        ):
            self._execute_server_task(self._select_basket, component.get_index() + 1)

    def _do_load(self, sample=None):
        selected = self.get_selected_sample()
        if self.has_loaded_sample():
            if (sample is None) or (sample == self.get_loaded_sample()):
                raise Exception(
                    "The sample "
                    + str(self.get_loaded_sample().get_address())
                    + " is already loaded"
                )
            self._execute_server_task(
                self._chained_load,
                [
                    sample.get_basket_no(),
                    sample.get_vial_no(),
                    sample.get_holder_length(),
                ],
            )
        else:
            if sample is None:
                if selected is None:
                    raise Exception("No sample selected")
                else:
                    sample = selected
            elif (sample is not None) and (sample != selected):
                self._do_select(sample)
            self._execute_server_task(self._load, sample.get_holder_length())

    def _do_unload(self, sample_slot=None):
        if sample_slot is not None:
            self._do_select(sample_slot)
        self._execute_server_task(self._unload)

    def _do_reset(self):
        self._execute_server_task(self._reset)

    def clear_basket_info(self, basket):
        self._reset_basket_info(basket)

    # ########     PRIVATE   ########

    def _execute_server_task(self, method, *args):
        self._wait_device_ready(3.0)
        task_id = method(*args)
        ret = None
        if task_id is None:  # Reset
            while self._is_device_busy():
                gevent.sleep(0.1)
        else:
            while str(self._is_task_running(task_id)).lower() == "true":
                gevent.sleep(0.1)
            try:
                ret = self._check_task_result(task_id)
            except Exception:
                raise
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
        self._set_state(state)

    def _read_state(self):
        state = str(self._state.get_value() or "").upper()
        state_converter = {
            "ALARM": SampleChangerState.Alarm,
            "FAULT": SampleChangerState.Fault,
            "MOVING": SampleChangerState.Moving,
            "STANDBY": SampleChangerState.Ready,
            "READY": SampleChangerState.Ready,
            "RUNNING": SampleChangerState.Moving,
            "LOADING": SampleChangerState.Charging,
            "INIT": SampleChangerState.Initializing,
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
        basket = None
        sample = None
        try:
            basket_no = self._selected_basket.get_value()
            if basket_no is not None and basket_no > 0 and basket_no <= 5:
                basket = self.get_component_by_address(
                    Basket.get_basket_address(basket_no)
                )
                sample_no = self._selected_sample.get_value()
                if sample_no is not None and sample_no > 0 and sample_no <= 10:
                    sample = self.get_component_by_address(
                        Pin.get_sample_address(basket_no, sample_no)
                    )
        except Exception:
            pass
        self._set_selected_component(basket)
        self._set_selected_sample(sample)


if __name__ == "__main__":

    def onStateChanged(state, former):
        print(("State Change:  " + str(former) + " => " + str(state)))

    def onInfoChanged():
        print("Info Changed")

    sc = SC3()
    sc.channel_type = "tango"
    sc.tangoname = "tango://pc445.embl.fr:17100/EMBL/MXSC/1#dbase=no"
    sc.channel_state = "State"
    sc.channel_selected_basket = "SelectedBasketLocation"
    sc.channel_selected_sample = "SelectedSampleLocation"
    sc.command_abort = "abort"
    sc.command_info = "GetInformationAsXML"
    sc.command_is_task_running = "isTaskRunning"
    sc.command_check_task_result = "checkTaskResult"
    sc.command_load = "LoadSample"
    sc.command_unload = "UnLoadSample"
    sc.command_chained_load = "ChainedLoadSample"
    sc.command_set_sample_charge = "SetBasketTransferMode"
    sc.command_scan_basket = "ScanBasketForDatamatrix"
    sc.command_scan_samples = "ScanSamplesForDatamatrix"
    sc.command_select_sample = "MoveSampleLocation"
    sc.command_select_basket = "MoveBasketLocation"
    sc.command_reset = "Reset"

    sc.connect(sc, sc.STATE_CHANGED_EVENT, onStateChanged)
    sc.connect(sc, sc.INFO_CHANGED_EVENT, onInfoChanged)
    sc.init()

    while True:
        try:
            sc.abort()
            sc.reset()
            sc.change_mode(SampleChangerMode.Normal)
            # or else sc.select(sc.get_component_by_address('1'), wait=True)
            sc.select("1", wait=True)
            sc.unload(wait=True)
            sc.load(None, wait=True)
            sc.load("3:04", wait=True)
            sc.unload("4:01", wait=True)
            sc.scan("1:01", wait=True)
            sc.scan("1:02", wait=True)
            sc.scan("1:03", wait=True)
            sc.scan("2:02", wait=True)
            sc.scan("3", wait=True)
            sc.scan("4", recursive=True, wait=True)
        except Exception:
            print((sys.exc_info()[1]))
