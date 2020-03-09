import logging

from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository import HardwareRepository as HWR


class ALBAEnergy(Device):
    def __init__(self, *args):
        Device.__init__(self, *args)
        self.energy_position = None
        self.wavelength_position = None

    def init(self):
        self.wavelength_hwobj = self.getObjectByRole("wavelength")

        HWR.beamline.energy.connect("positionChanged", self.energy_position_changed)
        self.wavelength_hwobj.connect(
            "positionChanged", self.wavelength_position_changed
        )

    def isReady(self):
        return True

    def can_move_energy(self):
        return True

    def get_energy(self):
        if self.energy_position is None:
            self.energy_position = HWR.beamline.energy.get_value()
        return self.energy_position

    get_current_energy = get_energy

    def get_wavelength(self):
        if self.wavelength_position is None:
            self.wavelength_position = self.wavelength_hwobj.get_value()
        return self.wavelength_position

    def update_values(self):
        HWR.beamline.energy.update_values()

    def energy_position_changed(self, value):
        self.energy_position = value
        if None not in [self.energy_position, self.wavelength_position]:
            self.emit("energyChanged", self.energy_position, self.wavelength_position)

    def wavelength_position_changed(self, value):
        self.wavelength_position = value
        if None not in [self.energy_position, self.wavelength_position]:
            self.emit("energyChanged", self.energy_position, self.wavelength_position)

    def move_energy(self, value):
        current_egy = self.get_energy()

        logging.getLogger("HWR").debug(
            "moving energy to %s. now is %s" % (value, current_egy)
        )
        HWR.beamline.energy.set_value(value)

    def wait_move_energy_done(self):
        HWR.beamline.energy.wait_end_of_move()

    def move_wavelength(self, value):
        self.wavelength_hwobj.set_value(value)

    def get_energy_limits(self):
        return HWR.beamline.energy.getLimits()

    def getEnergyLimits(self):
        return self.get_energy_limits()

    def get_wavelength_limits(self):
        return self.wavelength_hwobj.getLimits()


def test_hwo(hwo):

    print("Energy is: ", hwo.get_energy())
    print("Wavelength is: ", hwo.get_wavelength())
    print("Energy limits are: ", hwo.get_energy_limits())
    print("Wavelength limits are: ", hwo.get_wavelength_limits())


if __name__ == "__main__":
    test()
