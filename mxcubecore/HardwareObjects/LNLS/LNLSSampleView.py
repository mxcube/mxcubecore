import logging

import gevent
from mxcubeweb.app import MXCUBEApplication as frontendApplication
from mxcubeweb.core.util.convertutils import to_camel

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractSampleChanger import SampleChangerState
from mxcubecore.HardwareObjects.SampleView import Grid, SampleView


class LNLSSampleView(SampleView):
    def init(self):
        SampleView.init(self)
        self.user_level_log = logging.getLogger("user_level_log")
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")
        self.sc = HWR.beamline.get_object_by_role("sample_changer")
        self.READY_FOR_NEXT_CLICK = gevent.event.Event()
        self.x, self.y = None, None
        self.frontend_application = frontendApplication
        self.current_centring_method = None

    def move_to_beam_bluesky(self, x, y, plan_name, step=-1):
        beam_pos = HWR.beamline.beam.get_beam_position_on_screen()
        plan_kwargs = {
            "x_px": beam_pos[0] - x,
            "y_px": y - beam_pos[1],
        }
        if step != -1:
            plan_kwargs["step"] = step
        self._bluesky_api.execute_plan(plan_name=plan_name, kwargs=plan_kwargs)

    def move_to_beam(self, x, y):
        if self.sc.get_state() != SampleChangerState.Ready:
            return
        self.user_level_log.info("Moving to beam...")
        self.move_to_beam_bluesky(x, y, "move_to_beam")
        self.user_level_log.info("Move to beam has finished...")

    def start_centring(self, centring_method):
        self.current_centring_method = centring_method
        self.current_centring_procedure = centring_method
        self.emit("centringStarted", (centring_method))

    def finish_centring(self):
        self.centring_status["valid"] = True
        omega, phiy, phiz, sampx, sampy = self.get_current_diffractometer_positions()
        self.centring_status["motors"] = {
            "omega": omega,
            "phiy": phiy,
            "phiz": phiz,
            "sampx": sampx,
            "sampy": sampy,
        }
        self.emit(
            "centringSuccessful",
            (self.current_centring_method, self.get_centring_status()),
        )
        if self.current_centring_method == "Manual":
            self.shapes.clear()
            self.frontend_application.server.emit(
                "update_shapes", {"shapes": self.shapes}, namespace="/hwr"
            )
            self.frontend_application.server.emit("abort_centring", namespace="/hwr")
        self.current_centring_procedure = None
        self.current_centring_method = None

    def start_auto_centring(self):
        self.user_level_log.info("Initializing automatic sample alignment...")
        if self.current_centring_method is not None:
            self.user_level_log.info("Already centring")
            return
        self.start_centring("Automatic")
        self._bluesky_api.execute_plan(plan_name="automatic_alignment")
        self.user_level_log.info("Automatic sample alignment has finished...")
        self.finish_centring()

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
        if self.current_centring_method is not None:
            self.user_level_log.info("Already centring")
            return
        self.start_centring("Manual")
        for step in range(3):
            self.READY_FOR_NEXT_CLICK.clear()
            self.READY_FOR_NEXT_CLICK.wait()
            if (self.x is not None) and (self.y is not None):
                self.move_to_beam_bluesky(self.x, self.y, "manual_alignment", step)
                self.x = None
                self.y = None
        self.user_level_log.info("Manual sample alignment has finished...")
        self.finish_centring()

    def get_snapshot(self):
        return None

    def _wait_for_centring_finishes(self):
        return

    def get_current_diffractometer_positions(self):
        d = HWR.beamline.diffractometer
        omega = d.omega.get_value()
        phiy = d.phiy.get_value()
        phiz = d.phiz.get_value()
        sampx = d.sampx.get_value()
        sampy = d.sampy.get_value()
        return omega, phiy, phiz, sampx, sampy

    def get_current_mm_per_pixel(self):
        d = HWR.beamline.diffractometer
        zoom_enum = d.zoom.get_value()
        current_zoom = zoom_enum.name
        mm_per_pixel_x = d.zoom.get_property("mm_per_pixel_x")[current_zoom]
        mm_per_pixel_y = d.zoom.get_property("mm_per_pixel_y")[current_zoom]
        return mm_per_pixel_x, mm_per_pixel_y

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        omega, phiy, phiz, sampx, sampy = self.get_current_diffractometer_positions()

        beam_pos = HWR.beamline.beam.get_beam_position_on_screen()
        x_px = beam_pos[0] - x
        y_px = y - beam_pos[1]

        mm_per_pixel_x, mm_per_pixel_y = self.get_current_mm_per_pixel()

        sampx = sampx + x_px * mm_per_pixel_x
        sampy = sampy + y_px * mm_per_pixel_y

        return {
            "omega": omega,
            "phiy": phiy,
            "phiz": phiz,
            "sampx": sampx,
            "sampy": sampy,
        }

    def _update_shape_positions(self, *args, **kwargs):
        for shape in self.get_shapes():
            if not isinstance(shape, Grid):
                shape.update_position(self.motor_positions_to_screen)
        self.emit("shapesChanged")

    def update_grid_positions(self, pixel_diff_x, pixel_diff_y):
        final_shape_dict = {}
        grid_list = self.get_grids()
        for grid in grid_list:
            shape = self.get_shape(grid.id)
            shape_dict = to_camel(shape.as_dict())
            previous_coord = shape_dict["screenCoord"]
            new_coord = [
                (previous_coord[0] - pixel_diff_x),
                previous_coord[1] - pixel_diff_y,
            ]
            shape_dict["screenCoord"] = new_coord
            shape_dict["cellCountFun"] = "left-to-right"
            grid.update_from_dict({"screenCoord": new_coord})
            grid.screen_coord = new_coord
            final_shape_dict.update({grid.id: shape_dict})
            self.frontend_application.server.emit(
                "update_shapes", {"shapes": final_shape_dict}, namespace="/hwr"
            )
            self.emit("shapesChanged")
