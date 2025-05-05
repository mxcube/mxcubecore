# encoding: utf-8
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Photon flux calculations
Example xml_ configuration:

.. code-block:: yaml

 class: ESRF.ESRFPhotonFlux.ESRFPhotonFlux
  configuration:
    beam_check_name: checkbeam
    counter_name: i0
    threshold: 5000000000.0
    username: Photon flux
  objects:
    aperture: udiff_aperture.yaml
    controller: bliss.yaml
    monitor_beam: monitor_beam.yaml
"""

import logging

from gevent import sleep, spawn

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractFlux import AbstractFlux


class ESRFPhotonFlux(AbstractFlux):
    """Photon flux calculation"""

    def __init__(self, name):
        super().__init__(name)
        self._counter = None
        self._flux_calc = None
        self._beam_check_obj = None
        self.beam_check_name = None
        self.counter_name = None
        self.threshold = None
        self.aperture = None
        self.controller = None
        self.monitor_beam = None

    def init(self):
        """Initialisation"""
        super().init()
        self.threshold = self.threshold or 0.0
        self.controller = self.get_object_by_role("controller")

        try:
            self._flux_calc = self.controller.CalculateFlux()
            self._flux_calc.init()
        except AttributeError:
            logging.getLogger("HWR").exception(
                "Could not get flux calculation from BLISS"
            )
        counter_name = self.get_property("counter_name")

        if counter_name:
            self._counter = getattr(self.controller, counter_name)
        else:
            logging.getLogger("HWR").exception(
                "Counter to read the flux is not configured"
            )

        if self.beam_check_name:
            self._beam_check_obj = getattr(self.controller, self.beam_check_name)

        try:
            HWR.beamline.safety_shutter.connect("stateChanged", self.update_value)
        except AttributeError as err:
            raise RuntimeError("Safety shutter is not configured") from err

        self._poll_task = spawn(self._poll_flux)

    def _poll_flux(self):
        """Poll the flux every 3 seconds"""
        while True:
            self.re_emit_values()
            sleep(3)

    def get_value(self):
        """Get the flux value as function of a diode reading, the energy
           and the aperture factor (if any).
        Returns:
            (float): The flux value or 0 if below the pre-defined threshold.
        """
        counts = self._counter.raw_read
        if isinstance(counts, list):
            counts = float(counts[0])
        if counts == -9999:
            # no good value from the diode
            return 0.0

        try:
            egy = HWR.beamline.energy.get_value()
            calib = self._flux_calc.calc_flux_factor(egy * 1000.0)[
                self._counter.diode.name
            ]
        except AttributeError:
            egy = 0
            calib = 0

        factor = 1.0
        if self.aperture:
            label = self.aperture.get_value().name
            aperture_factor = self.aperture.get_factor(label)
            if isinstance(aperture_factor, tuple):
                factor = aperture_factor[0] + aperture_factor[1] * egy
            else:
                factor = float(aperture_factor)

        counts = abs(counts * calib * factor)
        if counts < self.threshold:
            return 0.0

        return counts

    @property
    def check_beam(self):
        """Check if there is beam
        Returns:
            (bool): True if beam present, False otherwise
        """
        return self._beam_check_obj.check_beam()

    def wait_for_beam(self, timeout=None):
        """Wait until beam present.
        Args:
            timeout (float): optional - timeout [s],
                             If timeout == 0: return at once and do not wait
                                              (default);
                             if timeout is None: wait forever.
        """
        try:
            if self.monitor_beam.get_value().value is True:
                if self._beam_check_obj:
                    return self._beam_check_obj.wait_for_beam(timeout)
                return True
        except AttributeError:
            return True
