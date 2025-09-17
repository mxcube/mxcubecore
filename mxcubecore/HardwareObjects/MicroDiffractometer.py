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

from gevent import Timeout, sleep

from mxcubecore.Command.Exporter import Exporter, ExporterStates
from mxcubecore.HardwareObjects.abstract.AbstractDiffractometer import (
    AbstractDiffractometer,
    DiffractometerHead,
    DiffractometerPhase,
)

__copyright__ = """ Copyright © 2010-2022 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class MicroDiffractometer(AbstractDiffractometer):
    """Microdiff with Exporter implementation of AbstartDiffractometer"""

    def __init__(self, name):
        super().__init__(name)
        self._exporter = None

    def init(self):
        """Initialise the device"""
        super().init()
        # Initialise the commands and channels
        exporter_address = self.get_property("exporter_address")
        _host, _port = exporter_address.split(":")
        self._exporter = Exporter(_host, int(_port))
        self.update_state(self.get_state())

    def abort(self):
        """Immediately terminate action."""
        self._exporter.execute("abort")

    @property
    def _get_hwstate(self) -> str:
        """Get the hardware state, reported by the MD2 application.
        Returns:
            (str): The state.
        """
        try:
            return self._exporter.read_property("HardwareState")
        except AttributeError:
            return "Ready"

    @property
    def _get_swstate(self) -> str:
        """Get the software state, reported by the MD2 application.
        Returns:
            (str): The state.
        """
        return self._exporter.read_property("State")

    def get_state(self):
        """Get the diffractometer general state.
        Returns:
            (enum 'HardwareObjectState'): state
        """
        try:
            self._state = ExporterStates(self._get_swstate)
        except ValueError:
            self._state = self.STATES.UNKNOWN
        return self._state

    @property
    def _ready(self) -> bool:
        """Get the "Ready" state - software and hardware.
        Returns:
            (bool): True if both "Ready", False otherwise.
        """
        return self._get_swstate == "Ready" and self._get_hwstate == "Ready"

    def _wait_ready(self, timeout: [None | float] = None):
        """Wait timeout seconds until status is ready.
        Args:
            timeout(float): Timeout [s]. None means infinite timeout.
        """
        with Timeout(timeout, RuntimeError("Timeout waiting for status ready")):
            while not self._ready:
                sleep(0.5)

    def set_values_motors(
        self,
        motors_positions_list: list,
        timeout: [None | float] = None,
    ):
        """Move specified motors to the requested positions.
        Args:
            motors_positions_list (list): list of tuples (motor role, target value).
            timeout (float): optional - timeout [s],
                             If timeout = 0: return at once and do not wait
                             if timeout is None: wait forever (default).
        Raises:
            TimeoutError: Timeout
            KeyError: The name does not correspond to an existing motor
        """
        # prepare the command
        argin = ""
        for mot, pos in motors_positions_list:
            name = self.motors_hwobj[mot].name
            argin += f"{name}={pos:0.3f};"

        self._exporter.execute("startSimultaneousMoveMotors", (argin,))
        if timeout != 0:
            self.wait_ready(timeout)

    def get_values_motors(self, motors_list: [list | None] = None) -> dict:
        """Get the positions of diffractometer motors. If the
            motors_positions_list is empty, return the positions of all
            the availble motors
        Args:
            motors_list (list): List of motor names or hwobj
        Returns:
            motors_positions_dict (dict): role: position dictionary
        """
        motors_positions_dict = super().get_values_motors(self, motors_list)
        if not self.in_kappa_mode():
            motors_positions_dict["kappa"] = None
            motors_positions_dict["kappa_phi"] = None
        return motors_positions_dict

    @property
    def get_head_type(self) -> DiffractometerHead:
        """Get the head type
        Returns:
            head_type(enum): Head type
        """
        try:
            self.head_type = DiffractometerHead(
                self._exporter.read_property("HeadType")
            )
        except ValueError:
            self.head_type = DiffractometerHead.UNKNOWN
        return self.head_type

    def _set_phase(self, phase: DiffractometerPhase):
        """Specific implementation to set the diffractometer to selected phase
        Args:
            phase (Enum): DiffractometerPhase value.
        """
        self._exporter.execute("startSetPhase", (phase.value,))

    def get_phase(self) -> DiffractometerPhase:
        """Get the current phase
        Returns:
            (Enum): DiffractometerPhase value.
        """
        phase = self._exporter.read_property("CurrentPhase")
        try:
            self.current_phase = DiffractometerPhase(phase)
        except ValueError:
            self.current_phase = DiffractometerPhase.UNKNOWN
        return self.current_phase

    def get_phase_list(self) -> list:
        """Get the available phases list."""
        phase_list = []
        for member in DiffractometerPhase:
            _nam = member.name
            if _nam not in ["IN", "OUT", "UNKNOWN"]:
                phase_list.append(_nam)
        return phase_list

    def get_pixels_per_mm(self) -> tuple:
        """Get the pixel/mm values.
        Returns:
            (tuple): x,y [pixel/mm]
        """
        x_calib = self._exporter.read_property("CoaxCamScaleX")
        y_calib = self._exporter.read_property("CoaxCamScaleY")
        return 1.0 / x_calib, 1.0 / y_calib

    def check_scan_limits(self, start: float, end: float, exptime: float) -> bool:
        """Check if the scan parameters are within the limits
        Args:
            start (float): scan start position.
            end (float): scan end position.
            exptime (float): scan exposure time (total).
        Returns:
            (bool): True (parameters within the limits), False otherwise.
        """
        if self.in_plate_mode():
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
        self, start: float, end: float, exptime: float, timeout: [None | float] = None
    ):
        """Do an oscillation scan on omega.
        Args:
            start (float): scan start position.
            end (float): scan end position.
            exptime (float): scan exposure time (total).
            timeout (float): optional - timeout [s],
                             If timeout = 0: return at once and do not wait
                             if timeout is None: wait forever (default).
        Raises:
            RuntimeError: Timeout waiting for status ready.
            ValueError: Scan parameters not within limits (if relevant).
        """
        # check the scan limits
        self.check_scan_limits(start, end, exptime)
        # set only one frame
        self._exporter.write_property("ScanNumberOfFrames", 1)
        scan_params = f"1\t{start:0.3f}\t{(end - start):0.3f}\t{exptime:0.3f}\t1"
        self._exporter.execute("startScanEx", (scan_params,))
        self._wait_ready(timeout)

    def do_line_scan(self, start, end, exptime, motors_pos, timeout=None):
        """Do helical (line) scan on omega.
        Args:
            start (float): scan start position.
            end (float): scan end position.
            exptime (float): scan exposure time (total).
            timeout (float): optional - timeout [s],
                             If timeout = 0: return at once and do not wait
                             if timeout is None: wait forever (default).
        Raises:
            RuntimeError: Timeout waiting for status ready.
            ValueError: Scan parameters not within limits (if relevant).
        """
        # check the scan limits
        self.check_scan_limits(start, end, exptime)
        # set only one frame
        self._exporter.write_property("ScanNumberOfFrames", 1)
        scan_params = f"{start:0.3f}\t{(end - start):0.3f}\t{exptime:0.3f}\t"
        for name in ["phiy", "phiz", "sampx", "sampy"]:
            scan_params += f"{motors_pos['1'][name]:0.3f}"
        for name in ["phiy", "phiz", "sampx", "sampy"]:
            scan_params += f"{motors_pos['2'][name]:0.3f}"

        self._exporter.execute("startScan4DEx", (scan_params,))
        self._wait_ready(timeout)

    def do_mesh_scan(
        self,
        start: float,
        end: float,
        exptime: float,
        nb_lines: int,
        nb_frames_total: int,
        grid_centre: list,
        mesh_range: dict,
        dead_time: float = 0,
        timeout: [None | float] = None,
    ):
        """Do a mesh scan.
        Args:
            start (float): scan start position.
            end (float): scan end position.
            exptime (float): scan exposure time (total).
            nb_lines (int): Total number of lines.
            nb_frames_total (int): Total number of frames
            grid_centre (list): List of tuples (motor_role, position)
                                representing the centre of the mesh grid.
            mesh_range (dict): Hirizontal and vertical range.
            dead_time (float): Dead time between the adjust the pulses.
            timeout (float): optional - timeout [s],
                             If timeout = 0: return at once and do not wait
                             if timeout is None: wait forever (default).
        Raises:
            RuntimeError: Timeout waiting for status ready.
        """

        # enable gate pulses
        self._exporter.write_property("DetectorGatePulseEnabled", value=True)
        # Adding the servo time to the readout time to avoid any
        # servo cycle jitter
        servo_time = 0.110

        self._exporter.write_property(
            "DetectorGatePulseReadoutTime", (dead_time * 1000 + servo_time)
        )

        self.set_values_motors(grid_centre, simultaneous=True, timeout=timeout)
        scan_params = f"{(end - start):0.3f}\t"
        scan_params += f"{-mesh_range['horizontal_range']:0.3f}\t"
        scan_params += f"{-mesh_range['vertical_range']:0.3f}\t"
        scan_params += f"{start:0.3f}\t"
        for name in ["phiy", "phiz", "sampx", "sampy"]:
            for mot in grid_centre:
                if name == mot[0].name:
                    scan_params += f"{float(mot[1]):0.3f}\t"
        scan_params += f"{nb_lines}\t"
        scan_params += f"{nb_frames_total / nb_lines}\t"
        scan_params += f"{exptime / nb_lines}\t"
        scan_params += "True\tTrue\tTrue\t"
        self._exporter.execute("startRasterScanEx", (scan_params,))
        self._wait_ready(timeout)

    def do_still_scan(
        self,
        pulse_duration: float,
        pulse_period: float,
        nb_pulse: int,
        timeout: [None | float] = None,
    ):
        """Do a zero oscillation acquisition.
        Args:
            pulse_duration (float): Duration of the pulse sent to the detector.
            pulse_period (float): The period of the pulse sent to the detector.
            nb_pulse (int): Number of pulses to be sent.
        """
        scan_params = f"{pulse_duration:0.6f}\t{pulse_period:0.6f}\t{nb_pulse}"
        self._exporter.execute("startStillScan", (scan_params,))
        self._wait_ready(timeout)
