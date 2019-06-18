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

"""
EMBL implementation of MD2 and MD3 diffractometers
"""

import ast
import time
import logging
from math import sqrt

import gevent

try:
    import lucid2 as lucid
except ImportError:
    try:
        import lucid
    except ImportError:
        logging.warning(
            "Could not find autocentring library, automatic centring is disabled"
        )

from HardwareRepository.HardwareObjects.GenericDiffractometer import (
    GenericDiffractometer,
)
from HardwareRepository.TaskUtils import task


__credits__ = ["EMBL Hamburg"]
__category__ = "General"


class EMBLMiniDiff(GenericDiffractometer):
    """
    Based on the GenericDiffractometer and uses exporter for communication with the
    device. Supports:
    - MD2 (horizontal spindle direction)
    - MD3 (vertical spindle direction)
    """

    AUTOMATIC_CENTRING_IMAGES = 6
    CENTRING_METHOD_IMAGING = "3-click imaging"
    CENTRING_METHOD_IMAGING_N = "n-click imaging"

    def __init__(self, *args):
        """
        Inherits GenericDiffractometer and contains exporter channels and commands
        :param args:
        """
        GenericDiffractometer.__init__(self, *args)

        self.current_state = None
        self.head_type = None
        self.beam_position = []
        self.fast_shutter_is_open = None
        self.pixels_per_mm_x = None
        self.pixels_per_mm_y = None
        self.centring_status = {}
        # Hardware objects ----------------------------------------------------

        self.zoom_motor_hwobj = None
        self.camera_hwobj = None
        self.omega_reference_motor = None
        self.centring_hwobj = None
        self.minikappa_correction_hwobj = None
        self.detector_distance_motor_hwobj = None
        self.imaging_centring_hwobj = None

        # Channels and commands -----------------------------------------------
        self.chan_calib_x = None
        self.chan_calib_y = None
        self.chan_current_phase = None
        self.chan_head_type = None
        self.chan_fast_shutter_is_open = None
        self.chan_state = None
        self.chan_status = None
        self.chan_sync_move_motors = None
        self.chan_scintillator_position = None
        self.chan_capillary_position = None
        self.cmd_start_set_phase = None
        self.cmd_start_auto_focus = None
        self.cmd_get_omega_scan_limits = None
        self.cmd_save_centring_positions = None

        # Internal values -----------------------------------------------------
        self.use_sc = False
        self.omega_reference_par = None
        self.omega_reference_pos = [0, 0]
        self.imaging_pixels_per_mm = [0, 0]

        self.current_phase = None

    def init(self):
        """
        Initializes all channels and commands
        :return:
        """
        GenericDiffractometer.init(self)
        self.centring_status = {"valid": False}

        self.chan_state = self.getChannelObject("State")
        self.current_state = self.chan_state.getValue()
        self.chan_state.connectSignal("update", self.state_changed)

        self.chan_status = self.getChannelObject("Status")
        self.chan_status.connectSignal("update", self.status_changed)

        self.chan_calib_x = self.getChannelObject("CoaxCamScaleX")
        self.chan_calib_y = self.getChannelObject("CoaxCamScaleY")
        self.update_pixels_per_mm()

        self.chan_head_type = self.getChannelObject("HeadType")
        self.head_type = self.chan_head_type.getValue()

        self.chan_current_phase = self.getChannelObject("CurrentPhase")
        self.connect(self.chan_current_phase, "update", self.current_phase_changed)

        self.chan_fast_shutter_is_open = self.getChannelObject("FastShutterIsOpen")
        self.chan_fast_shutter_is_open.connectSignal(
            "update", self.fast_shutter_state_changed
        )

        self.chan_scintillator_position = self.getChannelObject("ScintillatorPosition")
        self.chan_capillary_position = self.getChannelObject("CapillaryPosition")

        self.cmd_start_set_phase = self.getCommandObject("startSetPhase")
        self.cmd_start_auto_focus = self.getCommandObject("startAutoFocus")
        self.cmd_get_omega_scan_limits = self.getCommandObject(
            "getOmegaMotorDynamicScanLimits"
        )
        self.cmd_save_centring_positions = self.getCommandObject(
            "saveCentringPositions"
        )

        self.centring_hwobj = self.getObjectByRole("centring")
        self.imaging_centring_hwobj = self.getObjectByRole("imaging-centring")
        self.minikappa_correction_hwobj = self.getObjectByRole("minikappa_correction")
        self.detector_distance_motor_hwobj = self.getObjectByRole(
            "detector_distance_motor"
        )

        self.zoom_motor_hwobj = self.getObjectByRole("zoom")
        self.connect(
            self.zoom_motor_hwobj, "positionChanged", self.zoom_position_changed
        )
        self.connect(
            self.zoom_motor_hwobj,
            "predefinedPositionChanged",
            self.zoom_motor_predefined_position_changed,
        )
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

        self.omega_reference_par = ast.literal_eval(self.getProperty("omega_reference"))
        self.omega_reference_motor = self.getObjectByRole(
            self.omega_reference_par["motor_name"]
        )
        self.connect(
            self.omega_reference_motor,
            "positionChanged",
            self.omega_reference_motor_moved,
        )

        self.imaging_pixels_per_mm = [1, 1]
        self.centring_methods[
            EMBLMiniDiff.CENTRING_METHOD_IMAGING
        ] = self.start_imaging_centring
        self.centring_methods[
            EMBLMiniDiff.CENTRING_METHOD_IMAGING_N
        ] = self.start_imaging_centring_n

    def use_sample_changer(self):
        """Returns true if sample changer is used

        :return: bool
        """
        return not self.in_plate_mode()

    def beam_position_changed(self, value):
        """
        Updates beam position
        :param value: list of two ints
        :return:
        """
        self.beam_position = value

    def state_changed(self, state):
        """
        Updates state
        :param state: str
        :return:
        """
        self.current_state = state
        self.emit("minidiffStateChanged", self.current_state)
        self.emit("minidiffStatusChanged", self.current_state)

    def status_changed(self, status):
        """
        Updates status
        :param status:
        :return:
        """
        self.emit("statusMessage", ("diffractometer", status, "busy"))

    def zoom_position_changed(self, value):
        """
        Updates pixels per mm after the zoom position has been changed
        :param value: int
        :return:
        """
        self.update_pixels_per_mm()
        self.current_motor_positions["zoom"] = value
        self.refresh_omega_reference_position()

    def zoom_motor_predefined_position_changed(self, position_name, offset):
        """
        Updates pixels per mm after the zoom position has been changed
        :param position_name: str
        :param offset:
        :return:
        """
        self.update_pixels_per_mm()
        self.emit("zoomMotorPredefinedPositionChanged", (position_name, offset))

    def omega_reference_add_constraint(self):
        """
        Updates omega contrains
        :return:
        """
        if self.omega_reference_par is None or self.beam_position is None:
            return
        elif self.omega_reference_par["camera_axis"].lower() == "x":
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
        Updates omega reference
        :param pos: motor position in float
        :return:
        """
        if self.omega_reference_par["camera_axis"].lower() == "x":
            pos = (
                self.omega_reference_par["direction"]
                * (pos - self.omega_reference_par["position"])
                * self.pixels_per_mm_x
                + self.zoom_centre["x"]
            )
            self.omega_reference_pos = (pos, -10)
        else:
            pos = (
                self.omega_reference_par["direction"]
                * (pos - self.omega_reference_par["position"])
                * self.pixels_per_mm_y
                + self.zoom_centre["y"]
            )
            self.omega_reference_pos = (-10, pos)
        self.emit("omegaReferenceChanged", (self.omega_reference_pos,))

    def fast_shutter_state_changed(self, is_open):
        """
        Updates fast shutter position
        :param is_open:
        :return:
        """
        self.fast_shutter_is_open = is_open
        if is_open:
            msg = "Opened"
        else:
            msg = "Closed"
        self.emit("minidiffShutterStateChanged", (self.fast_shutter_is_open, msg))

    def phi_motor_moved(self, pos):
        """
        Updates current_motor_positions dict
        :param pos: float
        :return:
        """
        self.current_motor_positions["phi"] = pos
        self.emit("phiMotorMoved", pos)

    def phiy_motor_moved(self, pos):
        """
        Updates current_motor_positions dict
        :param pos: float
        :return:
        """
        self.current_motor_positions["phiy"] = pos

    def phiz_motor_moved(self, pos):
        """
        Updates current_motor_positions dict
        :param pos: float
        :return:
        """
        self.current_motor_positions["phiz"] = pos

    def sampx_motor_moved(self, pos):
        """
        Updates current_motor_positions dict
        :param pos: float
        :return:
        """
        self.current_motor_positions["sampx"] = pos

    def sampy_motor_moved(self, pos):
        """
        Updates current_motor_positions dict
        :param pos: float
        :return:
        """
        self.current_motor_positions["sampy"] = pos

    def kappa_motor_moved(self, pos):
        """
        Updates current_motor_positions dict. Resets the centering if the kappa during
        the centering has been changed
        :param pos: float
        :return:
        """
        self.current_motor_positions["kappa"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()
        self.emit("kappaMotorMoved", pos)

    def kappa_phi_motor_moved(self, pos):
        """
        Updates current_motor_positions dict and resets the centering if the kappa phi
        during the centering has been changed
        :param pos: float
        :return:
        """
        self.current_motor_positions["kappa_phi"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()
        self.emit("kappaPhiMotorMoved", pos)

    def refresh_omega_reference_position(self):
        """
        Refresh omega ref.
        :return:
        """
        if self.omega_reference_motor is not None:
            reference_pos = self.omega_reference_motor.get_position()
            self.omega_reference_motor_moved(reference_pos)

    def update_pixels_per_mm(self):
        """
        Updates pixels per mm values
        :return:
        """
        self.pixels_per_mm_x = 1.0 / self.chan_calib_x.getValue()
        self.pixels_per_mm_y = 1.0 / self.chan_calib_y.getValue()
        self.emit("pixelsPerMmChanged", ((self.pixels_per_mm_x, self.pixels_per_mm_y),))

    def set_phase(self, phase, timeout=80):
        """Sets diffractometer to the selected phase.
           In the plate mode before going to or away from
           Transfer or Beam location phase if needed then detector
           is moved to the safe distance to avoid collision.
        :param phase: str
        """
        msg = "Diffractometer: Setting %s phase. Please wait..." % phase
        logging.getLogger("GUI").warning(msg)

        if self.in_plate_mode() and (
            phase
            in (GenericDiffractometer.PHASE_TRANSFER, GenericDiffractometer.PHASE_BEAM)
            or self.current_phase
            in (GenericDiffractometer.PHASE_TRANSFER, GenericDiffractometer.PHASE_BEAM)
        ):
            detector_distance = self.detector_distance_motor_hwobj.get_position()
            if detector_distance < 350:
                logging.getLogger("GUI").info("Moving detector to safe distance")
                self.detector_distance_motor_hwobj.move(350, timeout=20)

        if timeout is not None:
            _start = time.time()
            self.cmd_start_set_phase(phase)
            gevent.sleep(5)
            with gevent.Timeout(
                timeout, Exception("Timeout waiting for phase %s" % phase)
            ):
                while phase != self.chan_current_phase.getValue():
                    gevent.sleep(0.1)
            self.wait_device_ready(30)
            self.wait_device_ready(30)
            _howlong = time.time() - _start
            if _howlong > 11.0:
                msg = "Changing phase to %s took %.1f seconds" % (phase, _howlong)
                logging.getLogger("HWR").error(msg)
        else:
            self.cmd_start_set_phase(phase)

    def start_auto_focus(self, timeout=None):
        """
        Starts auto focus
        :param timeout: sec in int
        :return:
        """
        if timeout:
            self.ready_event.clear()
            gevent.spawn(self.execute_server_task, self.cmd_start_auto_focus(), timeout)
            self.ready_event.wait()
            self.ready_event.clear()
        else:
            self.cmd_start_auto_focus()

    def emit_diffractometer_moved(self, *args):
        """
        Emits diffractomereMoved
        :param args:
        :return:
        """
        self.emit("diffractometerMoved", ())

    def invalidate_centring(self):
        """
        Resets current centering
        :return:
        """
        if self.current_centring_procedure is None and self.centring_status["valid"]:
            self.centring_status = {"valid": False}
            self.emit_progress_message("")
            self.emit("centringInvalid", ())

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        Returns centring point based on the screen coordinates
        :param x: screen x (int)
        :param y: screen y (int)
        :param return_by_names: bool
        :return: queue_model_objects.CentredPosition
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

    def move_to_beam(self, x, y, omega=None):
        """Creates a new centring point based on all motors positions
        """
        if self.current_phase != "BeamLocation":
            GenericDiffractometer.move_to_beam(self, x, y, omega)
        else:
            logging.getLogger("GUI").error(
                "Diffractometer: Move to screen"
                + " position disabled in the BeamLocation phase."
            )

    def manual_centring(self):
        """
        Starts manual centring procedure
        :return:
        """
        self.centring_hwobj.initCentringProcedure()
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
                dynamic_limits = self.get_osc_limits()
                if click == 0:
                    self.motor_hwobj_dict["phi"].move(dynamic_limits[0] + 0.5)
                elif click == 1:
                    self.motor_hwobj_dict["phi"].move(dynamic_limits[1] - 0.5)
                elif click == 2:
                    self.motor_hwobj_dict["phi"].move(
                        (dynamic_limits[0] + dynamic_limits[1]) / 2.0
                    )
            else:
                if click < 2:
                    self.motor_hwobj_dict["phi"].move_relative(90)
        self.omega_reference_add_constraint()
        return self.centring_hwobj.centeredPosition(return_by_name=False)

    def automatic_centring(self):
        """Automatic centring procedure. Rotates n times and executes
           centring algorithm. Optimal scan position is detected.
        """
        self.wait_device_ready(20)
        surface_score_list = []
        self.zoom_motor_hwobj.move_to_position("Zoom 1")
        self.centring_hwobj.initCentringProcedure()
        for image in range(EMBLMiniDiff.AUTOMATIC_CENTRING_IMAGES):
            x, y, score = self.find_loop()
            if x > 0 and y > 0:
                self.centring_hwobj.appendCentringDataPoint(
                    {
                        "X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                        "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y,
                    }
                )
            surface_score_list.append(score)
            self.motor_hwobj_dict["phi"].move_relative(
                360.0 / EMBLMiniDiff.AUTOMATIC_CENTRING_IMAGES
            )
            gevent.sleep(0.01)
            self.wait_device_ready(15)
        self.omega_reference_add_constraint()
        centred_pos_dir = self.centring_hwobj.centeredPosition(return_by_name=False)

        return centred_pos_dir

    def start_imaging_centring(self, sample_info=None, wait_result=None):
        """
        Starts 3 click centering based on xray imaging
        :param sample_info:
        :param wait_result:
        :return:
        """
        self.emit_progress_message("Imaging based 3 click centring...")
        self.current_centring_procedure = gevent.spawn(self.imaging_centring)
        self.current_centring_procedure.link(self.centring_done)

    def start_imaging_centring_n(self, sample_info=None, wait_result=None):
        """
        Starts n click centering based on xray imaging
        :param sample_info:
        :param wait_result:
        :return:
        """
        self.emit_progress_message("Imaging based n click centring...")
        self.current_centring_procedure = gevent.spawn(self.imaging_centring_n)
        self.current_centring_procedure.link(self.centring_done)

    def imaging_centring(self):
        """
        Centering procedure based on xray imaging.
        :return:
        """
        self.imaging_centring_hwobj.initCentringProcedure()
        for click in range(3):
            self.user_clicked_event = gevent.event.AsyncResult()
            x, y = self.user_clicked_event.get()
            self.imaging_centring_hwobj.appendCentringDataPoint(
                {
                    "X": (x - 1024.0) / self.imaging_pixels_per_mm[0],
                    "Y": (y - 1024.0) / self.imaging_pixels_per_mm[1],
                }
            )
            if click < 2:
                self.motor_hwobj_dict["phi"].move_relative(90)
            # print "rotate omega"
        # self.omega_reference_add_constraint()
        return self.imaging_centring_hwobj.centeredPosition(return_by_name=False)

    def imaging_centring_n(self):
        """
        N click centering based on xray imaging
        :return:
        """
        self.imaging_centring_hwobj.initCentringProcedure()
        while True:
            self.user_clicked_event = gevent.event.AsyncResult()
            x, y = self.user_clicked_event.get()
            self.imaging_centring_hwobj.appendCentringDataPoint(
                {
                    "X": (x - 1024.0) / self.imaging_pixels_per_mm[0],
                    "Y": (y - 1024.0) / self.imaging_pixels_per_mm[1],
                }
            )
        # self.omega_reference_add_constraint()
        return self.imaging_centring_hwobj.centeredPosition(return_by_name=False)

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Returns x and y screen coordinates based on the centred positions
        :param centred_positions_dict: dict with motor positions
        :return: x, y(int, int)
        """
        c = centred_positions_dict
        kappa = self.motor_hwobj_dict["kappa"].get_position()
        phi = self.motor_hwobj_dict["kappa_phi"].get_position()

        if (c["kappa"], c["kappa_phi"]) != (
            kappa,
            phi,
        ) and self.minikappa_correction_hwobj is not None:
            c["sampx"], c["sampy"], c["phiy"] = self.minikappa_correction_hwobj.shift(
                c["kappa"],
                c["kappa_phi"],
                [c["sampx"], c["sampy"], c["phiy"]],
                kappa,
                phi,
            )
        x = None
        y = None

        xy = self.centring_hwobj.centringToScreen(c)
        if xy:
            x = (xy["X"] + c["beam_x"]) * self.pixels_per_mm_x + self.zoom_centre["x"]
            y = (xy["Y"] + c["beam_y"]) * self.pixels_per_mm_y + self.zoom_centre["y"]
            return x, y

    def move_to_centred_position(self, centred_position):
        """
        Moves to centred position
        :param centred_position: dict with motor positions
        :return:
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
                    self.motor_hwobj_dict["sampx"]: centred_position.sampx,
                    self.motor_hwobj_dict["sampy"]: centred_position.sampy,
                    self.motor_hwobj_dict["phi"]: centred_position.phi,
                    self.motor_hwobj_dict["phiy"]: centred_position.phiy
                    + self.centring_hwobj.camera2alignmentMotor(
                        self.motor_hwobj_dict["phiy"], {"X": dx, "Y": dy}
                    ),
                    self.motor_hwobj_dict["phiz"]: centred_position.phiz
                    + self.centring_hwobj.camera2alignmentMotor(
                        self.motor_hwobj_dict["phiz"], {"X": dx, "Y": dy}
                    ),
                    self.motor_hwobj_dict["kappa"]: centred_position.kappa,
                    self.motor_hwobj_dict["kappa_phi"]: centred_position.kappa_phi,
                }
                self.move_to_motors_positions(motor_pos)
            except BaseException:
                logging.exception("Could not move to centred position")
        else:
            logging.getLogger("HWR").debug(
                "Move to centred position disabled in BeamLocation phase."
            )

    def move_kappa_and_phi(self, kappa=None, kappa_phi=None, wait=False):
        """
        Starts move kappa kappa_phi task
        :param kappa: float
        :param kappa_phi: float
        :param wait: bool
        :return:
        """
        try:
            return self.move_kappa_and_phi_procedure(kappa, kappa_phi)
        except BaseException:
            logging.exception("Could not move kappa and kappa_phi")

    @task
    def move_kappa_and_phi_procedure(self, new_kappa=None, new_kappa_phi=None):
        """
        Task to move kappa and kappa_phi
        :param new_kappa: float
        :param new_kappa_phi: float
        :return:
        """
        kappa = self.motor_hwobj_dict["kappa"].get_position()
        kappa_phi = self.motor_hwobj_dict["kappa_phi"].get_position()

        if new_kappa is None:
            new_kappa = kappa
        if new_kappa_phi is None:
            new_kappa_phi = kappa_phi

        motor_pos_dict = {}

        if (kappa, kappa_phi) != (
            new_kappa,
            new_kappa_phi,
        ) and self.minikappa_correction_hwobj is not None:
            sampx = self.motor_hwobj_dict["sampx"].get_position()
            sampy = self.motor_hwobj_dict["sampy"].get_position()
            phiy = self.motor_hwobj_dict["phiy"].get_position()
            new_sampx, new_sampy, new_phiy = self.minikappa_correction_hwobj.shift(
                kappa, kappa_phi, [sampx, sampy, phiy], new_kappa, new_kappa_phi
            )

            motor_pos_dict[self.motor_hwobj_dict["kappa"]] = new_kappa
            motor_pos_dict[self.motor_hwobj_dict["kappa_phi"]] = new_kappa_phi
            motor_pos_dict[self.motor_hwobj_dict["sampx"]] = new_sampx
            motor_pos_dict[self.motor_hwobj_dict["sampy"]] = new_sampy
            motor_pos_dict[self.motor_hwobj_dict["phiy"]] = new_phiy

            self.move_motors(motor_pos_dict, timeout=30)

    def convert_from_obj_to_name(self, motor_pos):
        """
        Converts motor_pos dict containing objects to dict containing motor names
        :param motor_pos:
        :return:
        """
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
            mot_obj = self.getObjectByRole(motor_role)
            try:
                motors[motor_role] = motor_pos[mot_obj]
            except KeyError:
                motors[motor_role] = mot_obj.get_position()
        motors["beam_x"] = (
            self.beam_position[0] - self.zoom_centre["x"]
        ) / self.pixels_per_mm_y
        motors["beam_y"] = (
            self.beam_position[1] - self.zoom_centre["y"]
        ) / self.pixels_per_mm_x
        return motors

    def visual_align(self, point_1, point_2):
        """
        Visual align procedure
        :param point_1:
        :param point_2:
        :return:
        """
        if self.in_plate_mode():
            logging.getLogger("HWR").info(
                "EMBLMiniDiff: Visual align not available in Plate mode"
            )
        else:
            t1 = [point_1.sampx, point_1.sampy, point_1.phiy]
            t2 = [point_2.sampx, point_2.sampy, point_2.phiy]
            kappa = self.motor_hwobj_dict["kappa"].get_position()
            phi = self.motor_hwobj_dict["kappa_phi"].get_position()
            new_kappa, new_phi, (
                new_sampx,
                new_sampy,
                new_phiy,
            ) = self.minikappa_correction_hwobj.alignVector(t1, t2, kappa, phi)
            self.move_to_motors_positions(
                {
                    self.motor_hwobj_dict["kappa"]: new_kappa,
                    self.motor_hwobj_dict["kappa_phi"]: new_phi,
                    self.motor_hwobj_dict["sampx"]: new_sampx,
                    self.motor_hwobj_dict["sampy"]: new_sampy,
                    self.motor_hwobj_dict["phiy"]: new_phiy,
                }
            )

    def update_values(self):
        """
        Reemits values
        :return:
        """
        self.emit("minidiffPhaseChanged", (self.current_phase,))
        self.emit("omegaReferenceChanged", (self.reference_pos,))
        self.emit("minidiffShutterStateChanged", (self.fast_shutter_is_open,))

    def toggle_fast_shutter(self):
        """
        Toggles fast shutter
        :return:
        """
        if self.chan_fast_shutter_is_open is not None:
            self.chan_fast_shutter_is_open.setValue(not self.fast_shutter_is_open)

    def find_loop(self):
        """
        Finds loop
        :return: int, int, int
        """
        image_array = self.camera_hwobj.get_snapshot(return_as_array=True)
        (info, x, y) = lucid.find_loop(image_array)
        surface_score = 10
        return x, y, surface_score

    def move_omega(self, angle):
        """
        Moves omega
        :param angle: float
        :return:
        """
        self.motor_hwobj_dict["phi"].move(angle, timeout=5)

    def move_omega_relative(self, relative_angle, timeout=5):
        """
        Relative omega move
        :param relative_angle: float
        :param timeout:
        :return:
        """
        self.motor_hwobj_dict["phi"].move_relative(relative_angle, timeout=timeout)

    def close_kappa(self):
        """
        Starts close kappa task
        :return:
        """
        gevent.spawn(self.close_kappa_task)

    def close_kappa_task(self):
        """Close kappa task
        """
        logging.getLogger("HWR").debug("Diffractometer: Closing Kappa started...")
        self.move_kappa_and_phi_procedure(0, None)
        self.wait_device_ready(180)
        self.motor_hwobj_dict["kappa"].home()
        self.wait_device_ready(60)
        logging.getLogger("HWR").debug("Diffractometer: Done Closing Kappa")

    def set_zoom(self, position):
        """
        Sets zoom
        :param position:
        :return:
        """
        self.zoom_motor_hwobj.move_to_position(position)

    def get_point_from_line(self, point_one, point_two, frame_num, frame_total):
        """
        method used to get a new motor position based on a position
        between two positions. As arguments both motor positions are
        given. frame_num and frame_total is used estimate new point position
        Helical line goes from point_one to point_two.
        In this direction also new position is estimated
        """
        new_point = {}
        point_one = point_one.as_dict()
        point_two = point_two.as_dict()
        for motor in point_one.keys():
            new_motor_pos = point_one[motor] + (
                point_two[motor] - point_one[motor]
            ) * frame_num / float(frame_total)
            new_point[motor] = new_motor_pos
        return new_point

    def get_osc_limits(self, speed=None):
        """
        Returns osc limits
        :param speed: float
        :return: list of two floats
        """
        if speed:
            limits = self.cmd_get_omega_scan_limits(speed)
        else:
            limits = self.motor_hwobj_dict["phi"].get_dynamic_limits()
        return (min(limits), max(limits))

    def get_osc_max_speed(self):
        """
        Returns max osc speed
        :return: float
        """
        return self.motor_hwobj_dict["phi"].get_max_speed()

    def get_scan_limits(self, num_images=0, exp_time=0.001343):
        """
        Gets scan limits. Necessary for example in the plate mode
        where osc range is limited
        """

        total_exposure_time = num_images * exp_time
        a = 0.002
        b = 0.1537
        w0 = 155.7182
        w1 = 204.8366  # was 196 not to shadow laser

        if num_images == 0:
            return (w0, w1)

        speed = (
            (
                -2 * b
                - total_exposure_time
                + sqrt((2 * b + total_exposure_time) ** 2 - 8 * a * (w0 - w1))
            )
            / 4
            / a
        )
        if speed < 0:
            return None, None
        else:
            delta = a * speed ** 2 + b * speed

            return (w0 + delta, w1 - delta)

    def get_scintillator_position(self):
        """
        Returns scintillator position
        :return: str
        """
        return self.chan_scintillator_position.getValue()

    def set_scintillator_position(self, position):
        """
        Sets scintillator position
        :param position: str
        :return:
        """
        self.chan_scintillator_position.setValue(position)
        with gevent.Timeout(5, Exception("Timeout waiting for scintillator position")):
            while position != self.get_scintillator_position():
                gevent.sleep(0.01)

    def get_capillary_position(self):
        """
        Returns capillary position
        :return: str
        """
        return self.chan_capillary_position.getValue()

    def set_capillary_position(self, position):
        """
        Sets capillary position
        :param position: str
        :return:
        """
        self.chan_capillary_position.setValue(position)
        with gevent.Timeout(5, Exception("Timeout waiting for capillary position")):
            while position != self.get_capillary_position():
                gevent.sleep(0.01)

    def zoom_in(self):
        """
        Steps zoom in
        :return:
        """
        self.zoom_motor_hwobj.zoom_in()

    def zoom_out(self):
        """
        Steps one
        :return:
        """
        self.zoom_motor_hwobj.zoom_out()

    def save_centring_positions(self):
        self.cmd_save_centring_positions()

    def move_sample_out(self):
        self.motor_hwobj_dict["phiy"].move_relative(-2, wait=True, timeout=5)

    def move_sample_in(self):
        self.motor_hwobj_dict["phiy"].move_relative(2, wait=True, timeout=5)
