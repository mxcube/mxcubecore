from mxcubecore.HardwareObjects.abstract import AbstractFlux
from mxcubecore.BaseHardwareObjects import HardwareObject
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


def test_hwo(hwo):
    print(hwo.get_value())
