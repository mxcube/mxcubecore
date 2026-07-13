import logging

import gevent
from mxcubeweb.app import MXCUBEApplication as frontendApplication

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractSampleChanger import SampleChangerState
from mxcubecore.HardwareObjects.SampleView import SampleView


class LNLSSampleView(SampleView):
    def init(self):
        SampleView.init(self)
        self.user_level_log = logging.getLogger("user_level_log")
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")
        self.sc = HWR.beamline.get_object_by_role("sample_changer")
        self.READY_FOR_NEXT_CLICK = gevent.event.Event()
        self.x, self.y = None, None
        self.frontend_application = frontendApplication

    def move_to_beam(self, x, y):
        if self.sc.get_state() != SampleChangerState.Ready:
            return
        self.user_level_log.info("Moving to beam...")

        beam_pos = HWR.beamline.beam.get_beam_position_on_screen()
        self._bluesky_api.execute_plan(
            plan_name="move_to_beam",
            kwargs={
                "x_px": beam_pos[0] - x,
                "y_px": y - beam_pos[1],
            },
        )
        self.user_level_log.info("Move to beam has finished...")

    def image_clicked(self, x, y):
        logging.getLogger("user_level_log").info(
            f"LNLS Centring click at x:{int(x)}, y:{int(y)}"
        )
        self.x = x
        self.y = y
        self.READY_FOR_NEXT_CLICK.set()

    def start_manual_centring(self, nb_click: int = 3):
        if self.sc.get_state() != SampleChangerState.Ready:
            return
        self.user_level_log.info("Initializing manual sample alignment...")
        if self.current_centring_procedure is not None:
            self.user_level_log.exception("Already centring")
        self.current_centring_procedure = "Manual"
        self.emit("centringStarted", ("Manual"))
        for step in range(nb_click):
            self.READY_FOR_NEXT_CLICK.clear()
            self.READY_FOR_NEXT_CLICK.wait()
            beam_pos = HWR.beamline.beam.get_beam_position_on_screen()
            if (self.x is not None) and (self.y is not None):
                self._bluesky_api.execute_plan(
                    plan_name="manual_alignment",
                    kwargs={
                        "x_px": beam_pos[0] - self.x,
                        "y_px": self.y - beam_pos[1],
                        "step": step,
                    },
                )
        self.user_level_log.info("Manual sample alignment has finished...")
        self.centring_done()
        self.accept_centring()
        self.emit("centringSuccessful", ("Manual", self.get_centring_status()))
        # Clear all shapes at frontend when 3-click centring finishes
        self.shapes.clear()
        self.frontend_application.server.emit(
            "update_shapes", {"shapes": self.shapes}, namespace="/hwr"
        )

    def start_auto_centring(self):
        self.user_level_log.info("Initializing automatic sample alignment...")
        if self.current_centring_procedure is not None:
            self.user_level_log.exception("Already centring")
        self.current_centring_procedure = "Automatic"
        self.emit("centringStarted", ("Automatic"))
        self._bluesky_api.execute_plan(plan_name="automatic_alignment")
        self.user_level_log.info("Automatic sample alignment has finished...")
        self.centring_done()
        self.accept_centring()

    def get_snapshot(self):
        return None

    def _wait_for_centring_finishes(self):
        return

    def get_centred_point_from_coord(self, x, y, return_by_names=None):  # noqa: ARG002
        return {"omega": 0, "phiy": 0, "phiz": 0, "sampx": 0, "sampy": 0}
