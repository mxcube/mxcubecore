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
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
Example xml file
<object class = "MicroDiff"
  <username>MD2S</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <exporter_commands>
    <move_multiple_motors>SyncMoveMotors</move_multiple_motors>
    <move_to_phase>startSetPhase</move_to_phase>
    <scan_limits>getOmegaMotorDynamicScanLimits</scan_limits>
    <abort>abort</abort>
    <move_motors_sync>startSimultaneousMoveMotors</move_motors_sync>
    <osc_scan>startScanEx</osc_scan>
    <helical_scan>startScan4DEx</helical_scan>
    <mesh_scan>startRasterScan</mesh_scan>
    <still_scan>startStillScan</still_scan>
    <set_plate_vertical>setPlateVertical</set_plate_vertical>
  </exporter_commands>
  <exporter_channels>
    <scale_x>CoaxCamScaleX</scale_x>
    <scale_y>CoaxCamScaleY</scale_y>
    <head_type>HeadType</head_type>
    <kappa_enable>KappaIsEnabled</kappa_enable>
    <current_phase>CurrentPhase</current_phase>
    <hwstate>HardwareState</hwstate>
    <swstate>State</swstate>
    <scan_range>ScanRange</scan_range>
    <scan_start_angle>ScanStartAngle</scan_start_angle>
    <scan_nb_frames>ScanNumberOfFrames</scan_nb_frames>
    <scan_exposure_time>ScanExposureTime</scan_exposure_time>
    <scan_detector_gate_pulse_enabled>DetectorGatePulseEnabled</scan_detector_gate_pulse_enabled>
    <detector_gate_pulse_readout_time>DetectorGatePulseReadoutTime</detector_gate_pulse_readout_time>
  </exporter_channels>
