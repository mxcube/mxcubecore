import sys
import logging
import math
import gevent
from mx3core.BaseHardwareObjects import Equipment

"""
Example xml file:
  - for tunable wavelength beamline:
<object class="Energy">
  <object href="/energy" role="energy"/>
  <object href="/bliss" role="controller"/>
  <tunable_energy>True</tunable_energy>
</object>
The energy should have methods get_value, get_limits and move.
If used, the controller should have method moveEnergy.

  - for fixed wavelength beamline:
<object class="Energy">
  <default_energy>12.8123</tunable_energy>
</object>
"""


class Energy(Equipment):
    def init(self):
        self.ready_event = gevent.event.Event()
        self.energy_motor = None
        self.tunable = False
        self.moving = None
        self.default_en = None
        self.ctrl = None
        self.en_lims = []

        try:
            self.energy_motor = self.get_object_by_role("energy")
        except KeyError:
            logging.getLogger("HWR").warning("Energy: error initializing energy motor")

        try:
            self.default_en = self.get_property("default_energy")
        except KeyError:
            logging.getLogger("HWR").warning("Energy: no default energy")

        try:
            self.tunable = self.get_property("tunable_energy")
        except KeyError:
            logging.getLogger("HWR").warning("Energy: will set to fixed energy")

        try:
            self.ctrl = self.get_object_by_role("controller")
        except KeyError:
            logging.getLogger("HWR").info("No controller used")

        if self.energy_motor is not None:
            self.energy_motor.connect("valueChanged", self.energyPositionChanged)
            self.energy_motor.connect("stateChanged", self.energyStateChanged)

    def is_connected(self):
        return True

    def get_value(self):
        if self.energy_motor is not None:
            try:
                return self.energy_motor.get_value()
            except Exception:
                logging.getLogger("HWR").exception(
                    "EnergyHO: could not read current energy"
                )
                return None
        return self.default_en

    def get_wavelength(self):
        current_en = self.get_current_energy()
        if current_en:
            return 12.3984 / current_en
        return None

    def get_limits(self):
        logging.getLogger("HWR").debug("Get energy limits")
        if not self.tunable:
            energy = self.get_value()
            return (energy, energy)

        if self.energy_motor is not None:
            try:
                self.en_lims = self.energy_motor.get_limits()
                return self.en_lims
            except Exception:
                logging.getLogger("HWR").exception(
                    "EnergyHO: could not read energy motor limits"
                )
                return None
        return None

    def get_wavelength_limits(self):
        logging.getLogger("HWR").debug("Get wavelength limits")
        if not self.tunable:
            return None
        self.en_lims = self.get_limits()
        if self.en_lims:
            lims = (12.3984 / self.en_lims[1], 12.3984 / self.en_lims[0])
        return lims

    # def start_move_energy(self, value, wait=True):
    #     if not self.tunable:
    #         return False
    #
    #     try:
    #         value = float(value)
    #     except (TypeError, ValueError) as diag:
    #         logging.getLogger("user_level_log").error(
    #             "Energy: invalid energy (%s)" % value
    #         )
    #         return False
    #
    #     current_en = self.get_current_energy()
    #     if current_en:
    #         if math.fabs(value - current_en) < 0.001:
    #             self.moveEnergyCmdFinished(True)
    #     if self.checkLimits(value) is False:
    #         return False
    #
    #     self.moveEnergyCmdStarted()
    #
    #     def change_egy():
    #         try:
    #             self.set_value(value, wait=True)
    #         except Exception:
    #             sys.excepthook(*sys.exc_info())
    #             self.moveEnergyCmdFailed()
    #         else:
    #             self.moveEnergyCmdFinished(True)
    #
    #     if wait:
    #         change_egy()
    #     else:
    #         gevent.spawn(change_egy)

    def moveEnergyCmdStarted(self):
        self.moving = True
        self.emit("moveEnergyStarted", ())

    def moveEnergyCmdFailed(self):
        self.moving = False
        self.emit("moveEnergyFailed", ())

    def moveEnergyCmdAborted(self):
        pass

    def moveEnergyCmdFinished(self, result):
        self.moving = False
        self.emit("moveEnergyFinished", ())

    def checkLimits(self, value):
        logging.getLogger("HWR").debug("Checking the move limits")
        if self.get_limits():
            if value >= self.en_lims[0] and value <= self.en_lims[1]:
                logging.getLogger("HWR").info("Limits ok")
                return True
            logging.getLogger("user_level_log").info("Requested value is out of limits")
        return False

    # def start_move_wavelength(self, value, wait=True):
    #     logging.getLogger("HWR").info("Moving wavelength to (%s)" % value)
    #     return self.startMoveEnergy(12.3984 / value, wait)

    def cancelMoveEnergy(self):
        logging.getLogger("user_level_log").info("Cancel move")
        self.moveEnergy.abort()

    def set_value(self, energy, wait=True):
        current_en = self.get_value()
        pos = math.fabs(current_en - energy)
        if pos < 0.001:
            logging.getLogger("user_level_log").debug(
                "Energy: already at %g, not moving", energy
            )
        else:
            logging.getLogger("user_level_log").debug(
                "Energy: moving energy to %g", energy
            )
            if pos > 0.02:
                try:
                    if self.ctrl:
                        self.ctrl.change_energy(energy)
                    else:
                        self.execute_command("moveEnergy", energy, wait=True)
                except RuntimeError as AttributeError:
                    self.energy_motor.set_value(energy)
            else:
                self.energy_motor.set_value(energy)

    def energyPositionChanged(self, pos):
        wl = 12.3984 / pos
        if wl:
            self.emit("energyChanged", (pos, wl))
            self.emit("valueChanged", (pos,))

    def energyStateChanged(self, state):
        self.emit("stateChanged", (state,))
