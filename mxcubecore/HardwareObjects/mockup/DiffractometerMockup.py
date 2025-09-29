#
#  Project: MXCuBE
#  https://github.com/mxcube
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
#   You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.
"""
Example xml file:

.. code-block:: xml

 <object class = "DiffractometerMockup">
  <username>MD2S</username>
  <motors>
    <device role="omega" hwrid="/diff-omega-mockup"/>
    <device role="phiy" hwrid="/diff-phiy-mockup"/>
    <device role="phiz" hwrid="/diff-phiz-mockup"/>
    <device role="phiz" hwrid="/diff-phiz-mockup"/>
    <device role="sampx" hwrid="/diff-sampx-mockup"/>
    <device role="sampy" hwrid="/diff-sampy-mockup"/>
    <device role="kappa" hwrid="/diff-kappa-mockup"/>
    <device role="kappa_phi" hwrid="/diff-kappaphi-mockup"/>
  </motors>
  <nstate_equipment>
    <object role="fshutter" href="/fast-shutter-mockup"/>
    <object role="beamstop" href="/beamstop-mockup"/>
  </nstate_equipment>
 </object>
"""

import random
import time
from warnings import warn

from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.abstract.AbstractDiffractometer import (
    AbstractDiffractometer,
    DiffractometerConstraint,
    DiffractometerHead,
    DiffractometerPhase,
)


class DiffractometerMockup(AbstractDiffractometer):
    """
    Descript. :
    """

    def init(self):
        super().init()
        self.head_type = DiffractometerHead.MINI_KAPPA
        self.current_phase = DiffractometerPhase.CENTRE
        self.current_constraint = DiffractometerConstraint.RELEASE
        self.update_state(HardwareObjectState.READY)
        for mot in self.motors_hwobj_dict.values():
            mot.set_value(random.uniform(0.0, 8.8))
        self.omega.set_value(random.uniform(0, 359.9))

    def abort(self):
        self.update_state(HardwareObjectState.READY)

    def do_oscillation_scan(self, *args, **kwargs):
        if self.in_kappa_mode:
            self.update_state(HardwareObjectState.BUSY)
            time.sleep(random.uniform(0, 2.2))
        self.update_state(HardwareObjectState.READY)

    def get_pixels_per_mm(self):
        """Get the pixel/mm values.
        Returns:
            (tuple): x,y [pixel/mm]
        """
        # calibration values
        x_calib = 0.000444
        y_calib = 0.000446
        return 1.0 / x_calib, 1.0 / y_calib

    def move_motors(self, motors_positions_dict):
        warn(
            "move_motors is deprecated, please use set_value_motors instead",
            DeprecationWarning,
        )
        self.set_value_motors(motors_positions_dict)

    def get_positions(self):
        warn(
            "get_positions is deprecated, please use get_value_motors instead",
            DeprecationWarning,
        )
        return self.get_value_motors()

    def get_current_phase(self):
        warn(
            "get_current_phase is deprecated, please use get get_phase instead",
            DeprecationWarning,
        )
        return self.get_phase().name

    def _set_phase(self, value: DiffractometerPhase):
        """Set a phase."""
        print(f"Change phase to ---> {value}")
        self.current_phase = value

    def _set_constraint(self, value):
        self.current_constraint = value
