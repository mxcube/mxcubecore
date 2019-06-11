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

"""
Example xml file

<object class = "AbstractDiffractometer">
  <username>Diffractometer</username>
  <object role="onaxis_viewer" href="/prosilica"/>
  <object role="onaxis_shapes" href="/onaxis_shapes"/>
  <motors>
    <device role="omega" hwrid="/omega"/>
    <device role="chi" hwrid="/chi"/>
    <device role="holderlength" hwrid="/phix"/>
    <device role="horizontal_alignment" hwrid="/phiy"/>
    <device role="vertical_alignment" hwrid="/phiz"/>
    <device role="horizontal_centring" hwrid="/sampx"/>
    <device role="vertical_centring" hwrid="/sampy"/>
    <device role="x_centring" hwrid="/centring_x"/>
    <device role="y_centring" hwrid="/centring_y"/>
    <device role="kappa" hwrid="/kappa"/>
    <device role="kappa_phi" hwrid="/kappa_phi"/>
    <device role="zoom" hwrid="/zoom"/>
    <device role="focus" hwrid="/focus"/>
    <device role="front_light" hwrid="/front_light"/>
    <device role="back_light" hwrid="/back_light"/>
    <device role="beamstop_horizontal" hwrid="/bstopy"/>
    <device role="beamstop_verical" hwrid="/bstopz"/>
    <device role="aperture_horizontal" hwrid="/apy"/>
    <device role="aperture_vertical" hwrid="/apz"/>
  </motors>
  <actuators>
    <object role="fast_shutter" href="/fshut"/>
    <object role="scintillator" href="/scintillator"/>
    <object role="diode" href="/diode"/>
    <object role="cryostream" href="/cryo"/>
    <object role="fluo_detector" href="/fluodet"/>
    <object role="front_light" href="/flight"/>
    <object role="back_light" href="/backlight"/>
  </actuators>
  <complex_equipment>
    <object role="beamstop" href="/beamstop"/>
    <object role="capillary" href="/capillary"/>
    <object role="aperture" href="/aperture"/>
    <object role="zoom" href="/zoom"/>
    <object role="centring_vertical" href="/centring_vertical"/>
    <object role="centring_horizontal" href="/centring_horizontal"/>
  </complex_equipment>
</object>
"""

from __future__ import absolute_import
import logging
import enum
import gevent

from BaseHardwareObjects import HardwareObject
from TaskUtils import cleanup

__credits__ = ["MXCuBE collaboration"]


@enum.unique
class DiffrState(enum.IntEnum):
    """
    Enumeration of diffractometer states
    """

    UNKNOWN = 0
    READY = 1
    BUSY = 2
    FAULT = 3
    ALARM = 4


@enum.unique
class DiffrHead(enum.Enum):
    """
    Enumeration diffractometer head types
    """

    MINI_KAPPA = "MiniKappa"
    SMART_MAGNET = "SmartMagnet"
    PLATE = "Plate"
    PERMANENT = "Permanent"


@enum.unique
class DiffrPhase(enum.Enum):
    """
    Enumeration diffractometer phases
    """

    CENTRE = "Centring"
    COLLECT = "DataCollection"
    SEE_BEAM = "BeamLocation"
    TRANSFER = "Transfer"
    SEE_SAMPLE = "LightSample"


