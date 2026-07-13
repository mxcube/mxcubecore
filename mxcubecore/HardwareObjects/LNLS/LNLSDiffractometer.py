from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractDiffractometer import (
    AbstractDiffractometer,
    DiffractometerPhase,
)


class LNLSDiffractometer(AbstractDiffractometer):
    def init(self):
        AbstractDiffractometer.init(self)
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")
        self.current_phase = DiffractometerPhase.UNKNOWN
        self.set_is_ready(True)

    def get_pixels_per_mm(self):
        return (1, 1)

    def save_centring_positions(self):
        return

    def wait_status_ready(self, timeout=None):
        return True
