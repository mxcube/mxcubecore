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

""" Photon fluc calculations
Example xml file:
<object class="ESRF.ESRFPhotonFlux">
  <username>Photon flux</username>
  <object role="controller" href="/bliss"/>
  <object role="aperture" href="/udiff_aperture"/>
  <counter_name>i0</counter_name>
</object>
"""
import logging
import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractFlux import AbstractFlux


class ESRFPhotonFlux(AbstractFlux):
    """Photon flux calculation for ID30B"""

    def __init__(self, name):
        super().__init__(name)
        self._counter = None
        self._flux_calc = None
        self._aperture = None
        self.threshold = None

    def init(self):
        """Initialisation"""
        super().init()
        controller = self.get_object_by_role("controller")

        self._aperture = self.get_object_by_role("aperture")
        self.threshold = self.get_property("threshold") or 0.0

        try:
            self._flux_calc = controller.CalculateFlux()
            self._flux_calc.init()
        except AttributeError:
            logging.getLogger("HWR").exception(
                "Could not get flux calculation from BLISS"
            )

        counter = self.get_property("counter_name")
        if counter:
            self._counter = getattr(controller, counter)
        else:
            self._counter = self.get_object_by_role("counter")

        beam_check = self.get_property("beam_check_name")
        
        if beam_check:
            self.beam_check = getattr(controller, beam_check)

        HWR.beamline.safety_shutter.connect("stateChanged", self.update_value)
        #self._poll_task = gevent.spawn(self._poll_flux)

    def _poll_flux(self):
        while True:
            self.re_emit_values()
            gevent.sleep(0.5)

    def get_value(self):
        """Calculate the flux value as function of a reading
        """

        counts = self._counter.raw_read
        if isinstance(counts, list):
            counts = float(counts[0])
        counts = float(self._counter.raw_read)
        if counts == -9999:
            counts = 0.0

        egy = HWR.beamline.energy.get_value()
        calib = self._flux_calc.calc_flux_factor(egy * 1000.0)[self._counter.diode.name]

        try:
            label = self._aperture.get_value().name
            aperture_factor = self._aperture.get_factor(label)
            if isinstance(aperture_factor, tuple):
                factor = aperture_factor[0] + aperture_factor[1]*egy
            else:
                factor = float(aperture_factor)
        except (AttributeError, ValueError, RuntimeError):
            factor = 1.

        counts = abs(counts * calib * factor)
        if counts < self.threshold:
            return 0.0

        return counts

    def check_beam(self):
        """Check if there is beam
        Returns:
            (bool): True if beam present, False otherwise
        """
        return self.beam_check.check_beam()

    def wait_for_beam(self, timeout=None):
        """Wait until beam present
        Args:
            timeout (float): optional - timeout [s],
                             If timeout == 0: return at once and do not wait
                                              (default);
                             if timeout is None: wait forever.
        """
        return self.beam_check.wait_for_beam(timeout)
