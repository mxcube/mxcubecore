from PyTransmission import matt_control
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR


class Transmission(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.labels = []
        self.indexes = []
        self.attno = 0
        # TO DO: clean this!!!
        # self.get_value = self.get_value
        # self.getAttFactor = self.get_value
        # self.setTransmission = self.set_value

    def init(self):

        self.__matt = matt_control.MattControl(
            self.get_property("wago_ip"),
            len(self["filter"]),
            0,
            self.get_property("type"),
            self.get_property("alternate"),
            self.get_property("status_module"),
            self.get_property("control_module"),
            self.get_property("datafile"),
        )
        self.__matt.connect()

    def is_ready(self):
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
