# encoding: utf-8
#
#  Project name: MXCuBE
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Micro Diffractometer implementation of the AbstractDiffractometer class."""
import time


from gevent import Timeout, sleep

from mxcubecore import HardwareRepository as HWR
from mxcubecore.Command.Exporter import Exporter
from mxcubecore.Command.exporter.ExporterStates import ExporterStates
from mxcubecore.HardwareObjects.abstract.AbstractDiffractometer import (
    AbstractDiffractometer,
    DiffractometerConstraint,
    DiffractometerHead,
    DiffractometerPhase,
)

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class MicroDiffractometer(AbstractDiffractometer):
    """Microdiff with Exporter implementation of AbstractDiffractometer"""

    def __init__(self, name):
        super().__init__(name)
        self._exporter = None

    def init(self):
        """Initialise the device"""
        super().init()
        exporter_address = self.get_property("exporter_address")
        _host, _port = exporter_address.split(":")
        self._exporter = Exporter(_host, int(_port))
        self.head_type = self._head_type

        # add the custom commands
        for nam, cmd in self.get_property("commands").items():
            _cmd = {
                "type": "exporter",
                "exporter_address": exporter_address,
                "name": nam,
            }
            setattr(self, nam, self.add_command(_cmd, cmd))

        # add the custom channels
        for nam, attr in self.get_property("channels").items():
            _attr = {
                "type": "exporter",
                "exporter_address": exporter_address,
                "name": nam,
            }
            setattr(self, nam, self.add_channel(_attr, attr))

        self.update_state()

        # we must have global_state and phase_channel channels configured
        try:
            self.phase_channel.connect_signal("update", self.update_phase)
            self.global_state.connect_signal("update", self._update_state)
        except AttributeError:
            self.log.exception("global_state and phase_channel not configured!")

    def abort(self):
        """Immediately terminate action."""
        self._exporter.execute("abort")

    @property
    def _get_hwstate(self) -> str:
        """Get the hardware state, reported by the MD2 application.

        Returns:
            The state.
        """
        try:
            return self._exporter.read_property("HardwareState")
        except AttributeError:
            return "Ready"

    @property
    def _get_swstate(self) -> str:
        """Get the software state, reported by the MD2 application.

        Returns:
            The state.
        """
        return self.global_state.get_value()

    def _update_state(self, value):
        if isinstance(value, str):
            self.update_state(self.get_state())
        else:
            self.update_state(value)

    def get_state(self):
        """Get the diffractometer general state.

        Returns:
            (enum 'HardwareObjectState'): state
        """
        try:
            return ExporterStates[self._get_swstate.upper()].value
        except ValueError:
            return self.STATES.UNKNOWN

    @property
    def _ready(self) -> bool:
        """Get the "Ready" state - software and hardware.

        Returns:
            True if both "Ready", False otherwise.
        """
        return self._get_swstate == "Ready" and self._get_hwstate == "Ready"

    def wait_status_ready(self, timeout: float | None = None):
        """Wait timeout seconds until status is ready.

        Args:
            Timeout [s]. None means infinite timeout.
        """
        with Timeout(timeout, RuntimeError("Timeout waiting for status ready")):
            while not self._ready:
                sleep(0.5)

    def set_value_motors(
        self,
        motors_positions_dict: dict[str, float],
        simultaneous: bool = True,
        timeout: float | None = None,
    ):
        """Move specified motors to the requested positions.

        Args:
            motors_positions_dict (dict): Dictionary {motor_role: target_value}.
            simultaneous: Move the motors simultaneously (True - default) or not.
            timeout: optional - timeout [s],
                     if timeout = 0: return at once and do not wait,
                     if timeout is None: wait forever (default).

        Raises:
            TimeoutError: Timeout
            KeyError: The name does not correspond to an existing motor
        """
        if not simultaneous:
            super().set_value_motors(motors_positions_dict, simultaneous, timeout)
        else:
            # prepare the command
            cmd = ""
            for role, pos in motors_positions_dict.items():
                name = self.motors_hwobj_dict[role].actuator_name
                cmd += f"{name}={pos:0.3f};"
            self._exporter.execute("startSimultaneousMoveMotors", (cmd,))
            if timeout != 0:
                self.wait_status_ready(timeout)
            self.update_state()

    def get_value_motors(self, motors_list: [list | None] = None) -> dict[str, float]:
        """Get the positions of diffractometer motors. If the motors_list
           is empty, return the positions of all the availble motors.

        Args:
            motors_list: List of motor roles.

        Returns:
            Dictionary {role: position}.
        """
        motors_positions_dict = super().get_value_motors(motors_list)
        if not self.in_kappa_mode:
            motors_positions_dict.update({"kappa": None, "kappa_phi": None})
        return motors_positions_dict

    def get_motors(self):
        """Get the dictionary of all the motors which can be used.

        Returns:
            Ddctionary {role: hardware_object}.
        """

        def find_elem(ddict, val):
            """Find dictionary elemnt from motor actuator_name"""
            for role, hwobj in ddict.items():
                if hwobj.actuator_name == val:
                    return {role: hwobj}
            return {}

        motors = self._exporter.read_property("MotorStates")
        motors_dict = {}
        for mot in motors:
            mot_stat = mot.split("=")
            if mot_stat[1] not in ("Disable", "Unknown"):
                elem = find_elem(self.motors_hwobj_dict, mot_stat[0])
                motors_dict.update(elem)

        return motors_dict

    @property
    def _head_type(self) -> DiffractometerHead:
        """Get the head type."""
        try:
            self.head_type = DiffractometerHead(
                self._exporter.read_property("HeadType")
            )
        except ValueError:
            self.head_type = DiffractometerHead.UNKNOWN
        return self.head_type

    def _set_phase(self, value: DiffractometerPhase):
        """Specific implementation to set the diffractometer to selected phase.

        Args:
            value: requested phase.
        """
        _use_custom = self.get_property("use_custom_phase_script") or False
        current_phase = self.get_phase()

        if value != current_phase:
            msg = f"Current phase is {current_phase} and moving to {value}"
            self.log.info(msg)

        # protect the detector or open the cover if detector cover defined
        # do not wait it to finish.
        det_cover = self.get_object_by_role("detector_cover")
        if det_cover:
            if value in (DiffractometerPhase.TRANSFER, DiffractometerPhase.SEE_BEAM):
                det_cover.set_value(det_cover.detector_cover.VALUES.CLOSE, timeout=0)
            if value == DiffractometerPhase.COLLECT:
                det_cover.set_value(det_cover.detector_cover.VALUES.OPEN, timeout=0)

        if _use_custom and not self.in_plate_mode:
            script = "ChangePhase_" + value.value.lower()
            msg = f"Changing phase to {value.value}, using pmac script"
            self.log.info(msg)
            self.run_custom_script(script)
        else:
            self._exporter.execute("startSetPhase", (value.value,))
        self.wait_status_ready(timeout=600)

    def get_phase(self) -> DiffractometerPhase:
        """Get the current phase."""
        value = self.phase_channel.get_value()
        try:
            self.current_phase = DiffractometerPhase(value)
        except ValueError:
            self.current_phase = DiffractometerPhase.UNKNOWN
        return self.current_phase

    def _set_constraint(self, value: DiffractometerConstraint):
        """Specific implementation to set the diffractometer to selected constraint
        Args:
            value: requested constraint.
        """
        self._exporter.execute("startSetMode", (value.value,))

    def get_constraint(self) -> DiffractometerConstraint:
        """Get the diffrractometer constraint type."""
        value = self._exporter.read_property("CurrentMode")
        try:
            self.current_constraint = DiffractometerConstraint(value)
        except ValueError:
            self.current_constraint = DiffractometerConstraint.UNKNOWN
        return self.current_constraint

    def check_scan_limits(self, start: float, end: float, exptime: float) -> bool:
        """Check if the scan parameters are within the limits

        Args:
            start: scan start position.
            end: scan end position.
            exptime: scan exposure time (total) [s].

        Returns:
            True (parameters within the limits), False otherwise.
        """
        if self.in_plate_mode:
            scan_speed = abs(end - start) / exptime
            llim, hlim = map(
                float,
                self._exporter.execute("getOmegaMotorDynamicScanLimits", (scan_speed,)),
            )
            if start < llim:
                msg = f"Scan start below the allowed value {llim}"
                raise ValueError(msg)
            if end > hlim:
                msg = f"Scan end above the allowed value {hlim}"
                raise ValueError(msg)
        return True

    def do_oscillation_scan(
        self,
        start: float,
        end: float,
        exptime: float,
        number_of_images: int = 1,
        timeout: float | None = None,
    ):
        """Do an oscillation scan on omega.

        Args:
            start: omega start position.
            end: omega end position.
            exptime: scan exposure time (total).
            number_of_images: Used if need to set number of frames.
            timeout: optional - timeout [s],
                     if timeout = 0: return at once and do not wait,
                     if timeout is None: wait forever (default).

        Raises:
            RuntimeError: Timeout waiting for status ready.
            ValueError: Scan parameters not within limits (if relevant).
        """
        # check the scan limits
        self.check_scan_limits(start, end, exptime)
        # set the number of frames
        if not self.get_property("md_set_number_of_frames"):
            number_of_images = 1
        self._exporter.write_property("ScanNumberOfFrames", number_of_images)
        scan_params = f"1\t{start:0.3f}\t{(end - start):0.3f}\t{exptime:0.3f}\t1"
        self._exporter.execute("startScanEx", (scan_params,))
        self.wait_status_ready(timeout)

    def do_line_scan(
        self,
        start: float,
        end: float,
        exptime: float,
        number_of_images: int,
        motors_pos: dict[str, dict],
        timeout: float | None = None,
    ):
        """Do helical (line) scan on omega.
        Args:
            start: scan start position.
            end: scan end position.
            exptime: scan exposure time (total).
            number_of_images: Used only if more tahn one frame needed.
            timeout: optional - timeout [s],
                     if timeout = 0: return at once and do not wait,
                     if timeout is None: wait forever (default).
            motors_pos: {"1": [centred position], "2": [centred position]}

        Raises:
            RuntimeError: Timeout waiting for status ready.
            ValueError: Scan parameters not within limits (if relevant).
        """
        # check the scan limits
        self.check_scan_limits(start, end, exptime)
        if not self.get_property("md_set_number_of_frames"):
            number_of_images = 1

        self._exporter.write_property("ScanNumberOfFrames", number_of_images)

        scan_params = f"{start:0.3f}\t{(end - start):0.3f}\t{exptime:0.3f}\t"
        for name in ["phiy", "phiz", "sampx", "sampy"]:
            scan_params += f"{motors_pos['1'][name]:0.3f}\t"
        for name in ["phiy", "phiz", "sampx", "sampy"]:
            scan_params += f"{motors_pos['2'][name]:0.3f}\t"

        self._exporter.execute("startScan4DEx", (scan_params,))
        self.wait_status_ready(timeout)

    def do_mesh_scan(
        self,
        start: float,
        end: float,
        exptime: float,
        dead_time: float,
        nb_lines: int,
        nb_frames_total: int,
        grid_centre: list[tuple[str, float]],
        mesh_range: dict,
        timeout: float | None = None,
    ):
        """Do a mesh scan.

        Args:
            start: scan start position.
            end: scan end position.
            exptime: scan exposure time (total).
            dead_time: Dead time between the pulses. Detector dependant.
            nb_lines: Total number of lines.
            nb_frames_total: Total number of frames.
            grid_centre: List of tuples (motor_role, position).
                         representing the centre of the mesh grid.
            mesh_range: Horizontal and vertical range.
            timeout: optional - timeout [s],
                     if timeout = 0: return at once and do not wait,
                     if timeout is None: wait forever (default).

        Raises:
            RuntimeError: Timeout waiting for status ready.
        """

        # enable gate pulses
        self._exporter.write_property("DetectorGatePulseEnabled", value=True)

        # dead_time depends on the detector. We transform it to us
        dead_time = dead_time or HWR.beamline.detector.get_deadtime() * 1000
        self._exporter.write_property("DetectorGatePulseReadoutTime", dead_time)

        grid_centre = grid_centre.as_dict()
        self.set_value_motors(grid_centre, simultaneous=True, timeout=timeout)

        scan_params = f"{(end - start):0.3f}\t"
        scan_params += f"{-mesh_range['horizontal_range']:0.3f}\t"
        scan_params += f"{mesh_range['vertical_range']:0.3f}\t"
        scan_params += f"{start:0.3f}\t"
        for name in ["phiy", "phiz", "sampx", "sampy"]:
            for key, val in grid_centre.items():
                if name == key:
                    scan_params += f"{float(val):0.3f}\t"
        scan_params += f"{nb_lines}\t"
        scan_params += f"{nb_frames_total / nb_lines}\t"
        scan_params += f"{exptime / nb_lines}\t"
        scan_params += "True\tTrue\tTrue\t"
        self._exporter.execute("startRasterScanEx", (scan_params,))
        self.wait_status_ready(timeout)

    def do_still_scan(
        self,
        pulse_duration: float,
        pulse_period: float,
        nb_pulse: int,
        timeout: [None | float] = None,
    ):
        """Do a zero oscillation acquisition.

        Args:
            pulse_duration: Duration of the pulse sent to the detector.
            pulse_period: The period of the pulse sent to the detector.
            nb_pulse: Number of pulses to be sent.
            timeout: optional - timeout [s],
                     if timeout = 0: return at once and do not wait,
                     if timeout is None: wait forever (default).

        Raises:
            RuntimeError: Timeout waiting for status ready.
        """
        scan_params = f"{pulse_duration:0.6f}\t{pulse_period:0.6f}\t{nb_pulse}"
        self._exporter.execute("startStillScan", (scan_params,))
        self.wait_status_ready(timeout)

    def do_characterisation_scan(
        self,
        start: float,
        scan_range: float,
        nb_frames: int,
        exptime: float,
        nb_scans: int,
        angle: float,
        timeout: float | None = None,
    ):
        """Do fast characterisation.
        Args:
            start: Position of omega for the first scan [deg].
            scan_range: range for each scan [deg].
            nb_frames: Frame numbers for each scan.
            exptime: Total exposure time for each scan [s].
            nb_scans: How many times a scan to be repeated.
            angle: The angle between each scan [deg]. This number,
                   added to the last position of each scan and will
                   be the start position of the following scan.
            timeout (float): optional - timeout [s],
                             if timeout = 0: return at once and do not wait,
                             if timeout is None: wait forever (default).

        Raises:
            RuntimeError: Timeout waiting for status ready.
        """

        if self.in_plate_mode:
            # to see if needed when plates
            return

        scan_params = f"{nb_frames}\t{start:0.3f}\t{scan_range:0.3f}\t"
        scan_params += f"{exptime:0.3f}\t{nb_scans}\t{angle:0.3f}"
        self._exporter.execute("startCharacterisationScanEx", (scan_params,))
        if timeout:
            # min timeout is 20 min
            timeout = max(timeout, 20 * 60)

        self.wait_status_ready(timeout)

    def get_pixels_per_mm(self) -> tuple[int, int]:
        """Get the pixel/mm values.

        Returns:
            (x ,y) [pixel/mm]
        """
        x_calib = self._exporter.read_property("CoaxCamScaleX")
        y_calib = self._exporter.read_property("CoaxCamScaleY")
        return 1.0 / x_calib, 1.0 / y_calib

    def get_beam_position(self) -> tuple:
        """Get the beam position defined in MD"""
        return (
            self.beam_position_horizontal.get_value(),
            self.beam_position_vertical.get_value(),
        )

    def run_custom_script(self, script_cmd: str, timeout: float | None = None):
        """Run custom script."""
        self.run_script(script_cmd)
        # Wait for script to start before checking status,
        # can perhaps be improved to wait for ready-busy-ready ?
        time.sleep(0.4) 
        self.wait_status_ready(timeout)
