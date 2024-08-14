import logging

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR


class ALBAEnergy(HardwareObject):
    def __init__(self, *args):
        super().__init__(*args)
        self.energy_position = None
        self.wavelength_position = None

    def init(self):
        self.wavelength_hwobj = self.get_object_by_role("wavelength")

        HWR.beamline.energy.connect("valueChanged", self.energy_position_changed)
        self.wavelength_hwobj.connect("valueChanged", self.wavelength_position_changed)

    def is_ready(self):
        return True

    def get_value(self):
        if self.energy_position is None:
            self.energy_position = HWR.beamline.energy.get_value()
        return self.energy_position

    def get_wavelength(self):
        if self.wavelength_position is None:
            self.wavelength_position = self.wavelength_hwobj.get_value()
        return self.wavelength_position

    def re_emit_values(self):
        HWR.beamline.energy.re_emit_values()

    def energy_position_changed(self, value):
        self.energy_position = value
        if None not in [self.energy_position, self.wavelength_position]:
            self.emit("energyChanged", self.energy_position, self.wavelength_position)

    def wavelength_position_changed(self, value):
        self.wavelength_position = value
        if None not in [self.energy_position, self.wavelength_position]:
            self.emit("energyChanged", self.energy_position, self.wavelength_position)

    def set_value(self, value):
        current_egy = self.get_value()

        logging.getLogger("HWR").debug(
            "moving energy to %s. now is %s" % (value, current_egy)
        )
        HWR.beamline.energy.set_value(value)

    def wait_move_energy_done(self):
        HWR.beamline.energy.wait_end_of_move()

    def set_wavelength(self, value):
        self.wavelength_hwobj.set_value(value)

    def get_limits(self):
        return HWR.beamline.energy.get_limits()

    def get_wavelength_limits(self):
        return self.wavelength_hwobj.get_limits()


def test_hwo(hwo):

    print("Wavelength is: ", hwo.get_wavelength())
    print("Energy limits are: ", hwo.get_limits())
    print("Wavelength limits are: ", hwo.get_wavelength_limits())


if __name__ == "__main__":
    test()
