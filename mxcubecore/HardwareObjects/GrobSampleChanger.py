"""Sample Changer Hardware Object
"""

import logging

import gevent

from mxcubecore.BaseHardwareObjects import HardwareObject


class GrobSampleChanger(HardwareObject):
    (FLAG_SC_IN_USE, FLAG_MINIDIFF_CAN_MOVE, FLAG_SC_CAN_LOAD, FLAG_SC_NEVER) = (
        1,
        2,
        4,
        8,
    )
    (STATE_BASKET_NOTPRESENT, STATE_BASKET_UNKNOWN, STATE_BASKET_PRESENT) = (-1, 0, 1)

    USE_SPEC_LOADED_SAMPLE = False
    ALWAYS_ALLOW_MOUNTING = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init(self):
        self._procedure = ""
        self._successCallback = None
        self._failureCallback = None
        self._holderlength = 22
        self._sample_id = None
        self._sample_location = (0, 0)
        self.loaded_sample_dict = {}
        self.samples_map = dict(zip(range(30), ["unknown"] * 30))
        self.matrix_codes = []
        for i in range(30):
            sample_num = i + 1
            basket = int((sample_num - 1) / 10) + 1
            vial = 1 + ((sample_num - 1) % 10)
            self.matrix_codes.append(
                ("HA%d" % sample_num, basket, vial, "A%d" % basket, 0)
            )

        grob = self.get_object_by_role("grob")
        self.grob = grob.controller
        self.connect(self.grob, "transfer_state", self.sample_changer_state_changed)
        self.connect(self.grob, "io_bits", self.io_bits_changed)
        self.connect(self.grob, "mounted_sample", self.mounted_sample_changed)
        self.connect(self.grob, "samples_map", self.samples_map_changed)

    def connect_notify(self, signal):
        logging.info("%s: connect_notify %s", self.name(), signal)
        if signal == "stateChanged":
            self.sample_changer_state_changed(self.get_state())
        elif signal == "loadedSampleChanged":
            self.mounted_sample_changed(self._get_loaded_sampleNum())
        elif signal == "samples_map_changed":
            self.samples_map_changed(self.get_samples_map())

    def get_state(self):
        return self.grob.transfer_state()

    def io_bits_changed(self, bits):
        bits, output_bits = map(int, bits.split())
        status = {}
        for bit_number, name in {
            1: "lid",
            2: "puck1",
            3: "puck2",
            4: "puck3",
            6: "ln2_alarm_low",
        }.items():
            status[name] = bits & (1 << (bit_number - 1)) != 0
        self.emit("ioStatusChanged", (status,))

    def samples_map_changed(self, samples_map_dict):
        samples_map_int_keys = {}
        for k, v in samples_map_dict.items():
            samples_map_int_keys[int(k)] = v
        self.samples_map = samples_map_int_keys
        self.emit("samples_map_changed", (self.samples_map,))

    def get_samples_map(self):
        return self.samples_map

    def mounted_sample_changed(self, sample_num=None):
        self.emit("sampleIsLoaded", (sample_num > 0,))

        if sample_num > 0:
            basket = int((sample_num - 1) / 10) + 1
            vial = 1 + ((sample_num - 1) % 10)

    def sample_changer_state_changed(self, state):
        self.emit("stateChanged", (state,))

    def _callSuccessCallback(self):
        if callable(self._successCallback):
            try:
                self._successCallback()
            except Exception:
                logging.exception(
                    "%s: exception while calling success callback", self.name()
                )

    def _call_failure_callback(self):
        if callable(self._failureCallback):
            try:
                self._failureCallback()
            except Exception:
                logging.exception(
                    "%s: exception while calling failure callback", self.name()
                )

    def _sample_transfer_done(self, transfer_greenlet):
        status = transfer_greenlet.get()
        if status == "READY":
            self.prepare_centring()
            self.sample_changer_state_changed("READY")
            self._callSuccessCallback()
        else:
            self.sample_changer_state_changed("ERROR")
            self._call_failure_callback()

    def prepare_centring(self):
        pass

    def get_loaded_sample(self):
        return self.loaded_sample_dict

    def _set_moving_state(self):
        self.sample_changer_state_changed("MOVING")

    def _get_loaded_sampleNum(self):
        samples_map = self.get_samples_map()
        for i in range(30):
            if samples_map[i] == "on_axis":
                return i + 1

    def unload_mounted_sample(
        self,
        holderLength=None,
        sample_id=None,
        sample_location=None,
        sampleIsUnloadedCallback=None,
        failureCallback=None,
    ):
        self._procedure = "UNLOAD"

        self._successCallback = sampleIsUnloadedCallback
        self._failureCallback = failureCallback

        gevent.spawn(self.continue_transfer, self.prepare_transfer()).link(
            self._sample_transfer_done
        )

    def load(
        self,
        sample=None,
        sample_id=None,
        holderLength=None,
        successCallback=None,
        failureCallback=None,
        prepareCentring=None,
        prepareCentringMotors={},
        prepare_centring=None,
        prepare_centring_motors=None,
        wait=True,
    ):
        self._successCallback = successCallback
        self._failureCallback = failureCallback
        self._holderlength = holderLength
        self._sample_id = sample_id
        self._sample_location = sample

        if self._get_loaded_sampleNum():
            self._procedure = "UNLOAD_LOAD"
        else:
            self._procedure = "LOAD"

        gevent.spawn(self.continue_transfer, self.prepare_transfer()).link(
            self._sample_transfer_done
        )

    def prepare_transfer(self):
        return True

    def continue_transfer(self, ok):
        if not ok:
            self.sample_changer_state_changed("ERROR")
            self._call_failure_callback()
            return

        basket, vial = self._sample_location
        sample_num = (basket - 1) * 10 + vial

        if self._procedure == "LOAD":
            logging.info("asking robot to load sample %d", sample_num)
            return self.grob.mount(sample_num)
        elif self._procedure == "UNLOAD_LOAD":
            sample_to_unload_num = self._get_loaded_sampleNum()
            logging.info(
                "asking robot to unload sample %d and to load sample %d",
                sample_to_unload_num,
                sample_num,
            )
            self.grob.unmount(sample_to_unload_num)
            return self.grob.mount(sample_num)
        elif self._procedure == "UNLOAD":
            sample_num = self._get_loaded_sampleNum()
            logging.info("asking robot to unload sample %d", sample_num)
            return self.grob.unmount(sample_num)

    def is_microdiff(self):
        return False

    def get_loaded_sampleDataMatrix(self):
        return None

    def get_loaded_sampleLocation(self):
        sample_num = self._get_loaded_sampleNum()
        if sample_num < 0:
            return None
        basket = int((sample_num - 1) / 10) + 1
        vial = 1 + ((sample_num - 1) % 10)
        return (basket, vial)

    def get_loaded_holder_length(self):
        return self._holderlength

    def get_matrix_codes(self):
        return self.matrix_codes

    def update_data_matrices(self):
        self.emit("matrixCodesUpdate", (self.matrix_codes,))

    def canLoadSample(self, sample_code=None, sample_location=None, holder_length=None):
        already_loaded = False

        loaded_sample_location = self.get_loaded_sampleLocation()

        if loaded_sample_location is not None:
            if (
                sample_location is not None
                and sample_location == loaded_sample_location
            ):
                already_loaded = True

        return (True, already_loaded)

    def open_dewar(self, callback):
        gevent.spawn(self.grob.open_dewar).link(callback)

    def close_dewar(self, callback):
        gevent.spawn(self.grob.close_dewar).link(callback)
