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

"""
Example xml file

<object class = "GenericDiffractometer">
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
    <device role="x_centring hwrid="/centring_x"/>
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
  <centring_motors>
    omega
    horizontal_alignment
    vertical_alignment
    horizontal_centring
    vertical_centring
    zoom
    focus
  </centring_motors>
  <grid_directions>
    <holderlength>-1</holderlength>
    <horizontal_centring>-1</horizontal_centring>
  </grid_directions>
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

from __future__ import print_function
import gevent
import logging
import enum
from warnings import warn

from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.TaskUtils import cleanup, error_cleanup

__credits__ = ["MXCuBE colaboration"]


@enum.unique
class DiffrState(enum.Enum):
    """
    Enumeration of diffractometer states
    """

    Created = 0
    Initializing = 1
    On = 2
    Off = 3
    Closed = 4
    Open = 5
    Ready = 6
    Busy = 7
    Moving = 8
    Standby = 9
    Running = 10
    Started = 11
    Stopped = 12
    Paused = 13
    Remote = 14
    Reset = 15
    Closing = 16
    Disable = 17
    Waiting = 18
    Positioned = 19
    Starting = 20
    Loading = 21
    Unknown = 22
    Alarm = 23
    Fault = 24
    Invalid = 25
    Offline = 26


@enum.unique
class DiffrHead(enum.Enum):
    MINI_KAPPA = "MiniKappa"
    SMART_MAGNET = "SmartMagnet"
    PLATE = "Plate"
    PERMANENT = "Permanent"


@enum.unique
class DiffrPhase(enum.Enum):
    CENTRE = "Centring"
    COLLECT = "DataCollection"
    SEE_BEAM = "BeamLocation"
    TRANSFER = "Transfer"
    SEE_SAMPLE = "LightSample"


class AbstractDiffractometer(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.head_type = None
        self.current_phase = None
        self.pixels_per_mm_x = None
        self.pixels_per_mm_y = None
        self.timeout = 3  # default timeout 3 s

    def init(self):
        # on axis viewer
        self.onaxis_viewer_hwobj = self.getObjectByRole("onaxis_viewer")
        self.onaxis_shapes_hwobj = self.getObjectByRole("onaxis_shapes")

        # motors and direction initialisation
        self.motors_hwobj = {}
        self.directions = {}
        try:
            for role in self["motors"].getRoles():
                motor = self["motors"].getObjectByRole(role)
                self.motors_hwobj[role] = motor
                self.directions[role] = 1
                self.connect(motor, "stateChanged", self.emit_motor_state_changed(role))
                self.connect(motor, "positionChanged", self.emit_diffractometer_moved)
        except IndexError:
            print("No motors configured")

        # get the grid directions, if any
        try:
            directions = self["grid_directions"].getProperties()
            for name, value in directions.iteritems():
                self.directions[name] = value
        except IndexError:
            pass

        # actuators
        self.actuators_hwobj = {}
        try:
            for role in self["actuators"].getRoles():
                self.actuators_hwobj[role] = self["actuators"].getObjectByRole(role)
        except IndexError:
            print("No actuators configured")

        # complex equipment
        self.complex_eqipment = {}
        try:
            for role in self["complex_equipment"].getRoles():
                self.complex_eqipment_hwobj[role] = self[
                    "complex_equipment"
                ].getObjectByRole(role)
        except IndexError:
            print("No complex equipment configured")

        # initialise the head type
        try:
            self.get_head_type()
        except BaseException:
            pass

    def wait_ready(self, timeout=None):
        """ Waits when diffractometer status is ready
        Args:
            timeout (int): timeout [s]
        :type timeout: int
        """
        pass

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
        motor_hwobj = []
        for role, pos in motors_positions_dict.iteritems():
            if isinstance(role, str, unicode):
                try:
                    name = str(role)
                    motor_hwobj.add(self.motors_hwobj[role])
                except KeyError:
                    logging.getLogger("HWR").error("Invalid motor name (%s)", str(role))
                    raise
            else:
                try:
                    name = role.name
                    motor_hwobj.add(self.motors_hwobj[role.name])
                except KeyError:
                    logging.getLogger("HWR").error("Invalid motor name (%s)", str(role))
                    raise
            self.motors_hwobj[name].move(pos, wait=False)

        if wait:
            with gevent.Timeout(timeout, RuntimeError("Timeout moving motors")):
                while not all([m.getState() == m.READY for m in iter(motor_hwobj)]):
                    gevent.sleep(0.1)

    def get_motor_positions(self, motors_positions_list=[]):
        """ Get the positions of diffractometer motors. If the
            motors_positions_list is empty, return the positions of all
            the availble motors
        Args:
            motors_positions_list (list): List of motor names or hwobj
        Returns:
            motors_positions_dict (dict): role:position dictionary
        """
        motors_positions_dict = {}

        if motors_positions_list:
            for motor in motors_positions_list:
                if isinstance(motor, str, unicode):
                    try:
                        motors_positions_dict[str(motor)] = self.motors_hwobj[
                            motor
                        ].get_position()
                    except KeyError:
                        logging.getLogger("HWR").error("Invalid motor name (%s)", motor)
                else:
                    motors_positions_dict[motor.name] = float(motor.get_position())
        else:
            for role, motor in iter(self.motors_hwobj.items()):
                motors_positions_dict[role] = float(motor.get_position())

        return motors_positions_dict

    def getPositions(self, motors_positions_list=[]):
        warn(
            "getPositions is deprecated. Use get_motor_positions instead",
            DeprecationWarning,
        )
        return self.get_motor_positions(motors_positions_list)

    def motor_positions_to_screen(self, centred_positions_dict):
        """ Retirns x, y coordinates of the centred point, calculated
            from positions of the centring motors
        Args:
            centred_positions_dict (dict): role:position dictionary
        Returns:
            (tuple): x, y [pixels]
        """

        if self.use_sample_centring:
            self.update_zoom_calibration()
            if None in (self.pixels_per_mm_x, self.pixels_per_mm_y):
                return 0, 0
            phi_angle = math.radians(
                self.centring_phi.direction * self.centring_phi.getPosition()
            )
            sampx = self.centring_sampx.direction * (
                centred_positions_dict["sampx"] - self.centring_sampx.getPosition()
            )
            sampy = self.centring_sampy.direction * (
                centred_positions_dict["sampy"] - self.centring_sampy.getPosition()
            )
            phiy = self.centring_phiy.direction * (
                centred_positions_dict["phiy"] - self.centring_phiy.getPosition()
            )
            phiz = self.centring_phiz.direction * (
                centred_positions_dict["phiz"] - self.centring_phiz.getPosition()
            )
            rot_matrix = numpy.matrix(
                [
                    math.cos(phi_angle),
                    -math.sin(phi_angle),
                    math.sin(phi_angle),
                    math.cos(phi_angle),
                ]
            )
            rot_matrix.shape = (2, 2)
            inv_rot_matrix = numpy.array(rot_matrix.I)
            dx, dy = (
                numpy.dot(numpy.array([sampx, sampy]), inv_rot_matrix)
                * self.pixels_per_mm_x
            )

            x = (phiy * self.pixels_per_mm_x) + self.beam_position[0]
            y = dy + (phiz * self.pixels_per_mm_y) + self.beam_position[1]

            return x, y
        else:
            raise NotImplementedError

    """ Head type and modes """

    def get_head_type(self):
        """ Get the head type
        Returns:
            head_type(enum): Head type
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

    """ Actuators In/Out """

    def set_actuator(self, hwobj, in_out, wait=True):
        """ Move an actuator in or out
        Args:
            hwobj (object): actuator hardware object
            in_out (boot): in (True), out (False)
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

    """ phases """

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
            phase (enum): DiffrPhase enumeration element
        """
        return self.current_phase

    """ snapshots """

    def take_snapshots(self, nb_snapshots=0, rot_offset=90., wait=True):
        """ Take snapshot(s)
        Kwargs:
           nb_snapshots(int): How many snapshots to take (defailt 0)
           rot_offset(float): Ofsset to move the axis [deg] (default 90)
           wait(bool): wait until procedure finished (True) or not (False)
        Retuns:
           (list): List of (position, image) tuples
        """
        if nb_snapshots < 1:
            return

        snapshots = []
        self.set_phase(DiffrPhase.CENTRE, wait)
        start = self.motors_hwobj["omega"].get_position()

        if nb_snapshots > 1 and self.get_head_type() == DiffrHead.PLATE:
            nb_snapshots = 1

        with cleanup(self.snapshot_cleanup(start=start, wait=wait)):
            for i, angle in enumerate([0] + [rot_offset] * (nb_snapshots - 1)):
                logging.getLogger("HWR").info("Taking snapshot #%d", i + 1)
                self.motors_hwobj["omega"].rmove(angle, wait)
                snapshots.append((start+i*angle, self.onaxis_shapes_hwobj.get_snapshot()))
        return snapshots

    def snapshot_cleanup(self, **kwargs):
        """ What to do after taking a snapshot
        Kwargs:
            (dict): wait(bool) - wait to finish (True) or not (False)
        """
        wait = kwargs.get("wait", True)
        
        if kwargs.get("start"):
            self.motors_hwobj["omega"].move(kwargs["start"], wait)

    def get_snapshot(self):
        """ Read the snapshot image from the onaxis viewer
        Returns:

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

    """ sample centring """

    def move_to_beam(self, coord_x, coord_y, wait=False):

        self.start_centring(
            DiffrCentringMethod.MOVE_TO_BEAM, coordinates=[coord_x, coord_y]
        )

    def start_centring(self, method, sample_info=None, wait=False):
        pass

    def cancel_centring(self):
        pass

    def manual_centring(self, motors_list, nb_rotations=3, rotation_angle=90):
        """ Do manual centring, using the motors, defined in the motors_list
        Args:
            motors_list (list): lis of motor hardware objects
            nb_rotations (int): Number of times to get the current position
                                after a rotation
            rotation_angle (float): Angle to rotate [deg]
        Returns:
            (dict): motor_hwobj:position dictionary
        """
        pass

    def automatic_centring(self, motors_list):
        """ Do manual centring, using the motors, defined in the motors_list
        Args:
            motors_list (list): lis of motor hardware objects
        Returns:
            (dict): motor_hwobj:position dictionary
        """
        pass

    """ data acquisition scans """

    def set_oscillation_scan(self, *args, **kwargs):
        pass

    def set_line_scan(self, *args, **kwargs):
        pass

    def set_mesh_scan(self, *args, **kwargs):
        pass

    def set_still_scan(self, *args, **kwargs):
        pass

    """ signals """

    def emit_diffractometer_moved(self, *args):
        self.emit("diffractometerMoved", ())

    def emit_diffractometer_ready(self):
        self.emit("minidiffReady", ())
        self.emit("diffractometerReady", ())

    def emit_diffractometer_not_ready(self):
        self.emit("minidiffNotReady", ())
        self.emit("diffractometerNotReady", ())

    def emit_motor_state_changed(self, role, state):
        """ Emit a signal with the state of the motor
        Args:
            role (str): motor role
            state (int): state
        """
        signal_name = "%sMotorStateChanged" % role
        self.emit(signal_name, (state,))

    def emit_phase_changed(self, phase):
        self.current_phase = phase
        self.emit("diffractometerPhaseChanged", (phase,))

    """ beam info """

    def get_pixels_per_mm(self):
        """ Pixel per mm values
        Returns:
            (tuple): pixels_per_mm_x, pixels_per_mm_y

        """
        return self.pixels_per_mm_x, self.pixels_per_mm_y

    """ Obsolete as the generic method can be used """
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
    """

    """
    def move_to_centred_position(self, centred_position):
        self.move_motors(centred_position)
    """
