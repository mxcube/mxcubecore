import logging

from gevent.event import AsyncResult

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.SampleView import SampleView


class LNLSSampleView(SampleView):
    def init(self):
        SampleView.init(self)
        self.user_level_log = logging.getLogger("user_level_log")
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")

    def move_to_beam(self, x, y):
        self.user_level_log.info("Moving to beam...")

        beam_pos = HWR.beamline.beam.get_beam_position_on_screen()
        self._bluesky_api.execute_plan(
            plan_name="move_to_beam",
            kwargs={
                "x_px": x - beam_pos[0],
                "y_px": y - beam_pos[1],
            },
        )
        self.user_level_log.info("Move to beam has finished...")

    def start_manual_centring(self, nb_click: int = 3):
        self.user_level_log.info("Initializing manual sample alignment...")
        for step in range(nb_click):
            self.user_level_log.info(f"Step {step + 1} of 3...")
            self.user_clicked_event = AsyncResult()
            x, y = self.user_clicked_event.get()
            self._bluesky_api.execute_plan(
                plan_name="manual_alignment",
                kwargs={"x_px": x, "y_px": y, "step": step},
            )
        self.user_level_log.info("Manual sample alignment has finished...")

    def start_auto_centring(self):
        self.user_level_log.info("Initializing automatic sample alignment...")
        self._bluesky_api.execute_plan(plan_name="automatic_alignment")
        self.user_level_log.info("Automatic sample alignment has finished...")