</object>
"""
from __future__ import absolute_import, division
import time
import math

from HardwareObjects.abstract.abstract_diffractometer import (
    AbstractDiffractometer,
    DiffrHead,
    DiffrPhase,
)

__credits__ = ["MXCuBE collaboration"]


class MicroDiff(AbstractDiffractometer):
    """ AbstractDiffractometer implementattion for EMBL Microdiff """

    def __init__(self, name):
        self.exporter_addr = None
        self.commands = {}
        self.channels = {}
        AbstractDiffractometer.__init__(self, name)

    def init(self):
        """ Initisalise the commands and the channels """
        self.exporter_addr = self.getProperty("exporter_address")

        for name, val in self["exporter_commands"].getProperties().items():
            self.commands[name] = self.addCommand(
                {
                    "type": "exporter",
                    "exporter_address": self.exporter_addr,
                    "name": name,
                },
                val,
            )

        for name, val in self["exporter_channels"].getProperties().items():
            self.channels[name] = self.addChannel(
                {
                    "type": "exporter",
                    "exporter_address": self.exporter_addr,
                    "name": name,
                },
                val,
            )

        AbstractDiffractometer.init(self)

    def _ready(self):
        """ Read the state.
        Returns:
            (bool): True if ready, False otherwise
        """
        try:
            hwstate = self.channels["hwstate"].get_value()
        except KeyError:
            hwstate = "Ready"

        swstate = self.channels["swstate"].get_value()

        return hwstate == "Ready" and swstate == "Ready"

    def get_head_type(self):
        """ Get the head type
        Returns:
            head_type(enum): Head type
        """
        head_type = self.channels["head_type"].get_value()
        for val in DiffrHead:
            if val.value == head_type:
                self.head_type = val
        return self.head_type

    def move_motors(
        self, motors_positions_list, wait=True, timeout=20, simultaneous=True
    ):
        """ Move simultaneously specified motors to the requested positions
        Args:
            motors_positions_list (list): list of tuples
                                   (motor names or hwobj, target values [mm]).
        Kwargs:
            wait (bool): wait for the move to finish (True) or not (False)
            timeout (float): wait time [s]
            simultaneous (bool): Move the motors simultaneously (True) or not.
        Raises:
            RuntimeError: Wrong motor name.
            KeyError: The name does not correspond to an existing motor
        """
        argin = ""
        # be sure the previous command has finished
        self.wait_ready()

        if simultaneous:
            # prepare the command
            for mot in motors_positions_list:
                try:
                    name = self.motors_hwobj[mot[0]].name
                    argin += "%s=%0.3f;" % (name, mot[1])
                except KeyError:
                    raise RuntimeError("The name does not correspond to an existing motor")

            self.commands["move_motors_sync"](argin)
        else:
            AbstractDiffractometer.move_motors(self, motors_positions_list, wait, timeout, simultaneous=False)

        self.wait_ready(timeout)

    def get_motor_positions(self, motors_list=None):
        """ Get the positions of diffractometer motors. If the
            motors_list is empty, return the positions of all
            the availble motors
        Args:
            motors_list (list): List of motor names or hwobj
        Returns:
            (list): list of tuples (motor role, position)
        """
        mot_pos_list = AbstractDiffractometer.get_motor_positions(self, motors_list)
        if not self.in_kappa_mode():
            for tup in mot_pos_list:
                if "kappa" in tup:
                    mot_pos_list[mot_pos_list.index(tup)] = ("kappa", None)
                if "kappa_phi" in tup:
                    mot_pos_list[mot_pos_list.index(tup)] = ("kappa_phi", None)
        return mot_pos_list

    def check_scan_limits(self, start, end, exptime):
        """ Check the parameters of a scan
        Args:
            start (float): start position
            end (float): final position
            exptime (float): exposure time [s]
        """
        if self.in_plate_mode():
            scan_speed = math.fabs(end - start) / exptime
            low_lim, hi_lim = map(float, self.commands["scan_limits"](scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            if end > hi_lim:
                raise ValueError("Scan end abobe the allowed value %f" % hi_lim)

    def do_oscillation_scan(self, start, end, exptime, timeout=600):
        """ Execute oscillation scan
        Args:
            start (float): start omega position
            end (float): final omega position
            exptime (float): exposure time/frame [s]
            timeout (int): time wait for the scan to finish [s] (default 10 min)
        """
        # check the scan limits
        self.check_scan_limits(start, end, exptime)

        self.channels["scan_nb_frames"].set(1)
        scan_params = "1\t%0.3f\t%0.3f\t%0.4f\t1" % (start, (end - start), exptime)
        self.commands["osc_scan"](scan_params)
        print("oscil scan started at -----------> %f" % time.time())
        self.wait_ready(timeout)
        print("finished at ----------> %f" % time.time())

    def do_line_scan(self, start, end, exptime, motors_pos, timeout=900):
        """ Execute line (helical) scan
        Args:
            start (float): start omega position
            end (float): final omega position
            exptime (float): exposure time/frame [s]
            motors_pos (list): list of two lists - motor positions of
                               phiy, phiz, sampx, sampy for
                               start and end point
            timeout (int): time wait for the scan to finish [s] (default 15 min)
        """
        # check the scan limits
        self.check_scan_limits(start, end, exptime)

        self.channels["scan_nb_frames"].set(1)
        scan_params = "%0.3f\t%0.3f\t%f\t" % (start, (end - start), exptime)
        scan_params += "%0.3f\t" % motors_pos["1"]["phiy"]
        scan_params += "%0.3f\t" % motors_pos["1"]["phiz"]
        scan_params += "%0.3f\t" % motors_pos["1"]["sampx"]
        scan_params += "%0.3f\t" % motors_pos["1"]["sampy"]
        scan_params += "%0.3f\t" % motors_pos["2"]["phiy"]
        scan_params += "%0.3f\t" % motors_pos["2"]["phiz"]
        scan_params += "%0.3f\t" % motors_pos["2"]["sampx"]
        scan_params += "%0.3f" % motors_pos["2"]["sampy"]

        self.commands["helical_scan"](scan_params)
        print("helical scan started at -----------> %f" % time.time())
        self.wait_ready(timeout)
        print("finished at ----------> %f" % time.time())

    def do_mesh_scan(
        self,
        start,
        end,
        exptime,
        dead_time,
        nb_lines,
        total_nb_frames,
        mesh_centre,
        mesh_range,
            timeout=1800,
    ):
        """ Execute mesh scan
        Args:
            start (float): start omega position
            end (float): final omega position
            exptime (float): exposure time/frame [s]
            dead_time (float): dead time between each point [s]
            nb_lines (int): number of lines for the scan
            total_nb_frames (int): total number of frames
            mesh_centre (list): centre of the mesh position
            mesh_range (list): horizontal and vertical range values
            timeout (int): time wait for the scan to finish [s] (default 30 min)
        """
        # check the scan limits
        self.check_scan_limits(start, end, exptime)

        self.channels["scan_range"].set_value(end - start)
        self.channels["scan_exposure_time"].set_value(exptime / nb_lines)
        self.channels["scan_start_angle"].set_value(start)
        self.channels["scan_detector_gate_pulse_enabled"].set_value(True)
        # adding time [ms] to the readout time to avoid any servo cycle jitter
        servo_time = 0.11
        self.channels["detector_gate_pulse_readout_time"].set_value(
            dead_time * 1000 + servo_time
        )

        # move to the centre of the grid
        self.move_motors(mesh_centre)
        hpos = self.grid_directions["horizontal_centring"] * mesh_range["horizontal"]
        vpos = self.grid_directions["centring_y"] * mesh_range["vertical"]
        self.motors_hwobj["horizontal_alignment"].rmove(hpos / 2)
        self.motors_hwobj["centring_y"].rmove(vpos / 2)

        scan_params = "%0.3f\t" % -mesh_range["horizontal"]
        scan_params += "%0.3f\t" % mesh_range["vertical"]
        scan_params += "%d\t" % nb_lines
        scan_params += "%d\t" % (total_nb_frames // nb_lines)
        scan_params += "%r" % True
        """ ???
        scan_params += "%r\t" % True
        scan_params += "%r" % False
        """

        self.commands["mesh_scan"](scan_params)
        print("mesh scan started at -----------> %f" % time.time())
        if wait:
            self.wait_ready(1800)  # timeout of 30 min
        print("finished at ----------> %f" % time.time())

    def do_still_scan(self, duration, period, nb_pulses, wait=True):
        """ Execute mesh scan
        Args:
            duration (float): pulse duration [s]
            period (float): pulse periond [s]
            nb_pulses (int): number of pulses
            wait (bool): wait for the scan to finish
        """
        scan_params = "%0.6f\t%0.6f\t%d" % (duration, period, nb_pulses)

        self.commands["still_scan"](scan_params)
        print("still scan started at -----------> %f" % time.time())
        if wait:
            self.wait_ready(1800)  # timeout of 30 min
        print("finished at ----------> %f" % time.time())

    def set_phase(self, phase=None, wait=False):
        """Sets diffractometer to selected phase
        Args:
            phase (str or enum): desired phase
            waith (bool): wait (True) or not (False) until the phase is set
        """
        if isinstance(phase, str):
            for i in DiffrPhase:
                if phase == i.value:
                    self.current_phase = i
        elif isinstance(phase, DiffrPhase):
            self.current_phase = phase
            phase = self.current_phase.value
        else:
            self.current_phase = None
        self.command["move_to_phase"](phase)

    def get_phase(self):
        """ Get the current phase
        Returns:
            phase (enum): DiffrPhase enumeration element
        """
        phase = self.channels["current_phase"].get_value()
        for i in DiffrPhase:
            if phase == i.value:
                self.current_phase = i
        return self.current_phase

    def get_pixels_per_mm(self):
        """ Pixel per mm values
        Returns:
            (tuple): pixels_per_mm_x, pixels_per_mm_y

        """
        try:
            self.pixels_per_mm_x = 1. / self.channels["scale_x"].get_value()
            self.pixels_per_mm_y = 1. / self.channels["scale_y"].get_value()
        except (TypeError, ValueError):
            return None, None
        return self.pixels_per_mm_x, self.pixels_per_mm_y
