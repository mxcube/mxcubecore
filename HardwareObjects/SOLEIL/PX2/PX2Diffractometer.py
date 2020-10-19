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

import os
import time
import logging
import traceback
import pickle
import copy
import datetime
import h5py

import numpy as np
from scipy.optimize import minimize
from math import sqrt

import gevent

from goniometer import goniometer
from detector import detector
from camera import camera

import beam_align
import scan_and_align
import optical_alignment

from anneal import anneal as anneal_procedure
from queue_model_enumerables_v1 import CENTRING_METHOD

try:
    import lmfit
    from lmfit import fit_report
except ImportError:
    logging.warning(
        "Could not lmfit minimization library, "
        + "refractive model centring will not work."
    )

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
from HardwareRepository import HardwareRepository as HWR

__credits__ = ["SOLEIL"]
__version__ = "2.3."
__category__ = "General"


class PX2Diffractometer(GenericDiffractometer):
    """
    Description:
    """

    AUTOMATIC_CENTRING_IMAGES = 6

    motor_name_mapping = [
        ("AlignmentX", "phix"),
        ("AlignmentY", "phiy"),
        ("AlignmentZ", "phiz"),
        ("CentringX", "sampx"),
        ("CentringY", "sampy"),
        ("Omega", "phi"),
        ("Kappa", "kappa"),
        ("Phi", "kappa_phi"),
        ("beam_x", "beam_x"),
        ("beam_y", "beam_y"),
    ]

    def __init__(self, *args):
        """
        Description:
        """
        GenericDiffractometer.__init__(self, *args)

        # Hardware objects ----------------------------------------------------
        self.zoom_motor_hwobj = None
        self.omega_reference_motor = None
        self.centring_hwobj = None
        self.minikappa_correction_hwobj = None
        self.nclicks = None
        self.step = None
        self.centring_method = None
        self.collecting = False

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
        self.centring_time = None
        # Internal values -----------------------------------------------------
        self.use_sc = False
        self.omega_reference_pos = [0, 0]
        self.reference_pos = [680, 512]

        self.goniometer = goniometer()
        self.camera = camera()
        self.detector = detector()

        self.md2_to_mxcube = dict(
            [(key, value) for key, value in self.motor_name_mapping]
        )
        self.mxcube_to_md2 = dict(
            [(value, key) for key, value in self.motor_name_mapping]
        )

        self.log = logging.getLogger("HWR")

    def init(self):
        """
        Description:
        """
        GenericDiffractometer.init(self)
        self.centring_status = {"valid": False}

        self.chan_state = self.get_channel_object("State")
        self.chan_status = self.get_channel_object("Status")

        self.current_state = self.chan_state.get_value()
        self.current_status = self.chan_status.get_value()

        self.chan_state.connect_signal("update", self.state_changed)
        self.chan_status.connect_signal("update", self.status_changed)

        self.chan_calib_x = self.get_channel_object("CoaxCamScaleX")
        self.chan_calib_y = self.get_channel_object("CoaxCamScaleY")
        self.update_pixels_per_mm()

        self.chan_head_type = self.get_channel_object("HeadType")
        self.head_type = self.chan_head_type.get_value()

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
        self.minikappa_correction_hwobj = self.get_object_by_role(
            "minikappa_correction"
        )

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

        self.omega_reference_motor_moved(self.omega_reference_motor.get_value())

        # self.use_sc = self.get_property("use_sample_changer")

    def use_sample_changer(self):
        """
        Description:
        """
        return not self.in_plate_mode()

    def beam_position_changed(self, value):
        self.beam_position = value

    def state_changed(self, state):
        # logging.getLogger("HWR").debug("State changed: %s" % str(state))
        if self.current_state != state:
            self.current_state = state
            self.emit("minidiffStateChanged", (self.current_state))

    def status_changed(self, status):
        if self.current_status != status:
            self.current_status = status
            self.emit("minidiffStatusChanged", (self.current_status))

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
        """
        Description:
        """
        self.fast_shutter_is_open = is_open
        if is_open:
            msg = "Opened"
        else:
            msg = "Closed"
        self.emit("minidiffShutterStateChanged", (self.fast_shutter_is_open, msg))

    def current_phase_changed(self, current_phase):
        """
        Descript. :
        """
        if self.current_phase == current_phase:
            return
        self.current_phase = current_phase
        if current_phase != GenericDiffractometer.PHASE_UNKNOWN:
            logging.getLogger("GUI").info(
                "Diffractometer: Current phase changed to %s" % current_phase
            )
        self.emit("minidiffPhaseChanged", (current_phase,))

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

    def refresh_omega_reference_position(self):
        """
        Descript. :
        """
        if self.omega_reference_motor is not None:
            reference_pos = self.omega_reference_motor.get_value()
            self.omega_reference_motor_moved(reference_pos)

    def update_pixels_per_mm(self, *args):
        """
        Descript. :
        """
        if self.chan_calib_x:
            self.pixels_per_mm_x = 1.0 / self.chan_calib_x.get_value()
            self.pixels_per_mm_y = 1.0 / self.chan_calib_y.get_value()
            self.emit(
                "pixelsPerMmChanged", ((self.pixels_per_mm_x, self.pixels_per_mm_y),)
            )

    def set_phase(self, phase, timeout=60):
        """Sets diffractometer to the selected phase.
           In the plate mode before going to or away from
           Transfer or Beam location phase if needed then detector
           is moved to the safe distance to avoid collision.
        """
        # self.wait_device_ready(2)
        logging.getLogger("GUI").warning(
            "Diffractometer: Setting %s phase. Please wait..." % phase
        )

        if phase in (
            GenericDiffractometer.PHASE_TRANSFER,
            GenericDiffractometer.PHASE_BEAM,
        ) or self.current_phase in (
            GenericDiffractometer.PHASE_TRANSFER,
            GenericDiffractometer.PHASE_BEAM,
        ):
            detector_distance = HWR.beamline.detector.distance.get_value()
            logging.getLogger("HWR").debug(
                "Diffractometer current phase: %s " % self.current_phase
                + "selected phase: %s " % phase
                + "detector distance: %d mm" % detector_distance
            )
            if detector_distance < 350:
                logging.getLogger("GUI").info("Moving detector to safe distance")
                HWR.beamline.detector.distance.set_value(350)
                self.detector.insert_protective_cover()

        if timeout is not None:
            self.cmd_start_set_phase(phase)
            gevent.sleep(1)
            with gevent.Timeout(
                timeout, Exception("Timeout waiting for phase %s" % phase)
            ):
                while phase != self.chan_current_phase.get_value():
                    gevent.sleep(0.01)
        else:
            self.cmd_start_set_phase(phase)

    def start_auto_focus(self, timeout=None):
        """
        Descript. :
        """
        if timeout:
            self.ready_event.clear()
            set_phase_task = gevent.spawn(
                self.execute_server_task, self.cmd_start_auto_focus(), timeout
            )
            self.ready_event.wait()
            self.ready_event.clear()
        else:
            self.cmd_start_auto_focus()

    def centring_done(self, centring_procedure):
        """
        Descript. :
        """
        try:
            motor_pos = centring_procedure.get()
            # if isinstance(motor_pos, gevent.GreenletExit):
            # raise motor_pos
            # self.log.info('motor_pos from centring_procedure %s' % motor_pos)
        except Exception:
            logging.exception("Could not complete centring")
            self.emit_centring_failed()
        else:
            self.emit_progress_message("Moving sample to centred position...")
            self.emit_centring_moving()
            try:
                self.move_to_motors_positions(motor_pos)
            except Exception:
                logging.exception("Could not move to centred position")
                self.emit_centring_failed()

            if (
                self.current_centring_method
                == GenericDiffractometer.CENTRING_METHOD_AUTO
            ):
                self.emit("newAutomaticCentringPoint", motor_pos)

            self.ready_event.set()
            self.centring_time = time.time()
            self.emit_centring_successful()

    def move_motors(self, motor_positions, timeout=15):
        """
        Moves diffractometer motors to the requested positions

        :param motors_dict:  with motor names or hwobj
                            and target values.
        :type motors_dict: dict
        """

        position = self.translate_from_mxcube_to_md2(motor_positions)

        self.goniometer.set_position(position, timeout=timeout)

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        Descript. :
        """

        self.log.info("get_centred_point_from_coord: x, y: %s %s" % (x, y))
        self.log.info(
            "get_centred_point_from_coord: self.pixels_per_mm_x, self.pixels_per_mm_ y: %s %s"
            % (self.pixels_per_mm_x, self.pixels_per_mm_y)
        )
        self.log.info(
            "get_centred_point_from_coord: self.beam_position: %s"
            % str(self.beam_position)
        )

        current_position = self.goniometer.get_aligned_position()

        omega_reference = self.omega_reference_par["position"]

        alignmentz_shift = current_position["AlignmentZ"] - omega_reference

        vertical_shift = y - self.beam_position[1]

        horizontal_shift = x - self.beam_position[0]

        vertical_shift /= self.pixels_per_mm_y
        horizontal_shift /= self.pixels_per_mm_x

        self.log.info(
            "get_centred_point_from_coord: original_vertical_shift: %s "
            % vertical_shift
        )

        vertical_shift += alignmentz_shift

        centringx_shift, centringy_shift = self.goniometer.get_x_and_y(
            0, vertical_shift, current_position["Omega"]
        )

        centred_point = copy.deepcopy(current_position)

        self.log.info(
            "get_centred_point_from_coord: alignmentz_shift: %s " % alignmentz_shift
        )
        self.log.info(
            "get_centred_point_from_coord: horizontal_shift: %s " % horizontal_shift
        )

        self.log.info(
            "get_centred_point_from_coord: vertical_shift: %s " % vertical_shift
        )
        self.log.info(
            "get_centred_point_from_coord: centringx_shift: %s " % centringx_shift
        )
        self.log.info(
            "get_centred_point_from_coord: centringy_shift: %s " % centringy_shift
        )

        centred_point["AlignmentZ"] -= alignmentz_shift
        centred_point["AlignmentY"] -= horizontal_shift

        centred_point["CentringX"] += centringx_shift
        centred_point["CentringY"] += centringy_shift

        # centred_point['Omega'] += 90.
        pos = self.translate_from_md2_to_mxcube(centred_point)

        self.log.info("get_centred_point_from_coord: centred_point: %s " % str(pos))

        return pos

        self.centring_hwobj.initCentringProcedure()
        self.centring_hwobj.appendCentringDataPoint(
            {
                "X": (x - self.beam_position[0]) / self.pixels_per_mm_x,
                "Y": (y - self.beam_position[1]) / self.pixels_per_mm_y,
            }
        )
        self.omega_reference_add_constraint()
        pos = self.centring_hwobj.centeredPosition()
        self.log.info("get_centred_point_from_coord: pos %s" % str(pos))
        if return_by_names:
            pos = self.convert_from_obj_to_name(pos)
        return pos

    def move_to_beam(self, x, y, omega=None):
        """Creates a new centring point based on all motors positions
        """
        if self.current_phase != "BeamLocation":
            GenericDiffractometer.move_to_beam(
                self, x, y, omega=self.goniometer.get_omega_position()
            )
        else:
            logging.getLogger("HWR").debug(
                "Diffractometer: Move to screen"
                + " position disabled in BeamLocation phase."
            )

    def manual_centring(
        self,
        n_clicks=3,
        alignmenty_direction=-1.0,
        alignmentz_direction=1.0,
        centringx_direction=-1.0,
        centringy_direction=1.0,
        refractive_model=False,
    ):
        """
        Descript. :
        """
        logging.getLogger("user_level_log").info("starting manual centring")
        _start = time.time()
        result_position = {}
        self.goniometer.insert_backlight()
        self.goniometer.extract_frontlight()

        reference_position = self.goniometer.get_aligned_position()

        vertical_clicks = []
        horizontal_clicks = []
        vertical_discplacements = []
        horizontal_displacements = []
        omegas = []
        images = []
        auxiliary_images = []
        calibrations = []

        if isinstance(self.nclicks, int) and self.nclicks >= 3:
            n_clicks = self.nclicks

        logging.getLogger("user_level_log").info(
            "expected number of clicks %d" % (n_clicks)
        )

        if self.step is not None:
            step = self.step
        else:
            step = 360.0 / (n_clicks)

        logging.getLogger("user_level_log").info("default centring step %.2f" % (step))

        start_clicks = time.time()

        for k in range(n_clicks):
            self.user_clicked_event = gevent.event.AsyncResult()
            x, y = self.user_clicked_event.get()
            image = HWR.beamline.sample_view.camera.get_last_image()
            calibration = self.camera.get_calibration()
            omega = self.goniometer.get_omega_position()

            vertical_clicks.append(y)
            horizontal_clicks.append(x)
            omegas.append(omega)
            images.append(image)
            calibrations.append([calibration])

            x -= self.beam_position[0]
            x /= self.pixels_per_mm_x
            y -= self.beam_position[1]
            y /= self.pixels_per_mm_y
            vertical_discplacements.append(y)
            horizontal_displacements.append(x)

            logging.getLogger("HWR").info("click %d %f %f %f" % (k + 1, omega, x, y))

            if k <= n_clicks:
                self.goniometer.set_position({"Omega": omega + step})

        end_clicks = time.time()

        name_pattern = "%s_%s" % (os.getuid(), time.asctime().replace(" ", "_"))
        directory = "%s/manual_optical_alignment" % os.getenv("HOME")

        save_history_command = "history_saver.py -s %.2f -e %.2f -d %s -n %s &" % (
            start_clicks,
            end_clicks,
            directory,
            name_pattern,
        )

        self.log.info("save_history_command: %s" % save_history_command)
        os.system(save_history_command)

        vertical_discplacements = np.array(vertical_discplacements) * 1.0e3

        angles = np.radians(omegas)

        if self.centring_method != CENTRING_METHOD.REFRACTIVE:
            initial_parameters = [4.0, 25.0, 0.05]
            fit_y = minimize(
                self.circle_model_residual,
                initial_parameters,
                method="nelder-mead",
                args=(angles, vertical_discplacements),
            )

            c, r, alpha = fit_y.x
            c *= 1e-3
            r *= 1.0e-3
            v = {"c": c, "r": r, "alpha": alpha}

        else:
            initial_parameters = lmfit.Parameters()
            initial_parameters.add_many(
                ("c", 0.0, True, -5e3, +5e3, None, None),
                ("r", 0.0, True, 0.0, 4e3, None, None),
                ("alpha", -np.pi / 3, True, -2 * np.pi, 2 * np.pi, None, None),
                ("front", 0.01, True, 0.0, 1.0, None, None),
                ("back", 0.005, True, 0.0, 1.0, None, None),
                ("n", 1.31, True, 1.29, 1.33, None, None),
                ("beta", 0.0, True, -2 * np.pi, +2 * np.pi, None, None),
            )

            fit_y = lmfit.minimize(
                self.refractive_model_residual,
                initial_parameters,
                method="nelder",
                args=(angles, vertical_discplacements),
            )
            self.log.info(fit_report(fit_y))
            optimal_params = fit_y.params
            v = optimal_params.valuesdict()
            c = v["c"]
            r = v["r"]
            alpha = v["alpha"]
            front = v["front"]
            back = v["back"]
            n = v["n"]
            beta = v["beta"]

            c *= 1.0e-3
            r *= 1.0e-3
            front *= 1.0e-3
            back *= 1.0e-3

        horizontal_center = np.mean(horizontal_displacements)

        d_sampx = centringx_direction * r * np.sin(alpha)
        d_sampy = centringy_direction * r * np.cos(alpha)
        d_y = alignmenty_direction * horizontal_center
        d_z = alignmentz_direction * c

        move_vector_dictionary = {
            "AlignmentZ": d_z,
            "AlignmentY": d_y,
            "CentringX": d_sampx,
            "CentringY": d_sampy,
        }

        for motor in reference_position:
            result_position[motor] = reference_position[motor]
            if motor in move_vector_dictionary:
                result_position[motor] += move_vector_dictionary[motor]

        _end = time.time()
        duration = _end - _start
        self.log.info(
            "input and analysis in manual_centring took %.3f seconds" % duration
        )

        results = {
            "vertical_clicks": vertical_clicks,
            "horizontal_clicks": horizontal_clicks,
            "vertical_discplacements": vertical_discplacements,
            "horizontal_displacements": horizontal_displacements,
            "omegas": omegas,
            "angles": angles,
            "calibrations": calibrations,
            "reference_position": reference_position,
            "result_position": result_position,
            "duration": duration,
            "vertical_optimal_parameters": v,
        }

        template = os.path.join(directory, name_pattern)

        if not os.path.isdir(directory):
            os.makedirs(directory)

        images_filename = "%s_images.h5" % template
        images_file = h5py.File(images_filename, "w")
        images_file.create_dataset(
            "images", data=np.array(images), compression="lzf", dtype=np.uint8
        )
        images_file.close()

        clicks_filename = "%s_clicks.pickle" % template
        f = open(clicks_filename, "w")
        pickle.dump(results, f)
        f.close()

        self.log.info(
            "manual_centring finished in %.3f seconds" % (time.time() - _start)
        )

        translated_position = self.translate_from_md2_to_mxcube(result_position)
        return translated_position

    def translate_from_md2_to_mxcube(self, position):
        translated_position = {}

        for key in position:
            translated_position[self.md2_to_mxcube[key]] = position[key]

        return translated_position

    def convert_from_obj_to_name(self, motor_pos):
        """
        """
        # self.log.info('convert_from_obj_to_name motor_pos %s' % str(motor_pos))
        # self.log.info('convert_from_obj_to_name cml %s ' % str(self.centring_motors_list))
        # self.log.info('convert_from_obj_to_name motor_names %s' % str([motor.motor_name for motor in motor_pos]))

        aligned_position = self.goniometer.get_aligned_position()

        motors = self.translate_from_mxcube_to_md2(motor_pos)

        for key in aligned_position:
            if key not in motors:
                motors[key] = aligned_position[key]

        motors = self.translate_from_md2_to_mxcube(motors)
        # motors = {}
        # for motor_role in self.centring_motors_list:
        # self.log.info('motor_role %s' % motor_role)
        # motor_obj = self.get_object_by_role(motor_role)
        # try:
        # motors[motor_role] = motor_pos[motor_obj]
        # except KeyError:

        # self.log.exception('convert_from_obj_to_name %s' % traceback.format_exc())
        # if motor_obj:
        # motors[motor_role] = motor_obj.get_value()

        motors["beam_x"] = (
            self.beam_position[0] - self.zoom_centre["x"]
        ) / self.pixels_per_mm_y
        motors["beam_y"] = (
            self.beam_position[1] - self.zoom_centre["y"]
        ) / self.pixels_per_mm_x
        self.log.info("convert_from_obj_to_name motors %s" % str(motors))
        return motors

    def translate_from_mxcube_to_md2(self, position):
        translated_position = {}

        for key in position:
            if isinstance(key, str):
                translated_position[self.mxcube_to_md2[key]] = position[key]
            else:
                translated_position[key.motor_name] = position[key]
        return translated_position

    def circle_model(self, angles, c, r, alpha):
        return c + r * np.cos(angles - alpha)

    def circle_model_residual(self, parameters, angles, data):
        c, r, alpha = parameters
        model = self.circle_model(angles, c, r, alpha)
        # return 1./(2*len(model)) * np.sum(np.sum(np.abs(data - model)**2))
        return self.cost(data, model, normalize=True)

    def circle_model_residual2(self, parameters, angles, data):
        v = parameters.valuesdict()
        c = v["c"]
        r = v["r"]
        alpha = v["alpha"]
        model = self.circle_model(angles, c, r, alpha)

        return self.cost_array(data, model)

    def refractive_model(self, t, c, r, alpha, front, back, n, beta):
        return self.circle_model(t, c, r, alpha) - self.shift(t, front, back, n, beta)

    def refractive_model_residual(self, parameters, angles, data):
        v = parameters.valuesdict()
        c = v["c"]
        r = v["r"]
        alpha = v["alpha"]
        front = v["front"]
        back = v["back"]
        n = v["n"]
        beta = v["beta"]
        model = self.refractive_model(angles, c, r, alpha, front, back, n, beta)

        return self.cost_array(data, model)

    def cost(self, data, model, factor=1.0, normalize=False):
        if normalize == True:
            factor = 1.0 / (2 * len(model))
        return factor * np.sum(np.sum(np.abs(data - model) ** 2))

    def cost_array(self, data, model):
        return np.abs(data - model) ** 2

    def i(self, t, n):
        return np.arcsin(np.sin(t) / n)

    def planparallel_shift(self, depth, t, n, sense=1):
        i = self.i(t, n)
        return -depth * np.sin(sense * t - i) / np.cos(i)

    def shift(self, t, f, b, n, beta):
        t = t - beta
        dt = np.degrees(t)
        s = np.zeros(dt.shape)
        t_base = t % (2 * np.pi)
        mask = np.where(((t_base < 3 * np.pi / 2) & (t_base >= np.pi / 2)), 1, 0)
        s[mask == 0] = self.planparallel_shift(f, t_base[mask == 0], n, sense=1)
        s[mask == 1] = self.planparallel_shift(b, t_base[mask == 1], n, sense=-1)
        return s

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Descript. :
        """
        c = centred_positions_dict

        # self.log.info('motor_positions_to_screen c %s ' % str(c))

        # kappa = self.current_motor_positions["kappa"]
        # phi = self.current_motor_positions["kappa_phi"]
        self.log.info("centred_positions_dict %s" % str(centred_positions_dict))
        try:
            for key in c:
                if c[key] is None:
                    try:
                        c[key] = self.motor_hwobj_dict[key].get_value()
                    except Exception:
                        # self.log.info('motor_positions_to_screen exception key %s' % key)
                        self.log.info(traceback.format_exc())

            if "kappa" in c and c["kappa"] is None:
                kappa = self.motor_hwobj_dict["kappa"].get_value()
                c["kappa"] = kappa
            else:
                c["kappa"] = self.goniometer.get_kappa_position()

            if "kappa_phi" in c and c["kappa_phi"] is None:
                phi = self.motor_hwobj_dict["kappa_phi"].get_value()
                c["kappa_phi"] = phi
            else:
                c["kappa_phi"] = self.goniometer.get_phi_position()

            if "beam_x" in c and c["beam_x"] in [0.0, None]:
                c["beam_x"] = 0.0  # self.beam_position[0]
            else:
                c["beam_x"] = 0.0  # self.beam_position[0]

            if "beam_y" not in c and c["beam_y"] in [0.0, None]:
                c["beam_y"] = 0.0  # self.beam_position[1]
            else:
                c["beam_y"] = 0.0  # self.beam_position[1]

            # self.log.info('motor_positions_to_screen c2 %s ' % str(c))

            if (c["kappa"], c["kappa_phi"]) != (
                self.goniometer.get_kappa_position(),
                self.goniometer.get_phi_position(),
            ) and self.minikappa_correction_hwobj is not None:
                self.log.info("calculating minikappa correction")
                (
                    c["sampx"],
                    c["sampy"],
                    c["phiy"],
                ) = self.minikappa_correction_hwobj.shift(
                    c["kappa"],
                    c["kappa_phi"],
                    [c["sampx"], c["sampy"], c["phiy"]],
                    c["kappa"],
                    c["kappa_phi"],
                )

            xy = self.centring_hwobj.centringToScreen(c)
            # self.log.info('xy %s' % xy)

            if xy:
                x = (xy["X"] + c["beam_x"]) * self.pixels_per_mm_x + self.zoom_centre[
                    "x"
                ]
                y = (xy["Y"] + c["beam_y"]) * self.pixels_per_mm_y + self.zoom_centre[
                    "y"
                ]
                return x, y
        except Exception:
            return 0, 0

    def move_to_centred_position(self, centred_position):
        """
        Descript. :
        """
        # self.log.info('in move_to_centred_position')
        # self.log.info('centred_position %s' % centred_position)

        if centred_position.beam_x is None:
            centred_position.beam_x = 0.0

        if centred_position.beam_y is None:
            centred_position.beam_y = 0.0

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
            except Exception:
                logging.exception("Could not move to centred position")
        else:
            logging.getLogger("HWR").debug(
                "Move to centred position disabled in BeamLocation phase."
            )

    def move_to_motors_positions(self, motors_positions, wait=False):
        """
        """
        self.emit_progress_message("Moving to motors positions...")
        self.move_to_motors_positions_procedure = gevent.spawn(
            self.move_motors, motors_positions
        )
        self.move_to_motors_positions_procedure.link(self.move_motors_done)

    def move_kappa_and_phi(self, kappa=None, kappa_phi=None, wait=False):
        """
        Descript. :
        """
        try:
            return self.move_kappa_and_phi_procedure(kappa, kappa_phi, wait=wait)
        except Exception:
            logging.exception("Could not move kappa and kappa_phi")

    @task
    def move_kappa_and_phi_procedure(self, new_kappa=None, new_kappa_phi=None):
        """
        Descript. :
        """
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

    def visual_align(self, point_1, point_2):
        """
        Descript. :
        """
        if self.in_plate_mode():
            logging.getLogger("HWR").info(
                "PX2Diffractometer: Visual align not available in Plate mode"
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
            ) = self.goniometer.get_align_vector(t1, t2, kappa, phi)
            # self.minikappa_correction_hwobj.alignVector(t1,t2,kappa,phi)
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
        """
        Description:
        """
        self.emit("minidiffPhaseChanged", (self.current_phase,))
        self.emit("omegaReferenceChanged", (self.reference_pos,))
        self.emit("minidiffShutterStateChanged", (self.fast_shutter_is_open,))

    def toggle_fast_shutter(self):
        """
        Description:
        """
        if self.chan_fast_shutter_is_open is not None:
            self.chan_fast_shutter_is_open.set_value(not self.fast_shutter_is_open)

    def find_loop(self):
        """
        Description:
        """
        image_array = HWR.beamline.sample_view.get_snapshot(return_as_array=True)
        (info, x, y) = lucid.find_loop(image_array)
        surface_score = 10
        return x, y, surface_score

    def move_omega_relative(self, relative_angle):
        """
        Description:
        """
        self.motor_hwobj_dict["phi"].set_value_relative(relative_angle, 5)

    def close_kappa(self):
        """
        Descript. :
        """
        gevent.spawn(self.close_kappa_task)

    def close_kappa_task(self):
        """Close kappa task
        """
        logging.getLogger("HWR").debug("Started closing Kappa")
        self.move_kappa_and_phi_procedure(0, None)
        self.wait_device_ready(60)
        self.motor_hwobj_dict["kappa"].homeMotor()
        self.wait_device_ready(60)
        self.move_kappa_and_phi_procedure(0, None)
        self.wait_device_ready(60)
        logging.getLogger("HWR").debug("Done closing Kappa")
        # self.kappa_phi_motor_hwobj.homeMotor()

    def set_zoom(self, position):
        """
        """
        self.zoom_motor_hwobj.moveToPosition(position)

    def get_status(self):
        self.current_status = self.chan_status.get_value()
        return self.current_status

    def get_point_from_line(self, point_one, point_two, frame_num, frame_total):
        """
        Descript. : method used to get a new motor position based on a position
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

    def get_osc_limits(self):
        return self.motor_hwobj_dict["phi"].getDynamicLimits()

    def get_osc_max_speed(self):
        return self.motor_hwobj_dict["phi"].getMaxSpeed()

    def get_scan_limits(self, speed=None, num_images=None, exp_time=None):
        """optical_alignment
        Gets scan limits. Necessary for example in the plate mode
        where osc range is limited
        """
        if speed is not None:
            return self.cmd_get_omega_scan_limits(speed), None
        total_exposure_time = num_images * exp_time
        tmp = self.cmd_get_omega_scan_limits(0)
        max_speed = self.get_osc_max_speed()
        w0 = tmp[0]
        w1 = tmp[1]
        x1 = 10
        x2 = 100

        c1 = self.cmd_get_omega_scan_limits(x1)[0] - w0
        c2 = self.cmd_get_omoptical_alignmentega_scan_limits(x2)[0] - w0

        a = -(c2 * x1 - c1 * x2) / (x1 * x2 * (x1 - x2))
        b = -(-c2 * pow(x1, 2) + c1 * pow(x2, 2)) / (x1 * x2 * (x1 - x2))

        result_speed = (
            (
                -2 * b
                - total_exposure_time
                + sqrt((2 * b + total_exposure_time) ** 2 - 8 * a * (w0 - w1))
            )
            / 4
            / a
        )
        if result_speed < 0:
            return (None, None), None
        elif result_speed > max_speed:
            delta = a * max_speed ** 2 + b * max_speed
            # total_exposure_time = total_exposure_time * result_speed / max_speed
            total_exposure_time = (w1 - w0 - 2 * delta) / (max_speed - 0.1)
        else:
            delta = a * result_speed ** 2 + b * result_speed

        return (w0 + delta, w1 - delta), total_exposure_time / num_images

        """
        if speed is not None:
            return self.cmd_get_omega_scan_limits(speed)
        elif speed == 0:
            return self.get_osc_limits()
        else:
            motor_acc_const = 5
            motor_acc_time = num_images / exp_time / motor_acc_const
            min_acc_time = 0.0015
            acc_time = max(motor_acc_time, min_acc_time)

            shutter_time = 3.7 / 1000.
            max_limit = num_images / exp_time * (acc_time+2*shutter_time + 0.2) / 2

            return [0, max_limit]
        """

    def get_scintillator_position(self):
        return self.chan_scintillator_position.get_value()

    def set_scintillator_position(self, position):
        self.chan_scintillator_position.set_value(position)
        with gevent.Timeout(5, Exception("Timeout waiting for scintillator position")):
            while position != self.get_scintillator_position():
                gevent.sleep(0.01)

    def get_capillary_position(self):
        return self.chan_capillary_position.get_value()

    def set_capillary_position(self, position):
        self.chan_capillary_position.set_value(position)
        with gevent.Timeout(5, Exception("Timeout waiting for capillary position")):
            while position != self.get_capillary_position():
                gevent.sleep(0.01)

    def zoom_in(self):
        self.zoom_motor_hwobj.zoom_in()

    def zoom_out(self):
        self.zoom_motor_hwobj.zoom_out()

    def save_centring_positions(self):
        self.cmd_save_centring_positions()

    def beam_position_check(self):
        logging.getLogger("user_level_log").info("Going to check the beam position")
        self.bpc(wait=False)

    @task
    def bpc(self):
        ba = beam_align.beam_align(
            name_pattern="%s_%s" % (os.getuid(), time.asctime().replace(" ", "_")),
            directory="%s/beam_align" % os.getenv("HOME"),
        )
        logging.getLogger("user_level_log").info(
            "Align beam to the optical centre of the camera"
        )
        logging.getLogger("user_level_log").info(
            "Moving scintillator to sample position, please wait ..."
        )
        ba.execute()

        if ba.no_beam is False:
            logging.getLogger("user_level_log").info(
                "Initial mirror positions (vfm, hfm) [mrad]: %.4f %.4f"
                % tuple(ba.initial_mirror_positions)
            )
            logging.getLogger("user_level_log").info(
                "Initial pixel shift from center (vertical, horizontal): %.1f, %.1f"
                % tuple(ba.initial_pixel_shift)
            )
            logging.getLogger("user_level_log").info(
                "Beam position adjustment finished after %d iterations"
                % ba.number_of_iterations
            )
            logging.getLogger("user_level_log").info(
                "Final mirror positions (vfm, hfm) [mrad]: %.4f %.4f"
                % tuple(ba.final_mirror_position)
            )
            logging.getLogger("user_level_log").info(
                "Final pixel shift from center (vertical, horizontal): %.1f, %.1f"
                % tuple(ba.final_pixel_shift)
            )
            logging.getLogger("user_level_log").info(
                "Delta in motor positions [mrad]: %.4f, %.4f"
                % tuple(ba.final_mirror_position - ba.initial_mirror_positions)
            )
        else:
            logging.getLogger("user_level_log").info(ba.no_beam_message)

    @task
    def anneal(self, time=1.0):
        anneal_procedure(time)

    @task
    def excenter(
        self,
        scan_length=0.1,
        step=90.0,
        start=0.0,
        base_directory="/nfs/ruche/proxima2a-spool/2019_Run1/excenter",
        name_pattern="excenter",
    ):

        directory = os.path.join(base_directory, datetime.datetime.today().isoformat())

        angles = str(tuple(np.arange(start, 360.0, step)))

        execute_line = 'excenter.py -d %s -n %s -l %.2f -a "%s" &' % (
            directory,
            name_pattern,
            scan_length,
            angles,
        )

        self.log.info("excenter angles %s" % angles)
        self.log.info("excenter line %s" % execute_line)

        os.system(execute_line)

    def aperture_align(self):
        logging.getLogger("user_level_log").info("Aligning the current aperture")
        self.aa(wait=False)

    @task
    def aa(self):
        logging.getLogger("user_level_log").info(
            "Adjusting camera exposure time for visualisation on the scintillator"
        )
        a = scan_and_align.scan_and_align("aperture", display=False)
        logging.getLogger("user_level_log").info("Scanning the aperture")
        a.scan()
        a.align(optimum="com")
        a.save_scan()
        logging.getLogger("user_level_log").info(
            "Setting camera exposure time back to 0.050 seconds"
        )
        logging.getLogger("user_level_log").info("Aligning aperture finished")
        a.predict()

    def start_automatic_centring(
        self, sample_info=None, loop_only=False, wait_result=None
    ):
        """
        """
        self.emit_progress_message("Automatic centring...")
        self.current_centring_procedure = gevent.spawn(self.optical_alignment)
        self.current_centring_procedure.link(self.centring_done)

        if wait_result:
            self.ready_event.wait()
            self.ready_event.clear()

        # self.optical_alignment(wait=False)

    # @task
    def optical_alignment(self):
        start = time.time()
        oa = optical_alignment.optical_alignment(
            name_pattern="%s_%s" % (os.getuid(), time.asctime().replace(" ", "_")),
            directory="%s/automated_optical_alignment" % os.getenv("HOME"),
            analysis=True,
            conclusion=True,
            move_zoom=True,
            film_step=120.0,
        )

        oa.execute()

        self.log.info(
            "optical sample alignment finished in %.3f seconds" % (time.time() - start)
        )
        # self.emit_centring_successful()
        self.emit("centringSuccessful", self.current_centring_method, ())
        result_position = oa.get_result_position()
        translated_position = self.translate_from_md2_to_mxcube(result_position)
        return translated_position

    def set_nclicks(self, nclicks):
        self.log.info(
            "PX2Diffractometer: number of centring clicks changed: %s" % nclicks
        )
        try:
            self.nclicks = int(nclicks)
        except Exception:
            logging.getLogger("HWR").exception(traceback.format_exc())

    def set_step(self, step):
        self.log.info("PX2Diffractometer: centring step changed: %s" % step)
        try:
            self.step = float(step)
        except Exception:
            logging.getLogger("HWR").exception(traceback.format_exc())

    def set_centring_method(self, centring_method):
        self.log.info(
            "PX2Diffractometer: centring method changed: %s" % centring_method
        )
        try:
            self.centring_method = centring_method
        except Exception:
            logging.getLogger("HWR").exception(traceback.format_exc())

    def is_ready(self):
        """
        Detects if device is ready
        """
        condition1 = self.current_state == DiffractometerState.tostring(
            DiffractometerState.Ready
        )

        condition2 = self.collecting == False

        # self.log.info('Diffractometer is_ready collecting %s' % self.collecting)

        return condition1 and condition2

    def set_collecting(self, collecting=True):
        self.collecting = collecting
