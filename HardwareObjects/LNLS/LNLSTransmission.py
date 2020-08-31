# encoding: utf-8
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

import logging

from HardwareRepository.HardwareObjects.abstract.AbstractTransmission import (
    AbstractTransmission,
)
from HardwareRepository.HardwareObjects.LNLS.EPICSActuator import EPICSActuator

from HardwareRepository.HardwareObjects.LNLS.read_transmission_mnc import (
    read_transmission
)
from HardwareRepository.HardwareObjects.LNLS.set_transmission_mnc import (
    get_transmission, set_foils
)

__copyright__ = """ Copyright © 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class LNLSTransmission(EPICSActuator, AbstractTransmission):
    """Transmission value as a percentage """

    def init(self):
        """Override method."""
        AbstractTransmission.init(self)
        self.energy = self.getObjectByRole("energy")

    def get_value(self):
        """Override method."""
        try:
            energy_val = float(self.energy.get_value())  # Check if valid energy
            value, status = read_transmission(energy_val)
        except Exception as e:
            return "--"

        if status == 1:
            return "--"  # Invalid transmission read

        percentage = round(value * 100, 2)
        return percentage

    def _set_value(self, value):
        """Override method."""
        try:
            energy_val = float(self.energy.get_value())  # Check if valid energy
            _, actual_transmission, filter_setup = get_transmission(
                energy_val, value)
            actual_transmission = round(actual_transmission * 100, 2)

            logging.getLogger("HWR").info(
                "Requested transmission: %s. Closest possible value: %s" %
                (str(value), str(actual_transmission))
            )

            # status 0 is ok, status 1 is failure
            foil_status = set_foils(filter_setup)
        except Exception as e:
            logging.getLogger("HWR").error(
                "Error while setting transmission: %s" % str(e)
            )
        else:
            if foil_status == 0:
                logging.getLogger("HWR").info(
                    "Transmission is successfully set!"
                )
                return
            logging.getLogger("HWR").error(
                "Error: transmission could not be set (returned status %s)." %
                foil_status
            )
