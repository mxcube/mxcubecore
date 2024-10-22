import logging
import time

import gevent

from mxcubecore.HardwareObjects import sample_centring
from mxcubecore.HardwareObjects.GenericDiffractometer import GenericDiffractometer


class PX1MiniDiff(GenericDiffractometer):

    CENTRING_MOTORS_NAME = [
        "phi",
        "phiz",
        "phiy",
        "sampx",
        "sampy",
        "kappa",
        "kappa_phi",
        "beam_x",
        "beam_y",
        "zoom",
    ]

    def init(self):
        self.smargon = self.get_object_by_role("smargon")
        self.connect(self.smargon, "stateChanged", self.smargon_state_changed)

        self.lightarm_hwobj = self.get_object_by_role("lightarm")
        # self.centring_hwobj = self.get_object_by_role('centring')

        self.px1conf_ho = self.get_object_by_role("px1configuration")
        self.px1env_ho = self.get_object_by_role("px1environment")

        self.pixels_per_mm_x = 0
        self.pixels_per_mm_y = 0

        GenericDiffractometer.init(self)

        self.centring_methods = {
            GenericDiffractometer.CENTRING_METHOD_MANUAL: self.px1_manual_centring,
            GenericDiffractometer.CENTRING_METHOD_AUTO: self.start_automatic_centring,
            GenericDiffractometer.CENTRING_METHOD_MOVE_TO_BEAM: self.start_move_to_beam,
        }

    def prepare_centring(self, timeout=20):
        self.px1env_ho.gotoSampleViewPhase()

        gevent.sleep(0.5)

        if self.px1env_ho.isPhaseVisuSample():
            t0 = time.time()
            while True:
                env_state = self.px1env_ho.get_state()
                if env_state != "RUNNING" and self.px1env_ho.isPhaseVisuSample():
                    break
                if time.time() - t0 > timeout:
                    logging.getLogger("HWR").debug(
                        "timeout sending supervisor to sample view phase"
                    )
                    break
                gevent.sleep(0.1)

        self.lightarm_hwobj.adjustLightLevel()

    def smargon_state_changed(self, value):
        logging.getLogger("HWR").debug("smargon state changed")
        self.smargon_state = value
        self.emit("minidiffStateChanged", (value,))

    def is_ready(self):
        return self.smargon.get_state() == "STANDBY"

        # self.smargon_state = str(self.smargon_state_ch.get_value())
        # return self.smargon_state == "STANDBY"

    def get_pixels_per_mm(self):
        self.update_zoom_calibration()
        return GenericDiffractometer.get_pixels_per_mm(self)

    def update_zoom_calibration(self):
        """ """
        if "zoom" not in self.motor_hwobj_dict:
            # not initialized yet
            return

        zoom_motor = self.motor_hwobj_dict["zoom"]

        props = zoom_motor.getCurrentPositionProperties()

        if "pixelsPerMmZ" in props.keys() and "pixelsPerMmY" in props.keys():
            self.pixels_per_mm_x = float(props["pixelsPerMmY"])
            self.pixels_per_mm_y = float(props["pixelsPerMmZ"])
        else:
            self.pixels_per_mm_x = 0
            self.pixels_per_mm_y = 0

        if "beamPositionX" in props.keys() and "beamPositionY" in props.keys():
            self.beam_xc = float(props["beamPositionX"])
            self.beam_yc = float(props["beamPositionY"])

        if 0 not in [self.pixels_per_mm_x, self.pixels_per_mm_y]:
            self.emit(
                "pixelsPerMmChanged", ((self.pixels_per_mm_x, self.pixels_per_mm_y),)
            )

    def px1_manual_centring(self, sample_info=None, wait_result=None):
        """ """
        self.emit_progress_message("Manual 3 click centring...")
        logging.getLogger("HWR").debug(
            "   starting manual 3 click centring. phiy is %s" % str(self.centring_phiy)
        )

        centring_points = self.px1conf_ho.getCentringPoints()
        centring_phi_incr = self.px1conf_ho.getCentringPhiIncrement()
        centring_sample_type = self.px1conf_ho.getCentringSampleType()

        self.current_centring_procedure = sample_centring.px1_start(
            {
                "phi": self.centring_phi,
                "phiy": self.centring_phiy,
                "sampx": self.centring_sampx,
                "sampy": self.centring_sampy,
                "phiz": self.centring_phiz,
            },
            self.pixels_per_mm_x,
            self.pixels_per_mm_y,
            self.beam_position[0],
            self.beam_position[1],
            n_points=centring_points,
            phi_incr=centring_phi_incr,
            sample_type=centring_sample_type,
        )

        self.current_centring_procedure.link(self.centring_done)

    def centring_done(self, centring_procedure):
        """
        Descript. :
        """
        logging.getLogger("HWR").debug("Diffractometer: centring procedure done.")
        try:
            motor_pos = centring_procedure.get()
            if isinstance(motor_pos, gevent.GreenletExit):
                raise motor_pos
        except Exception:
            logging.exception("Could not complete centring")
            self.emit_centring_failed()
        else:
            logging.getLogger("HWR").debug(
                "Diffractometer: centring procedure done. %s" % motor_pos
            )

            for motor in motor_pos:
                position = motor_pos[motor]
                logging.getLogger("HWR").debug(
                    "   - motor is %s - going to %s" % (motor.name(), position)
                )

            self.emit_progress_message("Moving sample to centred position...")
            self.emit_centring_moving()
            try:
                self.move_to_motors_positions(motor_pos, wait=True)
            except Exception:
                logging.exception("Could not move to centred position")
                self.emit_centring_failed()
            else:
                # done already by px1_center
                pass
                # if 3 click centring move -180
                # if not self.in_plate_mode():
                # self.wait_device_ready()
                # self.motor_hwobj_dict['phi'].set_value_relative(-180, timeout=None)

            if (
                self.current_centring_method
                == GenericDiffractometer.CENTRING_METHOD_AUTO
            ):
                self.emit("newAutomaticCentringPoint", motor_pos)
            self.centring_time = time.time()
            self.emit_centring_successful()
            self.emit_progress_message("")
            self.ready_event.set()

    def move_to_motors_positions(self, motors_positions, wait=False):
        """ """
        self.emit_progress_message("Moving to motors positions...")
        self.move_to_motors_positions_procedure = gevent.spawn(
            self.move_motors, motors_positions
        )

        self.move_to_motors_positions_procedure.link(self.move_motors_done)

        if wait:
            self.wait_device_ready(10)

    def move_omega_relative(self, relative_pos):
        omega_mot = self.motor_hwobj_dict.get("phi")
        omega_mot.set_value_relative(relative_pos, timeout=None)

    def move_motors(self, motor_positions, timeout=15):
        """
        Moves diffractometer motors to the requested positions

        :param motors_dict: dictionary with motor names or hwobj
                            and target values.
        :type motors_dict: dict
        """
        from mxcubecore.model.queue_model_objects import CentredPosition

        if isinstance(motor_positions, CentredPosition):
            motor_positions_copy = motor_positions.as_dict()
        else:
            # We do not want ot modify teh input dict
            motor_positions_copy = motor_positions.copy()

        logging.getLogger("HWR").debug(
            "MiniDiff moving motors. %s" % str(motor_positions_copy)
        )

        self.wait_device_ready(timeout)
        logging.getLogger("HWR").debug("   now ready to move them")
        for motor in motor_positions_copy.keys():
            position = motor_positions_copy[motor]
            if type(motor) in (str, unicode):
                motor_role = motor
                motor = self.motor_hwobj_dict.get(motor_role)
                del motor_positions_copy[motor_role]
                if None in (motor, position):
                    continue
                motor_positions_copy[motor] = position

            logging.getLogger("HWR").debug(
                "  / moving motor. %s to %s" % (motor.name(), position)
            )
            self.wait_device_ready(timeout)
            try:
                motor.set_value(position, timeout=None)
            except Exception:
                import traceback

                logging.getLogger("HWR").debug(
                    "  / error moving motor on diffractometer. state is %s"
                    % (self.smargon_state)
                )
                logging.getLogger("HWR").debug("     / %s " % traceback.format_exc())

        self.wait_device_ready(timeout)
