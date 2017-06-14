from HardwareRepository.BaseHardwareObjects import HardwareObject

class Transmission(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.labels = []
        self.indexes = []
        self.attno = 0
        # TO DO: clean this!!!
        self.getValue = self.get_value
        self.getAttFactor = self.get_value
        self.setTransmission = self.set_value

    def init(self):
        module_name = self.getProperty("module_name")
        ctrl = self.getObjectByRole("controller")
        self.__transmission = getattr(ctrl, module_name)

    def isReady(self):
        return True

    def getAtteConfig(self):
        self.attno = len(self['filter'])

        for att_i in range(self.attno):
            obj = self['filter'][att_i]
            self.labels.append(obj.label)
            self.indexes.append(obj.index)

    def getAttState(self):
        return self.__transmission.matt.pos_read()

    def set_value(self, trans):
        self.__transmission.set(trans)
        self._update()

    def _update(self):
        self.emit("attStateChanged", self.getAttState())
        self.emit("attFactorChanged", self.getAttFactor())

    def toggle(self, attenuator_index):
        idx = self.indexes[attenuator_index]
        if self.is_in(attenuator_index):
            self.__transmission.matt.mattout(idx)
        else:
            self.__transmission.matt.mattin(idx)
        self._update()

    def get_value(self):
        return self.__transmission.get()

    def is_in(self, attenuator_index):
        curr_bits = self.getAttState()
        idx = self.indexes[attenuator_index]
        return bool((1<<idx) & curr_bits)
