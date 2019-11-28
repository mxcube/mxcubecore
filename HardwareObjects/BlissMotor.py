#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.
"""
Example xml file:
<device class="BlissMotor">
  <username>Detector Distance</username>
  <motor_name>dtox</motor_name>
  <tolerance>1e-2</tolerance>
</device>
"""

from gevent import Timeout
from bliss.config import static
from HardwareRepository.HardwareObjects.abstract.AbstractMotor import (
    AbstractMotor,
    MotorStates,
)

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class BlissMotor(AbstractMotor):
    """Bliss Motor implementation"""

    def __init__(self, name):
        AbstractMotor.__init__(self, name)
        self.motor = None

    def init(self):
        """Initialise the motor"""
        AbstractMotor.init(self)
        cfg = static.get_config()
        self.motor = cfg.get(self.motor_name)
        self.connect(self.motor, "position", self.update_position)
        self.connect(self.motor, "state", self.update_state)
        self.connect(self.motor, "move_done", self.update_state)

    def get_state(self):
        """Get the motor state.
        Returns:
            (list): list of 'MotorStates'.
        """
        states = []
        _state = self.motor.state.current_states_names

        # convert from bliss states to MotorStates
        try:
            for stat in _state:
                states.append(MotorStates.__members__[stat.upper()])
        except KeyError:
            states.append(MotorStates.UNKNOWN)
        self.state = states
        return self.state

    def get_position(self):
        """Read the motor position.
        Returns:
            float: Motor position.
        """
        return self.motor.position

    def get_limits(self):
        """Returns motor low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit).
        """
        # no limit = None, but None is a problematic value
        # for some GUI components (like MotorSpinBox), so
        # instead we return very large value.

        _low, _high = self.motor.limits
        _low = _low if _low else -1e6
        _high = _high if _high else 1e6
        self._limits = (_low, _high)
        return self._limits

    def get_velocity(self):
        """Read motor velocity.
        Returns:
            (float): velocity [unit/s]
        """
        self._velocity = self.motor.velocity
        return self._velocity

    def move(self, position, wait=True, timeout=None):
        """Move motor to absolute position. Wait the move to finish.
        Args:
            position (float): target position
            wait (bool): optional - wait until motor movement finished.
            timeout (float): optional - timeout [s].
        """
        self.motor.move(position, wait=wait)
        if timeout:
            self.wait_move(timeout)

    def wait_move(self, timeout=None):
        """Wait until the end of move ended, using the application state.
        Args:
            timeout(float): Timeout [s].
        """
        if timeout:
            with Timeout(timeout, RuntimeError("Execution timeout")):
                self.motor.wait_move()

    def stop(self):
        """Stop the motor movement"""
        self.motor.stop(wait=False)

    def name(self):
        """Get the motor name. Should be removed when GUI ready"""
        return self.motor_name
