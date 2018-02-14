from XRFSpectrum import *
import logging


class ID29XRFSpectrum(XRFSpectrum):
    def __init__(self, *args, **kwargs):
        XRFSpectrum.__init__(self, *args, **kwargs)
        self.mca_hwobj = self.getObjectByRole('mca')
        self.ctrl_hwobj = self.getObjectByRole('controller')

    def preset_mca(self, ctime, fname=None):
        self.mca_hwobj.set_roi(2, 15, channel=1)
        self.mca_hwobj.set_presets(erange=1, ctime=ctime, fname=fname)

    def choose_attenuation(self, ctime, fname=None):
        res = True
        if not fname:
            fname = self.spectrumInfo["filename"].replace('.dat', '.raw')

        self.preset_mca(ctime, fname)

        self.ctrl_hwobj.detcover.set_in()
        try:
            tt = self.ctrl_hwobj.find_max_attenuation(ctime=ctime,
                                                      fname=fname,
                                                      roi=[2., 15.])
            self.spectrumInfo["beamTransmission"] = tt
        except Exception as e:
            logging.getLogger('user_level_log').exception(str(e))
            res = False

        return res

    def _findAttenuation(self, ct):
        return self.choose_attenuation(ct)
