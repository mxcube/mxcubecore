"""
CATS sample changer hardware object.

Implements the abstract interface of the AbstractSampleChanger for the CATS
and ISARA sample changer model.

Derived from Alexandre Gobbo's implementation for the EMBL SC3 sample changer.
Derived from Michael Hellmig's implementation for the BESSY CATS sample changer

Known sites using cats90
   BESSY -
       BL14. (CATS) 3lid * 3puck (SPINE) * 10 = 90 samples
   ALBA -
       XALOC. (CATS) 3lid * 3puck (UNIPUCK) * 16 = 144 samples
   MAXIV -
       BIOMAX. (ISARA) 1 lid * 10puck (SPINE) * 10 + 19puck (UNIPUCK) * 16 = 404 samples
   SOLEIL
       PX1. (CATS)
       PX2. (CATS)
"""

from __future__ import print_function

import logging
import time

import PyTango

from mxcubecore.HardwareObjects.abstract.AbstractSampleChanger import (
    Container,
    Sample,
    SampleChanger,
    SampleChangerState,
    argin,
    gevent,
    has_been_loaded,
    new_loaded,
)

__author__ = "Michael Hellmig, Jie Nan, Bixente Rey"
__credits__ = ["The MXCuBE collaboration"]

__email__ = "txo@txolutions.com"

#
# Attention. Numbers here correspond to values returned by CassetteType of device server
#
BASKET_UNKNOWN, BASKET_SPINE, BASKET_UNIPUCK = (0, 1, 2)

#
# Number of samples per puck type
#
SAMPLES_SPINE = 10
SAMPLES_UNIPUCK = 16

TOOL_FLANGE, TOOL_UNIPUCK, TOOL_SPINE, TOOL_PLATE, TOOL_LASER, TOOL_DOUBLE_GRIPPER = (
    0,
    1,
    2,
    3,
    4,
    5,
)

TOOL_TO_STR = {
    "Flange": TOOL_FLANGE,
    "Unipuck": TOOL_UNIPUCK,
    "EMBL": TOOL_SPINE,
    "Plate": TOOL_PLATE,
    "Laser": TOOL_LASER,
    "Double": TOOL_DOUBLE_GRIPPER,
}


def cats_basket_presence_void(value, basket=1):
    logging.getLogger("HWR").warning(
        "Basket %s presence changed void. %s" % (basket, value)
    )


class Basket(Container):
    __TYPE__ = "Puck"

    def __init__(self, container, number, samples_num=10, name="Puck"):
        super(Basket, self).__init__(
            self.__TYPE__, container, Basket.get_basket_address(number), True
        )

        self.samples_num = samples_num

        for i in range(samples_num):
            slot = Pin(self, number, i + 1)
            self._add_component(slot)

    @staticmethod
    def get_basket_address(basket_number):
        return str(basket_number)

    def get_number_of_samples(self):
        return self.samples_num

    def clear_info(self):
        # self.get_container()._reset_basket_info(self.get_index()+1)
        self.get_container()._trigger_info_changed_event()


class SpineBasket(Basket):
    def __init__(self, container, number, name="SpinePuck"):
        super(SpineBasket, self).__init__(
            container, Basket.get_basket_address(number), SAMPLES_SPINE, True
        )


class UnipuckBasket(Basket):
    def __init__(self, container, number, name="UniPuck"):
        super(UnipuckBasket, self).__init__(
            container, Basket.get_basket_address(number), SAMPLES_UNIPUCK, True
        )


class Pin(Sample):
    STD_HOLDERLENGTH = 22.0

    def __init__(self, basket, basket_no, sample_no):
        super(Pin, self).__init__(
            basket, Pin.get_sample_address(basket_no, sample_no), False
        )
        self._set_holder_length(Pin.STD_HOLDERLENGTH)

    def get_basket_no(self):
        return self.get_container().get_index() + 1

    def get_vial_no(self):
        return self.get_index() + 1

    @staticmethod
    def get_sample_address(basket_number, sample_number):
        if basket_number is not None and sample_number is not None:
            return str(basket_number) + ":" + "%02d" % (sample_number)
        else:
            return ""


