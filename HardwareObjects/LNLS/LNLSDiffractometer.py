#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import ast
import time
import logging
import random
import warnings

from HardwareRepository.HardwareObjects.GenericDiffractometer import (
    GenericDiffractometer
)
from HardwareRepository import HardwareRepository as HWR
from gevent.event import AsyncResult


class LNLSDiffractometer(GenericDiffractometer):
    """
    Descript. :
    """

    def __init__(self, *args):
        """
        Descript. :
        """
        GenericDiffractometer.__init__(self, *args)

    def init(self):
        """
        Descript. :
        """
        # self.image_width = 100
        # self.image_height = 100

        GenericDiffractometer.init(self)
        # Bzoom: 1.86 um/pixel (or 0.00186 mm/pixel) at minimum zoom
        self.x_calib = 0.00186
        self.y_calib = 0.00186
        self.last_centred_position = [318, 238]

        self.pixels_per_mm_x = 1.0 / self.x_calib
        self.pixels_per_mm_y = 1.0 / self.y_calib
        if "zoom" not in self.motor_hwobj_dict.keys():
            self.motor_hwobj_dict["zoom"] = self.getObjectByRole("zoom")
        calibration = self.zoom.getProperty("calibration")
        self.zoom_calibration = ast.literal_eval(calibration)

        self.beam_position = [318, 238]

        self.current_phase = GenericDiffractometer.PHASE_CENTRING

        self.cancel_centring_methods = {}
        self.current_motor_positions = {
            "phiy": 1.0,
            "sampx": 0.0,
            "sampy": -1.0,
            "zoom": 8.53,
            "focus": -0.42,
            "phiz": 1.1,
            "phi": 311.1,
            "kappa": 11,
            "kappa_phi": 22.0,
        }
        #self.move_motors(self._get_random_centring_position())

        self.current_state_dict = {}
        self.centring_status = {"valid": False}
        self.centring_time = 0

        # self.image_width = 400
        # self.image_height = 400

        self.mount_mode = self.getProperty("sample_mount_mode")
        if self.mount_mode is None:
            self.mount_mode = "manual"

        self.equipment_ready()

        # TODO FFS get this cleared up - one function, one name
        self.getPositions = self.get_positions
        #self.moveMotors = self.move_motors

        self.connect(
            self.motor_hwobj_dict["phi"], "positionChanged", self.phi_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["phiy"], "positionChanged", self.phiy_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["phiz"], "positionChanged", self.phiz_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["kappa"], "positionChanged", self.kappa_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["kappa_phi"],
            "positionChanged",
            self.kappa_phi_motor_moved,
        )
        self.connect(
            self.motor_hwobj_dict["sampx"], "positionChanged", self.sampx_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["sampy"], "positionChanged", self.sampy_motor_moved
        )

    def getStatus(self):
        """
        Descript. :
        """
        return "ready"

    def execute_server_task(self, method, timeout=30, *args):
        return

    def in_plate_mode(self):
        return self.mount_mode == "plate"

    def use_sample_changer(self):
        return self.mount_mode == "sample_changer"

    def is_reversing_rotation(self):
        return True

    def get_grid_direction(self):
        """
        Descript. :
        """
        return self.grid_direction

    def manual_centring(self):
        """
        Descript. :
        """
        for click in range(3):
            self.user_clicked_event = AsyncResult()
            x, y = self.user_clicked_event.get()
            if click < 2:
                self.motor_hwobj_dict["phi"].set_value_relative(90)
        self.last_centred_position[0] = x
        self.last_centred_position[1] = y
        centred_pos_dir = self._get_random_centring_position()
        return centred_pos_dir

    def automatic_centring(self):
        """Automatic centring procedure"""
        centred_pos_dir = self._get_random_centring_position()
        self.emit("newAutomaticCentringPoint", centred_pos_dir)
        return centred_pos_dir

    def _get_random_centring_position(self):
        """Get random centring result for current positions"""

        # Names of motors to vary during centring
        vary_motor_names = ("sampx", "sampy", "phiy")

        # Range of random variation
        var_range = 0.08

        # absolute value limit for varied motors
        var_limit = 2.0

        result = self.current_motor_positions.copy()
        for tag in vary_motor_names:
            val = result.get(tag)
            if val is not None:
                random_num = random.random()
                var = (random_num - 0.5) * var_range
                val += var
                if abs(val) > var_limit:
                    val *= 1 - var_range / var_limit
                result[tag] = val
        #
        return result

    def is_ready(self):
        """
        Descript. :
        """
        return True

    def isValid(self):
        """
        Descript. :
        """
        return True

    def invalidate_centring(self):
        """
        Descript. :
        """
        if self.current_centring_procedure is None and self.centring_status["valid"]:
            self.centring_status = {"valid": False}
            # self.emitProgressMessage("")
            self.emit("centringInvalid", ())

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        Descript. :
        """
        centred_pos_dir = self._get_random_centring_position()
        return centred_pos_dir

    def get_calibration_data(self, offset):
        """
        Descript. :
        """
        # return (1.0 / self.x_calib, 1.0 / self.y_calib)
        return (1.0 / self.x_calib, 1.0 / self.y_calib)

    def refresh_omega_reference_position(self):
        """
        Descript. :
        """
        return

    # def get_omega_axis_position(self):
    #     """
    #     Descript. :
    #     """
    #     return self.current_positions_dict.get("phi")

    def beam_position_changed(self, value):
        """
        Descript. :
        """
        self.beam_position = value

    def get_current_centring_method(self):
        """
        Descript. :
        """
        return self.current_centring_method

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Descript. :
        """
        return self.last_centred_position[0], self.last_centred_position[1]

    def moveToCentredPosition(self, centred_position, wait=False):
        """
        Descript. :
        """
        try:
            return self.move_to_centred_position(centred_position)
        except BaseException:
            logging.exception("Could not move to centred position")

    def phi_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["phi"] = pos
        self.emit("phiMotorMoved", pos)

    def phiy_motor_moved(self, pos):
        self.current_motor_positions["phiy"] = pos

    def phiz_motor_moved(self, pos):
        self.current_motor_positions["phiz"] = pos

    def sampx_motor_moved(self, pos):
        self.current_motor_positions["sampx"] = pos

    def sampy_motor_moved(self, pos):
        self.current_motor_positions["sampy"] = pos

    def kappa_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["kappa"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()
        self.emit("kappaMotorMoved", pos)

    def kappa_phi_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["kappa_phi"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()
        self.emit("kappaPhiMotorMoved", pos)

    def refresh_video(self):
        """
        Descript. :
        """
        self.emit("minidiffStateChanged", "testState")
        if HWR.beamline.beam:
            HWR.beamline.beam.beam_pos_hor_changed(300)
            HWR.beamline.beam.beam_pos_ver_changed(200)

    def start_auto_focus(self):
        """
        Descript. :
        """
        return

    def calculate_move_to_beam_pos(self, x, y):
        """
        Descript. : calculate motor positions to put sample on the beam.
        Returns: dict of motor positions
        """
        # Update beam position
        self.beam_position[0], self.beam_position[1] = HWR.beamline.beam.get_beam_position_on_screen()

        print(("moving to beam position: %d %d" % (
            self.beam_position[0],
            self.beam_position[1],
        )))

        # Set velocity of omega to move during centring
        #self.set_omega_default_velocity()

        # Set scale of pixels per mm according to current zoom
        #self.pixels_per_mm_x = self.motor_zoom_hwobj.getPixelsPerMm(0)
        #self.pixels_per_mm_y = self.motor_zoom_hwobj.getPixelsPerMm(1)

        # Get clicked position of mouse pointer
        #self.user_clicked_event = AsyncResult()
        #x, y = self.user_clicked_event.get()
        # Last clicked position
        self.last_centred_position[0] = x
        self.last_centred_position[1] = y

        # Get current value of involved motors
        omega_pos  = self.motor_hwobj_dict["phi"].get_value()
        # For now, phiz refers to gonio x motor
        goniox_pos = self.motor_hwobj_dict["phiz"].get_value()
        sampx_pos  = self.motor_hwobj_dict["sampx"].get_value()
        sampy_pos  = self.motor_hwobj_dict["sampy"].get_value()

        # Pixels to move axis X of whole goniometer
        move_goniox = (self.beam_position[0] - self.last_centred_position[0])
        # mm to move
        move_goniox = move_goniox / self.pixels_per_mm_x

        # Move absolute
        move_goniox += goniox_pos

        # Calculate new position of X
        import math
        move_sampx = (math.cos(math.radians(omega_pos)) * (self.beam_position[1] - float(self.last_centred_position[1])))
        # print("math.cos(math.radians(omega_pos)): ", math.cos(math.radians(omega_pos)))
        # print("self.beam_position[1]: ", self.beam_position[1])
        # print("float(last_centred_position[1])", float(last_centred_position[1]))
        # print("move_sampx = (math.cos(math.radians(omega_pos)) * (self.beam_position[1] - float(last_centred_position[1]))): ", move_sampx)
        #move_sampx = move_sampx / self.pixels_per_mm_x
        move_sampx = (move_sampx / self.pixels_per_mm_x) * -1
        # print("move_sampx = move_sampx / self.pixels_per_mm_x: ", move_sampx)
        # Move absolute
        move_sampx += sampx_pos
        # print("move_sampx += sampx_pos: ", move_sampx)

        # Calculate new position of Y
        move_sampy = (math.sin(math.radians(omega_pos)) * (self.beam_position[1] - float(self.last_centred_position[1])))
        # print("math.sin(math.radians(omega_pos)): ", math.sin(math.radians(omega_pos)))
        # print("self.beam_position[1]: ", self.beam_position[1])
        # print("float(last_centred_position[1])", float(last_centred_position[1]))
        # print("move_sampy = (math.sin(math.radians(omega_pos)) * (self.beam_position[1] - float(last_centred_position[1]))): ", move_sampy)
        move_sampy = (move_sampy / self.pixels_per_mm_y) * -1
        #move_sampy = move_sampy / self.pixels_per_mm_y
        # print("move_sampy = move_sampy / self.pixels_per_mm_y: ", move_sampy)
        # Move absolute
        move_sampy += sampy_pos
        # print("move_sampy += sampy_pos: ", move_sampy)
        centred_pos_dir = { 'phiz': move_goniox, 'sampx': move_sampx, 'sampy': move_sampy }
        return centred_pos_dir

    def move_to_beam(self, x, y, omega=None):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """

        centred_pos_dir = self.calculate_move_to_beam_pos(x, y)
        print('Moving motors to beam...')
        self.move_to_motors_positions(centred_pos_dir, wait=True)
        return centred_pos_dir

    def move_to_coord(self, x, y, omega=None):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """
        warnings.warn(
            "Deprecated method, call move_to_beam instead", DeprecationWarning
        )
        return self.move_to_beam(x, y, omega)

    def start_move_to_beam(self, coord_x=None, coord_y=None, omega=None):
        """
        Descript. :
        """
        self.last_centred_position[0] = coord_x
        self.last_centred_position[1] = coord_y
        self.centring_time = time.time()
        curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.centring_status = {
            "valid": True,
            "startTime": curr_time,
            "endTime": curr_time,
        }
        motors = self.get_positions()
        motors["beam_x"] = 0.1
        motors["beam_y"] = 0.1
        self.last_centred_position[0] = coord_x
        self.last_centred_position[1] = coord_y
        self.centring_status["motors"] = motors
        self.centring_status["valid"] = True
        self.centring_status["angleLimit"] = False
        self.emit_progress_message("")
        self.accept_centring()
        self.current_centring_method = None
        self.current_centring_procedure = None

    def update_values(self):
        self.emit("zoomMotorPredefinedPositionChanged", None, None)
        omega_ref = [0, 238]
        self.emit("omegaReferenceChanged", omega_ref)

    def move_kappa_and_phi(self, kappa, kappa_phi):
        return

    def get_osc_max_speed(self):
        return 66

    def get_osc_limits(self):
        if self.in_plate_mode:
            return (170, 190)
        else:
            return (-360, 360)

    def get_scan_limits(self, speed=None, num_images=None, exp_time=None):
        if self.in_plate_mode:
            return (170, 190)
        else:
            return (-360, 360)

    def get_osc_dynamic_limits(self):
        """Returns dynamic limits of oscillation axis"""
        return (0, 20)

    def get_scan_dynamic_limits(self, speed=None):
        return (-360, 360)

    def move_omega_relative(self, relative_angle):
        self.motor_hwobj_dict["phi"].syncMoveRelative(relative_angle, 5)

    def set_phase(self, phase, timeout=None):
        self.current_phase = str(phase)
        self.emit("minidiffPhaseChanged", (self.current_phase,))

    def get_point_from_line(self, point_one, point_two, index, images_num):
        return point_one.as_dict()

    @property
    def zoom(self):
        """
        Override method.
        """
        return self.motor_hwobj_dict.get("zoom")

    def get_zoom_calibration(self):
        """Returns tuple with current zoom calibration (px per mm)."""
        zoom_enum = self.zoom.get_value()  # Get current zoom enum
        zoom_enum_str = zoom_enum.name # as str
        calib_val = self.zoom_calibration.get(zoom_enum_str)
        self.x_calib = calib_val
        self.y_calib = calib_val
        try:
            float(calib_val)
            self.pixels_per_mm_x = 1.0 / self.x_calib
            self.pixels_per_mm_y = 1.0 / self.y_calib
        except Exception as e:
            print("[Zoom] Error on calibration: " + str(e))
        return (self.pixels_per_mm_x, self.pixels_per_mm_y)

    def get_pixels_per_mm(self):
        """
        Override method.
        """
        pixels_per_mm_x, pixels_per_mm_y = self.get_zoom_calibration()
        return (pixels_per_mm_x, pixels_per_mm_y)

    def update_zoom_calibration(self):
        """
        Override method.
        """
        self.emit("pixelsPerMmChanged", ((self.pixels_per_mm_x,
                                          self.pixels_per_mm_y)))