class AbstractDiffractometer(HardwareObject):
    """
    Abstract Diffractometer class
    """

    def __init__(self, name):
        super().__init__(name)
        self.head_type = None
        self.current_phase = None
        self.pixels_per_mm_x = None
        self.pixels_per_mm_y = None
        self.timeout = 3  # default timeout 3 s
        self.motors_hwobj = {}
        self.actuators_hwobj = {}
        self.complex_eqipment = {}

    def init(self):
        """
        Initialise the defined in the configuration file equipment.
        """
        # on axis viewer
        self.onaxis_viewer_hwobj = self.getObjectByRole("onaxis_viewer")
        self.onaxis_shapes_hwobj = self.getObjectByRole("onaxis_shapes")

        # motors and direction initialisation
        try:
            for role in self["motors"].getRoles():
                motor = self["motors"].getObjectByRole(role)
                self.motors_hwobj[role] = motor
                _slot = self.emit_motor_state_changed(role, None)
                self.connect(motor, "stateChanged", _slot)
                self.connect(motor, "positionChanged", self.emit_diffractometer_moved)
        except IndexError:
            logging.getLogger("HWR").warning("No motors configured")

        # actuators
        try:
            for role in self["actuators"].getRoles():
                self.actuators_hwobj[role] = self["actuators"].getObjectByRole(role)
        except IndexError:
            logging.getLogger("HWR").warning("No actuators configured")

        # complex equipment
        try:
            for role in self["complex_equipment"].getRoles():
                self.complex_eqipment_hwobj[role] = self[
                    "complex_equipment"
                ].getObjectByRole(role)
        except IndexError:
            logging.getLogger("HWR").warning("No complex equipment configured")

        # initialise the head type
        self.get_head_type()

    def wait_ready(self, timeout=None):
        """ Wait until diffractometer status is ready or timeout occured.
        Args:
            timeout (int): timeout [s]
        """
        if timeout is not None:
            timeout = self.timeout
        with gevent.Timeout(
            timeout, TimeoutError("While waiting for diffractometer to be ready")
        ):
            while not self._ready():
                gevent.sleep(0.5)

    def _ready(self):
        """ Check the status of the diffractometer
        Returns:
            (bool): True of ready, False otrerwise
        """
        return True

    # -------- motors handling --------

    def move_motors(
        self, motors_positions_list, wait=False, timeout=20, simultaneous=True
    ):
        """ Move specified motors to the requested positions
        Args:
            motors_positions_list (list): list of tuples
                                   (motor role, target value [mm]).
            wait (bool): wait for the move to finish (True) or not (False)
            timeout (float): wait time [s]
            simultaneous (bool): Move the motors simultaneously (True) or not.
        Raises:
            TimeoutError: Timeout
            KeyError: The name does not correspond to an existing motor
        """
        motor_hwobj = []
        for motor in motors_positions_list:
            try:
                motor_hwobj.append(self.motors_hwobj[motor[0]])
            except KeyError:
                logging.getLogger("HWR").error("Invalid motor name (%s)", str(motor[0]))
                raise
            if simultaneous:
                self.motors_hwobj[motor[0]].move(motor[1], wait=False)
            else:
                self.motors_hwobj[motor[0]].move(motor[1], wait=True)

        if wait:
            with gevent.Timeout(timeout, TimeoutError("While moving motors")):
                while not all([m.get_state() == m.READY for m in iter(motor_hwobj)]):
                    gevent.sleep(0.1)

    def get_motor_positions(self, motors_list=None):
        """ Get the positions of diffractometer motors. If the motors_list is empty,
            return the positions of all the available motors.
        Args:
            motors_list (list): List of motor roles
        Returns:
            (list): list of tuples (motor role, position)
        """
        mot_pos_list = []

        if motors_list:
            for motor in motors_list:
                try:
                    mot_pos_list.append(
                        (str(motor), float(self.motors_hwobj[motor].get_position()))
                    )
                except KeyError:
                    logging.getLogger("HWR").error("Invalid motor name (%s)", motor)
        else:
            for role, motor in self.motors_hwobj.items():
                mot_pos_list.append((role, float(motor.get_position())))

        return mot_pos_list

    # -------- Head type and modes --------

    def get_head_type(self):
        """ Get the head type
        Returns:
            (enum): Head type
        """
        return self.head_type

    def in_plate_mode(self):
        """ Check if the head is a plate
        Returns:
            (bool): True/False
        """
        return self.get_head_type() == DiffrHead.PLATE

    def in_kappa_mode(self):
        """ Check if the head is a plate
        Returns:
            (bool): True/False
        """

        return self.get_head_type() == DiffrHead.MINI_KAPPA

    # -------- Actuators In/Out --------

    def set_actuator(self, hwobj, in_out, wait=True):
        """ Move an actuator in or out
        Args:
            hwobj (object): actuator hardware object
            in_out (bool): True (in), False (out)
            wait (bool): wait for the movement to finish
        """
        if in_out:
            hwobj.set_in(wait=wait)
        else:
            hwobj.set_out(wait=wait)

    def get_actuator_position(self, hwobj):
        """ Get the actuator position
        Args:
            hwobj (object): actuator hardware object
        Returns:
            (str): Actuator position as string
        """
        return hwobj.get_state()

    # -------- phases --------

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
        else:
            self.current_phase = None

    def get_phase(self):
        """ Get the current phase
        Returns:
            (enum): DiffrPhase enumeration element
        """
        return self.current_phase

    # -------- data acquisition scans --------

    def do_oscillation_scan(self, *args, **kwargs):
        """ Do an oscillation scan """

    def do_line_scan(self, *args, **kwargs):
        """ Do a line (helical) scan """

    def do_mesh_scan(self, *args, **kwargs):
        """ Do a mesh scan """

    def do_still_scan(self, *args, **kwargs):
        """ Do a still acquisition """

    # -------- signals --------

    def emit_diffractometer_moved(self):
        """ Emit signal diffractometerMoved """
        self.emit("diffractometerMoved", ())

    def emit_diffractometer_ready(self):
        """ Emit signal diffractometerReady """
        self.emit("diffractometerReady", ())

    def emit_diffractometer_not_ready(self):
        """ Emit signal diffractometerNotReady """
        self.emit("diffractometerNotReady", ())

    def emit_motor_state_changed(self, role, state):
        """ Emit a signal with the state of the motor
        Args:
            role (str): motor role
            state (int): state
        """

        def _func(state=state):
            signal_name = "%sMotorStateChanged" % role
            func_name = "emit_%s_state_changed" % role
            self.emit(signal_name, (state,))
            return func_name

        return _func

    def emit_phase_changed(self, phase):
        """ Emit signal diffractometerPhaseChanged """
        self.current_phase = phase
        self.emit("diffractometerPhaseChanged", (phase,))

    # -------- beam info --------

    def get_pixels_per_mm(self):
        """ Pixel per mm values
        Returns:
            (tuple): pixels_per_mm_x, pixels_per_mm_y

        """
        return self.pixels_per_mm_x, self.pixels_per_mm_y

    # -------- Obsolete as the generic method can be used --------?
    """
    def fluodetector_in(self):
        self.set_actuator(self.actuators_hwobj['fluo_detector'], True)

    def fluodetector_out(self):
        self.set_actuator(self.actuators_hwobj['fluo_detector'], False)

    def cryo_in(self):
        self.set_actuator(self.actuators_hwobj['cryostream'], True)

    def cryo_out(self):
        self.set_actuator(self.actuators_hwobj['cryostream'], False)

    def scintillator_in(self):
        self.set_actuator(self.actuators_hwobj['scintillator'], True)

    def scintillator_out(self):
        self.set_actuator(self.actuators_hwobj['scintillator'], False)

    def move_to_centred_position(self, centred_position):
        self.move_motors(centred_position)
    """

    # """ To be moved to Beamline """
    # -------- snapshots --------

    def take_snapshots(self, nb_snapshots=0, rot_offset=90., wait=True):
        """ Take snapshot(s)
        Kwargs:
           nb_snapshots(int): How many snapshots to take (defailt 0)
           rot_offset(float): Ofsset to move the rotation axis [deg]
                              (default 90)
           wait(bool): wait until procedure finished (True) or not (False)
        Retuns:
           (list): List of tuples (position, image)
        """
        if nb_snapshots < 1:
            return []

        snapshots = []
        self.set_phase(DiffrPhase.CENTRE, wait)
        start = self.motors_hwobj["omega"].get_position()

        if nb_snapshots > 1 and self.get_head_type() == DiffrHead.PLATE:
            nb_snapshots = 1

        with cleanup(self.snapshot_cleanup(start=start, wait=wait)):
            for i, angle in enumerate([0] + [rot_offset] * (nb_snapshots - 1)):
                logging.getLogger("HWR").info("Taking snapshot #%d", i + 1)
                self.motors_hwobj["omega"].rmove(angle, wait)
                snapshots.append(
                    (start + i * angle, self.onaxis_shapes_hwobj.get_snapshot())
                )
        return snapshots

    def snapshot_cleanup(self, **kwargs):
        """ What to do after taking a snapshot
        Kwargs:
            (dict): wait (bool) - wait to finish (True) or not (False)
                    start (float) - move omega to start position
        """
        wait = kwargs.get("wait", True)

        if kwargs.get("start"):
            self.motors_hwobj["omega"].move(kwargs["start"], wait)

    def get_snapshot(self):
        """ Read the snapshot image from the onaxis viewer
        Returns:
            (image): snapshot
        """
        if self.onaxis_viewer_hwobj:
            return self.onaxis_viewer_hwobj.get_snapshot()

    def save_snapshot(self, filename=None):
        """ Save the snapshot image
        Args:
            filename (str): Optional file name to save the image (full path)
        """
        if self.onaxis_viewer_hwobj:
            self.onaxis_viewer_hwobj.save_snapshot(filename)
