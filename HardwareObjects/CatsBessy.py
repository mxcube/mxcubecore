from HardwareRepository.HardwareObjects.abstract.AbstractSampleChanger import *
import time


class Pin(Sample):
    STD_HOLDERLENGTH = 22.0

    def __init__(self, basket, basket_no, sample_no):
        super(Pin, self).__init__(
            basket, Pin.getSampleAddress(basket_no, sample_no), True
        )
        self._setHolderLength(Pin.STD_HOLDERLENGTH)

    def getBasketNo(self):
        return self.getContainer().getIndex() + 1

    def getVialNo(self):
        return self.getIndex() + 1

    @staticmethod
    def getSampleAddress(basket_number, sample_number):
        return str(basket_number) + ":" + "%02d" % (sample_number)


class Basket(Container):
    __TYPE__ = "Puck"
    NO_OF_SAMPLES_PER_PUCK = 10

    def __init__(self, container, number):
        super(Basket, self).__init__(
            self.__TYPE__, container, Basket.getBasketAddress(number), True
        )
        for i in range(Basket.NO_OF_SAMPLES_PER_PUCK):
            slot = Pin(self, number, i + 1)
            self._addComponent(slot)

    @staticmethod
    def getBasketAddress(basket_number):
        return str(basket_number)

    def clearInfo(self):
        self.getContainer()._reset_basket_info(self.getIndex() + 1)
        self.getContainer()._triggerInfoChangedEvent()


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
            self._addComponent(basket)

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
            self._lidStatus.connectSignal("update", self._updateOperationMode)
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
        self._pathRunning = self.add_channel(
            {
                "type": "tango",
                "name": "PathRunning",
                "tangoname": self.tangoname,
                "polling": "events",
            },
            "PathRunning",
        )

        self._initSCContents()

        # SampleChanger.init must be called _after_ initialization of the Cats because it starts the update methods which access
        # the device server's status attributes
        SampleChanger.init(self)

    def getSampleProperties(self):
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)

    # ########################           TASKS           #########################
    def _doUpdateInfo(self):
        self._updateSCContents()
        self._updateSelection()
        self._updateState()
        self._updateLoadedSample()

    def _doChangeMode(self, mode):
        pass

    def getSelectedComponent(self):
        return self.getComponents()[self._selected_basket - 1]

    def _doSelect(self, component):
        if isinstance(component, Sample):
            selected_basket = self.getSelectedComponent()
            if (selected_basket is None) or (
                selected_basket != component.getContainer()
            ):
                # self._executeServerTask(self._select_basket , component.getBasketNo())
                self._selected_basket = component.getBasketNo()
            # self._executeServerTask(self._select_sample, component.getIndex()+1)
            self._selected_sample = component.getIndex() + 1
        elif isinstance(component, Container) and (
            component.getType() == Basket.__TYPE__
        ):
            # self._executeServerTask(self._select_basket, component.getIndex()+1)
            self._selected_basket = component.getIndex() + 1

    def _doAbort(self):
        self._abort()

    def _doScan(self, component, recursive):
        selected_basket = self.getSelectedComponent()
        if isinstance(component, Sample):
            # scan a single sample
            if (selected_basket is None) or (
                selected_basket != component.getContainer()
            ):
                self._doSelect(component)
            # self._executeServerTask(self._scan_samples, [component.getIndex()+1,])
            lid = ((self._selected_basket - 1) / 3) + 1
            sample = (((self._selected_basket - 1) % 3) * 10) + (
                component.getIndex() + 1
            )
            argin = ["2", str(lid), str(sample), "0", "0"]
            self._executeServerTask(self._barcode, argin)
        elif isinstance(component, Container) and (
            component.getType() == Basket.__TYPE__
        ):
            # component is a basket
            if recursive:
                pass
                # self._executeServerTask(self._scan_basket, (component.getIndex()+1))
            else:
                if (selected_basket is None) or (selected_basket != component):
                    self._doSelect(component)
                # self._executeServerTask(self._scan_samples, (0,))
                for sample_index in range(Basket.NO_OF_SAMPLES_PER_PUCK):
                    lid = ((self._selected_basket - 1) / 3) + 1
                    sample = (((self._selected_basket - 1) % 3) * 10) + (
                        sample_index + 1
                    )
                    argin = ["2", str(lid), str(sample), "0", "0"]
                    self._executeServerTask(self._barcode, argin)
        elif isinstance(component, Container) and (component.getType() == SC3.__TYPE__):
            for basket in self.getComponents():
                self._doScan(basket, True)

    def _doLoad(self, sample=None):
        selected = self.getSelectedSample()
        if self.hasLoadedSample():
            if (sample is None) or (sample == self.getLoadedSample()):
                raise Exception(
                    "The sample "
                    + str(self.getLoadedSample().getAddress())
                    + " is already loaded"
                )
            lid = ((self._selected_basket - 1) / 3) + 1
            sample = (((self._selected_basket - 1) % 3) * 10) + self._selected_sample
            argin = ["2", str(lid), str(sample), "0", "0", "0", "0", "0"]
            self._executeServerTask(self._chained_load, argin)
        else:
            if sample is None:
                if selected is None:
                    raise Exception("No sample selected")
                else:
                    sample = selected
            elif (sample is not None) and (sample != selected):
                self._doSelect(sample)
            # self._executeServerTask(self._load,sample.getHolderLength())
            lid = ((self._selected_basket - 1) / 3) + 1
            sample = (((self._selected_basket - 1) % 3) * 10) + self._selected_sample
            argin = ["2", str(lid), str(sample), "0", "0", "0", "0", "0"]
            self._executeServerTask(self._load, argin)

    def _doUnload(self, sample_slot=None):
        if sample_slot is not None:
            self._doSelect(sample_slot)
        argin = ["2", "0", "0", "0", "0"]
        self._executeServerTask(self._unload, argin)

    def _doReset(self):
        self._executeServerTask(self._reset)

    def clearBasketInfo(self, basket):
        self._reset_basket_info(basket)

    # ########################           PRIVATE           #########################
    def _updateOperationMode(self, value):
        self._scIsCharging = not value

    def _executeServerTask(self, method, *args):
        self._waitDeviceReady(3.0)
        task_id = method(*args)
        # introduced wait because it takes some time before the attribute PathRunning is set
        # after launching a transfer
        time.sleep(2.0)
        ret = None
        if task_id is None:  # Reset
            while self._isDeviceBusy():
                gevent.sleep(0.1)
        else:
            while str(self._pathRunning.getValue()).lower() == "true":
                gevent.sleep(0.1)
            # try:
            #    ret = self._check_task_result(task_id)
            # except Exception,err:
            #    raise
            ret = True
        return ret

    def _updateState(self):
        try:
            state = self._readState()
        except BaseException:
            state = SampleChangerState.Unknown
        if state == SampleChangerState.Moving and self._isDeviceBusy(self.getState()):
            return
        if self._scIsCharging and not (state == SampleChangerState.Alarm):
            state = SampleChangerState.Charging
        self._setState(state)

    def _readState(self):
        state = self._state.getValue()
        if state is not None:
            stateStr = str(state).upper()
        else:
            stateStr = ""
        # state = str(self._state.getValue() or "").upper()
        state_converter = {
            "ALARM": SampleChangerState.Alarm,
            "ON": SampleChangerState.Ready,
            "RUNNING": SampleChangerState.Moving,
        }
        return state_converter.get(stateStr, SampleChangerState.Unknown)

    def _isDeviceBusy(self, state=None):
        if state is None:
            state = self._readState()
        return state not in (
            SampleChangerState.Ready,
            SampleChangerState.Loaded,
            SampleChangerState.Alarm,
            SampleChangerState.Disabled,
            SampleChangerState.Fault,
            SampleChangerState.StandBy,
        )

    def _isDeviceReady(self):
        state = self._readState()
        return state in (SampleChangerState.Ready, SampleChangerState.Charging)

    def _waitDeviceReady(self, timeout=None):
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self._isDeviceReady():
                gevent.sleep(0.01)

    def _updateSelection(self):
        basket = None
        sample = None
        try:
            basket_no = self._selected_basket
            if (
                basket_no is not None
                and basket_no > 0
                and basket_no <= CatsBessy.NO_OF_BASKETS
            ):
                basket = self.getComponentByAddress(Basket.getBasketAddress(basket_no))
                sample_no = self._selected_sample
                if (
                    sample_no is not None
                    and sample_no > 0
                    and sample_no <= Basket.NO_OF_SAMPLES_PER_PUCK
                ):
                    sample = self.getComponentByAddress(
                        Pin.getSampleAddress(basket_no, sample_no)
                    )
        except BaseException:
            pass
        self._setSelectedComponent(basket)
        self._setSelectedSample(sample)

    def _updateLoadedSample(self):
        loadedSampleLid = self._lidSampleOnDiff.getValue()
        loadedSampleNum = self._numSampleOnDiff.getValue()
        if loadedSampleLid != -1 or loadedSampleNum != -1:
            lidBase = (loadedSampleLid - 1) * 3
            lidOffset = ((loadedSampleNum - 1) / 10) + 1
            samplePos = ((loadedSampleNum - 1) % 10) + 1
            basket = lidBase + lidOffset
        else:
            basket = None
            samplePos = None

        if basket is not None and samplePos is not None:
            new_sample = self.getComponentByAddress(
                Pin.getSampleAddress(basket, samplePos)
            )
        else:
            new_sample = None

        if self.getLoadedSample() != new_sample:
            # remove 'loaded' flag from old sample but keep all other information
            old_sample = self.getLoadedSample()
            if old_sample is not None:
                # there was a sample on the gonio
                loaded = False
                has_been_loaded = True
                old_sample._setLoaded(loaded, has_been_loaded)
            if new_sample is not None:
                # update information of recently loaded sample
                datamatrix = str(self._barcode.getValue())
                scanned = len(datamatrix) != 0
                if not scanned:
                    datamatrix = "----------"
                loaded = True
                has_been_loaded = True
                new_sample._setInfo(new_sample.isPresent(), datamatrix, scanned)
                new_sample._setLoaded(loaded, has_been_loaded)

    def _initSCContents(self):
        # create temporary list with default basket information
        basket_list = [("", 4)] * CatsBessy.NO_OF_BASKETS
        # write the default basket information into permanent Basket objects
        for basket_index in range(CatsBessy.NO_OF_BASKETS):
            basket = self.getComponents()[basket_index]
            datamatrix = None
            present = scanned = False
            basket._setInfo(present, datamatrix, scanned)

        # create temporary list with default sample information and indices
        sample_list = []
        for basket_index in range(CatsBessy.NO_OF_BASKETS):
            for sample_index in range(Basket.NO_OF_SAMPLES_PER_PUCK):
                sample_list.append(
                    ("", basket_index + 1, sample_index + 1, 1, Pin.STD_HOLDERLENGTH)
                )
        # write the default sample information into permanent Pin objects
        for spl in sample_list:
            sample = self.getComponentByAddress(Pin.getSampleAddress(spl[1], spl[2]))
            datamatrix = None
            present = scanned = loaded = has_been_loaded = False
            sample._setInfo(present, datamatrix, scanned)
            sample._setLoaded(loaded, has_been_loaded)
            sample._setHolderLength(spl[4])

    def _updateSCContents(self):
        for basket_index in range(CatsBessy.NO_OF_BASKETS):
            # get presence information from the device server
            newBasketPresence = self._basketChannels[basket_index].getValue()
            # get saved presence information from object's internal bookkeeping
            basket = self.getComponents()[basket_index]

            # check if the basket was newly mounted or removed from the dewar
            if newBasketPresence ^ basket.isPresent():
                # a mounting action was detected ...
                if newBasketPresence:
                    # basket was mounted
                    present = True
                    scanned = False
                    datamatrix = None
                    basket._setInfo(present, datamatrix, scanned)
                else:
                    # basket was removed
                    present = False
                    scanned = False
                    datamatrix = None
                    basket._setInfo(present, datamatrix, scanned)
                # set the information for all dependent samples
                for sample_index in range(Basket.NO_OF_SAMPLES_PER_PUCK):
                    sample = self.getComponentByAddress(
                        Pin.getSampleAddress((basket_index + 1), (sample_index + 1))
                    )
                    present = sample.getContainer().isPresent()
                    if present:
                        datamatrix = "          "
                    else:
                        datamatrix = None
                    scanned = False
                    sample._setInfo(present, datamatrix, scanned)
                    # forget about any loaded state in newly mounted or removed basket)
                    loaded = has_been_loaded = False
                    sample._setLoaded(loaded, has_been_loaded)
