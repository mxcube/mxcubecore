"""
CATS sample changer hardware object.

Implements the abstract interface of the GenericSampleChanger for the CATS
sample changer model.
Derived from Alexandre Gobbo's implementation for the EMBL SC3 sample changer.
Derived from Michael Hellmig's implementation for the BESSY CATS sample changer
 -fix the Abort Bug
 -enable setondiff for the catsmaint object
 -fix the bug of MD2 jam during exchange or unload
"""
from abstract.AbstractSampleChanger import *
import time
import qt

__author__ = "Jie Nan"
__credits__ = ["The MxCuBE collaboration"]

__email__ = "jie.nan@maxlab.lu.se"
__status__ = "Alpha"


class Pin(Sample):
    STD_HOLDERLENGTH = 22.0

    def __init__(self, basket, basket_no, sample_no):
        super(Pin, self).__init__(
            basket, Pin.getSampleAddress(basket_no, sample_no), False
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


class MAXLABCats90(SampleChanger):
    """
    Actual implementation of the CATS Sample Changer with 3 lids and 90 samples
    """

    __TYPE__ = "CATS"
    NO_OF_LIDS = 3
    NO_OF_BASKETS = 9

    def __init__(self, *args, **kwargs):
        super(MAXLABCats90, self).__init__(self.__TYPE__, False, *args, **kwargs)

    def init(self):
        self._selected_sample = None
        self._selected_basket = None
        self._scIsCharging = None
        self._startLoad = (
            False
        )  # add flag to disable Load or UnLoad/Exchange Button immediately after 1 click (Avoid Click multiple times)

        # add support for CATS dewars with variable number of lids
        # assumption: each lid provides access to three baskets
        self._propNoOfLids = self.getProperty("no_of_lids")
        if self._propNoOfLids is not None:
            try:
                self.NO_OF_LIDS = int(self._propNoOfLids)
            except ValueError:
                pass
            else:
                self.NO_OF_BASKETS = 3 * self.NO_OF_LIDS

        # initialize the sample changer components, moved here from __init__ after allowing
        # variable number of lids
        for i in range(self.NO_OF_BASKETS):
            basket = Basket(self, i + 1)
            self._addComponent(basket)

        for channel_name in (
            "_chnState",
            "_chnPowered",
            "_chnNumLoadedSample",
            "_chnLidLoadedSample",
            "_chnSampleBarcode",
            "_chnPathRunning",
            "_chnSampleIsDetected",
            "_chnCurrentPhase",
            "_chnTransferMode",
        ):
            setattr(self, channel_name, self.getChannelObject(channel_name))

        for command_name in (
            "_cmdAbort",
            "_cmdLoad",
            "_cmdUnload",
            "_cmdChainedLoad",
            "_cmdRestartMD2",
        ):
            setattr(self, command_name, self.getCommandObject(command_name))

        for basket_index in range(self.NO_OF_BASKETS):
            channel_name = "_chnBasket%dState" % (basket_index + 1)
            setattr(self, channel_name, self.getChannelObject(channel_name))

        self._lidStatus = self.getChannelObject("_chnTotalLidState")
        if self._lidStatus is not None:
            self._lidStatus.connectSignal("update", self._updateOperationMode)

        self._initSCContents()

        # SampleChanger.init must be called _after_ initialization of the Cats because it starts the update methods which access
        # the device server's status attributes
        SampleChanger.init(self)

    def getSampleProperties(self):
        """
        Get the sample's holder length

        :returns: sample length [mm]
        :rtype: double
        """
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)

    def getBasketList(self):
        basket_list = []
        for basket in self.getComponents():
            if isinstance(basket, Basket):
                basket_list.append(basket)
        return basket_list

    #########################           TASKS           #########################

    def _doUpdateInfo(self):
        """
        Updates the sample changers status: mounted pucks, state, currently loaded sample

        :returns: None
        :rtype: None
        """
        self._updateSCContents()
        # periodically updating the selection is not needed anymore, because each call to _doSelect
        # updates the selected component directly:
        # self._updateSelection()
        self._updateState()
        self._updateLoadedSample()

    def _doChangeMode(self, mode):
        """
        Changes the SC operation mode, not implemented for the CATS system

        :returns: None
        :rtype: None
        """
        pass

    def _directlyUpdateSelectedComponent(self, basket_no, sample_no):
        basket = None
        sample = None
        try:
            if (
                basket_no is not None
                and basket_no > 0
                and basket_no <= self.NO_OF_BASKETS
            ):
                basket = self.getComponentByAddress(Basket.getBasketAddress(basket_no))
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

    def _doSelect(self, component):
        """
        Selects a new component (basket or sample).
        Uses method >_directlyUpdateSelectedComponent< to actually search and select the corrected positions.

        :returns: None
        :rtype: None
        """
        if isinstance(component, Sample):
            selected_basket_no = component.getBasketNo()
            selected_sample_no = component.getIndex() + 1
        elif isinstance(component, Container) and (
            component.getType() == Basket.__TYPE__
        ):
            selected_basket_no = component.getIndex() + 1
            selected_sample_no = None
        self._directlyUpdateSelectedComponent(selected_basket_no, selected_sample_no)

    # JN 20150324, load for CATS GUI, no timer and the window will not freeze
    def load_cats(self, sample=None, wait=True):
        """
        Load a sample.
        """
        sample = self._resolveComponent(sample)
        self.assertNotCharging()
        logging.info("call load without a timer")
        if not self._chnPowered.getValue():
            #            raise Exception("CATS power is not enabled. Please switch on arm power before transferring samples.")
            # logging.getLogger("HWR").error("CATS power is not enabled. Please switch on arm power before transferring samples.")
            qt.QMessageBox.warning(
                None,
                "Error",
                "CATS power is not enabled. Please switch on arm power before transferring samples.",
            )
            return

        # JN, 20150512, make sure MD2 TransferMode is "SAMPLE_CHANGER"
        if not self._chnTransferMode.getValue() == "SAMPLE_CHANGER":
            qt.QMessageBox.warning(
                None,
                "Error",
                "TransferMode is %s. Please set the value to SAMPLE_CHANGER in MD2 software."
                % str(self._chnTransferMode.getValue()),
            )
            return

        return self._executeTask(SampleChangerState.Loading, wait, self._doLoad, sample)

    # JN 20150324, add load for queue mount, sample centring can start after
    # MD2 in Centring phase instead of waiting for CATS finishes completely
    def load(self, sample=None, wait=True):
        """
        Load a sample.
         """
        if not self._chnPowered.getValue():
            #            raise Exception("CATS power is not enabled. Please switch on arm power before transferring samples.")
            # logging.getLogger("HWR").error("CATS power is not enabled. Please switch on arm power before transferring samples.")
            qt.QMessageBox.warning(
                None,
                "Error",
                "CATS power is not enabled. Please switch on arm power before transferring samples.",
            )
            raise Exception(
                "CATS power is not enabled. Please switch on arm power before transferring samples."
            )
            return

        # JN, 20150512, make sure MD2 TransferMode is "SAMPLE_CHANGER"
        if not self._chnTransferMode.getValue() == "SAMPLE_CHANGER":
            qt.QMessageBox.warning(
                None,
                "Error",
                "TransferMode is %s. Please set the value to SAMPLE_CHANGER in MD2 software."
                % str(self._chnTransferMode.getValue()),
            )
            raise Exception(
                "TransferMode is %s. Please set the value to SAMPLE_CHANGER in MD2 software."
                % str(self._chnTransferMode.getValue())
            )
            return

        sample = self._resolveComponent(sample)
        self.assertNotCharging()
        # Do a chained load in this case
        # if self.hasLoadedSample():
        # Do a chained load in this case
        # raise Exception("A sample is loaded")
        # if self.getLoadedSample() == sample:
        #    raise Exception("The sample " + sample.getAddress() + " is already loaded")

        # return self._executeTask(SampleChangerState.Loading,wait,self._doLoad,sample)
        logging.info("call load with a timer")
        self._executeTask(SampleChangerState.Loading, False, self._doLoad, sample)
        timeout = 0
        time.sleep(
            20
        )  # in case MD2 starts with Centring phase before loading the new sample
        while self._chnCurrentPhase.getValue() != "Centring":
            if timeout > 60:
                logging.info("waited for too long, change to centring mode manually")
                return
            time.sleep(1)
            timeout += 1
            logging.info("current phase is " + self._chnCurrentPhase.getValue())

    def _doScan(self, component, recursive):
        """
        Scans the barcode of a single sample, puck or recursively even the complete sample changer.

        :returns: None
        :rtype: None
        """
        selected_basket = self.getSelectedComponent()
        if isinstance(component, Sample):
            # scan a single sample
            if (selected_basket is None) or (
                selected_basket != component.getContainer()
            ):
                self._doSelect(component)
            selected = self.getSelectedSample()
            # self._executeServerTask(self._scan_samples, [component.getIndex()+1,])
            lid = ((selected.getBasketNo() - 1) / 3) + 1
            sample = (((selected.getBasketNo() - 1) % 3) * 10) + selected.getVialNo()
            argin = ["2", str(lid), str(sample), "0", "0"]
            self._executeServerTask(self._cmdScanSample, argin)
            self._updateSampleBarcode(component)
        elif isinstance(component, Container) and (
            component.getType() == Basket.__TYPE__
        ):
            # component is a basket
            if recursive:
                pass
            else:
                if (selected_basket is None) or (selected_basket != component):
                    self._doSelect(component)
                # self._executeServerTask(self._scan_samples, (0,))
                selected = self.getSelectedSample()
                for sample_index in range(Basket.NO_OF_SAMPLES_PER_PUCK):
                    lid = ((selected.getBasketNo() - 1) / 3) + 1
                    sample = (((selected.getBasketNo() - 1) % 3) * 10) + (
                        sample_index + 1
                    )
                    argin = ["2", str(lid), str(sample), "0", "0"]
                    self._executeServerTask(self._cmdScanSample, argin)
        elif isinstance(component, Container) and (component.getType() == SC3.__TYPE__):
            for basket in self.getComponents():
                self._doScan(basket, True)

    def _doLoad(self, sample=None):
        """
        Loads a sample on the diffractometer. Performs a simple put operation if the diffractometer is empty, and
        a sample exchange (unmount of old + mount of new sample) if a sample is already mounted on the diffractometer.

        :returns: None
        :rtype: None
        """

        selected = self.getSelectedSample()
        if sample is not None:
            if sample != selected:
                self._doSelect(sample)
                selected = self.getSelectedSample()
        else:
            if selected is not None:
                sample = selected
            else:
                raise Exception("No sample selected")

        # calculate CATS specific lid/sample number
        lid = ((selected.getBasketNo() - 1) / 3) + 1
        sample = (((selected.getBasketNo() - 1) % 3) * 10) + selected.getVialNo()
        argin = ["2", str(lid), str(sample), "0", "0", "0", "0", "0"]

        if self.hasLoadedSample():
            if selected == self.getLoadedSample():
                raise Exception(
                    "The sample "
                    + str(self.getLoadedSample().getAddress())
                    + " is already loaded"
                )
            else:
                self._startLoad = True
                self._cmdRestartMD2(
                    0
                )  # fix the bug of waiting for MD2 by a hot restart, JN,20140708
                time.sleep(5)  # wait for the MD2 restart
                self._startLoad = False
                self._executeServerTask(self._cmdChainedLoad, argin)
        else:
            self._executeServerTask(self._cmdLoad, argin)

    def _doUnload(self, sample_slot=None):
        """
        Unloads a sample from the diffractometer.

        :returns: None
        :rtype: None
        """
        if not self._chnPowered.getValue():
            raise Exception(
                "CATS power is not enabled. Please switch on arm power before transferring samples."
            )

        if sample_slot is not None:
            self._doSelect(sample_slot)
        argin = ["2", "0", "0", "0", "0"]
        self._startLoad = True

        self._cmdRestartMD2(
            0
        )  # fix the bug of waiting for MD2 by a hot restart, JN,20140703
        time.sleep(5)  # wait for the MD2 restart
        self._startLoad = False
        self._executeServerTask(self._cmdUnload, argin)

    def clearBasketInfo(self, basket):
        pass

    ################################################################################

    def _doAbort(self):
        """
        Aborts a running trajectory on the sample changer.

        :returns: None
        :rtype: None
        """
        self._cmdAbort()

    def _doReset(self):
        pass

    #########################           PRIVATE           #########################

    def _updateOperationMode(self, value):
        self._scIsCharging = not value

    def _executeServerTask(self, method, *args):
        """
        Executes a task on the CATS Tango device server

        :returns: None
        :rtype: None
        """
        self._waitDeviceReady(3.0)
        task_id = method(*args)
        print "self._executeServerTask", task_id
        ret = None
        if task_id is None:  # Reset
            while self._isDeviceBusy():
                gevent.sleep(0.1)
        else:
            # introduced wait because it takes some time before the attribute PathRunning is set
            # after launching a transfer
            time.sleep(2.0)
            while str(self._chnPathRunning.getValue()).lower() == "true":
                gevent.sleep(0.1)
            ret = True
        return ret

    def _updateState(self):
        """
        Updates the state of the hardware object

        :returns: None
        :rtype: None
        """
        try:
            state = self._readState()
        except BaseException:
            state = SampleChangerState.Unknown
        if state == SampleChangerState.Moving and self._isDeviceBusy(self.getState()):
            # print "*** _updateState return"
            return

        # _chnSampleIsDetected does not exist in our CATS.
        if self.hasLoadedSample() ^ self._chnSampleIsDetected.getValue():
            # go to Unknown state if a sample is detected on the gonio but not registered in the internal database
            # or registered but not on the gonio anymore
            state = SampleChangerState.Unknown
        elif self._chnPathRunning.getValue() and not (
            state in [SampleChangerState.Loading, SampleChangerState.Unloading]
        ):
            state = SampleChangerState.Moving
        elif self._scIsCharging and not (
            state
            in [
                SampleChangerState.Alarm,
                SampleChangerState.Moving,
                SampleChangerState.Loading,
                SampleChangerState.Unloading,
            ]
        ):
            state = SampleChangerState.Charging
        self._setState(state)

    def _readState(self):
        """
        Read the state of the Tango DS and translate the state to the SampleChangerState Enum

        :returns: Sample changer state
        :rtype: AbstractSampleChanger.SampleChangerState
        """
        state = self._chnState.getValue()
        # print "*** _readState: ", state
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
        """
        Checks whether Sample changer HO is busy.

        :returns: True if the sample changer is busy
        :rtype: Bool
        """
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
        """
        Checks whether Sample changer HO is ready.

        :returns: True if the sample changer is ready
        :rtype: Bool
        """
        state = self._readState()
        return state in (SampleChangerState.Ready, SampleChangerState.Charging)

    def _waitDeviceReady(self, timeout=None):
        """
        Waits until the samle changer HO is ready.

        :returns: None
        :rtype: None
        """

        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self._isDeviceReady():
                gevent.sleep(0.01)

    def _updateSelection(self):
        """
        Updates the selected basket and sample. NOT USED ANYMORE FOR THE CATS.
        Legacy method left from the implementation of the SC3 where the currently selected sample
        is always read directly from the SC3 Tango DS

        :returns: None
        :rtype: None
        """
        # import pdb; pdb.set_trace()
        basket = None
        sample = None
        # print "_updateSelection: saved selection: ", self._selected_basket,
        # self._selected_sample
        try:
            basket_no = self._selected_basket
            if (
                basket_no is not None
                and basket_no > 0
                and basket_no <= self.NO_OF_BASKETS
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
        # if basket is not None and sample is not None:
        #    print "_updateSelection: basket: ", basket, basket.getIndex()
        #    print "_updateSelection: sample: ", sample, sample.getIndex()
        self._setSelectedComponent(basket)
        self._setSelectedSample(sample)

    def _updateLoadedSample(self):
        """
        Reads the currently mounted sample basket and pin indices from the CATS Tango DS,
        translates the lid/sample notation into the basket/sample notation and marks the
        respective sample as loaded.

        :returns: None
        :rtype: None
        """
        loadedSampleLid = self._chnLidLoadedSample.getValue()
        loadedSampleNum = self._chnNumLoadedSample.getValue()
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
            # import pdb; pdb.set_trace()
            # remove 'loaded' flag from old sample but keep all other information
            old_sample = self.getLoadedSample()
            if old_sample is not None:
                # there was a sample on the gonio
                loaded = False
                has_been_loaded = True
                old_sample._setLoaded(loaded, has_been_loaded)
            if new_sample is not None:
                self._updateSampleBarcode(new_sample)
                loaded = True
                has_been_loaded = True
                new_sample._setLoaded(loaded, has_been_loaded)

    def _updateSampleBarcode(self, sample):
        """
        Updates the barcode of >sample< in the local database after scanning with
        the barcode reader.

        :returns: None
        :rtype: None
        """
        # update information of recently scanned sample
        datamatrix = str(self._chnSampleBarcode.getValue())
        scanned = len(datamatrix) != 0
        if not scanned:
            datamatrix = "----------"
        sample._setInfo(sample.isPresent(), datamatrix, scanned)

    def _initSCContents(self):
        """
        Initializes the sample changer content with default values.

        :returns: None
        :rtype: None
        """
        # create temporary list with default basket information
        basket_list = [("", 4)] * self.NO_OF_BASKETS
        # write the default basket information into permanent Basket objects
        for basket_index in range(self.NO_OF_BASKETS):
            basket = self.getComponents()[basket_index]
            datamatrix = None
            present = scanned = False
            basket._setInfo(present, datamatrix, scanned)

        # create temporary list with default sample information and indices
        sample_list = []
        for basket_index in range(self.NO_OF_BASKETS):
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
        """
        Updates the sample changer content. The state of the puck positions are
        read from the respective channels in the CATS Tango DS.
        The CATS sample sample does not have an detection of each individual sample, so all
        samples are flagged as 'Present' if the respective puck is mounted.

        :returns: None
        :rtype: None
        """
        for basket_index in range(self.NO_OF_BASKETS):
            # get presence information from the device server
            newBasketPresence = getattr(
                self, "_chnBasket%dState" % (basket_index + 1)
            ).getValue()
            # get saved presence information from object's internal bookkeeping
            basket = self.getComponents()[basket_index]

            # check if the basket was newly mounted or removed from the dewar
            if newBasketPresence ^ basket.isPresent():
                # import pdb; pdb.set_trace()
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
