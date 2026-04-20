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

"""Micro Diffractometer Up (MD3) implementation."""

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.MicroDiffractometer import MicroDiffractometer

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class MicroDiffractometerUp(MicroDiffractometer):
    """Micro Diffractometer Up (MD3)."""

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

        for name in ["phiz", "phiy", "sampx", "sampy"]:
            scan_params += f"{motors_pos['1'][name]:0.3f}\t"
        for name in ["phiz", "phiy", "sampx", "sampy"]:
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
        scan_params += f"{mesh_range['vertical_range']:0.3f}\t"
        scan_params += f"{-mesh_range['horizontal_range']:0.3f}\t"
        scan_params += f"{start:0.3f}\t"
        for name in ["phiz", "phiy", "sampx", "sampy"]:
            for key, val in grid_centre.items():
                if name == key:
                    scan_params += f"{float(val):0.3f}\t"
        scan_params += f"{nb_lines}\t"
        scan_params += f"{nb_frames_total / nb_lines}\t"
        scan_params += f"{exptime / nb_lines}\t"
        scan_params += "True\tTrue\tTrue\t"
        self._exporter.execute("startRasterScanEx", (scan_params,))
        self.wait_status_ready(timeout)
