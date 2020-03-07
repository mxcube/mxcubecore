import logging
import math
import gevent
from scipy.constants import h, c, e
from HardwareRepository.HardwareObjects.abstract.AbstractEnergy import AbstractEnergy
from HardwareRepository.BaseHardwareObjects import HardwareObjectState

"""
Example xml file:
  - for tunable wavelength beamline:
<object class="Energy">
  <object href="/energy" role="energy_motor"/>
  <object href="/bliss" role="bliss"/>
  <tunable_energy>True</tunable_energy>
</object>
The energy should have methods get_value, get_limits and move.
If used, the controller should have method moveEnergy.

  - for fixed wavelength beamline:
<object class="Energy">
  <default_energy>12.8123</tunable_energy>
</object>
"""


class BlissEnergy(AbstractEnergy):
    def __init__(self, name):
        AbstractEnergy.__init__(self, name)
        self._energy_motor = None
        self._bliss_session = None
        self.state = None

    def init(self):
        self._energy_motor = self.getObjectByRole("energy_motor")
        self.tunable = self.getProperty("tunable_energy")
        self._bliss_session = self.getObjectByRole("bliss")
        self._default_energy = self.getObjectByRole("default_energy")
        self.state = HardwareObjectState.READY

        if self._energy_motor is not None:
            self.state = self._energy_motor.get_state()
            self._energy_motor.connect("valueChanged", self.update_value)
            self._energy_motor.connect("stateChanged", self.update_state)

    def is_ready(self):
        """Check if the energy motor state is READY.
        Returns:
            (bool): True if ready, otherwise False.
        """
        if not self.tunable:
            return True

        try:
            return "READY" in self._energy_motor.state.current_states_names
        except AttributeError:
            return False

    def get_value(self):
        """Read the energy
        Returns:
            (float): Energy [keV]
        """
        return self.get_energy()

    def get_energy(self):
        """Read the energy
        Returns:
            (float): Energy [keV]
        """
        if not self.tunable:
            return self._default_energy

        self._energy_value = self._energy_motor.get_value()
        return self._energy_value

    def get_wavelength(self):
        """Read the wavelength
        Returns:
            (float): Wavelength [Å]
        """
        _en = self.get_energy()
        if _en:
            return self._calculate_wavelength(_en)
        return None

    def get_limits(self):
        """Return energy low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit).
        """
        logging.getLogger("HWR").debug("Get energy limits")
        if not self.tunable:
            self._energy_limits = (self._default_energy, self._default_energy)
        else:
            self._energy_limits = self._energy_motor.get_limits()
        return self._energy_limits

    def get_wavelength_limits(self):
        """Return wavelength low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit).
        """
        logging.getLogger("HWR").debug("Get wavelength limits")
        if self.tunable:
            _low, _high = self.get_limits()
            self._wavelength_limits = (
                self._calculate_wavelength(_low),
                self._calculate_wavelength(_high),
            )
        else:
            self._wavelength_limits = (self.get_wavelength(), self.get_wavelength())
        return self._wavelength_limits

    def stop(self):
        """Stop the energy motor movement"""
        self._energy_motor.stop()

    def get_state(self):
        if not self.tunable:
            self.state = HardwareObjectState.READY
        else:
            self.state = self._energy_motor.get_state()
        return self.state

    def move_energy(self, value, wait=True, timeout=None):
        """Move energy to absolute position. Wait the move to finish.
        Args:
            value (float): target value.
            wait (bool): optional - wait until motor movement finished.
            timeout (float): optional - timeout [s].
        """
        _en = self.get_energy()

        pos = math.fabs(_en - value)
        if pos < 0.001:
            logging.getLogger("user_level_log").debug(
                "Energy: already at %g, not moving", value
            )
            return

        logging.getLogger("user_level_log").debug("Energy: moving energy to %g", value)

        def change_energy():
            try:
                # self._bliss_session.change_energy(value)
                self._energy_motor.set_value(value)
            except RuntimeError:
                self._energy_motor.set_value(value)

        if pos > 0.02:
            if wait:
                change_energy()
            else:
                gevent.spawn(change_energy)
        else:
            self._energy_motor.set_value(value, wait=wait)

    def set_wavelength(self, value, wait=True, timeout=None):
        value = self._calculate_energy(value)
        self.move_energy(value, wait, timeout)

    def update_value(self, position):
        """Check if the position has changed. Emist signal positionChanged.
        Args:
            position (float): energy position
        """
        wavelength = self._calculate_wavelength(position)
        self.emit("energyChanged", (position, wavelength))
        self.emit("valueChanged", (position,))

    """
    def start_move_energy(self, value, wait=True):
        if not self.tunable:
            return False

        try:
            value = float(value)
        except (TypeError, ValueError) as diag:
            logging.getLogger("user_level_log").error(
                "Energy: invalid energy (%s)" % value
            )
            return False

        current_en = self.get_current_energy()
        if current_en:
            if math.fabs(value - current_en) < 0.001:
                self.moveEnergyCmdFinished(True)
        if self.checkLimits(value) is False:
            return False

        self.moveEnergyCmdStarted()

        def change_egy():
            try:
                self.move_energy(value, wait=True)
            except BaseException:
                sys.excepthook(*sys.exc_info())
                self.moveEnergyCmdFailed()
            else:
                self.moveEnergyCmdFinished(True)

        if wait:
            change_egy()
        else:
            gevent.spawn(change_egy)

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
        if self.get_energy_limits():
            if value >= self.en_lims[0] and value <= self.en_lims[1]:
                logging.getLogger("HWR").info("Limits ok")
                return True
            logging.getLogger("user_level_log").info("Requested value is out of limits")
        return False

    def start_move_wavelength(self, value, wait=True):
        logging.getLogger("HWR").info("Moving wavelength to (%s)" % value)
        return self.startMoveEnergy(12.3984 / value, wait)

    def cancelMoveEnergy(self):
        logging.getLogger("user_level_log").info("Cancel move")
        self.moveEnergy.abort()

    def move_energy(self, energy, wait=True):
        current_en = self.get_current_energy()
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
                        self.executeCommand("moveEnergy", energy, wait=True)
                except RuntimeError as AttributeError:
                    self.energy_motor.set_value(energy)
            else:
                self.energy_motor.set_value(energy)

    """
