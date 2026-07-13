from gevent.event import AsyncResult

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractDiffractometer import AbstractDiffractometer, DiffractometerPhase


class LNLSDiffractometer(AbstractDiffractometer):

    def init(self):
        AbstractDiffractometer.init(self)
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")
        self.current_motor_positions = {}
        self.current_phase = DiffractometerPhase.UNKNOWN

    def manual_centring(self):
        self.log.info("Initializing manual sample alignment...")
        for step in range(3):
            self.log.info(f"Step {step + 1} of 3...")
            self.user_clicked_event = AsyncResult()
            self.waiting_for_click = True
            x, y = self.user_clicked_event.get()
            self.log.info(f"{x}, {y}")
            self._bluesky_api.execute_plan(
                plan_name="manual_alignment",
                kwargs={"x_px": x, "y_px": y, "step": step},
            )
        self.log.info("Manual sample alignment has finished...")
        return {}

    def automatic_centring(self):
        self.log.info("Initializing automatic sample alignment...")
        self._bluesky_api.execute_plan(plan_name="automatic_alignment")
        self.log.info("Automatic sample alignment has finished...")

    def move_to_beam(self, x, y, omega=None):
        self.log.info("Moving to beam...")

        self._bluesky_api.execute_plan(
            plan_name="move_to_beam",
            kwargs={
                "x_px": x - self.beam_position[0],
                "y_px": y - self.beam_position[1],
            },
        )
        self.log.info("Move to beam has finished...")
    
    def get_pixels_per_mm(self):
        return (1, 1)