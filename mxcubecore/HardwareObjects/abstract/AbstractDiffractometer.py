# encoding: utf-8
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Abstract Diffractometer class.
Initialises the username property and all the motors and nstate (discrete
possitions) equipment, which are part of the diffractometer.
The equipment is identified by the roles.
The fixed motor roles are:
omega, kappa, kappa_phi, horizontal_alignment, vertical_alignment,
horizontal_centring, vertical_centring, focus, front_light, back_light
The fixed nstate equipment roles are:
fast_shutter, scintillator, fluo_detector, cryostream, front_light, back_light,
zoom, aperture, beamstop, capillary, diode

Defines:
  methods: get/set_value_motors, get/set_phase, get_set_constraint
  properties: get_head_type, in_kappa_mode, in_plate_mode

Emits signals valueChanged and limitsChanged.

"""

import logging
import abc
from enum import Enum, unique

from mxcubecore.BaseHardwareObjects import HardwareObject


__copyright__ = """ Copyright © 2010-2022 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


@unique
class DiffractometerHead(Enum):
    """Enumeration diffractometer head types"""

    UNKNOWN = "Unknown"
    MINI_KAPPA = "MiniKappa"
    SMART_MAGNET = "SmartMagnet"
    PLATE = "Plate"
    SSX = "SSX"


@unique
class DiffractometerPhase(Enum):
    """Enumeration diffractometer phases"""

    UNKNOWN = "Unknown"
    CENTRE = "Centring"
    COLLECT = "DataCollection"
    SEE_BEAM = "BeamLocation"
    TRANSFER = "Transfer"
    SEE_SAMPLE = "LightSample"


@unique
class DiffractometerConstraint(Enum):
    """Enumeration diffractometer constraint types"""

    UNKNOWN = "Unknown"
    RELEASE = "Normal"
    INJECTOR = "Injector"
    STILL = "LockRotation"


