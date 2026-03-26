"""LimaPilatus4Detector Class
Lima Tango Device Server implementation of the Dectris Pilatus4 Detector.
Differs from Eiger only in the energy threshold handling.
"""

import math

import requests

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.LimaEigerDetector import LimaEigerDetector


class LimaPilatus4Detector(LimaEigerDetector):
    def init(self):
        """Initialise the photon_energy and the thresholds"""
        super().init()

        eiger_device = self.get_property("eiger_device")

        for channel_name in ("threshold_energy", "threshold_energy2"):
            self.add_channel(
                {"type": "tango", "name": channel_name, "tangoname": eiger_device},
                channel_name,
            )
        # the threshold must be reset after setting the photon_energy
        self.set_energy_threshold(HWR.beamline.energy.get_value())

    def set_energy_threshold(self, energy):
        min_e = self.get_property("minE")
        energy = max(energy, min_e)

        working_energy_chan = self.get_channel_object("photon_energy")
        working_energy = working_energy_chan.get_value() / 1000.0
        if math.fabs(working_energy - energy) > 0.1:
            egy = int(energy * 1000.0)
            working_energy_chan.set_value(egy)

        threshold = self.get_channel_object("threshold_energy").get_value()
        # set the other thresholds to the same value as 1
        for chn in range(2, 5, 1):
            api_url = self.get_property("detector_api_url")
            if not api_url:
                raise RuntimeError("Cannot set detector energy threshold")  # noqa: EM101
            url = f"{api_url}/config/threshold/{chn}/energy"
            try:
                requests.put(url, '{"value": %f}' % threshold, timeout=120)
            except Exception:  # noqa: BLE001
                requests.put(url, '{"value": %f}' % threshold, timeout=120)
