from bliss.config import channels
from TangoKeithleyPhotonFlux import TangoKeithleyPhotonFlux


class ID232PhotonFlux(TangoKeithleyPhotonFlux):
    def __init__(self, *args, **kwargs):
        TangoKeithleyPhotonFlux.__init__(self, *args, **kwargs)

    def init(self):
        self._flux_chan = channels.Channel("mxcube:flux")
        TangoKeithleyPhotonFlux.init(self)

    def emitValueChanged(self, flux=None):
        self._flux_chan.value = flux
        return TangoKeithleyPhotonFlux.emitValueChanged(self, flux)
