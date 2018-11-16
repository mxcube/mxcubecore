"""Sample Changer Hardware Object
"""
import logging
from HardwareRepository.BaseHardwareObjects import Equipment
import gevent


class GrobSampleChanger(Equipment):
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
        Equipment.__init__(self, *args, **kwargs)

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

        grob = self.getObjectByRole("grob")
        self.grob = grob.controller
        self.connect(self.grob, "transfer_state", self.sampleChangerStateChanged)
        self.connect(self.grob, "io_bits", self.ioBitsChanged)
        self.connect(self.grob, "mounted_sample", self.mountedSampleChanged)
        self.connect(self.grob, "samples_map", self.samplesMapChanged)

    def connectNotify(self, signal):
        logging.info("%s: connectNotify %s", self.name(), signal)
        if signal == "stateChanged":
            self.sampleChangerStateChanged(self.getState())
        elif signal == "loadedSampleChanged":
            self.mountedSampleChanged(self._getLoadedSampleNum())
        elif signal == "samplesMapChanged":
            self.samplesMapChanged(self.getSamplesMap())

    def getState(self):
        return self.grob.transfer_state()

    def ioBitsChanged(self, bits):
        bits, output_bits = map(int, bits.split())
        status = {}
        for bit_number, name in {
            1: "lid",
            2: "puck1",
            3: "puck2",
            4: "puck3",
            6: "ln2_alarm_low",
        }.iteritems():
            status[name] = bits & (1 << (bit_number - 1)) != 0
        self.emit("ioStatusChanged", (status,))

    def samplesMapChanged(self, samples_map_dict):
        samples_map_int_keys = {}
        for k, v in samples_map_dict.iteritems():
            samples_map_int_keys[int(k)] = v
        self.samples_map = samples_map_int_keys
        self.emit("samplesMapChanged", (self.samples_map,))

    def getSamplesMap(self):
        return self.samples_map

    def mountedSampleChanged(self, sample_num=None):
        self.emit("sampleIsLoaded", (sample_num > 0,))

        if sample_num > 0:
            basket = int((sample_num - 1) / 10) + 1
            vial = 1 + ((sample_num - 1) % 10)

    def sampleChangerStateChanged(self, state):
        self.emit("stateChanged", (state,))

    def _callSuccessCallback(self):
        if callable(self._successCallback):
            try:
                self._successCallback()
            except:
                logging.exception(
                    "%s: exception while calling success callback", self.name()
                )

    def _callFailureCallback(self):
        if callable(self._failureCallback):
            try:
                self._failureCallback()
            except:
                logging.exception(
                    "%s: exception while calling failure callback", self.name()
                )

    def _sampleTransferDone(self, transfer_greenlet):
        status = transfer_greenlet.get()
        if status == "READY":
            self.prepareCentring()
            self.sampleChangerStateChanged("READY")
            self._callSuccessCallback()
        else:
            self.sampleChangerStateChanged("ERROR")
            self._callFailureCallback()

    def prepareCentring(self):
        pass

    def getLoadedSample(self):
        return self.loaded_sample_dict

    def _setMovingState(self):
        self.sampleChangerStateChanged("MOVING")

    def _getLoadedSampleNum(self):
        samples_map = self.getSamplesMap()
        for i in range(30):
            if samples_map[i] == "on_axis":
                return i + 1

    def unloadMountedSample(
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

        gevent.spawn(self.continueTransfer, self.prepareTransfer()).link(
            self._sampleTransferDone
        )

    def loadSample(
        self,
        holderLength,
        sample_id=None,
        sample_location=None,
        successCallback=None,
        failureCallback=None,
        prepareCentring=None,
        prepareCentringMotors={},
        prepare_centring=None,
        prepare_centring_motors=None,
    ):
        self._successCallback = successCallback
        self._failureCallback = failureCallback
        self._holderlength = holderLength
        self._sample_id = sample_id
        self._sample_location = sample_location

        if self._getLoadedSampleNum():
            self._procedure = "UNLOAD_LOAD"
        else:
            self._procedure = "LOAD"

        gevent.spawn(self.continueTransfer, self.prepareTransfer()).link(
            self._sampleTransferDone
        )

    def prepareTransfer(self):
        return True

    def continueTransfer(self, ok):
        if not ok:
            self.sampleChangerStateChanged("ERROR")
            self._callFailureCallback()
            return

        basket, vial = self._sample_location
        sample_num = (basket - 1) * 10 + vial

        if self._procedure == "LOAD":
            logging.info("asking robot to load sample %d", sample_num)
            return self.grob.mount(sample_num)
        elif self._procedure == "UNLOAD_LOAD":
            sample_to_unload_num = self._getLoadedSampleNum()
            logging.info(
                "asking robot to unload sample %d and to load sample %d",
                sample_to_unload_num,
                sample_num,
            )
            self.grob.unmount(sample_to_unload_num)
            return self.grob.mount(sample_num)
        elif self._procedure == "UNLOAD":
            sample_num = self._getLoadedSampleNum()
            logging.info("asking robot to unload sample %d", sample_num)
            return self.grob.unmount(sample_num)

    def isMicrodiff(self):
        return False

    def getLoadedSampleDataMatrix(self):
        return None

    def getLoadedSampleLocation(self):
        sample_num = self._getLoadedSampleNum()
        if sample_num < 0:
            return None
        basket = int((sample_num - 1) / 10) + 1
        vial = 1 + ((sample_num - 1) % 10)
        return (basket, vial)

    def getLoadedHolderLength(self):
        return self._holderlength

    def getMatrixCodes(self):
        return self.matrix_codes

    def updateDataMatrices(self):
        self.emit("matrixCodesUpdate", (self.matrix_codes,))

    def canLoadSample(self, sample_code=None, sample_location=None, holder_length=None):
        already_loaded = False

        loaded_sample_location = self.getLoadedSampleLocation()

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
