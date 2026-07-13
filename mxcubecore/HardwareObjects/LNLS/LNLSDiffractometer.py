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
        self.update_state(self.STATES.READY)

    def get_pixels_per_mm(self):
        zoom_enum = self.zoom.get_value()
        current_zoom = zoom_enum.name
        mm_per_pixel_x = self.zoom.get_property("mm_per_pixel_x")[current_zoom]
        mm_per_pixel_y = self.zoom.get_property("mm_per_pixel_y")[current_zoom]
        pixel_per_mm_x = round(1 / mm_per_pixel_x, 6)
        pixel_per_mm_y = round(1 / mm_per_pixel_y, 6)
        return (pixel_per_mm_x, pixel_per_mm_y)

    def save_centring_positions(self):
        return

    def wait_status_ready(self, timeout=None):
        return True
