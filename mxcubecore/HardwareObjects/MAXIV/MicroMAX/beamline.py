"""Custom MicroMAX Beamline object.

Adds support for `sample_delivery` configurable, which
specifies the sample delivery mode for MXCuBE.

Following sample delivery modes are supported:

* osc - Oscillation sample delivery
* hve - HVE (injector) sample delivery

Example of `sample_delivery` configuration::

  configuration:
    sample_delivery: osc
"""

from enum import Enum

import mxcubecore.HardwareObjects.MAXIV.beamline


class SampleDelivery(Enum):
    osc = "osc"
    hve = "hve"


class Beamline(mxcubecore.HardwareObjects.MAXIV.beamline.Beamline):
    def __init__(self, name):
        super().__init__(name)

        # 'cached' Sample Delivery mode config
        self._sample_delivery = None

    #
    # 'sample_delivery' config
    #

    def _load_sample_delivery(self):
        val = self.get_property("sample_delivery", SampleDelivery.osc.value)
        self._sample_delivery = SampleDelivery(val)

    @property
    def sample_delivery(self) -> SampleDelivery:
        if self._sample_delivery is None:
            self._load_sample_delivery()

        return self._sample_delivery

    def is_hve_sample_delivery(self) -> bool:
        """True when HVE sample delivery mode is configured."""
        return self.sample_delivery == SampleDelivery.hve
