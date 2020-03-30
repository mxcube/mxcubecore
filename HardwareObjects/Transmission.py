from PyTransmission import matt_control
from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository import HardwareRepository as HWR


class Transmission(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.labels = []
        self.indexes = []
        self.attno = 0
        # TO DO: clean this!!!
        # self.getValue = self.get_value
        # self.getAttFactor = self.get_value
        # self.setTransmission = self.set_value

    def init(self):

        self.__matt = matt_control.MattControl(
            self.getProperty("wago_ip"),
            len(self["filter"]),
            0,
            self.getProperty("type"),
            self.getProperty("alternate"),
            self.getProperty("status_module"),
            self.getProperty("control_module"),
            self.getProperty("datafile"),
        )
        self.__matt.connect()

    def isReady(self):
        return True

    def getAtteConfig(self):
        self.attno = len(self["filter"])

        for att_i in range(self.attno):
            obj = self["filter"][att_i]
            self.labels.append(obj.label)
            self.indexes.append(obj.index)

    def getAttState(self):
        return self.__matt.pos_read()

    def _set_value(self, value):
        self.__matt.set_energy(HWR.beamline.energy.get_value())
        self.__matt.transmission_set(value)
        self._update()

    def _update(self):
        self.emit("attStateChanged", self.getAttState())
        self.emit("attFactorChanged", self.get_value())

    def toggle(self, attenuator_index):
        idx = self.indexes[attenuator_index]
        if self.is_in(attenuator_index):
            self.__matt.mattout(idx)
        else:
            self.__matt.mattin(idx)
        self._update()

    def get_value(self):
        self.__matt.set_energy(HWR.beamline.energy.get_value())
        return self.__matt.transmission_get()

    def is_in(self, attenuator_index):
        curr_bits = self.getAttState()
        idx = self.indexes[attenuator_index]
        return bool((1 << idx) & curr_bits)
