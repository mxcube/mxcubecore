#
#  Project: MXCuBE
#  https://github.com/mxcube.
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
#   You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import time
import logging
import random
import warnings

from HardwareRepository.HardwareObjects.GenericDiffractometer import (
    GenericDiffractometer,
)
from HardwareRepository import HardwareRepository as HWR
from gevent.event import AsyncResult


class DiffractometerMockup(GenericDiffractometer):
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
        self.x_calib = 0.000444
        self.y_calib = 0.000446
        self.last_centred_position = [318, 238]

        self.pixels_per_mm_x = 1.0 / self.x_calib
        self.pixels_per_mm_y = 1.0 / self.y_calib
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
        self.move_motors(self._get_random_centring_position())

        self.current_state_dict = {}
        self.centring_status = {"valid": False}
        self.centring_time = 0

        # self.image_width = 400
        # self.image_height = 400

        self.mount_mode = self.get_property("sample_mount_mode")
        if self.mount_mode is None:
            self.mount_mode = "manual"

        self.equipment_ready()

        self.connect(self.motor_hwobj_dict["phi"], "valueChanged", self.phi_motor_moved)
        self.connect(
            self.motor_hwobj_dict["phiy"], "valueChanged", self.phiy_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["phiz"], "valueChanged", self.phiz_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["kappa"], "valueChanged", self.kappa_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["kappa_phi"],
            "valueChanged",
            self.kappa_phi_motor_moved,
        )
        self.connect(
            self.motor_hwobj_dict["sampx"], "valueChanged", self.sampx_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["sampy"], "valueChanged", self.sampy_motor_moved
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
        vary_actuator_names = ("sampx", "sampy", "phiy")

        # Range of random variation
        var_range = 0.08

        # absolute value limit for varied motors
        var_limit = 2.0

        result = self.current_motor_positions.copy()
        for tag in vary_actuator_names:
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

    def is_valid(self):
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

    def move_to_beam(self, x, y, omega=None):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """

        print(
            (
                "moving to beam position: %d %d"
                % (self.beam_position[0], self.beam_position[1])
            )
        )

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

    def re_emit_values(self):
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
        self.motor_hwobj_dict["phi"].set_value_relative(relative_angle, 5)

    def set_phase(self, phase, timeout=None):
        self.current_phase = str(phase)
        self.emit("minidiffPhaseChanged", (self.current_phase,))

    def get_point_from_line(self, point_one, point_two, index, images_num):
        return point_one.as_dict()
