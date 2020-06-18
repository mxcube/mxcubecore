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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import time
import gevent
import logging

from math import sqrt

try:
    import lucid2 as lucid
except ImportError:
    try:
        import lucid
    except ImportError:
        logging.warning(
            "Could not find autocentring library, " + "automatic centring is disabled"
        )

from HardwareRepository.HardwareObjects.GenericDiffractometer import (
    GenericDiffractometer,
)
from HardwareRepository.TaskUtils import task

from HardwareRepository import HardwareRepository as HWR


__credits__ = ["EMBL Hamburg"]
__category__ = "General"


class EMBLMiniDiff(GenericDiffractometer):

    AUTOMATIC_CENTRING_IMAGES = 6
    CENTRING_METHOD_IMAGING = "3-click imaging"
    CENTRING_METHOD_IMAGING_N = "n-click imaging"

    def __init__(self, *args):
        GenericDiffractometer.__init__(self, *args)

        # Hardware objects ----------------------------------------------------
        self.zoom_motor_hwobj = None
        self.omega_reference_motor = None
        self.centring_hwobj = None
        self.minikappa_correction_hwobj = None

        # Channels and commands -----------------------------------------------
        self.chan_calib_x = None
        self.chan_calib_y = None
        self.chan_current_phase = None
        self.chan_head_type = None
        self.chan_fast_shutter_is_open = None
        self.chan_state = None
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
        self.imaging_static_positions = None
        self.imaging_beam_position = [959, 1140]

    def init(self):

        GenericDiffractometer.init(self)
        self.centring_status = {"valid": False}

        self.chan_state = self.get_channel_object("State")
        self.current_state = self.chan_state.getValue()
        self.chan_state.connect_signal("update", self.state_changed)

        self.chan_status = self.get_channel_object("Status")
        self.chan_status.connect_signal("update", self.status_changed)

        self.chan_calib_x = self.get_channel_object("CoaxCamScaleX")
        self.chan_calib_y = self.get_channel_object("CoaxCamScaleY")
        self.update_pixels_per_mm()

        self.chan_head_type = self.get_channel_object("HeadType")
        self.head_type = self.chan_head_type.getValue()

        self.chan_current_phase = self.get_channel_object("CurrentPhase")
        self.connect(self.chan_current_phase, "update", self.current_phase_changed)

        self.chan_fast_shutter_is_open = self.get_channel_object("FastShutterIsOpen")
        self.chan_fast_shutter_is_open.connect_signal(
            "update", self.fast_shutter_state_changed
        )

        self.chan_scintillator_position = self.get_channel_object(
            "ScintillatorPosition"
        )
        self.chan_capillary_position = self.get_channel_object("CapillaryPosition")

        self.cmd_start_set_phase = self.get_command_object("startSetPhase")
        self.cmd_start_auto_focus = self.get_command_object("startAutoFocus")
        self.cmd_get_omega_scan_limits = self.get_command_object(
            "getOmegaMotorDynamicScanLimits"
        )
        self.cmd_save_centring_positions = self.get_command_object(
            "saveCentringPositions"
        )

        self.centring_hwobj = self.get_object_by_role("centring")
        self.imaging_centring_hwobj = self.get_object_by_role("imaging-centring")
        self.minikappa_correction_hwobj = self.get_object_by_role("minikappa_correction")

        self.zoom_motor_hwobj = self.get_object_by_role("zoom")
        self.connect(self.zoom_motor_hwobj, "valueChanged", self.zoom_position_changed)
        self.connect(
            self.zoom_motor_hwobj,
            "predefinedPositionChanged",
            self.zoom_motor_predefined_position_changed,
        )
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

        self.omega_reference_par = eval(self.get_property("omega_reference"))
        self.omega_reference_motor = self.get_object_by_role(
            self.omega_reference_par["motor_name"]
        )
        self.connect(
            self.omega_reference_motor,
            "valueChanged",
            self.omega_reference_motor_moved,
        )

        # self.use_sc = self.get_property("use_sample_changer")
        self.imaging_pixels_per_mm = [3076.923, 3076.923]
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
        self.beam_position = value

    def state_changed(self, state):
        # logging.getLogger("HWR").debug("State changed: %s" % str(state))
        self.current_state = state
        self.emit("minidiffStateChanged", (self.current_state))
        self.emit("minidiffStatusChanged", (self.current_state))

    def status_changed(self, state):
        self.emit("statusMessage", ("diffractometer", state, "busy"))

    def zoom_position_changed(self, value):
        self.update_pixels_per_mm()
        self.current_motor_positions["zoom"] = value
        self.refresh_omega_reference_position()

    def zoom_motor_predefined_position_changed(self, position_name, offset):
        self.update_pixels_per_mm()
        self.emit("zoomMotorPredefinedPositionChanged", (position_name, offset))

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
        if is_open:
            msg = "Opened"
        else:
            msg = "Closed"
        self.emit("minidiffShutterStateChanged", (self.fast_shutter_is_open, msg))

    def phi_motor_moved(self, pos):
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
        self.current_motor_positions["kappa"] = pos
        if self.centring_time:
            if time.time() - self.centring_time > 1.0:
                self.invalidate_centring()
        self.emit_diffractometer_moved()
        self.emit("kappaMotorMoved", pos)

    def kappa_phi_motor_moved(self, pos):
        self.current_motor_positions["kappa_phi"] = pos
        if self.centring_time:
            if time.time() - self.centring_time > 1.0:
                self.invalidate_centring()
        self.emit_diffractometer_moved()
        self.emit("kappaPhiMotorMoved", pos)

    def refresh_omega_reference_position(self):
        if self.omega_reference_motor is not None:
            reference_pos = self.omega_reference_motor.get_value()
            self.omega_reference_motor_moved(reference_pos)

    def update_pixels_per_mm(self, *args):
        self.pixels_per_mm_x = 1.0 / self.chan_calib_x.getValue()
        self.pixels_per_mm_y = 1.0 / self.chan_calib_y.getValue()
        self.emit("pixelsPerMmChanged", ((self.pixels_per_mm_x, self.pixels_per_mm_y),))

    def set_phase(self, phase, timeout=80):
        """Sets diffractometer to the selected phase.
           In the plate mode before going to or away from
           Transfer or Beam location phase if needed then detector
           is moved to the safe distance to avoid collision.
        """
        # self.wait_device_ready(2)
        logging.getLogger("GUI").warning(
            "Diffractometer: Setting %s phase. Please wait..." % phase
        )
        if self.in_plate_mode() and phase == GenericDiffractometer.PHASE_TRANSFER:
            logging.getLogger("GUI").warning(
                "Diffractometer: Transfer phase in plate mode is not available"
            )
            return

        if self.in_plate_mode() and (
            phase
            in (GenericDiffractometer.PHASE_TRANSFER, GenericDiffractometer.PHASE_BEAM)
            or self.current_phase
            in (GenericDiffractometer.PHASE_TRANSFER, GenericDiffractometer.PHASE_BEAM)
        ):
            detector_distance = HWR.beamline.detector.distance.get_value()
            logging.getLogger("HWR").debug(
                "Diffractometer current phase: %s " % self.current_phase
                + "selected phase: %s" % phase
                + "detector distance: %d mm" % detector_distance
            )
            if detector_distance < 350:
                logging.getLogger("GUI").info("Moving detector to safe distance")
                HWR.beamline.detector.distance.set_value(350, timeout=20)

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
            if _howlong > 20.0:
                logging.getLogger("HWR").error(
                    "Changing phase to %s took %.1f seconds" % (phase, _howlong)
                )
        else:
            self.cmd_start_set_phase(phase)

    def start_auto_focus(self, timeout=None):
        if timeout:
            self.ready_event.clear()
            set_phase_task = gevent.spawn(
                self.execute_server_task, self.cmd_start_auto_focus(), timeout
            )
            self.ready_event.wait()
            self.ready_event.clear()
        else:
            self.cmd_start_auto_focus()

    def emit_diffractometer_moved(self, *args):
        self.emit("diffractometerMoved", ())

    def invalidate_centring(self):
        if self.current_centring_procedure is None and self.centring_status["valid"]:
            self.centring_status = {"valid": False}
            self.emit_progress_message("")
            self.emit("centringInvalid", ())

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
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
            logging.getLogger("HWR").debug(
                "Diffractometer: Move to screen"
                + " position disabled in BeamLocation phase."
            )

    def manual_centring(self):
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
                    self.motor_hwobj_dict["phi"].set_value(dynamic_limits[0] + 0.5)
                elif click == 1:
                    self.motor_hwobj_dict["phi"].set_value(dynamic_limits[1] - 0.5)
                elif click == 2:
                    self.motor_hwobj_dict["phi"].set_value(
                        (dynamic_limits[0] + dynamic_limits[1]) / 2.0
                    )
            else:
                if click < 2:
                    self.motor_hwobj_dict["phi"].set_value_relative(90)
        self.omega_reference_add_constraint()
        # _x = self.centring_hwobj.centeredPosition(return_by_name=True, shift_to_constraints=True)
        # logging.getLogger("HWR").debug("opti %s" %_x)
        return self.centring_hwobj.centeredPosition(
            return_by_name=False, shift_to_constraints=False
        )

    def imaging_centring(self):
        self.imaging_centring_hwobj.initCentringProcedure(
            0
        )  # static_positions=self.imaging_static_positions)
        for click in range(3):
            self.user_clicked_event = gevent.event.AsyncResult()
            x, y = self.user_clicked_event.get()
            self.imaging_centring_hwobj.appendCentringDataPoint(
                {
                    "X": (x - self.imaging_beam_position[0])
                    / self.imaging_pixels_per_mm[0],
                    "Y": (y - self.imaging_beam_position[1])
                    / self.imaging_pixels_per_mm[1],
                }
                # static_positions=self.imaging_static_positions
            )
            if click < 2:
                self.motor_hwobj_dict["phi"].set_value_relative(90)
        self.omega_reference_add_constraint()
        # _x = self.imaging_centring_hwobj.centeredPosition(return_by_name=True, shift_to_constraints=True)
        # logging.getLogger("HWR").debug("xray %s" %_x)
        return self.centring_hwobj.centeredPosition(
            return_by_name=False, shift_to_constraints=True
        )

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
            self.motor_hwobj_dict["phi"].set_value_relative(
                360.0 / EMBLMiniDiff.AUTOMATIC_CENTRING_IMAGES
            )
            gevent.sleep(0.01)
            self.wait_device_ready(15)
        self.omega_reference_add_constraint()
        centred_pos_dir = self.centring_hwobj.centeredPosition(
            return_by_name=False, shift_to_constraints=False
        )
        self.emit("newAutomaticCentringPoint", centred_pos_dir)

        return centred_pos_dir

    def set_static_positions(self, static_positions):
        self.imaging_static_positions = static_positions

    def set_imaging_beam_position(self, pos_x, pos_y):
        self.imaging_beam_position[0] = pos_x
        self.imaging_beam_position[1] = pos_y

    def start_imaging_centring(self, sample_info=None, wait_result=None):
        self.emit_progress_message("Imaging based 3 click centring...")
        self.current_centring_procedure = gevent.spawn(self.imaging_centring)
        self.current_centring_procedure.link(self.centring_done)

    def start_imaging_centring_n(self, sample_info=None, wait_result=None):
        self.emit_progress_message("Imaging based n click centring...")
        self.current_centring_procedure = gevent.spawn(self.imaging_centring_n)
        self.current_centring_procedure.link(self.centring_done)

    """
    def imaging_centring(self):
        self.imaging_centring_hwobj.initCentringProcedure(static_positions=self.imaging_static_positions)
        for click in range(3):
            self.user_clicked_event = gevent.event.AsyncResult()
            x, y = self.user_clicked_event.get()
            self.imaging_centring_hwobj.appendCentringDataPoint(
                {
                    "X": (x - self.imaging_beam_position[0]) / self.imaging_pixels_per_mm[0],
                    "Y": (y - self.imaging_beam_position[1]) / self.imaging_pixels_per_mm[1],
                },
                static_positions=self.imaging_static_positions
            )
            if click < 2:
                self.motor_hwobj_dict["phi"].set_value_relative(90)
        self.omega_reference_add_constraint()
        return self.imaging_centring_hwobj.centeredPosition(return_by_name=False, shift_to_constraints=True)

    def BRAKE_imaging_centring_n(self):
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
        self.omega_reference_add_constraint()
        return self.imaging_centring_hwobj.centeredPosition(return_by_name=False)
    """

    def motor_positions_to_screen(self, centred_positions_dict):
        c = centred_positions_dict

        # kappa = self.current_motor_positions["kappa"]
        # phi = self.current_motor_positions["kappa_phi"]

        kappa = self.motor_hwobj_dict["kappa"].get_value()
        phi = self.motor_hwobj_dict["kappa_phi"].get_value()
        # IK TODO remove this director call

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
        if xy:
            x = (xy["X"] + c["beam_x"]) * self.pixels_per_mm_x + self.zoom_centre["x"]
            y = (xy["Y"] + c["beam_y"]) * self.pixels_per_mm_y + self.zoom_centre["y"]
            return x, y

    def move_to_centred_position(self, centred_position):
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
        try:
            return self.move_kappa_and_phi_procedure(kappa, kappa_phi)
        except BaseException:
            logging.exception("Could not move kappa and kappa_phi")

    @task
    def move_kappa_and_phi_procedure(self, new_kappa=None, new_kappa_phi=None):
        kappa = self.motor_hwobj_dict["kappa"].get_value()
        kappa_phi = self.motor_hwobj_dict["kappa_phi"].get_value()

        if new_kappa is None:
            new_kappa = kappa
        if new_kappa_phi is None:
            new_kappa_phi = kappa_phi

        motor_pos_dict = {}

        if (kappa, kappa_phi) != (
            new_kappa,
            new_kappa_phi,
        ) and self.minikappa_correction_hwobj is not None:
            sampx = self.motor_hwobj_dict["sampx"].get_value()
            sampy = self.motor_hwobj_dict["sampy"].get_value()
            phiy = self.motor_hwobj_dict["phiy"].get_value()
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

    def visual_align(self, point_1, point_2):
        if self.in_plate_mode():
            logging.getLogger("HWR").info(
                "EMBLMiniDiff: Visual align not available in Plate mode"
            )
        else:
            t1 = [point_1.sampx, point_1.sampy, point_1.phiy]
            t2 = [point_2.sampx, point_2.sampy, point_2.phiy]
            kappa = self.motor_hwobj_dict["kappa"].get_value()
            phi = self.motor_hwobj_dict["kappa_phi"].get_value()
            (
                new_kappa,
                new_phi,
                (new_sampx, new_sampy, new_phiy,),
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

    def re_emit_values(self):
        self.emit("minidiffPhaseChanged", (self.current_phase,))
        self.emit("omegaReferenceChanged", (self.reference_pos,))
        self.emit("minidiffShutterStateChanged", (self.fast_shutter_is_open,))

    def toggle_fast_shutter(self):
        if self.chan_fast_shutter_is_open is not None:
            self.chan_fast_shutter_is_open.setValue(not self.fast_shutter_is_open)

    def find_loop(self):
        image_array = HWR.beamline.sample_view.camera.get_snapshot(return_as_array=True)
        (info, x, y) = lucid.find_loop(image_array)
        surface_score = 10
        return x, y, surface_score

    def move_omega(self, angle):
        self.motor_hwobj_dict["phi"].set_value(angle, timeout=5)

    def move_omega_relative(self, relative_angle, timeout=5):
        self.motor_hwobj_dict["phi"].set_value_relative(relative_angle, timeout=timeout)

    def close_kappa(self):
        gevent.spawn(self.close_kappa_task)

    def close_kappa_task(self):
        """Close kappa task
        """
        logging.getLogger("HWR").debug("Diffractometer: Closing Kappa started...")
        self.move_kappa_and_phi_procedure(0, 0)  # None)
        self.wait_device_ready(180)
        logging.getLogger("HWR").debug("Diffractometer: Done closing Kappa.")
        """
        try:      
           self.motor_hwobj_dict["kappa"].home()
           self.wait_device_ready(60)
           logging.getLogger("HWR").debug("Diffractometer: Done Closing Kappa")
        except BaseException:
           logging.getLogger("GUI").error("Diffractometer: Kappa homing failed")
        """

    def set_zoom(self, position):
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
        if speed:
            limits = self.cmd_get_omega_scan_limits(speed)
        else:
            limits = self.motor_hwobj_dict["phi"].get_dynamic_limits()
        return (min(limits), max(limits))

    def get_osc_max_speed(self):
        return self.motor_hwobj_dict["phi"].get_max_speed()

    def get_scan_limits(self, num_images=0, exp_time=0.001343):
        """
        Gets scan limits. Necessary for example in the plate mode
        where osc range is limited
        """

        """
        if num_images==0:
            try:
                return (155.7182, 204.8366)
                limits = self.cmd_get_omega_scan_limits(0)
                return (min(limits) + 0.01, max(limits) - 0.01)
            except:
                return (None, None)
        """

        total_exposure_time = num_images * exp_time
        a = 0.002
        b = 0.2037
        w0 = -24.2816
        w1 = 24.83680  # was 196 not to shadow laser

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

        """
        if speed is not None:
            try:
                limits = self.cmd_get_omega_scan_limits(speed)
                return (min(limits), max(limits)), None
            except:
                return None, None

        total_exposure_time = num_images * exp_time
        tmp = self.cmd_get_omega_scan_limits(0)
        max_speed = self.get_osc_max_speed()
        w0 = tmp[1]
        w1 = tmp[0]
        x1 = 10
        x2 = 50

        c1 = min(self.cmd_get_omega_scan_limits(x1)) - w0
        c2 = min(self.cmd_get_omega_scan_limits(x2)) - w0

        a = -(c2 * x1 - c1 * x2)/(x1 * x2 * (x1 -x2))
        b = -(-c2 * pow(x1, 2) + c1 * pow(x2, 2))/(x1 *x2 * (x1 - x2))

        result_speed = (-2*b-total_exposure_time+sqrt((2*b+total_exposure_time)**2-8*a*(w0-w1))) /4/a
        if result_speed < 0:
            return (None, None), None
        elif result_speed > max_speed:
            delta = a * max_speed**2 + b * max_speed
            #total_exposure_time = total_exposure_time * result_speed / max_speed
            total_exposure_time = (w1-w0-2*delta) / (max_speed - 0.1)
        else:
            delta = a * result_speed**2 + b * result_speed

        print "get scan limits 2 ", (w0 + delta, w1 - delta)

        return (w0 + delta, w1 - delta), total_exposure_time / num_images
        """

    def get_scintillator_position(self):
        return self.chan_scintillator_position.getValue()

    def set_scintillator_position(self, position):
        self.chan_scintillator_position.setValue(position)
        with gevent.Timeout(5, Exception("Timeout waiting for scintillator position")):
            while position != self.get_scintillator_position():
                gevent.sleep(0.01)

    def get_capillary_position(self):
        return self.chan_capillary_position.getValue()

    def set_capillary_position(self, position):
        self.chan_capillary_position.setValue(position)
        with gevent.Timeout(5, Exception("Timeout waiting for capillary position")):
            while position != self.get_capillary_position():
                gevent.sleep(0.01)

    def zoom_in(self):
        self.zoom_motor_hwobj.zoom_in()

    def zoom_out(self):
        self.zoom_motor_hwobj.zoom_out()

    def save_centring_positions(self):
        self.cmd_save_centring_positions()

    def move_sample_out(self):
        self.motor_hwobj_dict["phiy"].set_value_relative(-2, wait=True, timeout=5)

    def move_sample_in(self):
        self.motor_hwobj_dict["phiy"].set_value_relative(2, wait=True, timeout=5)
