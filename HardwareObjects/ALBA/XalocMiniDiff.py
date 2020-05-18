import logging
import time
from HardwareRepository.HardwareObjects.GenericDiffractometer import (
    GenericDiffractometer,
)
from gevent.event import AsyncResult
import gevent


class XalocMiniDiff(GenericDiffractometer):
    def __init__(self, *args):
        GenericDiffractometer.__init__(self, *args)
        self.centring_hwobj = None

    def init(self):
        self.calibration = self.getObjectByRole("calibration")
        self.centring_hwobj = self.getObjectByRole("centring")
        if self.centring_hwobj is None:
            logging.getLogger("HWR").debug("EMBLMinidiff: Centring math is not defined")

        self.cmd_start_auto_focus = self.get_command_object("startAutoFocus")

        self.phi_motor_hwobj = self.getObjectByRole("phi")
        self.phiz_motor_hwobj = self.getObjectByRole("phiz")
        self.phiy_motor_hwobj = self.getObjectByRole("phiy")
        self.zoom_motor_hwobj = self.getObjectByRole("zoom")
        self.focus_motor_hwobj = self.getObjectByRole("focus")
        self.sample_x_motor_hwobj = self.getObjectByRole("sampx")
        self.sample_y_motor_hwobj = self.getObjectByRole("sampy")

        if self.phi_motor_hwobj is not None:
            self.connect(
                self.phi_motor_hwobj, "stateChanged", self.phi_motor_state_changed
            )
            self.connect(self.phi_motor_hwobj, "valueChanged", self.phi_motor_moved)
        else:
            logging.getLogger("HWR").error("EMBLMiniDiff: Phi motor is not defined")

        if self.phiz_motor_hwobj is not None:
            self.connect(
                self.phiz_motor_hwobj, "stateChanged", self.phiz_motor_state_changed
            )
            self.connect(self.phiz_motor_hwobj, "valueChanged", self.phiz_motor_moved)
        else:
            logging.getLogger("HWR").error("EMBLMiniDiff: Phiz motor is not defined")

        if self.phiy_motor_hwobj is not None:
            self.connect(
                self.phiy_motor_hwobj, "stateChanged", self.phiy_motor_state_changed
            )
            self.connect(self.phiy_motor_hwobj, "valueChanged", self.phiy_motor_moved)
        else:
            logging.getLogger("HWR").error("EMBLMiniDiff: Phiy motor is not defined")

        if self.zoom_motor_hwobj is not None:
            self.connect(
                self.zoom_motor_hwobj, "valueChanged", self.zoom_position_changed
            )
            self.connect(
                self.zoom_motor_hwobj,
                "predefinedPositionChanged",
                self.zoom_motor_predefined_position_changed,
            )
            self.connect(
                self.zoom_motor_hwobj, "stateChanged", self.zoom_motor_state_changed
            )
        else:
            logging.getLogger("HWR").error("EMBLMiniDiff: Zoom motor is not defined")

        if self.sample_x_motor_hwobj is not None:
            self.connect(
                self.sample_x_motor_hwobj,
                "stateChanged",
                self.sampleX_motor_state_changed,
            )
            self.connect(
                self.sample_x_motor_hwobj, "valueChanged", self.sampleX_motor_moved
            )
        else:
            logging.getLogger("HWR").error("EMBLMiniDiff: Sampx motor is not defined")

        if self.sample_y_motor_hwobj is not None:
            self.connect(
                self.sample_y_motor_hwobj,
                "stateChanged",
                self.sampleY_motor_state_changed,
            )
            self.connect(
                self.sample_y_motor_hwobj, "valueChanged", self.sampleY_motor_moved
            )
        else:
            logging.getLogger("HWR").error("EMBLMiniDiff: Sampx motor is not defined")

        if self.focus_motor_hwobj is not None:
            self.connect(self.focus_motor_hwobj, "valueChanged", self.focus_motor_moved)

        GenericDiffractometer.init(self)

    def getCalibrationData(self, offset=None):
        calibx, caliby = self.calibration.getCalibration()
        return 1000.0 / caliby, 1000.0 / caliby
        # return 1000./self.md2.CoaxCamScaleX, 1000./self.md2.CoaxCamScaleY

    def get_pixels_per_mm(self):
        px_x, px_y = self.getCalibrationData()
        return (px_x, px_y)

    def update_pixels_per_mm(self, *args):
        """
        Descript. :
        """
        self.pixels_per_mm_x, self.pixels_per_mm_y = self.getCalibrationData()
        self.emit("pixelsPerMmChanged", ((self.pixels_per_mm_x, self.pixels_per_mm_y),))

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        """
        return {"omega": [200, 200]}
        # raise NotImplementedError

    def getBeamInfo(self, update_beam_callback):
        calibx, caliby = self.calibration.getCalibration()

        size_x = self.get_channel_object("beamInfoX").getValue() / 1000.0
        size_y = self.get_channel_object("beamInfoY").getValue() / 1000.0

        data = {"size_x": size_x, "size_y": size_y, "shape": "ellipse"}

        update_beam_callback(data)

    def in_plate_mode(self):
        return False

    def manual_centring(self):
        """
        Descript. :
        """
        self.centring_hwobj.initCentringProcedure()

        # self.head_type = self.chan_head_type.getValue()

        for click in range(3):
            self.user_clicked_event = gevent.event.AsyncResult()
            x, y = self.user_clicked_event.get()
            self.centring_hwobj.appendCentringDataPoint(
                {
                    "X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                    "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y,
                }
            )

            if self.in_plate_mode():
                dynamic_limits = self.phi_motor_hwobj.getDynamicLimits()
                if click == 0:
                    self.phi_motor_hwobj.set_value(dynamic_limits[0])
                elif click == 1:
                    self.phi_motor_hwobj.set_value(dynamic_limits[1])
            else:
                if click < 2:
                    self.phi_motor_hwobj.set_value_relative(-90)
        # self.omega_reference_add_constraint()
        return self.centring_hwobj.centeredPosition(return_by_name=False)

    def phi_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["phi"] = pos
        self.emit_diffractometer_moved()
        self.emit("phiMotorMoved", pos)
        # self.emit('stateChanged', (self.current_motor_states["phi"], ))

    def phi_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_motor_states["phi"] = state
        self.emit("stateChanged", (state,))

    def phiz_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["phiz"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def phiz_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.emit("stateChanged", (state,))

    def phiy_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.emit("stateChanged", (state,))

    def phiy_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["phiy"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def zoom_position_changed(self, value):
        self.update_pixels_per_mm()
        self.current_motor_positions["zoom"] = value
        self.refresh_omega_reference_position()

    def zoom_motor_predefined_position_changed(self, position_name, offset):
        """
        Descript. :
        """
        self.update_pixels_per_mm()
        self.emit("zoomMotorPredefinedPositionChanged", (position_name, offset))

    def zoom_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.emit("stateChanged", (state,))

    def sampleX_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["sampx"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def sampleX_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_motor_states["sampx"] = state
        self.emit("stateChanged", (state,))

    def sampleY_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["sampy"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def sampleY_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_motor_states["sampy"] = state
        self.emit("stateChanged", (state,))

    def focus_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["focus"] = pos

    def start_auto_focus(self):
        self.cmd_start_auto_focus()