class Cats90(SampleChanger):
    """

    Actual implementation of the CATS Sample Changer,
       BESSY BL14.1 installation with 3 lids and 90 samples

    """

    __TYPE__ = "CATS"

    default_no_lids = 3
    baskets_per_lid = 3

    default_basket_type = BASKET_SPINE

    def __init__(self, *args, **kwargs):
        super(Cats90, self).__init__(self.__TYPE__, False, *args, **kwargs)

    def init(self):
        #
        # DO NOT CALL SampleChanger.init()
        #  If SampleChanger.init() is called reception of signals at connection time is not done.
        #
        #  In the case of Cats90 we do not use an update_timer... update is done by signals from Tango channels
        #

        self._selected_sample = None
        self._selected_basket = None
        self._scIsCharging = None

        self.read_datamatrix = False
        self.unipuck_tool = TOOL_UNIPUCK

        self.former_loaded = None
        self.cats_device = None

        self.cats_datamatrix = ""
        self.cats_loaded_lid = None
        self.cats_loaded_num = None

        # Default values
        self.cats_powered = False
        self.cats_status = ""
        self.cats_running = False
        self.cats_state = PyTango.DevState.UNKNOWN
        self.cats_lids_closed = False

        self.basket_types = None
        self.number_of_baskets = None

        # add support for CATS dewars with variable number of lids

        # Create channels from XML

        self.cats_device = PyTango.DeviceProxy(self.get_property("tangoname"))

        no_of_lids = self.get_property("no_of_lids")
        if no_of_lids is None:
            self.number_of_lids = self.default_no_lids
        else:
            self.number_of_lids = int(no_of_lids)

        # Create channels
        self._chnState = self.get_channel_object("_chnState", optional=True)
        if self._chnState is None:
            self._chnState = self.add_channel(
                {
                    "type": "tango",
                    "name": "_chnState",
                    "tangoname": self.tangoname,
                    "polling": 300,
                },
                "State",
            )

        self._chnStatus = self.get_channel_object("_chnStatus", optional=True)
        if self._chnStatus is None:
            self._chnStatus = self.add_channel(
                {
                    "type": "tango",
                    "name": "_chnStatus",
                    "tangoname": self.tangoname,
                    "polling": 300,
                },
                "Status",
            )

        self._chnPowered = self.get_channel_object("_chnPowered", optional=True)
        if self._chnPowered is None:
            self._chnPowered = self.add_channel(
                {
                    "type": "tango",
                    "name": "_chnPowered",
                    "tangoname": self.tangoname,
                    "polling": 300,
                },
                "Powered",
            )

        self._chnPathRunning = self.get_channel_object("_chnPathRunning", optional=True)
        if self._chnPathRunning is None:
            self._chnPathRunning = self.add_channel(
                {
                    "type": "tango",
                    "name": "_chnPathRunning",
                    "tangoname": self.tangoname,
                    "polling": 1000,
                },
                "PathRunning",
            )

        self._chnPathSafe = self.get_channel_object("_chnPathSafe", optional=True)
        if self._chnPathSafe is None:
            self._chnPathSafe = self.add_channel(
                {
                    "type": "tango",
                    "name": "_chnPathSafe",
                    "tangoname": self.tangoname,
                    "polling": 1000,
                },
                "PathSafe",
            )

        self._chnNumLoadedSample = self.get_channel_object(
            "_chnNumLoadedSample", optional=True
        )
        if self._chnNumLoadedSample is None:
            self._chnNumLoadedSample = self.add_channel(
                {
                    "type": "tango",
                    "name": "_chnNumLoadedSample",
                    "tangoname": self.tangoname,
                    "polling": 1000,
                },
                "NumSampleOnDiff",
            )

        self._chnLidLoadedSample = self.get_channel_object(
            "_chnLidLoadedSample", optional=True
        )
        if self._chnLidLoadedSample is None:
            self._chnLidLoadedSample = self.add_channel(
                {
                    "type": "tango",
                    "name": "_chnLidLoadedSample",
                    "tangoname": self.tangoname,
                    "polling": 1000,
                },
                "LidSampleOnDiff",
            )

        self._chnSampleBarcode = self.get_channel_object(
            "_chnSampleBarcode", optional=True
        )
        if self._chnSampleBarcode is None:
            self._chnSampleBarcode = self.add_channel(
                {
                    "type": "tango",
                    "name": "_chnSampleBarcode",
                    "tangoname": self.tangoname,
                    "polling": 1000,
                },
                "Barcode",
            )

        self._chnSampleIsDetected = self.get_channel_object(
            "_chnSampleIsDetected", optional=True
        )
        if self._chnSampleIsDetected is None:
            self._chnSampleIsDetected = self.add_channel(
                {
                    "type": "tango",
                    "name": "_chnSampleIsDetected",
                    "tangoname": self.tangoname,
                },
                "di_PRI_SOM",
            )

        self._chnAllLidsClosed = self.get_channel_object(
            "_chnTotalLidState", optional=True
        )
        if self._chnAllLidsClosed is None:
            self._chnAllLidsClosed = self.add_channel(
                {
                    "type": "tango",
                    "name": "_chnAllLidsClosed",
                    "tangoname": self.tangoname,
                    "polling": 1000,
                },
                "di_AllLidsClosed",
            )

        self._chnCurrentTool = self.get_channel_object("_chnCurrentTool", optional=True)
        if self._chnCurrentTool is None:
            self._chnCurrentTool = self.add_channel(
                {
                    "type": "tango",
                    "name": "_chnCurrentTool",
                    "tangoname": self.tangoname,
                },
                "Tool",
            )

        # commands
        self._cmdLoad = self.get_command_object("_cmdLoad")
        if self._cmdLoad is None:
            self._cmdLoad = self.add_command(
                {"type": "tango", "name": "_cmdLoad", "tangoname": self.tangoname},
                "put",
            )

        self._cmdUnload = self.get_command_object("_cmdUnload")
        if self._cmdUnload is None:
            self._cmdUnload = self.add_command(
                {"type": "tango", "name": "_cmdUnload", "tangoname": self.tangoname},
                "get",
            )

        self._cmdChainedLoad = self.get_command_object("_cmdChainedLoad")
        if self._cmdChainedLoad is None:
            self._cmdChainedLoad = self.add_command(
                {
                    "type": "tango",
                    "name": "_cmdChainedLoad",
                    "tangoname": self.tangoname,
                },
                "getput",
            )

        self._cmdAbort = self.get_command_object("_cmdAbort")
        if self._cmdAbort is None:
            self._cmdAbort = self.add_command(
                {"type": "tango", "name": "_cmdAbort", "tangoname": self.tangoname},
                "abort",
            )

        self._cmdPowerOn = self.get_command_object("_cmdPowerOn")
        if self._cmdPowerOn is None:
            self._cmdPowerOn = self.add_command(
                {"type": "tango", "name": "_cmdPowerOn", "tangoname": self.tangoname},
                "powerOn",
            )

        self._cmdLoadBarcode = self.get_command_object("_cmdLoadBarcode")
        if self._cmdLoadBarcode is None:
            self._cmdLoadBarcode = self.add_command(
                {
                    "type": "tango",
                    "name": "_cmdLoadBarcode",
                    "tangoname": self.tangoname,
                },
                "put_bcrd",
            )

        self._cmdChainedLoadBarcode = self.get_command_object("_cmdChainedLoadBarcode")
        if self._cmdChainedLoadBarcode is None:
            self._cmdChainedLoadBarcode = self.add_command(
                {
                    "type": "tango",
                    "name": "_cmdChainedLoadBarcode",
                    "tangoname": self.tangoname,
                },
                "getput_bcrd",
            )

        self._cmdScanSample = self.get_command_object("_cmdScanSample")
        if self._cmdScanSample is None:
            self._cmdScanSample = self.add_command(
                {
                    "type": "tango",
                    "name": "_cmdScanSample",
                    "tangoname": self.tangoname,
                },
                "barcode",
            )

        # see if we can find model from devserver. Otherwise... CATS
        try:
            self.cats_model = self.cats_device.read_attribute("CatsModel").value
        except PyTango.DevFailed:
            self.cats_model = "CATS"

        # see if the device server can return CassetteTypes (and then number of
        # cassettes/baskets)
        try:
            self.basket_types = self.cats_device.read_attribute("CassetteType").value
            self.number_of_baskets = len(self.basket_types)
        except PyTango.DevFailed:
            pass

        # find number of baskets and number of samples per basket
        if self.number_of_baskets is not None:
            if self.is_cats():
                # if CATS... uniform type of baskets. the first number in CassetteType
                # is used for all
                basket_type = self.basket_types[0]
                if basket_type is BASKET_UNIPUCK:
                    self.samples_per_basket = SAMPLES_UNIPUCK
                else:
                    self.samples_per_basket = SAMPLES_SPINE
            else:
                self.samples_per_basket = None
        else:
            # ok. it does not. use good old way (xml or default) to find nb baskets
            # and samples
            no_of_baskets = self.get_property("no_of_baskets")
            samples_per_basket = self.get_property("samples_per_basket")

            if no_of_baskets is None:
                self.number_of_baskets = self.baskets_per_lid * self.number_of_lids
            else:
                self.number_of_baskets = int(no_of_baskets)

            self.basket_types = [None] * self.number_of_baskets

            if samples_per_basket is None:
                self.samples_per_basket = SAMPLES_SPINE
            else:
                self.samples_per_basket = int(samples_per_basket)

        # declare channels to detect basket presence changes
        if self.is_isara():
            self.basket_channels = None
            self._chnBasketPresence = self.get_channel_object(
                "_chnBasketPresence", optional=True
            )
            if self._chnBasketPresence is None:
                self._chnBasketPresence = self.add_channel(
                    {
                        "type": "tango",
                        "name": "_chnBasketPresence",
                        "tangoname": self.tangoname,
                        "polling": 1000,
                    },
                    "CassettePresence",
                )
            self.samples_per_basket = None
        else:
            self.basket_channels = [None] * self.number_of_baskets

            for basket_index in range(self.number_of_baskets):
                channel_name = "_chnBasket%dState" % (basket_index + 1)
                chan = self.get_channel_object(channel_name, optional=True)
                if chan is None:
                    chan = self.add_channel(
                        {
                            "type": "tango",
                            "name": channel_name,
                            "tangoname": self.tangoname,
                            "polling": 1000,
                        },
                        "di_Cassette%dPresence" % (basket_index + 1),
                    )
                self.basket_channels[basket_index] = chan
                logging.getLogger("HWR").debug(
                    "Creating channel for cassette presence %d" % (basket_index + 1)
                )

        #
        # determine Cats geometry and prepare objects
        #
        self._init_sc_contents()

        #
        # connect channel signals to update info
        #

        self.use_update_timer = False  # do not use update_timer for Cats

        self._chnState.connect_signal("update", self.cats_state_changed)
        self._chnStatus.connect_signal("update", self.cats_status_changed)
        self._chnPathRunning.connect_signal("update", self.cats_pathrunning_changed)
        self._chnPowered.connect_signal("update", self.cats_powered_changed)
        self._chnPathSafe.connect_signal("update", self.cats_pathsafe_changed)
        self._chnAllLidsClosed.connect_signal("update", self.cats_lids_closed_changed)
        self._chnLidLoadedSample.connect_signal("update", self.cats_loaded_lid_changed)
        self._chnNumLoadedSample.connect_signal("update", self.cats_loaded_num_changed)
        self._chnSampleBarcode.connect_signal("update", self.cats_barcode_changed)

        # connect presence channels
        if self.basket_channels is not None:  # old device server
            for basket_index in range(self.number_of_baskets):
                channel = self.basket_channels[basket_index]
                channel.connect_signal("update", self.cats_basket_presence_changed)
        else:  # new device server with global CassettePresence attribute
            self._chnBasketPresence.connect_signal("update", self.cats_baskets_changed)

        # Read other XML properties
        read_datamatrix = self.get_property("read_datamatrix")
        if read_datamatrix:
            self.set_read_barcode(True)

        unipuck_tool = self.get_property("unipuck_tool")
        try:
            unipuck_tool = int(unipuck_tool)
            if unipuck_tool:
                self.set_unipuck_tool(unipuck_tool)
        except Exception:
            pass

        self.update_info()

    def connect_notify(self, signal):
        if signal == SampleChanger.INFO_CHANGED_EVENT:
            self._update_cats_contents()

    def is_isara(self):
        return self.cats_model == "ISARA"

    def is_cats(self):
        return self.cats_model == "CATS"

    def _init_sc_contents(self):
        """
        Initializes the sample changer content with default values.

        :returns: None
        :rtype: None
        """
        logging.getLogger("HWR").warning("Cats90:  initializing contents")

        self.basket_presence = [None] * self.number_of_baskets

        for i in range(self.number_of_baskets):
            if self.basket_types[i] == BASKET_SPINE:
                basket = SpineBasket(self, i + 1)
            elif self.basket_types[i] == BASKET_UNIPUCK:
                basket = UnipuckBasket(self, i + 1)
            else:
                basket = Basket(self, i + 1, samples_num=self.samples_per_basket)

            self._add_component(basket)

        # write the default basket information into permanent Basket objects
        for basket_index in range(self.number_of_baskets):
            basket = self.get_components()[basket_index]
            datamatrix = None
            present = scanned = False
            basket._set_info(present, datamatrix, scanned)

        # create temporary list with default sample information and indices
        sample_list = []
        for basket_index in range(self.number_of_baskets):
            basket = self.get_components()[basket_index]
            for sample_index in range(basket.get_number_of_samples()):
                sample_list.append(
                    ("", basket_index + 1, sample_index + 1, 1, Pin.STD_HOLDERLENGTH)
                )

        # write the default sample information into permanent Pin objects
        for spl in sample_list:
            sample = self.get_component_by_address(
                Pin.get_sample_address(spl[1], spl[2])
            )
            datamatrix = None
            present = scanned = loaded = _has_been_loaded = False
            sample._set_info(present, datamatrix, scanned)
            sample._set_loaded(loaded, has_been_loaded)
            sample._set_holder_length(spl[4])

        logging.getLogger("HWR").warning("Cats90:  initializing contents done")

    def get_sample_properties(self):
        """
        Get the sample's holder length

        :returns: sample length [mm]
        :rtype: double
        """
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)

    def get_basket_list(self):
        basket_list = []
        for basket in self.get_components():
            if isinstance(basket, Basket):
                basket_list.append(basket)
        return basket_list

    def is_powered(self):
        return self._chnPowered.get_value()

    def is_path_running(self):
        return self._chnPathRunning.get_value()

    def set_read_barcode(self, value):
        """
        Activates reading of barcode during load or chained load trajectory
        Internally it will use put() or put_bcrd() in PyCats dev. server

        :value:  boolean argument
        """
        self.read_datamatrix = value

    def set_unipuck_tool(self, value):
        if value in [TOOL_UNIPUCK, TOOL_DOUBLE_GRIPPER]:
            self.unipuck_tool = value
        else:
            logging.warning(
                "wrong unipuck tool selected %s (valid: %s/%s). Selection IGNORED"
                % (value, TOOL_UNIPUCK, TOOL_DOUBLE_GRIPPER)
            )

    # ########################           TASKS           #########################

    def _do_update_info(self):
        """
        Updates the sample changers status: mounted pucks, state, currently loaded sample

        :returns: None
        :rtype: None
        """
        logging.info(
            "doUpdateInfo should not be called for cats. only for update timer type of SC"
        )
        return

        self._do_update_cats_contents()
        self._do_update_state()
        self._do_update_loaded_sample()

    def _do_change_mode(self, mode):
        """
        Changes the SC operation mode, not implemented for the CATS system

        :returns: None
        :rtype: None
        """

    def _directly_update_selected_component(self, basket_no, sample_no):
        basket = None
        sample = None
        try:
            if (
                basket_no is not None
                and basket_no > 0
                and basket_no <= self.number_of_baskets
            ):
                basket = self.get_component_by_address(
                    Basket.get_basket_address(basket_no)
                )
                if (
                    sample_no is not None
                    and sample_no > 0
                    and sample_no <= basket.get_number_of_samples()
                ):
                    sample = self.get_component_by_address(
                        Pin.get_sample_address(basket_no, sample_no)
                    )
        except Exception:
            pass
        self._set_selected_component(basket)
        self._set_selected_sample(sample)

    def _do_select(self, component):
        """
        Selects a new component (basket or sample).
        Uses method >_directly_update_selected_component< to actually search and select the corrected positions.

        :returns: None
        :rtype: None
        """
        logging.info(
            "selecting component %s / type=%s" % (str(component), type(component))
        )

        if isinstance(component, Sample):
            selected_basket_no = component.get_basket_no()
            selected_sample_no = component.get_index() + 1
        elif isinstance(component, Container) and (
            component.get_type() == Basket.__TYPE__
        ):
            selected_basket_no = component.get_index() + 1
            selected_sample_no = None
        elif isinstance(component, tuple) and len(component) == 2:
            selected_basket_no = component[0]
            selected_sample_no = component[1]
        self._directly_update_selected_component(selected_basket_no, selected_sample_no)

    def _do_scan(self, component, recursive):
        """
        Scans the barcode of a single sample, puck or recursively even the complete sample changer.

        :returns: None
        :rtype: None
        """
        selected_basket = self.get_selected_component()

        if isinstance(component, Sample):
            # scan a single sample
            if (selected_basket is None) or (
                selected_basket != component.get_container()
            ):
                self._do_select(component)

            selected = self.get_selected_sample()

            # self._execute_server_task(self._scan_samples, [component.get_index()+1,])
            lid, sample = self.basketsample_to_lidsample(
                selected.get_basket_no(), selected.get_vial_no()
            )
            argin = ["2", str(lid), str(sample), "0", "0"]
            self._execute_server_task(self._cmdScanSample, argin)
            self._update_sample_barcode(component)
        elif isinstance(component, Container) and (
            component.get_type() == Basket.__TYPE__
        ):
            # component is a basket
            basket = component
            if recursive:
                pass
            else:
                if (selected_basket is None) or (selected_basket != basket):
                    self._do_select(basket)

                selected = self.get_selected_sample()

                for sample_index in range(basket.get_number_of_samples()):
                    basket = selected.get_basket_no()
                    num = sample_index + 1
                    lid, sample = self.basketsample_to_lidsample(basket, num)
                    argin = ["2", str(lid), str(sample), "0", "0"]
                    self._execute_server_task(self._cmdScanSample, argin)

    def load(self, sample=None, wait=True):
        """
        Load a sample.
            overwrite original load() from AbstractSampleChanger to allow finer decision
            on command to use (with or without barcode / or allow for wash in some cases)
            Implement that logic in _do_load()
            Add initial verification about the Powered:
            (NOTE) In fact should be already as the power is considered in the state handling
        """
        if not self._chnPowered.get_value():
            raise Exception(
                "CATS power is not enabled. Please switch on arm power before transferring samples."
            )
            return

        self._update_state()  # remove software flags like Loading.
        logging.getLogger("HWR").debug(
            "   ==========CATS== load cmd .state is:  %s " % (self.state)
        )

        sample = self._resolve_component(sample)
        self.assert_not_charging()

        self._execute_task(SampleChangerState.Loading, wait, self._do_load, sample)

    def _do_load(self, sample=None, shifts=None):
        """
        Loads a sample on the diffractometer. Performs a simple put operation if the diffractometer is empty, and
        a sample exchange (unmount of old + mount of new sample) if a sample is already mounted on the diffractometer.

        :returns: None
        :rtype: None
        """
        if not self._chnPowered.get_value():
            self._cmdPowerOn()
            gevent.sleep(2)
            if not self._chnPowered.get_value():
                raise Exception(
                    "CATS power cannot be enabled. Please check arm power before transferring samples."
                )

        selected = self.get_selected_sample()
        if sample is not None:
            if sample != selected:
                self._do_select(sample)
                selected = self.get_selected_sample()
        else:
            if selected is not None:
                sample = selected
            else:
                raise Exception("No sample selected")

        basketno = selected.get_basket_no()
        sampleno = selected.get_vial_no()

        lid, sample = self.basketsample_to_lidsample(basketno, sampleno)

        tool = self.tool_for_basket(basketno)
        stype = self.get_cassette_type(basketno)

        # we should now check basket type on diffr to see if tool is different...
        # then decide what to do

        if shifts is None:
            xshift, yshift, zshift = ["0", "0", "0"]
        else:
            xshift, yshift, zshift = map(str, shifts)

        # prepare argin values
        argin = [
            str(tool),
            str(lid),
            str(sample),
            str(stype),
            "0",
            xshift,
            yshift,
            zshift,
        ]
        logging.getLogger("HWR").debug(
            "  ==========CATS=== doLoad argin:  %s / %s:%s"
            % (argin, basketno, sampleno)
        )

        if self.has_loaded_sample():
            if selected == self.get_loaded_sample():
                raise Exception(
                    "The sample "
                    + str(self.get_loaded_sample().get_address())
                    + " is already loaded"
                )
            else:
                if self.read_datamatrix and self._cmdChainedLoadBarcode is not None:
                    logging.getLogger("HWR").warning(
                        "  ==========CATS=== chained load sample (brcd), sending to cats:  %s"
                        % argin
                    )
                    self._execute_server_task(self._cmdChainedLoadBarcode, argin)
                else:
                    logging.getLogger("HWR").warning(
                        "  ==========CATS=== chained load sample, sending to cats:  %s"
                        % argin
                    )
                    self._execute_server_task(self._cmdChainedLoad, argin)
        else:
            if self.cats_sample_on_diffr() == 1:
                logging.getLogger("HWR").warning(
                    "  ==========CATS=== trying to load sample, but sample detected on diffr. aborting"
                )
                self._update_state()  # remove software flags like Loading.
            elif self.cats_sample_on_diffr() == -1:
                logging.getLogger("HWR").warning(
                    "  ==========CATS=== trying to load sample, but there is a conflict on loaded sample info. aborting"
                )
                self._update_state()  # remove software flags like Loading.
            else:
                if self.read_datamatrix and self._cmdLoadBarcode is not None:
                    logging.getLogger("HWR").warning(
                        "  ==========CATS=== load sample (bcrd), sending to cats:  %s"
                        % argin
                    )
                    self._execute_server_task(self._cmdLoadBarcode, argin)
                else:
                    logging.getLogger("HWR").warning(
                        "  ==========CATS=== load sample, sending to cats:  %s" % argin
                    )
                    self._execute_server_task(self._cmdLoad, argin)

    def _do_unload(self, sample_slot=None, shifts=None):
        """
        Unloads a sample from the diffractometer.

        :returns: None
        :rtype: None
        """
        if not self._chnPowered.get_value():
            raise Exception(
                "CATS power is not enabled. Please switch on arm power before transferring samples."
            )

        if not self.has_loaded_sample() or not self._chnSampleIsDetected.get_value():
            logging.getLogger("HWR").warning(
                "  Trying do unload sample, but it does not seem to be any on diffr:  %s"
                % argin
            )

        if sample_slot is not None:
            self._do_select(sample_slot)

        if shifts is None:
            xshift, yshift, zshift = ["0", "0", "0"]
        else:
            xshift, yshift, zshift = map(str, shifts)

        loaded_lid = self._chnLidLoadedSample.get_value()
        loaded_num = self._chnNumLoadedSample.get_value()

        if loaded_lid == -1:
            logging.getLogger("HWR").warning(
                "  ==========CATS=== unload sample, no sample mounted detected"
            )
            return

        loaded_basket, loaded_sample = self.lidsample_to_basketsample(
            loaded_lid, loaded_num
        )

        tool = self.tool_for_basket(loaded_basket)

        argin = [str(tool), "0", xshift, yshift, zshift]

        logging.getLogger("HWR").warning(
            "  ==========CATS=== unload sample, sending to cats:  %s" % argin
        )
        self._execute_server_task(self._cmdUnload, argin)

    def _on_task_failed(self, task, exception):
        if task in [SampleChangerState.Loading, SampleChangerState.Unloading]:
            logging.getLogger("HWR").warning(
                "  ==========CATS=== load/unload operation failed :  %s" % exception
            )
            self.emit("taskFailed", str(exception))

    def clear_basket_info(self, basket):
        pass

    # ###############################################################################

    def _do_abort(self):
        """
        Aborts a running trajectory on the sample changer.

        :returns: None
        :rtype: None
        """
        self._cmdAbort()
        self._update_state()  # remove software flags like Loading.. reflects current hardware state

    def _do_reset(self):
        pass

    # ########################           CATS EVENTS           #########################

    def cats_state_changed(self, value):
        if self.cats_state != value:
            # hack for transient states
            trials = 0

            while value in [PyTango.DevState.ALARM, PyTango.DevState.ON]:
                time.sleep(0.1)
                trials += 1
                logging.getLogger("HWR").warning(
                    "SAMPLE CHANGER could be in transient state. trying again"
                )
                value = self._chnState.get_value()
                if trials > 4:
                    break

        self.cats_state = value
        self._update_state()

    def cats_status_changed(self, value):
        self.cats_status = value
        self._update_state()

    def cats_pathrunning_changed(self, value):
        self.cats_running = value
        self._update_state()
        self.emit("runningStateChanged", (value,))

    def cats_powered_changed(self, value):
        self.cats_powered = value
        self._update_state()
        self.emit("powerStateChanged", (value,))

    def cats_pathsafe_changed(self, value):
        self.cats_pathsafe = value
        self._update_state()
        time.sleep(1.0)
        self.emit("path_safeChanged", (value,))
        self.emit("isCollisionSafe", (value,))

    def cats_lids_closed_changed(self, value):
        self.cats_lids_closed = value
        self._update_state()

    def cats_basket_presence_changed(self, value):
        presence = [None] * self.number_of_baskets
        for basket_index in range(self.number_of_baskets):
            value = self.basket_channels[basket_index].get_value()
            presence[basket_index] = value

        if presence != self.basket_presence:
            logging.getLogger("HWR").warning(
                "Basket presence changed. Updating contents"
            )
            self.basket_presence = presence
            self._update_cats_contents()
            self._update_loaded_sample()

    def cats_baskets_changed(self, value):
        logging.getLogger("HWR").warning("Baskets changed. %s" % value)
        for idx, val in enumerate(value):
            self.basket_presence[idx] = val
        self._update_cats_contents()
        self._update_loaded_sample()

    def cats_loaded_lid_changed(self, value):
        cats_loaded_lid = value
        cats_loaded_num = self._chnNumLoadedSample.get_value()
        self._update_loaded_sample(cats_loaded_num, cats_loaded_lid)

    def cats_loaded_num_changed(self, value):
        cats_loaded_lid = self._chnLidLoadedSample.get_value()
        cats_loaded_num = value
        self._update_loaded_sample(cats_loaded_num, cats_loaded_lid)

    def cats_barcode_changed(self, value):
        self.cats_datamatrix = value

        scanned = len(value) != 0

        lid_on_tool = self.cats_device.read_attribute("LidSampleOnTool").value
        sample_on_tool = self.cats_device.read_attribute("NumSampleOnTool").value

        if -1 in [lid_on_tool, sample_on_tool]:
            return

        basketno, sampleno = self.lidsample_to_basketsample(lid_on_tool, sample_on_tool)
        logging.getLogger("HWR").warning(
            "Barcode %s read. Assigning it to sample %s:%s"
            % (value, basketno, sampleno)
        )
        self.emit("barcodeChanged", (value,))

        sample = self.get_component_by_address(
            Pin.get_sample_address(basketno, sampleno)
        )
        sample._set_info(sample.is_present(), value, scanned)

    def cats_sample_on_diffr(self):
        detected = self._chnSampleIsDetected.get_value()
        on_diffr = -1 not in [self.cats_loaded_lid, self.cats_loaded_num]

        if detected and on_diffr:
            return 1
        elif detected or on_diffr:  # conflicting info
            return -1
        else:
            return 0

    # ########################           PRIVATE           #########################

    def _execute_server_task(self, method, *args, **kwargs):
        """
        Executes a task on the CATS Tango device server

        :returns: None
        :rtype: None
        """
        self._wait_device_ready(3.0)
        try:
            task_id = method(*args)
        except Exception:
            import traceback

            logging.getLogger("HWR").debug(
                "Cats90. exception while executing server task"
            )
            logging.getLogger("HWR").debug(traceback.format_exc())
            task_id = None

        waitsafe = kwargs.get("waitsafe", False)
        logging.getLogger("HWR").debug(
            "Cats90. executing method %s / task_id %s / waiting only for safe status is %s"
            % (str(method), task_id, waitsafe)
        )

        ret = None
        if task_id is None:  # Reset
            while self._is_device_busy():
                gevent.sleep(0.1)
            return False
        else:
            # introduced wait because it takes some time before the attribute PathRunning is set
            # after launching a transfer
            time.sleep(6.0)
            while True:
                if waitsafe:
                    if self.path_safe():
                        logging.getLogger("HWR").debug(
                            "Cats90. server execution polling finished as path is safe"
                        )
                        break
                else:
                    if not self.path_running():
                        logging.getLogger("HWR").debug(
                            "Cats90. server execution polling finished as path is not running"
                        )
                        break
                gevent.sleep(0.1)
            ret = True
        return ret

    def path_safe(self):
        return str(self._chnPathSafe.get_value()).lower() == "true"

    def path_running(self):
        return str(self._chnPathRunning.get_value()).lower() == "true"

    def _do_update_state(self):
        """
        Updates the state of the hardware object

        :returns: None
        :rtype: None
        """
        self.cats_running = self._chnPathRunning.get_value()
        self.cats_powered = self._chnPowered.get_value()
        self.cats_lids_closed = self._chnAllLidsClosed.get_value()
        self.cats_status = self._chnStatus.get_value()
        self.cats_state = self._chnState.get_value()

    def _update_state(self):
        has_loaded = self.has_loaded_sample()
        on_diff = self._chnSampleIsDetected.get_value()

        state = self._decide_state(
            self.cats_state,
            self.cats_powered,
            self.cats_lids_closed,
            has_loaded,
            on_diff,
        )

        status = SampleChangerState.tostring(state)
        self._set_state(state, status)

    def _read_state(self):
        """
        Read the state of the Tango DS and translate the state to the SampleChangerState Enum

        :returns: Sample changer state
        :rtype: AbstractSampleChanger.SampleChangerState
        """
        _state = self._chnState.get_value()
        _powered = self._chnPowered.get_value()
        _lids_closed = self._chnAllLidsClosed.get_value()
        _has_loaded = self.has_loaded_sample()
        _on_diff = self._chnSampleIsDetected.get_value()

        # hack for transient states
        trials = 0
        while _state in [PyTango.DevState.ALARM, PyTango.DevState.ON]:
            time.sleep(0.1)
            trials += 1
            logging.getLogger("HWR").warning(
                "SAMPLE CHANGER could be in transient state. trying again"
            )
            _state = self._chnState.get_value()
            if trials > 2:
                break

        state = self._decide_state(
            _state, _powered, _lids_closed, _has_loaded, _on_diff
        )

        return state

    def _decide_state(self, dev_state, powered, lids_closed, has_loaded, on_diff):
        if dev_state == PyTango.DevState.ALARM:
            _state = SampleChangerState.Alarm
        elif not powered:
            _state = SampleChangerState.Disabled
        elif dev_state == PyTango.DevState.RUNNING:
            if self.state not in [
                SampleChangerState.Loading,
                SampleChangerState.Unloading,
            ]:
                _state = SampleChangerState.Moving
            else:
                _state = self.state
        elif dev_state == PyTango.DevState.UNKNOWN:
            _state = SampleChangerState.Unknown
        elif has_loaded ^ on_diff:
            # go to Unknown state if a sample is detected on the gonio but not registered in the internal database
            # or registered but not on the gonio anymore
            logging.getLogger("HWR").warning(
                "SAMPLE CHANGER Unknown 2 (hasLoaded: %s / detected: %s)"
                % (self.has_loaded_sample(), self._chnSampleIsDetected.get_value())
            )
            _state = SampleChangerState.Unknown
        # elif not lids_closed:
        # _state = SampleChangerState.Charging
        elif dev_state == PyTango.DevState.ON:
            _state = SampleChangerState.Ready
        else:
            _state = SampleChangerState.Unknown

        return _state

    def _is_device_busy(self, state=None):
        """
        Checks whether Sample changer HO is busy.

        :returns: True if the sample changer is busy
        :rtype: Bool
        """
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
        """
        Checks whether Sample changer HO is ready.

        :returns: True if the sample changer is ready
        :rtype: Bool
        """
        state = self._read_state()
        return state in (SampleChangerState.Ready, SampleChangerState.Charging)

    def _wait_device_ready(self, timeout=None):
        """
        Waits until the samle changer HO is ready.

        :returns: None
        :rtype: None
        """
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self._is_device_ready():
                gevent.sleep(0.01)

    def _do_update_loaded_sample(self):
        """
        Reads the currently mounted sample basket and pin indices from the CATS Tango DS,
        translates the lid/sample notation into the basket/sample notation and marks the
        respective sample as loaded.

        :returns: None
        :rtype: None
        """
        cats_loaded_lid = self._chnLidLoadedSample.get_value()
        cats_loaded_num = self._chnNumLoadedSample.get_value()
        self.cats_datamatrix = str(self._chnSampleBarcode.get_value())
        self._update_loaded_sample(cats_loaded_num, cats_loaded_lid)

    def lidsample_to_basketsample(self, lid, num):
        if self.is_isara():
            return lid, num
        else:
            lid_base = (lid - 1) * self.baskets_per_lid  # nb of first basket in lid
            basket_type = self.basket_types[lid_base]

            if basket_type == BASKET_UNIPUCK:
                samples_per_basket = SAMPLES_UNIPUCK
            elif basket_type == BASKET_SPINE:
                samples_per_basket = SAMPLES_SPINE
            else:
                samples_per_basket = self.samples_per_basket

            lid_offset = ((num - 1) / samples_per_basket) + 1
            sample_pos = ((num - 1) % samples_per_basket) + 1
            basket = lid_base + lid_offset
            return basket, sample_pos

    def basketsample_to_lidsample(self, basket, num):
        if self.is_isara():
            return basket, num
        else:
            lid = ((basket - 1) / self.baskets_per_lid) + 1

            basket_type = self.basket_types[basket - 1]
            if basket_type == BASKET_UNIPUCK:
                samples_per_basket = SAMPLES_UNIPUCK
            elif basket_type == BASKET_SPINE:
                samples_per_basket = SAMPLES_SPINE
            else:
                samples_per_basket = self.samples_per_basket

            sample = (((basket - 1) % self.baskets_per_lid) * samples_per_basket) + num
            return lid, sample

    def tool_for_basket(self, basketno):
        basket_type = self.basket_types[basketno - 1]

        if basket_type == BASKET_SPINE:
            tool = TOOL_SPINE
        elif basket_type == BASKET_UNIPUCK:
            tool = self.unipuck_tool  # configurable (xml and command set_unipuck_tool()
        else:
            tool = -1

        logging.getLogger("HWR").debug(
            "   finding basket type for %s - is %s / tool is %s"
            % (basketno, basket_type, tool)
        )

        return tool

    def get_current_tool(self):
        tool_str = self._chnCurrentTool.get_value()
        return TOOL_TO_STR.get(tool_str, "Unknown")

    def get_cassette_type(self, basketno):
        basket_type = self.basket_types[basketno - 1]

        if self.is_isara():
            ret_type = 1
        else:
            if basket_type == BASKET_SPINE:
                ret_type = 0
            elif basket_type == BASKET_UNIPUCK:
                ret_type = 1
            else:
                ret_type = -1

        return ret_type

    def _update_loaded_sample(self, sample_num=None, lid=None):
        if None in [sample_num, lid]:
            loadedSampleNum = self._chnNumLoadedSample.get_value()
            loadedSampleLid = self._chnLidLoadedSample.get_value()
        else:
            loadedSampleNum = sample_num
            loadedSampleLid = lid

        self.cats_loaded_lid = loadedSampleLid
        self.cats_loaded_num = loadedSampleNum

        logging.getLogger("HWR").info(
            "Updating loaded sample %s:%s" % (loadedSampleLid, loadedSampleNum)
        )

        if -1 not in [loadedSampleLid, loadedSampleNum]:
            basket, sample = self.lidsample_to_basketsample(
                loadedSampleLid, loadedSampleNum
            )
            new_sample = self.get_component_by_address(
                Pin.get_sample_address(basket, sample)
            )
        else:
            basket, sample = None, None
            new_sample = None

        old_sample = self.get_loaded_sample()

        logging.getLogger("HWR").debug(
            "----- Cats90 -----.  Sample has changed. Dealing with it - new_sample = %s / old_sample = %s"
            % (new_sample, old_sample)
        )

        if old_sample != new_sample:
            # remove 'loaded' flag from old sample but keep all other information

            if old_sample is not None:
                # there was a sample on the gonio
                loaded = False
                has_been_loaded = True
                old_sample._set_loaded(loaded, has_been_loaded)

            if new_sample is not None:
                loaded = True
                has_been_loaded = True
                new_sample._set_loaded(loaded, has_been_loaded)

            if (
                (old_sample is None)
                or (new_sample is None)
                or (old_sample.get_address() != new_loaded.get_address())
            ):
                self._trigger_loaded_sample_changed_event(new_sample)
                self._trigger_info_changed_event()

    def _update_sample_barcode(self, sample):
        """
        Updates the barcode of >sample< in the local database after scanning with
        the barcode reader.

        :returns: None
        :rtype: None
        """
        # update information of recently scanned sample
        if sample is None:
            return

        scanned = len(self.cats_datamatrix) != 0
        if not scanned:
            datamatrix = "----------"
        else:
            datamatrix = self.cats_datamatrix
        sample._set_info(sample.is_present(), datamatrix, scanned)

    def _do_update_cats_contents(self):
        """
        Updates the sample changer content. The state of the puck positions are
        read from the respective channels in the CATS Tango DS.
        The CATS sample sample does not have an detection of each individual sample, so all
        samples are flagged as 'Present' if the respective puck is mounted.

        :returns: None
        :rtype: None
        """

        for basket_index in range(self.number_of_baskets):
            # get presence information from the device server
            channel = self.basket_channels[basket_index]
            is_present = channel.get_value()
            self.basket_presence[basket_index] = is_present

        self._update_cats_contents()

    def _update_cats_contents(self):
        logging.getLogger("HWR").warning(
            "Updating contents %s" % str(self.basket_presence)
        )
        for basket_index in range(self.number_of_baskets):
            # get saved presence information from object's internal bookkeeping
            basket = self.get_components()[basket_index]
            is_present = self.basket_presence[basket_index]

            if is_present is None:
                continue

            # check if the basket presence has changed
            if is_present ^ basket.is_present():
                # a mounting action was detected ...
                if is_present:
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
                for sample_index in range(basket.get_number_of_samples()):
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
                    loaded = _has_been_loaded = False
                    sample._set_loaded(loaded, has_been_loaded)

        self._trigger_contents_updated_event()
        self._update_loaded_sample()
        self._trigger_info_changed_event()


def test_hwo(hwo):
    basket_list = hwo.get_basket_list()
    sample_list = hwo.get_sample_list()
    print("Baskets/Samples in CATS: %s/%s" % (len(basket_list), len(sample_list)))
    gevent.sleep(2)
    sample_list = hwo.get_sample_list()

    for s in sample_list:
        if s.is_loaded():
            print("Sample %s loaded" % s.get_address())
            break

    if hwo.has_loaded_sample():
        print(
            (
                "Currently loaded (%s): %s"
                % (hwo.has_loaded_sample(), hwo.get_loaded_sample().get_address())
            )
        )
    print("CATS state is: ", hwo.state)
    print("Sample on Magnet : ", hwo.cats_sample_on_diffr())
    print("All lids closed: ", hwo._chnAllLidsClosed.get_value())

    print("Sample Changer State is: ", hwo.get_status())
    for basketno in range(hwo.number_of_baskets):
        no = basketno + 1
        print("Tool for basket %d is: %d" % (no, hwo.tool_for_basket(no)))
