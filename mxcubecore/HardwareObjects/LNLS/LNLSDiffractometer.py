import time

from gevent.event import AsyncResult

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.GenericDiffractometer import (
    GenericDiffractometer,
    PhaseEnum,
)


class LNLSDiffractometer(GenericDiffractometer):
    def __init__(self, name):
        GenericDiffractometer.__init__(self, name)

    def init(self):
        GenericDiffractometer.init(self)
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")
        self.pixels_per_mm_x = 10**-4
        self.pixels_per_mm_y = 10**-4
        self.beam_position = [318, 238]
        self.in_plate_mode = False
        self.last_centred_position = self.beam_position
        self.current_motor_positions = {
            "phiy": 0,
            "sampx": 0,
            "sampy": 0,
            "zoom": 0,
            "focus": 0,
            "phiz": 0,
            "omega": 0,
            "kappa": 0,
            "kappa_phi": 0,
        }

        self.centring_time = 0
        self.mount_mode = self.get_property("sample_mount_mode")
        if self.mount_mode is None:
            self.mount_mode = "manual"

    def is_ready(self) -> bool:
        return True

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

    def motor_positions_to_screen(self, motor_positions):
        return self.beam_position

    def get_value_motors(self):
        return self.current_motor_positions

    def get_phase(self):
        unknown_phase = PhaseEnum.unknown
        phase = self.get_current_phase()
        if not phase:
            phase = unknown_phase
        return phase

    def get_chip_configuration(self):
        return None
