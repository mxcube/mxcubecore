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

from HardwareRepository.BaseHardwareObjects import Device
import logging


class ALBAFlux(Device):

    def __init__(self, *args):
        logging.getLogger("HWR").debug("ALBAFlux : __init__")
        Device.__init__(self, *args)
        self.current_chn = None
        self.transmission_chn = None
        self.last_flux_chn = None
        self.last_flux_norm_chn = None

    def init(self):
        self.current_chn = self.getChannelObject("current")
        self.transmission_chn = self.getChannelObject("transmission")
        self.last_flux_chn = self.getChannelObject("last_flux")
        self.last_flux_norm_chn = self.getChannelObject("last_flux_norm")

    def get_flux(self):
        last_flux = self.last_flux_chn.getValue()
        try:
            if last_flux > 1e7:
                return self.get_last_current() * self.get_transmission()
        except Exception as e:
            pass

        logging.getLogger("HWR").debug("Flux value abnormally low, "
                                       "returning default value")
        default_flux = 6e11 * self.get_transmission()
        return default_flux

    def get_transmission(self):
        """ returns transmission between 0 and 1"""
        return self.transmission_chn.getValue() / 100.

    def get_last_current(self):
        last_flux_norm = self.last_flux_norm_chn.getValue()
        current = self.current_chn.getValue()
        last_current = (last_flux_norm/250.) * current
        return last_current


def test_hwo(hwo):
    print "Flux = %.4e" % hwo.get_flux()
    print "Last current = %.4e" % hwo.get_last_current()
    print "Transmission = %.2f" % hwo.get_transmission()