class AbstractDiffractometer(HardwareObject):
    """Abstract Diffractometer"""

    __metaclass__ = abc.ABCMeta

    unit = None

    def __init__(self, name):
        super().__init__(name)
        self.motors_hwobj_dict = {}
        self.nstate_equipment_hwobj_dict = {}
        self.username = name
        self.current_phase = None
        self.head_type = None
        self.current_constraint = None
        self.timeout = 3  # default timeout 3 s

    def init(self):
        """Initialise actuator_name and username properties.
        Initialise the equipment, defined in the configuration file
        """
        self.username = self.get_property("username") or self.username

        # motors
        for role in self["motors"].get_roles():
            try:
                self.motors_hwobj_dict[role] = self["motors"].get_object_by_role(role)
            except KeyError:
                logging.getLogger("HWR").warning("Diffractometer: No motors configured")

        # nstate (discrete positions) equipment
        for role in self["nstate_equipment"].get_roles():
            try:
                self.nstate_equipment_hwobj_dict[role] = self[
                    "nstate_equipment"
                ].get_object_by_role(role)
            except KeyError:
                logging.getLogger("HWR").warning(
                    "No nstate (discrete positions) equipment configured"
                )

    def get_motors(self):
        """Get the dictionary of all configured motors or the ones to use.
        Returns:
            (dict): Dictionary key=role: value=hardware_object
        """
        return self.motors_hwobj_dict.copy()

    def get_nstate_equipment(self):
        """Get the dictionary of all the nstate (discrete positions) equipment.
        Returns:
            (dict): Dictionary key=role: value=hardware_object
        """
        return self.nstate_equipment_hwobj_dict

    # -------- Motor Groups --------

    def set_value_motors(self, motors_positions_dict, simultaneous=True, timeout=None):
        """Move specified motors to the requested positions
        Args:
            motors_positions_dict (dict): Dictionary {motor_role: target_value}.
            simultaneous (bool): Move the motors simultaneously
                                 (True - default) or not.
            timeout (float): optional - timeout [s],
                             if timeout = 0: return at once and do not wait,
                             if timeout is None: wait forever (default).
        Raises:
            TimeoutError: Timeout
            KeyError: The name does not correspond to an existing motor
        """

        # use only the available motors
        mot_hwobj_dict = self.get_motors()

        tout = timeout
        if simultaneous:
            tout = 0

        for key, val in motors_positions_dict.items():
            try:
                mot_hwobj_dict[key].set_value(val, timeout=tout)
            except KeyError as err:
                raise RuntimeError(f"Invalid motor name {key}") from err

        # wait for the end of move of all the motors, if needed
        if simultaneous:
            for key in motors_positions_dict:
                mot_hwobj_dict[key].wait_ready(timeout)

    def get_value_motors(self, motors_list=None):
        """Get the positions of diffractometer motors. If the motors_list is
            empty, return the positions of all the available motors.
        Args:
            motors_list (list): List of motor roles (optional).
        Returns:
            (dict): Dictionary {motor_role: position}
        """
        mot_pos_dict = {}

        # use only the available motors
        mot_hwobj_dict = self.get_motors()

        if not motors_list:
            for role, motor in mot_hwobj_dict.items():
                try:
                    mot_pos_dict[role] = float(motor.get_value())
                except TypeError:
                    msg = f"No value for {role}"
                    logging.getLogger("HWR").warning(msg)
            return mot_pos_dict

        for motor in motors_list:
            try:
                mot_pos_dict[str(motor)] = float(mot_hwobj_dict[motor].get_value())
            except KeyError:
                msg = f"Invalid motor name {motor}"
                logging.getLogger("HWR").error(msg)
            except TypeError:
                msg = f"No value for {motor}"
                logging.getLogger("HWR").warning(msg)
        return mot_pos_dict

    # -------- Head Type and Modes --------

    @property
    def get_head_type(self):
        """Get the head type
        Returns:
            (Enum): DiffractometerHead member.
        """
        return self.head_type

    @property
    def in_plate_mode(self):
        """Check if the head is a plate.
        Returns:
            (bool): True/False
        """
        return self.get_head_type == DiffractometerHead.PLATE

    @property
    def in_kappa_mode(self):
        """Check if the head is MiniKappa.
        Returns:
            (bool): True/False
        """
        return self.get_head_type == DiffractometerHead.MINI_KAPPA

    def get_head_enum(self):
        """Get the diffractometer head Enum. Used when no import possible.
        Returns:
            (Enum): DiffractometerHead.
        """
        return DiffractometerHead

    # -------- Phases --------

    def set_phase(self, value, timeout=None):
        """Sets diffractometer to selected phase.
        Args:
            value (Enum): DiffractometerPhase value.
            timeout (float): optional - timeout [s],
                             If timeout = 0: return at once and do not wait;
                             if timeout is None: wait forever (default).
        """
        if isinstance(value, DiffractometerPhase):
            self.current_phase = value
        else:
            self.current_phase = self.value_to_enum(value, DiffractometerPhase)
        if self.current_phase != DiffractometerPhase.UNKNOWN:
            self._set_phase(self.current_phase)
            self._update_value(value_cmp=self.get_phase())
            if timeout == 0:
                return
            self.wait_ready(timeout)

    def _set_phase(self, value):
        """Specific implementation to set the diffractometer to selected phase
        Args:
            value (Enum): DiffractometerPhase value.
        """

    def get_phase(self):
        """Get the current phase
        Returns:
            (Enum): DiffractometerPhase member.
        """
        return self.current_phase

    def get_phase_enum(self):
        """Get the phase Enum. Used when no import possible.
        Returns:
            (Enum): DiffractometerPhase.
        """
        return DiffractometerPhase

    # -------- Constraints --------

    def set_constraint(self, value, timeout=None):
        """Sets diffractometer to selected constraint.
        Args:
            value (Enum): DiffractometerConstraint member.
            timeout (float): optional - timeout [s],
                             if timeout = 0: return at once and do not wait,
                             if timeout is None: wait forever (default).
        """
        if isinstance(value, DiffractometerConstraint):
            self.current_constraint = value
        else:
            self.current_constraint = self.value_to_enum(
                value, DiffractometerConstraint
            )
            self._set_constraint(self.current_constraint)
            self._update_value(value_cmp=self.get_constraint())
            if timeout == 0:
                return
            self.wait_ready(timeout)

    def _set_constraint(self, value):
        """Specific implementation to set the diffractometer to selected
        constraint.
        Args:
            value (Enum): DiffractometerConstraint member
        """

    def get_constraint(self):
        """Get the current constraint
        Returns:
            (Enum): DiffractometerConstraint member.
        """
        return self.current_constraint

    def get_constraint_enum(self):
        """Get the constraints Enum. Used when no import possible.
        Returns:
            (Enum): DiffractometerConstraint.
        """
        return DiffractometerConstraint

    # -------- data acquisition scans --------
    def do_oscillation_scan(self, *args, **kwargs):
        """Do an oscillation scan."""
        raise NotImplementedError

    def do_line_scan(self, *args, **kwargs):
        """Do a line (helical) scan."""
        raise NotImplementedError

    def do_mesh_scan(self, *args, **kwargs):
        """Do a mesh scan."""
        raise NotImplementedError

    def do_still_scan(self, *args, **kwargs):
        """Do a zero oscillation acquisition."""
        raise NotImplementedError

    def do_characterisation_scan(self, *args, **kwargs):
        """Do characterisation."""
        raise NotImplementedError

    def _update_value(self, value=None, value_cmp=None):
        """Check if the value has changed. Emits signal valueChanged.
        Args:
            value: value
            value_cmp: Value to compare with.
        """
        curr_value = None
        if value_cmp and value is None:
            curr_value = value_cmp

        if value != curr_value:
            self.emit("valueChanged", (value,))

    # -------- auxilarly methods --------

    def value_to_enum(self, value, which_enum):
        """Tranform a value to Enum
        Args:
           value(str, int, float, tuple, list): value
           which_enum (Enum): The enum to be checked.
        Returns:
            (Enum): Enum member, corresponding to the value or UNKNOWN.
        """
        try:
            return which_enum(value)
        except ValueError:
            for evar in which_enum:
                if isinstance(evar.value, (tuple, list)) and (value in evar.value):
                    return evar
        return which_enum.UNKNOWN
