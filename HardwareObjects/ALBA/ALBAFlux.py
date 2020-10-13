from HardwareRepository.HardwareObjects.abstract import AbstractFlux
from HardwareRepository.BaseHardwareObjects import Device
import taurus
import logging


class ALBAFlux(Device, AbstractFlux.AbstractFlux):
    def init(self):
        super(ALBAFlux, self).init()
        self.current_dev = taurus.Device("pc/mach_attrpc_ctrl/1")
        self.vars_dev = taurus.Device("bl13/ct/variables")
        self.trans_mot = taurus.Device("mbattrans")

    def get_value(self):
        fluxlast = self.vars_dev["fluxlast"].value

        try:
            if fluxlast > 1e7:
                return self.last_current_trans()
        except Exception:
            pass

        logging.getLogger("HWR").debug(
            " Abnormally low value of flux. Returning default value"
        )
        default_flux = 6e11 * self.get_transmission()
        return default_flux

    def get_transmission(self):
        """ returns transmission between 0 and 1"""
        return self.trans_mot.position / 100.0

    def last_current_trans(self):
        current = self.current_dev.value
        fluxlastnorm = self.vars_dev["fluxlastnorm"].value

        last_current = (fluxlastnorm / 250.0) * current

        return last_current * self.get_transmission()

    def get_dose_rate(self, energy=None):
        """
        Get dose rate in kGy/s for a standard crystal at current settings.
        Assumes Gaussian beam with beamsize giving teh FWHH in both dimensions.

        :param energy: float Energy for calculation of dose rate, in keV.
        :return: float
        """

        # The factor 1.25 converts from the average value over the beamsize
        # to an estimated flux density at the peak.
        return 1.25 * super(ALBAFlux, self).get_dose_rate(energy=energy)


def test_hwo(hwo):
    print(hwo.get_value())
