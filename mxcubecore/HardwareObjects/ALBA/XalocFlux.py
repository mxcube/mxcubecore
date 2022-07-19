#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name] XalocFlux

[Description]
HwObj used to get the flux

[Signals]
- None
"""

from __future__ import print_function

import logging

from mxcubecore.HardwareObjects.abstract.AbstractFlux import AbstractFlux
from mxcubecore import HardwareRepository as HWR
#from HardwareRepository.BaseHardwareObjects import Device

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"


class XalocFlux(AbstractFlux):

    def __init__(self, name):
        self.logger = logging.getLogger("HWR.XalocFlux")
        AbstractFlux.__init__(self, name)
        self.current_chn = None
        self.transmission_chn = None
        self.last_flux_chn = None
        self.last_flux_norm_chn = None

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        self.transmission_chn = self.get_channel_object("transmission")
        self.last_flux_chn = self.get_channel_object("last_flux")
        self.last_flux_norm_chn = self.get_channel_object("last_flux_norm")

    def get_value(self):
        return self.get_flux()

    def get_flux(self):
        last_flux = self.last_flux_chn.get_value()
        try:
            if last_flux > 1e7:
                return self.get_flux_from_last_measured() * self.get_transmission()
        except Exception as e:
            self.logger.error("Cannot read flux\n%s" % str(e))
            logging.getLogger("user_level_log").error("Cannot read flux\n%s" % str(e))

        default_flux = 6e11 * self.get_transmission()
        self.logger.debug("Flux value abnormally low, returning default value (%s)" %
                          default_flux)
        return default_flux

    def get_transmission(self):
        """ returns transmission between 0 and 1"""
        return self.transmission_chn.get_value() / 100.

    def get_flux_from_last_measured(self):
        last_flux_norm = self.last_flux_norm_chn.get_value()
        current = HWR.beamline.machine_info.get_mach_current()
        self.logger.debug("XalocFlux machine current %s" % current)
        
        last_current = (last_flux_norm / 250.) * current
        return last_current

    def get_dose_rate(self, energy=None):
        """
        Get dose rate in kGy/s for a standard crystal at current settings.
        Assumes Gaussian beam with beamsize giving teh FWHH in both dimensions.

        :param energy: float Energy for calculation of dose rate, in keV.
        :return: float
        """

        # The factor 1.25 converts from the average value over the beamsize
        # to an estimated flux density at the peak.
        return 1.25 * AbstractFlux.AbstractFlux.get_dose_rate_per_photon_per_mmsq(self, energy=energy)


def test_hwo(hwo):
    print("Flux = %.4e" % hwo.get_flux())
    print("Last current = %.4e" % hwo.get_last_current())
    print("Transmission = %.2f" % hwo.get_transmission())
