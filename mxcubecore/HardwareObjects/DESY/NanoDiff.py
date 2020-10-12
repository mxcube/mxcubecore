#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
import os
import copy
import time
import logging
import tempfile
import gevent
import numpy
import math
import lucid


from HardwareRepository.HardwareObjects import queue_model_objects as qmo

from gevent.event import AsyncResult
from HardwareRepository.TaskUtils import task
from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.ConvertUtils import string_types
from HardwareRepository import HardwareRepository as HWR

# from HardwareRepository.HardwareObjects.GenericDiffractometer import GenericDiffractometer


last_centred_position = [200, 200]


class NanoDiff(HardwareObject):
    """
    Description:
    """

    """
    Centring modes enumerate
    """
    MANUAL3CLICK_MODE = "Manual 3-click"
    C3D_MODE = "Computer automatic"
    MOVE_TO_BEAM_MODE = "Move to Beam"

    """
    Gonio mode enumerate
    """
    MINIKAPPA = "MiniKappa"
    PLATE = "Plate"
    PERMANENT = "Permanent"

    def __init__(self, *args):
        """
        Description:
        """
        HardwareObject.__init__(self, *args)

        qmo.CentredPosition.set_diffractometer_motor_names(
            "phi", "focus", "phiz", "phiy", "zoom", "sampx", "sampy", "beam_x", "beam_y"
        )

        # Hardware objects ----------------------------------------------------
        self.phi_motor_hwobj = None
        self.phiz_motor_hwobj = None
        self.phiy_motor_hwobj = None
        self.zoom_motor_hwobj = None
        self.sample_x_motor_hwobj = None
        self.sample_y_motor_hwobj = None
        self.focus_motor_hwobj = None
        self.omega_reference_motor = None
        self.centring_hwobj = None
        self.minikappa_correction_hwobj = None

        # Channels and commands -----------------------------------------------
        self.chan_calib_x = None
        self.chan_calib_y = None

        # self.chan_head_type = None
        print("PP__:  Attention, chan_head_type is commented out")

        self.chan_fast_shutter_is_open = None
        self.chan_sync_move_motors = None
        self.cmd_start_set_phase = None
        self.cmd_start_auto_focus = None

        # Internal values -----------------------------------------------------
        self.beam_position = None
        self.zoom_centre = None
        self.pixels_per_mm_x = None
        self.pixels_per_mm_y = None

        self.current_sample_info = None
        self.cancel_centring_methods = None
        self.current_centring_procedure = None
        self.current_centring_method = None
        self.current_positions_dict = None
        self.current_state_dict = None
        self.current_phase = None
        self.fast_shutter_is_open = None
        self.head_type = None
        self.centring_methods = None
        self.centring_status = None
        self.centring_time = None
        self.user_confirms_centring = None
        self.user_clicked_event = None
        self.omega_reference_par = None
        self.move_to_motors_positions_task = None
        self.move_to_motors_positions_procedure = None
        self.ready_event = None
        self.in_collection = None
        self.phase_list = []
        self.reference_pos = None

        self.connect(self, "equipmentReady", self.equipmentReady)
        self.connect(self, "equipmentNotReady", self.equipmentNotReady)

    def init(self):
        """
        Description:
        """
        self.ready_event = gevent.event.Event()
        self.centring_methods = {
            NanoDiff.MANUAL3CLICK_MODE: self.start_3Click_centring,
            NanoDiff.C3D_MODE: self.start_automatic_centring,
        }
        self.cancel_centring_methods = {}
        self.current_positions_dict = {
            "phiy": 0,
            "phiz": 0,
            "sampx": 0,
            "sampy": 0,
            "zoom": 0,
            "phi": 0,
            "focus": 0,
            "beam_x": 0,
            "beam_y": 0,
        }
        self.current_state_dict = {"sampx": "", "sampy": "", "phi": ""}
        self.centring_status = {"valid": False}
        self.centring_time = 0
        self.user_confirms_centring = True
        self.user_clicked_event = AsyncResult()
        self.head_type = NanoDiff.PERMANENT

        # self.chan_calib_x = self.get_channel_object('CoaxCamScaleX')
        # self.chan_calib_y = self.get_channel_object('CoaxCamScaleY')
        self.update_pixels_per_mm()

        # self.chan_head_type = self.get_channel_object('HeadType')
        # if self.chan_head_type is not None:
        #    self.head_type = self.chan_head_type.get_value()

        print("PP__:  Attention, chan_head_type is commented out")

        self.chan_current_phase = self.get_channel_object("CurrentPhase")
        if self.chan_current_phase is not None:
            self.connect(self.chan_current_phase, "update", self.current_phase_changed)
        else:
            logging.getLogger("HWR").debug(
                "NanoDiff: Current phase channel not defined"
            )

        self.chan_fast_shutter_is_open = self.get_channel_object("FastShutterIsOpen")
        if self.chan_fast_shutter_is_open is not None:
            self.chan_fast_shutter_is_open.connect_signal(
                "update", self.fast_shutter_state_changed
            )

        self.cmd_start_set_phase = self.get_command_object("startSetPhase")
        self.cmd_start_auto_focus = self.get_command_object("startAutoFocus")

        self.centring_hwobj = self.get_object_by_role("centring")
        if self.centring_hwobj is None:
            logging.getLogger("HWR").debug("NanoDiff: Centring math is not defined")

        self.phi_motor_hwobj = self.get_object_by_role("phi")
        self.phiz_motor_hwobj = self.get_object_by_role("phiz")
        self.phiy_motor_hwobj = self.get_object_by_role("phiy")
        self.zoom_motor_hwobj = self.get_object_by_role("zoom")
        self.focus_motor_hwobj = self.get_object_by_role("focus")
        self.sample_x_motor_hwobj = self.get_object_by_role("sampx")
        self.sample_y_motor_hwobj = self.get_object_by_role("sampy")

        if HWR.beamline.beam is not None:
            self.connect(
                HWR.beamline.beam, "beamPosChanged", self.beam_position_changed
            )
        else:
            logging.getLogger("HWR").debug("NanoDiff: Beaminfo is not defined")

        if self.phi_motor_hwobj is not None:
            self.connect(
                self.phi_motor_hwobj, "stateChanged", self.phi_motor_state_changed
            )
            self.connect(self.phi_motor_hwobj, "valueChanged", self.phi_motor_moved)
        else:
            logging.getLogger("HWR").error("NanoDiff: Phi motor is not defined")

        if self.phiz_motor_hwobj is not None:
            self.connect(
                self.phiz_motor_hwobj, "stateChanged", self.phiz_motor_state_changed
            )
            self.connect(self.phiz_motor_hwobj, "valueChanged", self.phiz_motor_moved)
        else:
            logging.getLogger("HWR").error("NanoDiff: Phiz motor is not defined")

        if self.phiy_motor_hwobj is not None:
            self.connect(
                self.phiy_motor_hwobj, "stateChanged", self.phiy_motor_state_changed
            )
            self.connect(self.phiy_motor_hwobj, "valueChanged", self.phiy_motor_moved)
        else:
            logging.getLogger("HWR").error("NanoDiff: Phiy motor is not defined")

        if self.zoom_motor_hwobj is not None:
            self.connect(
                self.zoom_motor_hwobj, "valueChanged", self.update_pixels_per_mm
            )
            self.connect(
                self.zoom_motor_hwobj,
                "predefinedPositionChanged",
                self.update_pixels_per_mm,
            )
            self.connect(
                self.zoom_motor_hwobj, "stateChanged", self.zoom_motor_state_changed
            )
        else:
            logging.getLogger("HWR").error("NanoDiff: Zoom motor is not defined")

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
            logging.getLogger("HWR").error("NanoDiff: Sampx motor is not defined")

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
            logging.getLogger("HWR").error("NanoDiff: Sampx motor is not defined")

        if self.focus_motor_hwobj is not None:
            self.connect(self.focus_motor_hwobj, "valueChanged", self.focus_motor_moved)

        # if HWR.beamline.sample_view.camera is None:
        #     logging.getLogger("HWR").error("NanoDiff: Camera is not defined")
        # else:
        #     self.image_height = HWR.beamline.sample_view.camera.getHeight()
        #     self.image_width = HWR.beamline.sample_view.camera.getWidth()

        try:
            self.zoom_centre = eval(self.get_property("zoom_centre"))
        except BaseException:
            self.zoom_centre = {"x": 0, "y": 0}
            logging.getLogger("HWR").warning(
                "NanoDiff: " + "zoom centre not configured"
            )

        self.reversing_rotation = self.get_property("reversingRotation")
        try:
            self.grid_direction = eval(self.get_property("gridDirection"))
        except BaseException:
            self.grid_direction = {"fast": (0, 1), "slow": (1, 0)}
            logging.getLogger("HWR").warning(
                "NanoDiff: Grid direction is not defined. Using default."
            )

        try:
            self.phase_list = eval(self.get_property("phaseList"))
        except BaseException:
            self.phase_list = []

    def in_plate_mode(self):
        # self.head_type = self.chan_head_type.get_value()
        print("PP__:  Attention, chan_head_type is commented out")

        return self.head_type == NanoDiff.PLATE

    def use_sample_changer(self):
        return False

    def get_grid_direction(self):
        """
        Descript. :
        """
        return self.grid_direction

    def is_reversing_rotation(self):
        return self.reversing_rotation is True

    def equipmentReady(self):
        """
        Descript. :
        """
        self.emit("minidiffReady", ())

    def equipmentNotReady(self):
        """
        Descript. :
        """
        self.emit("minidiffNotReady", ())

    def is_ready(self):
        """
        Descript. :
        """
        if self.is_valid():
            for motor in (
                self.sample_x_motor_hwobj,
                self.sample_y_motor_hwobj,
                self.zoom_motor_hwobj,
                self.phi_motor_hwobj,
                self.phiz_motor_hwobj,
                self.phiy_motor_hwobj,
            ):
                if motor is not None:
                    if motor.is_moving():
                        return False
            return True
        else:
            return False

    def is_valid(self):
        """
        Descript. :
        """
        return (
            self.sample_x_motor_hwobj is not None
            and self.sample_y_motor_hwobj is not None
            and self.zoom_motor_hwobj is not None
            and self.phi_motor_hwobj is not None
            and self.phiz_motor_hwobj is not None
            and self.phiy_motor_hwobj is not None
        )

    def current_phase_changed(self, phase):
        """
        Descript. :
        """
        self.current_phase = phase
        self.emit("minidiffPhaseChanged", (self.current_phase,))
        self.refresh_video()

    def get_head_type(self):
        """
        Descript. :
        """
        return self.head_type

    def get_current_phase(self):
        """
        Descript. :
        """
        return self.current_phase

    def beam_position_changed(self, value):
        """
        Descript. :
        """
        self.beam_position = list(value)

    def phi_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["phi"] = pos
        self.emit_diffractometer_moved()
        self.emit("phiMotorMoved", pos)
        # self.emit('stateChanged', (self.current_state_dict["phi"], ))

    def phi_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_state_dict["phi"] = state
        self.emit("stateChanged", (state,))

    def phiz_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["phiz"] = pos
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
        self.current_positions_dict["phiy"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

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
        self.refresh_video()

    def sampleX_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["sampx"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def sampleX_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_state_dict["sampx"] = state
        self.emit("stateChanged", (state,))

    def sampleY_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["sampy"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()

    def sampleY_motor_state_changed(self, state):
        """
        Descript. :
        """
        self.current_state_dict["sampy"] = state
        self.emit("stateChanged", (state,))

    def focus_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["focus"] = pos

    def zoom_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_positions_dict["zoom"] = pos

    def omega_reference_add_constraint(self):
        """
        Descript. :
        """
        if self.omega_reference_par is None or self.beam_position is None:
            return
        if self.omega_reference_par["camera_axis"].lower() == "x":
            on_beam = (
                (self.beam_position[0] - self.zoom_centre["x"])
                * self.omega_reference_par["direction"]
                / self.pixels_per_mm_x
                + self.omega_reference_par["position"]
            )
        else:
            on_beam = (
                (self.beam_position[1] - self.zoom_centre["y"])
                * self.omega_reference_par["direction"]
                / self.pixels_per_mm_y
                + self.omega_reference_par["position"]
            )
        self.centring_hwobj.appendMotorConstraint(self.omega_reference_motor, on_beam)

    def omega_reference_motor_moved(self, pos):
        """
        Descript. :
        """
        if self.omega_reference_par["camera_axis"].lower() == "x":
            pos = (
                self.omega_reference_par["direction"]
                * (pos - self.omega_reference_par["position"])
                * self.pixels_per_mm_x
                + self.zoom_centre["x"]
            )
            self.reference_pos = (pos, -10)
        else:
            pos = (
                self.omega_reference_par["direction"]
                * (pos - self.omega_reference_par["position"])
                * self.pixels_per_mm_y
                + self.zoom_centre["y"]
            )
            self.reference_pos = (-10, pos)
        self.emit("omegaReferenceChanged", (self.reference_pos,))

    def fast_shutter_state_changed(self, is_open):
        self.fast_shutter_is_open = is_open
        self.emit("minidiffShutterStateChanged", (self.fast_shutter_is_open,))

    def refresh_omega_reference_position(self):
        """
        Descript. :
        """
        if self.omega_reference_motor is not None:
            reference_pos = self.omega_reference_motor.get_value()
            self.omega_reference_motor_moved(reference_pos)

    def get_available_centring_methods(self):
        """
        Descript. :
        """
        return self.centring_methods.keys()

    def update_pixels_per_mm(self, *args):
        """
        Descript. :
        """
        self.pixels_per_mm_x = 1.0  # FIXME
        self.pixels_per_mm_y = 1.0  # FIXME
        self.emit("pixelsPerMmChanged", ((self.pixels_per_mm_x, self.pixels_per_mm_y),))

    def get_pixels_per_mm(self):
        """
        Descript. :
        """
        return (self.pixels_per_mm_x, self.pixels_per_mm_y)

    def get_positions(self):
        """
        Descript. :
        """
        # self.current_positions_dict["beam_x"] = (self.beam_position[0] - \
        #     self.zoom_centre['x'] )/self.pixels_per_mm_y
        # self.current_positions_dict["beam_y"] = (self.beam_position[1] - \
        #     self.zoom_centre['y'] )/self.pixels_per_mm_x
        return self.current_positions_dict

    def get_omega_position(self):
        """
        Descript. :
        """
        return self.current_positions_dict.get("phi")

    def get_current_positions_dict(self):
        """
        Descript. :
        """
        return self.current_positions_dict

    def set_sample_info(self, sample_info):
        """
        Descript. :
        """
        self.current_sample_info = sample_info

    def set_in_collection(self, in_collection):
        """
        Descrip. :
        """
        self.in_collection = in_collection

    def get_in_collection(self):
        """
        Descrip. :
        """
        return self.in_collection

    def get_phase_list(self):
        return self.phase_list

    def start_set_phase(self, name):
        """
        Descript. :
        """
        if self.cmd_start_set_phase is not None:
            self.cmd_start_set_phase(name)
        self.refresh_video()

    def refresh_video(self):
        """
        Descript. :
        """
        if HWR.beamline.sample_view.camera is not None:
            if self.current_phase != "Unknown":
                HWR.beamline.sample_view.camera.refresh_video()
        if HWR.beamline.beam is not None:
            self.beam_position = HWR.beamline.beam.get_beam_position()

    def start_auto_focus(self):
        """
        Descript. :
        """
        if self.cmd_start_auto_focus:
            self.cmd_start_auto_focus()

    def emit_diffractometer_moved(self, *args):
        """
        Descript. :
        """
        self.emit("diffractometerMoved", ())

    def invalidate_centring(self):
        """
        Descript. :
        """
        if self.current_centring_procedure is None and self.centring_status["valid"]:
            self.centring_status = {"valid": False}
            self.emit_progress_message("")
            self.emit("centringInvalid", ())

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        Descript. :
        """
        self.centring_hwobj.initCentringProcedure()
        self.centring_hwobj.appendCentringDataPoint(
            {
                "X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y,
            }
        )
        self.omega_reference_add_constraint()
        pos = self.centring_hwobj.centeredPosition()

        if return_by_names:
            pos = self.convert_from_obj_to_name(pos)
        return pos

    def get_point_between_two_points(
        self, point_one, point_two, frame_num, frame_total
    ):
        new_point = {}
        point_one = point_one.as_dict()
        point_two = point_two.as_dict()
        for motor in point_one.keys():
            new_motor_pos = (
                frame_num
                / float(frame_total)
                * abs(point_one[motor] - point_two[motor])
                + point_one[motor]
            )
            new_motor_pos += 0.5 * (point_two[motor] - point_one[motor]) / frame_total
            new_point[motor] = new_motor_pos
        return new_point

    def move_to_coord(self, x, y, omega=None):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """
        if self.current_phase != "BeamLocation":
            try:
                pos = self.get_centred_point_from_coord(x, y, return_by_names=False)
                if omega is not None:
                    pos["phiMotor"] = omega
                self.move_to_motors_positions(pos)
            except BaseException:
                logging.getLogger("HWR").exception(
                    "NanoDiff: could not center to beam, aborting"
                )
        else:
            logging.getLogger("HWR").debug(
                "Move to screen position disabled in BeamLocation phase."
            )

    def start_centring_method(self, method, sample_info=None):
        """
        Descript. :
        """
        if self.current_centring_method is not None:
            logging.getLogger("HWR").error(
                "NanoDiff: already in centring method %s" % self.currentCentringMethod
            )
            return
        curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.centring_status = {"valid": False, "startTime": curr_time}
        self.centring_status["angleLimit"] = None
        self.emit_centring_started(method)
        try:
            fun = self.centring_methods[method]
        except KeyError as diag:
            logging.getLogger("HWR").error(
                "NanoDiff: unknown centring method (%s)" % str(diag)
            )
            self.emit_centring_failed()
        else:
            try:
                fun(sample_info)
            except BaseException:
                logging.getLogger("HWR").exception("NanoDiff: problem while centring")
                self.emit_centring_failed()

    def cancel_centring_method(self, reject=False):
        """
        Descript. :
        """
        if self.current_centring_procedure is not None:
            try:
                self.current_centring_procedure.kill()
            except BaseException:
                logging.getLogger("HWR").exception(
                    "NanoDiff: problem aborting the centring method"
                )
            try:
                fun = self.cancel_centring_methods[self.current_centring_method]
            except KeyError as diag:
                self.emit_centring_failed()
            else:
                try:
                    fun()
                except BaseException:
                    self.emit_centring_failed()
        else:
            self.emit_centring_failed()
        self.emit_progress_message("")
        if reject:
            self.reject_centring()

    def get_current_centring_method(self):
        """
        Descript. :
        """
        return self.current_centring_method

    def start_3Click_centring(self, sample_info=None):
        """
        Descript. :
        """
        self.emit_progress_message("3 click centring...")
        self.current_centring_procedure = gevent.spawn(self.manual_centring)
        self.current_centring_procedure.link(self.manual_centring_done)

    def start_automatic_centring(self, sample_info=None, loop_only=False):
        """
        Descript. :
        """
        self.emit_progress_message("Automatic centring...")
        self.current_centring_procedure = gevent.spawn(self.automatic_centring)
        self.current_centring_procedure.link(self.automatic_centring_done)

    def start_2D_centring(self, coord_x=None, coord_y=None, omega=None):
        """
        Descript. :
        """
        try:
            self.centring_time = time.time()
            curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.centring_status = {
                "valid": True,
                "startTime": curr_time,
                "endTime": curr_time,
            }
            if coord_x is None and coord_y is None:
                coord_x = self.beam_position[0]
                coord_y = self.beam_position[1]

            motors = self.get_centred_point_from_coord(
                coord_x, coord_y, return_by_names=True
            )
            if omega is not None:
                motors["phi"] = omega

            self.centring_status["motors"] = motors
            self.centring_status["valid"] = True
            self.centring_status["angleLimit"] = True
            self.emit_progress_message("")
            self.accept_centring()
            self.current_centring_method = None
            self.current_centring_procedure = None
        except BaseException:
            logging.exception("Could not complete 2D centring")

    def manual_centring(self):
        """
        Descript. :
        """
        self.centring_hwobj.initCentringProcedure()
        # self.head_type = self.chan_head_type.get_value()

        self.pixels_per_mm_x = 0.865
        self.pixels_per_mm_y = 0.830  # 865
        self.centringPhiValues = []  # according values of phi-s - (mxcubes omegas)

        print("PP__:  Attention, chan_head_type is commented out")

        for click in (0, 1, 2):
            self.user_clicked_event = AsyncResult()
            x, y = self.user_clicked_event.get()
            phiValue = self.phi_motor_hwobj.get_value()

            self.centring_hwobj.appendCentringDataPoint(
                {
                    "X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                    "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y,
                }
            )

            self.centringPhiValues.append(phiValue)

            if self.in_plate_mode():
                dynamic_limits = self.phi_motor_hwobj.getDynamicLimits()
                if click == 0:
                    self.phi_motor_hwobj.set_value(dynamic_limits[0])
                elif click == 1:
                    self.phi_motor_hwobj.set_value(dynamic_limits[1])
            else:
                if click < 2:
                    self.phi_motor_hwobj.set_value_relative(90)
        self.omega_reference_add_constraint()

        # the following lines implement centering in horizontal direction (orthogonal)
        # to the beam
        horizontalCorrection = (
            self.centring_hwobj.centringDataMatrix[0][0]
            + self.centring_hwobj.centringDataMatrix[1][0]
            + self.centring_hwobj.centringDataMatrix[2][0]
        ) / 3.0
        horizontalCorrection = -horizontalCorrection / self.pixels_per_mm_x
        print(horizontalCorrection)
        self.phiy_motor_hwobj.set_value_relative(-horizontalCorrection)

        # the following 3 lines are debug version of centering procedure. Identical as in x direction
        # verticalCorrection = (self.centring_hwobj.centringDataMatrix[0][1] + self.centring_hwobj.centringDataMatrix[1][1] + self.centring_hwobj.centringDataMatrix[2][1])/3.0
        # verticalCorrection = -verticalCorrection/ self.pixels_per_mm_y
        # self.phiz_motor_hwobj.set_value_relative(verticalCorrection)

        # Solving following system of linear equation example:
        # 1a + 1b = 35
        # 2a + 4b = 94
        # a = numpy.array([[1, 1],[2,4]])
        # b = numpy.array([35, 94])
        # print(numpy.linalg.solve(a,b))

        # from deg to radians
        self.centringPhiValues[0] = self.centringPhiValues[0] / 360.0 * 2.0 * math.pi
        self.centringPhiValues[1] = self.centringPhiValues[1] / 360.0 * 2.0 * math.pi
        self.centringPhiValues[2] = self.centringPhiValues[2] / 360.0 * 2.0 * math.pi

        # linear algebraic eqs:
        a = numpy.array(
            [
                [
                    1,
                    math.cos(self.centringPhiValues[0]),
                    math.sin(self.centringPhiValues[0]),
                ],
                [
                    1,
                    math.cos(self.centringPhiValues[1]),
                    math.sin(self.centringPhiValues[1]),
                ],
                [
                    1,
                    math.cos(self.centringPhiValues[2]),
                    math.sin(self.centringPhiValues[2]),
                ],
            ]
        )

        b = numpy.array(
            [
                self.centring_hwobj.centringDataMatrix[0][1],
                self.centring_hwobj.centringDataMatrix[1][1],
                self.centring_hwobj.centringDataMatrix[2][1],
            ]
        )

        [phizc, sampyc, sampxc] = numpy.linalg.solve(a, b)
        print("phiz correction = ", phizc)
        print("sampy correction = ", sampyc)
        print("sampx correction = ", sampxc)

        self.phiz_motor_hwobj.set_value_relative(-phizc)
        self.sample_y_motor_hwobj.set_value_relative(-sampyc)
        self.sample_x_motor_hwobj.set_value_relative(-sampxc)

        # return self.centring_hwobj.centeredPosition(return_by_name=False)
        print("PP__:  Attention, return of manual_centring is replaced via 'dummy' one")
        return self.centring_hwobj.vector_to_centred_positions([0, 0])

    def automatic_centring(self):
        """
        Descript. :
        """
        x, y = self.find_loop()
        return x, y

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Descript. :
        """
        c = centred_positions_dict

        kappa = self.current_positions_dict["kappa"]
        phi = self.current_positions_dict["kappa_phi"]

        if (c["kappa"], c["kappa_phi"]) != (
            kappa,
            phi,
        ) and self.minikappa_correction_hwobj is not None:
            # c['sampx'], c['sampy'], c['phiy']
            c["sampx"], c["sampy"], c["phiy"] = self.minikappa_correction_hwobj.shift(
                c["kappa"],
                c["kappa_phi"],
                [c["sampx"], c["sampy"], c["phiy"]],
                kappa,
                phi,
            )
        xy = self.centring_hwobj.centringToScreen(c)
        x = (xy["X"] + c["beam_x"]) * self.pixels_per_mm_x + self.zoom_centre["x"]
        y = (xy["Y"] + c["beam_y"]) * self.pixels_per_mm_y + self.zoom_centre["y"]
        return x, y

    def manual_centring_done(self, manual_centring_procedure):
        """
        Descript. :
        """
        try:
            motor_pos = manual_centring_procedure.get()
            if isinstance(motor_pos, gevent.GreenletExit):
                raise motor_pos
        except BaseException:
            logging.exception("Could not complete manual centring")
            self.emit_centring_failed()
        else:
            self.emit_progress_message("Moving sample to centred position...")
            self.emit_centring_moving()
            try:
                self.move_to_motors_positions(motor_pos)
            except BaseException:
                logging.exception("Could not move to centred position")
                self.emit_centring_failed()
            else:
                if not self.in_plate_mode():
                    self.phi_motor_hwobj.set_value_relative(-180, timeout=None)
            # logging.info("EMITTING CENTRING SUCCESSFUL")
            self.centring_time = time.time()
            self.emit_centring_successful()
            self.emit_progress_message("")

    def automatic_centring_done(self, auto_centring_procedure):
        """
        Descript. :
        """
        print("automatic_centring_done...")
        res = auto_centring_procedure.get()
        self.emit("newAutomaticCentringPoint", (res[0], res[1]))

        return

        try:
            motor_pos = manual_centring_procedure.get()
            if isinstance(motor_pos, gevent.GreenletExit):
                raise motor_pos
        except BaseException:
            logging.exception("Could not complete automatic centring")
            self.emit_centring_failed()
        else:
            self.emit_progress_message("Moving sample to centred position...")
            self.emit_centring_moving()
            try:
                self.move_to_motors_positions(motor_pos)
            except BaseException:
                logging.exception("Could not move to centred position")
                self.emit_centring_failed()
            else:
                if not self.in_plate_mode():
                    self.phi_motor_hwobj.set_value(-180, timeout=None)
            # logging.info("EMITTING CENTRING SUCCESSFUL")
            self.centring_time = time.time()
            self.emit_centring_successful()
            self.emit_progress_message("")

    def move_to_centred_position(self, centred_position):
        """
        Descript. :
        """
        if self.current_phase != "BeamLocation":
            try:
                x, y = centred_position.beam_x, centred_position.beam_y
                dx = (
                    self.beam_position[0] - self.zoom_centre["x"]
                ) / self.pixels_per_mm_x - x
                dy = (
                    self.beam_position[1] - self.zoom_centre["y"]
                ) / self.pixels_per_mm_y - y
                motor_pos = {
                    self.sample_x_motor_hwobj: centred_position.sampx,
                    self.sample_y_motor_hwobj: centred_position.sampy,
                    self.phi_motor_hwobj: centred_position.phi,
                    self.phiy_motor_hwobj: centred_position.phiy
                    + self.centring_hwobj.camera2alignmentMotor(
                        self.phiy_motor_hwobj, {"X": dx, "Y": dy}
                    ),
                    self.phiz_motor_hwobj: centred_position.phiz
                    + self.centring_hwobj.camera2alignmentMotor(
                        self.phiz_motor_hwobj, {"X": dx, "Y": dy}
                    ),
                    self.kappa_motor_hwobj: centred_position.kappa,
                    self.kappa_phi_motor_hwobj: centred_position.kappa_phi,
                }
                self.move_to_motors_positions(motor_pos)
            except BaseException:
                logging.exception("Could not move to centred position")
        else:
            logging.getLogger("HWR").debug(
                "Move to centred position disabled in BeamLocation phase."
            )

    def move_kappa_and_phi(self, kappa, kappa_phi, wait=False):
        """
        Descript. :
        """
        try:
            return self.move_kappa_and_phi_procedure(kappa, kappa_phi, wait=wait)
        except BaseException:
            logging.exception("Could not move kappa and kappa_phi")

    @task
    def move_kappa_and_phi_procedure(self, new_kappa, new_kappa_phi):
        """
        Descript. :
        """
        kappa = self.current_positions_dict["kappa"]
        kappa_phi = self.current_positions_dict["kappa_phi"]
        motor_pos_dict = {}

        if (kappa, kappa_phi) != (
            new_kappa,
            new_kappa_phi,
        ) and self.minikappa_correction_hwobj is not None:
            sampx = self.sample_x_motor_hwobj.get_value()
            sampy = self.sample_y_motor_hwobj.get_value()
            phiy = self.phiy_motor_hwobj.get_value()
            new_sampx, new_sampy, new_phiy = self.minikappa_correction_hwobj.shift(
                kappa, kappa_phi, [sampx, sampy, phiy], new_kappa, new_kappa_phi
            )

            motor_pos_dict[self.kappa_motor_hwobj] = new_kappa
            motor_pos_dict[self.kappa_phi_motor_hwobj] = new_kappa_phi
            motor_pos_dict[self.sample_x_motor_hwobj] = new_sampx
            motor_pos_dict[self.sample_y_motor_hwobj] = new_sampy
            motor_pos_dict[self.phiy_motor_hwobj] = new_phiy

            self.move_motors(motor_pos_dict)

    def move_to_motors_positions(self, motors_pos, wait=False):
        """
        Descript. :
        """
        self.emit_progress_message("Moving to motors positions...")
        self.move_to_motors_positions_procedure = gevent.spawn(
            self.move_motors, motors_pos
        )
        self.move_to_motors_positions_procedure.link(self.move_motors_done)

    def get_motor_hwobj(self, motor_name):
        """
        Descript. :
        """
        if motor_name == "phi":
            return self.phi_motor_hwobj
        elif motor_name == "phiz":
            return self.phiz_motor_hwobj
        elif motor_name == "phiy":
            return self.phiy_motor_hwobj
        elif motor_name == "sampx":
            return self.sample_x_motor_hwobj
        elif motor_name == "sampy":
            return self.sample_y_motor_hwobj

    def move_motors(self, motor_position_dict):
        """
        Descript. : general function to move motors.
        Arg.      : motors positions in dict. Dictionary can contain motor names
                    as str or actual motor hwobj
        """
        # We do not want to modify the input dict
        motor_positions_copy = motor_position_dict.copy()
        for motor in motor_positions_copy.keys():
            position = motor_positions_copy[motor]
            if isinstance(motor, string_types):
                motor_role = motor
                motor = self.get_motor_hwobj(motor_role)
                del motor_positions_copy[motor_role]
                if motor is None:
                    continue
                motor_positions_copy[motor] = position
            # logging.getLogger("HWR").info("Moving motor '%s' to %f", motor.get_motor_mnemonic(), position)
            motor.set_value(position)
        while any([motor.motorIsMoving() for motor in motor_positions_copy]):
            time.sleep(0.5)
        """with gevent.Timeout(15):
             while not all([m.get_state() == m.READY for m in motors_positions if m is not None]):
                   time.sleep(0.1)"""

    def move_motors_done(self, move_motors_procedure):
        """
        Descript. :
        """
        self.move_to_motors_positions_procedure = None
        self.emit_progress_message("")

    def image_clicked(self, x, y, xi=None, yi=None):
        """
        Descript. :
        """
        self.user_clicked_event.set((x, y))

    def emit_centring_started(self, method):
        """
        Descript. :
        """
        self.current_centring_method = method
        self.emit("centringStarted", (method, False))

    def accept_centring(self):
        """
        Descript. :
        Arg.      " fully_centred_point. True if 3 click centring
                    else False
        """
        self.centring_status["valid"] = True
        self.centring_status["accepted"] = True
        self.emit("centringAccepted", (True, self.get_centring_status()))

    def reject_centring(self):
        """
        Descript. :
        """
        if self.current_centring_procedure:
            self.current_centring_procedure.kill()
        self.centring_status = {"valid": False}
        self.emit_progress_message("")
        self.emit("centringAccepted", (False, self.get_centring_status()))

    def emit_centring_moving(self):
        """
        Descript. :
        """
        self.emit("centringMoving", ())

    def emit_centring_failed(self):
        """
        Descript. :
        """
        self.centring_status = {"valid": False}
        method = self.current_centring_method
        self.current_centring_method = None
        self.current_centring_procedure = None
        self.emit("centringFailed", (method, self.get_centring_status()))

    def convert_from_obj_to_name(self, motor_pos):
        motors = {}
        for motor_role in (
            "phiy",
            "phiz",
            "sampx",
            "sampy",
            "zoom",
            "phi",
            "focus",
            "kappa",
            "kappa_phi",
        ):
            mot_obj = self.get_object_by_role(motor_role)
            try:
                motors[motor_role] = motor_pos[mot_obj]
            except KeyError:
                motors[motor_role] = mot_obj.get_value()
        motors["beam_x"] = (
            self.beam_position[0] - self.zoom_centre["x"]
        ) / self.pixels_per_mm_y
        motors["beam_y"] = (
            self.beam_position[1] - self.zoom_centre["y"]
        ) / self.pixels_per_mm_x
        return motors

    def emit_centring_successful(self):
        """
        Descript. :
        """
        if self.current_centring_procedure is not None:
            curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.centring_status["endTime"] = curr_time

            # motor_pos = self.current_centring_procedure.get()
            # motors = self.convert_from_obj_to_name(motor_pos)

            # self.centring_status["motors"] = motors
            # self.centring_status["method"] = self.current_centring_method
            print(
                "PP___: NanoDiff emit_centring_successful(self) commented code adnout motors  "
            )

            self.centring_status["valid"] = True

            method = self.current_centring_method
            self.emit("centringSuccessful", (method, self.get_centring_status()))
            self.current_centring_method = None
            self.current_centring_procedure = None
        else:
            logging.getLogger("HWR").debug(
                "NanoDiff: trying to emit centringSuccessful outside of a centring"
            )

    def emit_progress_message(self, msg=None):
        """
        Descript. :
        """
        self.emit("progressMessage", (msg,))

    def get_centring_status(self):
        """
        Descript. :
        """
        return copy.deepcopy(self.centring_status)

    def take_snapshots_procedure(self, image_count, drawing):
        """
        Descript. :
        """
        centred_images = []
        for index in range(image_count):
            logging.getLogger("HWR").info("NanoDiff: taking snapshot #%d", index + 1)
            # centred_images.append((self.phi_motor_hwobj.get_value(), str(myimage(drawing))))
            if not self.in_plate_mode() and image_count > 1:
                self.phi_motor_hwobj.set_value_relative(-90, timeout=None)
            centred_images.reverse()  # snapshot order must be according to positive rotation direction
        return centred_images

    def take_snapshots(self, image_count, wait=False):
        """
        Descript. :
        """

        return

        if image_count > 0:
            snapshots_procedure = gevent.spawn(
                self.take_snapshots_procedure, image_count, self._drawing
            )
            self.emit("centringSnapshots", (None,))
            self.emit_progress_message("Taking snapshots")
            self.centring_status["images"] = []
            snapshots_procedure.link(self.snapshots_done)
            if wait:
                self.centring_status["images"] = snapshots_procedure.get()

    def snapshots_done(self, snapshots_procedure):
        """
        Descript. :
        """
        try:
            self.centring_status["images"] = snapshots_procedure.get()
        except BaseException:
            logging.getLogger("HWR").exception(
                "NanoDiff: could not take crystal snapshots"
            )
            self.emit("centringSnapshots", (False,))
            self.emit_progress_message("")
        else:
            self.emit("centringSnapshots", (True,))
            self.emit_progress_message("")
        self.emit_progress_message("Sample is centred!")

    def visual_align(self, point_1, point_2):
        """
        Descript. :
        """
        if self.in_plate_mode():
            logging.getLogger("HWR").info(
                "NanoDiff: Visual align not available in Plate mode"
            )
        else:
            t1 = [point_1.sampx, point_1.sampy, point_1.phiy]
            t2 = [point_2.sampx, point_2.sampy, point_2.phiy]
            kappa = self.kappa_motor_hwobj.get_value()
            phi = self.kappa_phi_motor_hwobj.get_value()
            (
                new_kappa,
                new_phi,
                (new_sampx, new_sampy, new_phiy,),
            ) = self.minikappa_correction_hwobj.alignVector(t1, t2, kappa, phi)
        self.move_to_motors_positions(
            {
                self.kappa_motor_hwobj: new_kappa,
                self.kappa_phi_motor_hwobj: new_phi,
                self.sample_x_motor_hwobj: new_sampx,
                self.sample_y_motor_hwobj: new_sampy,
                self.phiy_motor_hwobj: new_phiy,
            }
        )

    def re_emit_values(self):
        self.emit("minidiffPhaseChanged", (self.current_phase,))
        self.emit("omegaReferenceChanged", (self.reference_pos,))
        self.emit("minidiffShutterStateChanged", (self.fast_shutter_is_open,))

    def toggle_fast_shutter(self):
        if self.chan_fast_shutter_is_open is not None:
            self.chan_fast_shutter_is_open.set_value(not self.fast_shutter_is_open)

    def find_loop(self):
        snapshot_filename = os.path.join(
            tempfile.gettempdir(), "mxcube_sample_snapshot.png"
        )
        HWR.beamline.sample_view.camera.take_snapshot(snapshot_filename, bw=True)
        info, x, y = lucid.find_loop(snapshot_filename)
        return x, y
