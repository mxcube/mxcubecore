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
<object class = "Microdiff"
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

import logging
import gevent
import math
import gevent
import time

# import AbstractDiffractometer
from AbstractDiffractometer import AbstractDiffractometer, DiffrHead, DiffrPhase

import sample_centring

MICRODIFF = None


class Microdiff(AbstractDiffractometer):
    def init(self):
        self.exporter_addr = self.getProperty("exporter_address")

        self.commands = {}
        for name, val in self["exporter_commands"].getProperties().iteritems():
            self.commands[name] = self.addCommand(
                {
                    "type": "exporter",
                    "exporter_address": self.exporter_addr,
                    "name": name,
                },
                val,
            )

        self.channels = {}
        for name, val in self["exporter_channels"].getProperties().iteritems():
            self.channels[name] = self.addChannel(
                {
                    "type": "exporter",
                    "exporter_address": self.exporter_addr,
                    "name": name,
                },
                val,
            )

        AbstractDiffractometer.init(self)

    def wait_ready(self, timeout=None):
        """ Waits when diffractometer status is ready
        Args:
            timeout (int): timeout [s]. None means infinite timeout,
        """
        if timeout is not None:
            timeout = self.timeout
        with gevent.Timeout(
            timeout, RuntimeError("Timeout waiting for diffractometer to be ready")
        ):
            while not self._ready():
                gevent.sleep(0.5)

    def _ready(self):
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

    """ motors handling """

    def move_motors(self, motors_positions_dict, wait=False, timeout=20):
        """ Move simultaneously specified motors to the requested positions
        Args:
            motors_positions_dict (dict): dictionary with motor names or hwobj
                            and target values [mm].
            wait (bool): wait for the move to finish (True) or not (False)
        Raises:
            RuntimeError: Timeout
            KeyError: The name does not correspond to an existing motor
        """
        argin = ""
        # be sure the previous command has finished
        if wait:
            self.wait_ready()

        # prepare the command
        for mot, pos in motors_positions_dict.iteritems():
            try:
                name = self.motors_hwobj[mot].name
                argin += "%s=%0.3f;" % (name, pos)
            except KeyError:
                raise

        self.commands["move_motors_sync"](argin)
        if wait:
            self.wait_ready(timeout)

    def get_motor_positions(self, motors_positions_list=[]):
        """ Get the positions of diffractometer motors. If the
            motors_positions_list is empty, return the positions of all
            the availble motors
        Args:
            motors_positions_list (list): List of motor names or hwobj
        Returns:
            motors_positions_dict (dict): role:position dictionary
        """
        motors_positions_dict = AbstractDiffractometer.get_motor_positions(
            self, motors_positions_list
        )
        if not self.in_kappa_mode():
            motors_positions_dict["kappa"] = None
            motors_positions_dict["kappa_phi"] = None
        return motors_positions_dict

    """ data acquisition scans """

    def check_scan_limits(self, start, end, exptime):
        if self.in_plate_mode():
            scan_speed = math.fabs(end - start) / exptime
            low_lim, hi_lim = map(float, self.commands["scan_limits"](scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            elif end > hi_lim:
                raise ValueError("Scan end abobe the allowed value %f" % hi_lim)

    def set_oscillation_scan(self, start, end, exptime, wait=False):
        # check the scan limits
        self.check_scan_limits(start, end, exptime)

        self.channelss["scan_nb_frames"].set(1)
        scan_params = "1\t%0.3f\t%0.3f\t%0.4f\t1" % (start, (end - start), exptime)
        self.commands["osc_scan"](scan_params)
        print("oscil scan started at -----------> %f" % time.time())
        if wait:
            self.wait_ready(600)
        print("finished at ----------> %f" % time.time())

    def set_line_scan(self, start, end, exptime, motors_pos, wait=False):
        # check the scan limits
        self.check_scan_limits(start, end, exptime)

        self.channels["scan_nb_frames"].set(1)
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
        if wait:
            self.wait_ready(900)  # timeout of 15 min
        print("finished at ----------> %f" % time.time())

    def set_mesh_scan(
        self,
        start,
        end,
        exptime,
        dead_time,
        nb_lines,
        total_nb_frames,
        mesh_centre,
        mesh_range,
        wait=False,
    ):

        self.channels["scan_range"].set_value(end - start)
        self.channels["scan_exposure_time"].set_value(exptime / mesh_num_lines)
        self.channels["scan_start_angle"].set_value(start)
        self.channels["scan_detector_gate_pulse_enabled"].set_value(True)
        # adding 0.11 ms to the readout time to avoid any servo cycle jitter
        self.channels["detector_gate_pulse_readout_time"].set_value(
            dead_time * 1000 + 0.11
        )

        # move to the centre of the grid
        self.move_motors(mesh_center.as_dict())
        hpos = (
            self.grid_directions["horizontal_centring"] * mesh_range["horizontal_range"]
        )
        vpos = self.grid_directions["centring_y"] * mesh_range["vertical_range"]
        self.motors_hwobj["horizontal_alignment"].rmove(hpos / 2)
        self.motors_hwobj["centring_y"].rmove(vpos / 2)

        scan_params = "%0.3f\t" % -mesh_range["horizontal_range"]
        scan_params += "%0.3f\t" % mesh_range["vertical_range"]
        scan_params += "%d\t" % mesh_num_lines
        scan_params += "%d\t" % (total_nb_frames / nb_lines)
        scan_params += "%r" % True
        scan_params += "%r\t" % True
        scan_params += "%r" % False

        self.commands["mesh_scan"](scan_params)
        print("mesh scan started at -----------> %f" % time.time())
        if wait:
            self.wait_ready(1800)  # timeout of 30 min
        print("finished at ----------> %f" % time.time())

    def set_still_scan(self, duration, period, nb_pulses, wait=False):
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

    def get_head_type(self):
        """ Get the head type
        Returns:
            head_type(enum): Head type
        """
        head = self.channels["head_type"].get_value()
        for i in DiffrHead:
            if phase == i.value:
                self.head_type = i
        return self.head_type

    def get_pixels_per_mm(self):
        """ Pixel per mm values
        Returns:
            (tuple): pixels_per_mm_x, pixels_per_mm_y

        """
        try:
            self.pixels_per_mm_x = 1./self.channels["scale_x"].get_value()
            self.pixels_per_mm_y = 1./self.channels["scale_y"].get_value()
        except (TypeError, ValueError):
            return None, None
        return self.pixels_per_mm_x, self.pixels_per_mm_y
