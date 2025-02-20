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

"""LNLS Energy"""

import logging

from mxcubecore.HardwareObjects.abstract.AbstractEnergy import AbstractEnergy
from mxcubecore.HardwareObjects.LNLS.EPICSActuator import EPICSActuator


class LNLSEnergy(EPICSActuator, AbstractEnergy):
    """LNLSEnergy class"""

    def init(self):
        """Initialise default properties"""
        super(LNLSEnergy, self).init()
        self.update_state(self.STATES.READY)
        self.detector = self.get_object_by_role("detector")

    def set_value(self):
        """Override method."""
        pass

    def get_value(self):
        """Read the actuator position.
        Returns:
            float: Actuator position.
        """
        value = super().get_value()
        # Nominal value stores last energy value with valid threshold energy
        #if abs(self._nominal_value - value) < 0.001:
        #    logging.getLogger("HWR").info("Pilatus threshold is still okay.")
        #    return value

        threshold_ok = self.check_threshold_energy(value)
        if threshold_ok:
            self._nominal_value = value
        else:
           value = None  # Invalid energy because threshold is invalid

        return value

    def check_threshold_energy(self, energy):
        """ Returns whether detector threshold energy is valid or not."""

        #logging.getLogger("HWR").info(
        #"Checking Pilatus threshold. Please wait..."
        #)
        #for i in range(3):
        #    logging.getLogger("user_level_log").info(
        #        "Checking Pilatus threshold. Please wait..."
        #    )
        threshold_ok = self.detector.set_threshold_energy(energy)

        if threshold_ok:
            logging.getLogger("HWR").info("Pilatus threshold is okay.")
            #logging.getLogger("user_level_log").info(
            #    "Pilatus threshold is okay."
            #)
            return True

        logging.getLogger("HWR").error("Pilatus threshold is not okay.")
        #logging.getLogger("user_level_log").error(
        #    "Pilatus threshold is not okay."
        #)
        return False
