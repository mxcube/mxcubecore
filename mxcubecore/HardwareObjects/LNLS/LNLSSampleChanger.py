import logging

from mxcubeweb.app import MXCUBEApplication

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractSampleChanger import (
    SampleChanger,
    SampleChangerState,
)
from mxcubecore.HardwareObjects.abstract.sample_changer import Container
from mxcubecore.HardwareObjects.LNLS.LNLSBeamlineActions import MountAction


class LNLSSampleChanger(SampleChanger):
    """
    This class calls the mount and unmount beamline actions, handles the
    logic of which sample is mounted and gives access to which samples
    are accessible from the 'get samples from SC' button.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSSampleChanger.LNLSSampleChanger
    epics:
    "MNC:B:ROBCS801:":
        channels:
            get_loop:
                suffix: "GetLoop"
            puck_id_1:
                suffix: "PuckID1"
            puck_id_2:
                suffix: "PuckID2"
            puck_id_3:
                suffix: "PuckID3"
    "MNC:B:SoftIOC:SP:1:SampPres_RBV":
        channels:
            sample_present:
                suffix : ""
    configuration:
        no_of_baskets: 3
        no_of_samples_in_basket: 16
    """

    __TYPE__ = "Sample Changer"

    def __init__(self, name):
        super().__init__(self.__TYPE__, scannable=False, name=name)
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")

    def init(self):
        self.frontend_application = MXCUBEApplication
        self._selected_sample = -1
        self._selected_basket = -1
        self.previous_get_loop_value = 0
        self.sc_channels = self._CommandContainer__channels
        self.no_of_baskets = self.get_property("no_of_baskets")
        self.no_of_samples_in_basket = self.get_property("no_of_samples_in_basket")
        self.add_baskets()
        self._init_sc_contents()
        SampleChanger.init(self)
        self.set_sample_changer_state("ready")
        self.log_filename = None

    def get_log_filename(self):
        return self.log_filename

    def sample_basket_to_index(self, basket, sample):
        return (int(basket) - 1) * 16 + int(sample)

    def index_to_sample_basket(self, index):
        sample = (index - 1) % 16 + 1
        basket = (index - 1) // 16 + 1
        self._selected_basket = basket
        self._selected_sample = sample

    def load(self, sample, wait=False):  # noqa: FBT002, ARG002
        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", True)  # noqa: FBT003
        previous_sample = self.get_loaded_sample()
        self._reset_loaded_sample()
        if isinstance(sample, tuple):
            basket, sample = sample
        else:
            basket, sample = sample.split(":")
        basket = int(basket)
        sample = int(sample)
        self._selected_basket = basket
        self._selected_sample = sample
        msg_text = f"Loading sample {basket}:{sample}"
        logging.getLogger("user_level_log").info(
            f"Sample changer: {msg_text}. Please wait..."
        )
        self.emit("progressInit", (msg_text, 100))
        frontend_msg = {
            "signal": "loadingSample",
            "location": f"{basket}:{sample}",
            "message": "Please wait, loading sample",
        }
        self.frontend_application.server.emit("sc", frontend_msg, namespace="/hwr")
        sc_value = self.sample_basket_to_index(basket, sample)
        mount_action = MountAction()
        mount_action.mount(int(sc_value))
        self.emit("progressStep", 100)
        mounted_sample = self.get_component_by_address(
            Container.Pin.get_sample_address(basket, sample)
        )
        if mounted_sample is not previous_sample:
            self._trigger_loaded_sample_changed_event(mounted_sample)
        self.update_info()
        logging.getLogger("user_level_log").info("Sample changer: Sample loaded")
        self.emit("progressStop", ())
        self.emit("fsmConditionChanged", "sample_is_loaded", True)
        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", False)
        return self.get_loaded_sample()

    def unload(self, sample_slot=None, wait=None):  # noqa: ARG002
        logging.getLogger("user_level_log").info("Unloading sample")
        sample = self.get_loaded_sample()
        mount_action = MountAction()
        mount_action.unmount()
        sample._set_loaded(False, True)  # noqa: SLF001
        self._selected_basket = -1
        self._selected_sample = -1
        new_sample = self.get_loaded_sample()
        self._trigger_loaded_sample_changed_event(new_sample)
        self.emit("fsmConditionChanged", "sample_is_loaded", False)

    def get_loaded_sample(self):
        """
        This fucntion is called periodically
        """
        get_loop = int(self.sc_channels["get_loop"].get_value())
        sample_present = self.sc_channels["sample_present"].get_value()

        if get_loop and sample_present and (1 <= get_loop <= 48):
            self.index_to_sample_basket(get_loop)
        else:
            self._selected_basket = -1
            self._selected_sample = -1

        value = self.get_component_by_address(
            Container.Pin.get_sample_address(
                self._selected_basket,
                self._selected_sample,
            )
        )

        if get_loop != self.previous_get_loop_value:
            self.previous_get_loop_value = get_loop
            self._trigger_loaded_sample_changed_event(value)

        return value

    def set_sample_changer_state(self, state):
        state = {
            "ready": SampleChangerState.Ready,
            "loading": SampleChangerState.Loading,
            "unloading": SampleChangerState.Unloading,
        }[state]
        self._set_state(state)

    def add_baskets(self):
        for idx in range(self.no_of_baskets):
            basket = Container.Basket(
                self,
                idx + 1,
                samples_num=self.no_of_samples_in_basket,
            )
            self._add_component(basket)

    def configure_baskets(self):
        for idx in range(self.no_of_baskets):
            basket = self.get_components()[idx]
            present = self.sc_channels[f"puck_id_{idx + 1}"].get_value() != "None"
            basket._set_info(present, None, False)  # noqa: SLF001

    def get_name_from_address(self, address):
        puck = address.split(":")[0]
        name = self.sc_channels[f"puck_id_{puck}"].get_value()
        return f"{name}-{address}"

    def configure_samples(self):
        """
        This function configures the current samples based
        on EPICS PVs that are set using an application
        outside of MXCuBE
        """
        sample_list = []

        for basket_idx in range(self.no_of_baskets):
            for sample_idx in range(self.no_of_samples_in_basket):
                sample_list.append(
                    (
                        "",
                        basket_idx + 1,
                        sample_idx + 1,
                        1,
                        Container.Pin.STD_HOLDERLENGTH,
                    )
                )

        for _, basket, sample, _, holder_length in sample_list:
            address = Container.Pin.get_sample_address(basket, sample)
            sample_obj = self.get_component_by_address(address)

            sample_name = self.get_name_from_address(address)
            if sample_name is not None:
                sample_obj._name = sample_name  # noqa: SLF001

            datamatrix = f"matr{basket}_{sample}"

            sample_obj._set_info(False, datamatrix, False)  # noqa: SLF001
            sample_obj._set_loaded(False, False)  # noqa: SLF001
            sample_obj._set_holder_length(holder_length)  # noqa: SLF001

    def _init_sc_contents(self):
        self.configure_baskets()
        self.configure_samples()

    def get_sample_list(self):
        self._init_sc_contents()
        return super().get_sample_list()
