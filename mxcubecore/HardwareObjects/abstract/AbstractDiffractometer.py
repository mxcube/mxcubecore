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
Initialises the username property and all the motors, actuators and
complex equipment which is a part of the diffractometer.
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
class DiffractometerConstraint(Enum):
    """Enumeration diffractometer constraint types"""

    UNKNOWN = "Unknown"
    JET = "Jet"
    STILL = "Still"


@unique
class DiffractometerPhase(Enum):
    """Enumeration diffractometer phases"""

    UNKNOWN = "Unknown"
    CENTRE = "Centring"
    COLLECT = "DataCollection"
    SEE_BEAM = "BeamLocation"
    TRANSFER = "Transfer"
    SEE_SAMPLE = "LightSample"


class AbstractDiffractometer(HardwareObject):
    """Abstract Diffractometer"""

    __metaclass__ = abc.ABCMeta

    unit = None

    def __init__(self, name):
        super().__init__(name)
        self.motors_hwobj_dict = {}
        self.actuators_hwobj_dict = {}
        self.complex_eqipment_hwobj_dict = {}
        self.username = name
        self.current_phase = None
        self.head_type = None
        self.constraint_type = None
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

        # actuators
        for role in self["actuators"].get_roles():
            try:
                self.actuators_hwobj_dict[role] = self["actuators"].get_object_by_role(
                    role
                )
            except KeyError:
                logging.getLogger("HWR").warning(
                    "Diffractometer: No actuators configured"
                )

        # complex equipment
        for role in self["complex_equipment"].get_roles():
            try:
                self.complex_eqipment_hwobj_dict[role] = self[
                    "complex_equipment"
                ].get_object_by_role(role)
            except KeyError:
                logging.getLogger("HWR").warning(
                    "Diffractometer: No complex equipment configured"
                )

    def get_motors(self):
        """Get the dictionary of all configured motors or the ones to use.
        Returns:
            (dict): Dictionary key=role: value=hardware_object
        """
        return self.motors_hwobj_dict

    def get_actuators(self):
        """Get the dictionary of all configured actuators or the ones to use.
        Returns:
            (dict): Dictionary key=role: value=hardware_object
        """
        return self.actuators_hwobj_dict

    def get_complex_equipment(self):
        """Get the dictionary of all configured complex equipment or the
           ones to use.
        Returns:
            (dict): Dictionary key=role: value=hardware_object
        """
        return self.complex_eqipment_hwobj_dict

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
                    logging.getLogger("HWR").warning(f"No value for {role}")
            return mot_pos_dict

        for motor in motors_list:
            try:
                mot_pos_dict[str(motor)] = float(mot_hwobj_dict[motor].get_value())
            except KeyError:
                logging.getLogger("HWR").error(f"Invalid motor name {motor}")
            except TypeError:
                logging.getLogger("HWR").warning(f"No value for {motor}")
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

    # -------- Constraints --------

    def get_constraint(self):
        """Get the diffrractometer constraint type.
        Returns:
            (Enum): DiffractometerConstraint member.
        """
        return self.constraint_type

    def set_constraint(self, value, timeout=None):
        """Set the constraint type,
        Args:
            value (Enum): DiffractometerConstraint member.
            timeout (float): optional - timeout [s],
                             if timeout = 0: return at once and do not wait,
                             if timeout is None: wait forever (default).
        """
        if isinstance(value, DiffractometerConstraint):
            self.constraint_type = value
            self._set_constraint(self.constraint_type)
            self.update_value(method=self.get_constraint())
            if timeout == 0:
                return
            self.wait_ready(timeout)

    def _set_constraint(self, value):
        """Specific implementation to set the diffractometer to selected
           constraint type.
        Args:
            value (Enum): DiffractometerConstraint member
        """

    def get_constraint_enum(self):
        """Get the constraints Enum. Used when no import possible.
        Returns:
            (Enum): DiffractometerConstraint.
        """
        return DiffractometerConstraint

    # -------- Phases --------

    def set_phase(self, phase, timeout=None):
        """Sets diffractometer to selected phase.
        Args:
            phase (Enum): DiffractometerPhase value.
            timeout (float): optional - timeout [s],
                             if timeout = 0: return at once and do not wait,
                             if timeout is None: wait forever (default).
        """
        if isinstance(phase, DiffractometerPhase):
            self.current_phase = phase
        if self.current_phase:
            self._set_phase(self.current_phase)
            self.update_value(method=self.get_phase())
            if timeout == 0:
                return
            self.wait_ready(timeout)

    def _set_phase(self, phase):
        """Specific implementation to set the diffractometer to selected phase
        Args:
            phase (Enum): DiffractometerPhase value.
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

    def update_value(self, value=None, method=None):
        """Check if the value has changed. Emits signal valueChanged.
        Args:
            value: value
            method: Method or property to get the value to compare with.
        """
        if method:
            curr_value = method

        if value != curr_value:
            self.emit("valueChanged", (value,))
