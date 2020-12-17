from mx3core.HardwareObjects.mockup.EnergyMockup import EnergyMockup
from energy import energy
from scipy.constants import kilo, h, c, eV, angstrom
import logging


class PX2Energy(EnergyMockup):
    def init(self):
        self.energy = energy()

        self.energy_channel = self.get_channel_object("energy")
        self.energy_channel.connect_signal("update", self.energy_changed)

        self.state_channel = self.get_channel_object("state")
        self.state_channel.connect_signal("update", self.energy_state_changed)

        self.tunable = self.get_property("tunable")
        self.default_en = self.get_property("default_energy")

        self.minimum_energy = self.get_property("min_energy")
        self.maximum_energy = self.get_property("max_energy")

        self.current_energy = self.energy.get_value() / kilo
        self.current_wavelength = self.get_wavelegth_from_energy(self.current_energy)

        self.checkLimits = self.check_limits
        self.cancelMoveEnergy = self.cancel_move_energy

    def re_emit_values(self):
        self.emit("energyChanged", (self.current_energy, self.current_wavelength))
        self.emit("valueChanged", (self.current_energy,))

    def abort(self):
        self.energy.abort()

    def get_current_energy(self):
        return self.energy.get_energy() / kilo

    def get_wavelegth_from_energy(self, energy):
        return (h * c) / (eV * angstrom * kilo) / energy

    def get_energy_from_wavelength(self, wavelength):
        return (h * c) / (eV * angstrom * kilo) / wavelength

    def get_wavelength(self):
        return self.get_wavelegth_from_energy(self.get_current_energy())

    def get_limits(self):
        return self.minimum_energy, self.maximum_energy

    def get_wavelength_limits(self):
        minimum_wavelength = self.get_wavelegth_from_energy(self.maximum_energy)
        maximum_wavelength = self.get_wavelegth_from_energy(self.minimum_energy)
        return minimum_wavelength, maximum_wavelength

    def set_value(self, energy):
        logging.getLogger("user_level_log").info("Move energy to %6.3f keV" % energy)
        self.emit("moveEnergyStarted", ())
        self.energy.set_energy(energy)
        self.current_energy = self.get_current_energy()
        self.current_wavelength = self.get_wavelegth_from_energy(self.current_energy)
        self.re_emit_values()
        self.emit("moveEnergyFinished", ())

    def set_wavelength(self, wavelength):
        energy = self.get_energy_from_wavelength(wavelength)
        self.set_value(energy)

    def check_limits(self, value):
        logging.getLogger("HWR").debug("Checking the move limits")
        en_lims = self.get_limits()
        if value >= self.en_lims[0] and value <= self.en_lims[1]:
            logging.getLogger("HWR").info("Limits ok")
            return True
        logging.getLogger("user_level_log").info("Requested value is out of limits")
        return False

    def cancel_move_energy(self):
        logging.getLogger("user_level_log").info("Cancel energy move")
        self.abort()

    def energy_changed(self, pos):
        # logging.getLogger('HWR').info("energy_changed %s" % str(pos))
        energy = pos
        try:
            if abs(energy - self.current_energy) > 1e-3:
                self.current_energy = energy
                self.current_wavelength = 12.3984 / energy
                if self.current_wavelength is not None:
                    self.re_emit_values()
        except Exception:
            logging.getLogger("HWR").info(
                "energy_changed: error occured during an energy update"
            )

    def energy_state_changed(self, state):
        logging.getLogger("HWR").info("energy_state_changed %s" % str(state))
        # self.energy_server_check_for_errors(state)
        if state == "STANDBY":
            if self.moving:
                self.moving = False
                self.set_break_bragg()
            self.move_energy_finished(0)
            self.emit("stateChanged", "ready")
            self.emit("statusInfoChanged", "")
        elif state in ["MOVING", "ALARM"]:
            self.move_energy_started()
            self.emit("stateChanged", "busy")
