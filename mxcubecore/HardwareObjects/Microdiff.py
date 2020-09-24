import logging
import math
import time
from HardwareRepository.HardwareObjects import MiniDiff
import gevent
from HardwareRepository.HardwareObjects import sample_centring
from HardwareRepository import HardwareRepository as HWR

MICRODIFF = None


class Microdiff(MiniDiff.MiniDiff):
    def init(self):
        global MICRODIFF
        MICRODIFF = self
        self.phiMotor = self.get_object_by_role("phi")
        self.exporter_addr = self.get_property("exporter_address")

        self.x_calib = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "x_calib",
            },
            "CoaxCamScaleX",
        )
        self.y_calib = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "y_calib",
            },
            "CoaxCamScaleY",
        )
        self.moveMultipleMotors = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "move_multiple_motors",
            },
            "SyncMoveMotors",
        )
        self.head_type = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "head_type",
            },
            "HeadType",
        )
        self.kappa_channel = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "kappa_enable",
            },
            "KappaIsEnabled",
        )
        self.phases = {
            "Centring": 1,
            "BeamLocation": 2,
            "DataCollection": 3,
            "Transfer": 4,
        }
        self.movePhase = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "move_to_phase",
            },
            "startSetPhase",
        )
        self.readPhase = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "read_phase",
            },
            "CurrentPhase",
        )
        self.scanLimits = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "scan_limits",
            },
            "getOmegaMotorDynamicScanLimits",
        )
        if self.get_property("use_hwstate"):
            self.hwstate_attr = self.add_channel(
                {
                    "type": "exporter",
                    "exporter_address": self.exporter_addr,
                    "name": "hwstate",
                },
                "HardwareState",
            )
        else:
            self.hwstate_attr = None
        self.swstate_attr = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "swstate",
            },
            "State",
        )
        self.nb_frames = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "nbframes",
            },
            "ScanNumberOfFrames",
        )

        # raster scan attributes
        self.scan_range = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "scan_range",
            },
            "ScanRange",
        )
        self.scan_exposure_time = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "exposure_time",
            },
            "ScanExposureTime",
        )
        self.scan_start_angle = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "start_angle",
            },
            "ScanStartAngle",
        )
        self.scan_detector_gate_pulse_enabled = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "detector_gate_pulse_enabled",
            },
            "DetectorGatePulseEnabled",
        )
        self.scan_detector_gate_pulse_readout_time = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "detector_gate_pulse_readout_time",
            },
            "DetectorGatePulseReadoutTime",
        )

        self.abort_cmd = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "abort",
            },
            "abort",
        )

        self._move_sync_motors = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "move_sync_motors",
            },
            "startSimultaneousMoveMotors",
        )

        self.beam_position_horizontal = self.add_channel(
            {"type": "exporter", "exporter_address": self.exporter_addr, "name": "bph"},
            "BeamPositionHorizontal",
        )

        self.beam_position_vertical = self.add_channel(
            {"type": "exporter", "exporter_address": self.exporter_addr, "name": "bpv"},
            "BeamPositionVertical",
        )

        self.save_centring_positions = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "abort",
            },
            "saveCentringPositions",
        )

        MiniDiff.MiniDiff.init(self)
        self.centringPhiy.direction = -1
        self.MOTOR_TO_EXPORTER_NAME = self.getMotorToExporterNames()
        self.move_to_coord = self.move_to_beam

        self.centringVertical = self.get_object_by_role("centringVertical")
        self.centringFocus = self.get_object_by_role("centringFocus")

        self.frontLight = self.get_object_by_role("FrontLight")
        self.backLight = self.get_object_by_role("BackLight")

        self.wait_ready = self._wait_ready
        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(None)

    def getMotorToExporterNames(self):
        MOTOR_TO_EXPORTER_NAME = {
            "focus": self.focusMotor.get_property("actuator_name"),
            "kappa": self.kappaMotor.get_property("actuator_name"),
            "kappa_phi": self.kappaPhiMotor.get_property("actuator_name"),
            "phi": self.phiMotor.get_property("actuator_name"),
            "phiy": self.phiyMotor.get_property("actuator_name"),
            "phiz": self.phizMotor.get_property("actuator_name"),
            "sampx": self.sampleXMotor.get_property("actuator_name"),
            "sampy": self.sampleYMotor.get_property("actuator_name"),
            "zoom": "Zoom",
        }
        return MOTOR_TO_EXPORTER_NAME

    def getCalibrationData(self, offset):
        return (1.0 / self.x_calib.get_value(), 1.0 / self.y_calib.get_value())

    def emitCentringSuccessful(self):
        # check first if all the motors have stopped
        self._wait_ready(10)

        # save position in MD2 software
        self.save_centring_positions()

        # do normal stuff
        return MiniDiff.MiniDiff.emitCentringSuccessful(self)

    def _ready(self):
        if self.hwstate_attr:
            if (
                self.hwstate_attr.get_value() == "Ready"
                and self.swstate_attr.get_value() == "Ready"
            ):
                return True
        else:
            if self.swstate_attr.get_value() == "Ready":
                return True
        return False

    def _wait_ready(self, timeout=None):
        # None means infinite timeout
        # <=0 means default timeout
        if timeout is not None and timeout <= 0:
            timeout = self.timeout
        with gevent.Timeout(
            timeout, RuntimeError("Timeout waiting for diffractometer to be ready")
        ):
            while not self._ready():
                time.sleep(0.5)

    def set_phase(self, phase, wait=False, timeout=None):
        if self._ready():
            if phase in self.phases:
                self.movePhase(phase)
                if wait:
                    if not timeout:
                        timeout = 40
                    self._wait_ready(timeout)
        else:
            print("moveToPhase - Ready is: ", self._ready())

    def get_current_phase(self):
        return self.readPhase.get_value()

    def get_phase_list(self):
        return list(self.phases.keys())

    def move_sync_motors(self, motors_dict, wait=False, timeout=None):
        in_kappa_mode = self.in_kappa_mode()
        argin = ""
        # print "start moving motors =============", time.time()
        if wait:
            self._wait_ready()
        for motor in motors_dict.keys():
            position = motors_dict[motor]
            if position is None:
                continue
            name = self.MOTOR_TO_EXPORTER_NAME[motor]
            if not in_kappa_mode and motor in ("kappa", "kappa_phi"):
                continue
            argin += "%s=%0.3f;" % (name, position)
        if not argin:
            return

        self._move_sync_motors(argin)

        if wait:
            time.sleep(0.1)
            self._wait_ready()
        # print "end moving motors =============", time.time()

    def oscilScan(self, start, end, exptime, wait=False):
        if self.in_plate_mode():
            scan_speed = math.fabs(end - start) / exptime
            low_lim, hi_lim = map(float, self.scanLimits(scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            elif end > hi_lim:
                raise ValueError("Scan end abobe the allowed value %f" % hi_lim)

        self.nb_frames.set_value(1)
        scan_params = "1\t%0.3f\t%0.3f\t%0.4f\t1" % (start, (end - start), exptime)
        scan = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "start_scan",
            },
            "startScanEx",
        )
        scan(scan_params)
        print("oscil scan started at ----------->", time.time())
        if wait:
            self._wait_ready(
                600
            )  # timeout of 10 min # Changed on 20180406 Daniele, because of long exposure time set by users
            print("finished at ---------->", time.time())

    def oscilScan4d(self, start, end, exptime, motors_pos, wait=False):
        if self.in_plate_mode():
            scan_speed = math.fabs(end - start) / exptime
            low_lim, hi_lim = map(float, self.scanLimits(scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            elif end > hi_lim:
                raise ValueError("Scan end abobe the allowed value %f" % hi_lim)
        self.nb_frames.set_value(1)
        scan_params = "%0.3f\t%0.3f\t%f\t" % (start, (end - start), exptime)
        scan_params += "%0.3f\t" % motors_pos["1"]["phiy"]
        scan_params += "%0.3f\t" % motors_pos["1"]["phiz"]
        scan_params += "%0.3f\t" % motors_pos["1"]["sampx"]
        scan_params += "%0.3f\t" % motors_pos["1"]["sampy"]
        scan_params += "%0.3f\t" % motors_pos["2"]["phiy"]
        scan_params += "%0.3f\t" % motors_pos["2"]["phiz"]
        scan_params += "%0.3f\t" % motors_pos["2"]["sampx"]
        scan_params += "%0.3f" % motors_pos["2"]["sampy"]

        scan = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "start_scan4d",
            },
            "startScan4DEx",
        )

        scan(scan_params)

        print("helical scan started at ----------->", time.time())
        if wait:
            self._wait_ready(900)  # timeout of 15 min
            print("finished at ---------->", time.time())

    def oscilScanMesh(
        self,
        start,
        end,
        exptime,
        dead_time,
        mesh_num_lines,
        mesh_total_nb_frames,
        mesh_center,
        mesh_range,
        wait=False,
    ):
        self.scan_detector_gate_pulse_enabled.set_value(True)

        # Adding the servo time to the readout time to avoid any
        # servo cycle jitter
        servo_time = 0.110

        self.scan_detector_gate_pulse_readout_time.set_value(
            dead_time * 1000 + servo_time
        )

        self.move_motors(mesh_center.as_dict())
        positions = self.get_positions()

        params = "%0.3f\t" % (end - start)
        params += "%0.3f\t" % -mesh_range["horizontal_range"]
        params += "%0.3f\t" % mesh_range["vertical_range"]
        params += "%0.3f\t" % start
        params += "%0.3f\t" % positions["phiy"]
        params += "%0.3f\t" % positions["phiz"]
        params += "%0.3f\t" % positions["sampx"]
        params += "%0.3f\t" % positions["sampy"]
        params += "%d\t" % mesh_num_lines
        params += "%d\t" % (mesh_total_nb_frames / mesh_num_lines)
        params += "%0.3f\t" % (exptime / mesh_num_lines)
        params += "%r\t" % True
        params += "%r\t" % True
        params += "%r\t" % self.getProperty("use_fast_mesh", True)

        scan = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "start_raster_scan",
            },
            "startRasterScanEx",
        )

        self._wait_ready(900)  # timeout of 15 min

        scan(params)

        if wait:
            # timeout of 30 min
            self._wait_ready(1800)

    def stillScan(self, pulse_duration, pulse_period, pulse_nb, wait=False):
        scan_params = "%0.6f\t%0.6f\t%d" % (pulse_duration, pulse_period, pulse_nb)
        scan = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "start_scan",
            },
            "startStillScan",
        )
        scan(scan_params)
        print("still scan started at ----------->", time.time())
        if wait:
            self._wait_ready(1800)  # timeout of 30 min
            print("finished at ---------->", time.time())

    def in_plate_mode(self):
        try:
            return self.head_type.get_value() == "Plate"
        except BaseException:
            return False

    def in_kappa_mode(self):
        return (
            self.head_type.get_value() == "MiniKappa" and self.kappa_channel.get_value()
        )

    def get_positions(self):
        pos = {
            "phi": float(self.phiMotor.get_value()),
            "focus": float(self.focusMotor.get_value()),
            "phiy": float(self.phiyMotor.get_value()),
            "phiz": float(self.phizMotor.get_value()),
            "sampx": float(self.sampleXMotor.get_value()),
            "sampy": float(self.sampleYMotor.get_value()),
            "zoom": self.zoomMotor.get_value().value,
            "kappa": float(self.kappaMotor.get_value())
            if self.in_kappa_mode()
            else None,
            "kappa_phi": float(self.kappaPhiMotor.get_value())
            if self.in_kappa_mode()
            else None,
        }
        return pos

    def move_motors(self, roles_positions_dict):
        self.move_sync_motors(roles_positions_dict, wait=True)

    def move_to_beam(self, x, y):
        if not self.in_plate_mode():
            MiniDiff.MiniDiff.move_to_beam(self, x, y)
        else:
            try:
                beam_pos_x, beam_pos_y = HWR.beamline.beam.get_beam_position_on_screen()

                self.centringVertical.set_value_relative(
                    self.centringPhiz.direction
                    * (y - beam_pos_y)
                    / float(self.pixelsPerMmZ)
                )
                self.centringPhiy.set_value_relative(
                    self.centringPhiy.direction
                    * (x - beam_pos_x)
                    / float(self.pixelsPerMmY)
                )

            except BaseException:
                logging.getLogger("user_level_log").exception(
                    "Microdiff: could not move to beam, aborting"
                )

    def start_manual_centring(self, sample_info=None):
        beam_pos_x, beam_pos_y = HWR.beamline.beam.get_beam_position_on_screen()
        if self.in_plate_mode():
            plateTranslation = self.get_object_by_role("plateTranslation")
            cmd_set_plate_vertical = self.add_command(
                {
                    "type": "exporter",
                    "exporter_address": self.exporter_addr,
                    "name": "plate_vertical",
                },
                "setPlateVertical",
            )
            low_lim, high_lim = self.phiMotor.get_dynamic_limits()
            phi_range = math.fabs(high_lim - low_lim - 1)
            self.current_centring_procedure = sample_centring.start_plate_1_click(
                {
                    "phi": self.centringPhi,
                    "phiy": self.centringPhiy,
                    "sampx": self.centringSamplex,
                    "sampy": self.centringSampley,
                    "phiz": self.centringVertical,
                    "plateTranslation": plateTranslation,
                },
                self.pixelsPerMmY,
                self.pixelsPerMmZ,
                beam_pos_x,
                beam_pos_y,
                cmd_set_plate_vertical,
                low_lim + 0.5,
                high_lim - 0.5,
            )
        else:
            self.current_centring_procedure = sample_centring.start(
                {
                    "phi": self.centringPhi,
                    "phiy": self.centringPhiy,
                    "sampx": self.centringSamplex,
                    "sampy": self.centringSampley,
                    "phiz": self.centringPhiz,
                },
                self.pixelsPerMmY,
                self.pixelsPerMmZ,
                beam_pos_x,
                beam_pos_y,
                chi_angle=self.chiAngle,
            )

        self.current_centring_procedure.link(self.manualCentringDone)

    def interrupt_and_accept_centring(self):
        """ Used when plate. Kills the current 1 click centring infinite loop
        and accepts fake centring - only save the motor positions
        """
        self.current_centring_procedure.kill()
        self.do_centring = False
        self.start_centring_method(self, self.MANUAL3CLICK_MODE)
        self.do_centring = True

    def getFrontLightLevel(self):
        return self.frontLight.get_value()

    def setFrontLightLevel(self, level):
        return self.frontLight.set_value(level)

    def getBackLightLevel(self):
        return self.backLight.get_value()

    def setBackLightLevel(self, level):
        return self.backLight.set_value(level)

    def get_beam_position(self):
        return (
            self.beam_position_horizontal.get_value(),
            self.beam_position_vertical.get_value(),
        )


def set_light_in(light, light_motor, zoom):
    self.frontlight.set_value(0)
    MICRODIFF.get_object_by_role("BackLightSwitch").actuatorIn()


MiniDiff.set_light_in = set_light_in


def to_float(d):
    for k, v in d.items():
        try:
            d[k] = float(v)
        except BaseException:
            pass
