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
  methods: move_motors, get/set_phase methods
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
    """
    Enumeration diffractometer head types
    """

    UNKNOWN = "Unknown"
    MINI_KAPPA = "MiniKappa"
    SMART_MAGNET = "SmartMagnet"
    PLATE = "Plate"


@unique
class DiffractometerPhase(Enum):
    """
    Enumeration diffractometer phases
    """

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
        self.motors_hwobjs = {}
        self.actuators_hwobj = {}
        self.complex_eqipment = {}
        self.username = name
        self.current_phase = None
        self.head_type = None
        self.timeout = 3  # default timeout 3 s

    def init(self):
        """Initialise actuator_name and username properties.
        Initialise the equipment, defined in the configuration file
        """
        self.username = self.get_property("username") or self.username
        try:
            for role in self["motors"].get_roles():
                self.motors_hwobj[role] = self["motors"].get_object_by_role(role)
        except IndexError:
            print("No motors configured")

        # actuators
        try:
            for role in self["actuators"].get_roles():
                self.actuators_hwobj[role] = self["actuators"].get_object_by_role(role)
        except IndexError:
            print("No actuators configured")

        # complex equipment
        try:
            for role in self["complex_equipment"].get_roles():
                self.complex_eqipment_hwobj[role] = self[
                    "complex_equipment"
                ].get_object_by_role(role)
        except IndexError:
            print("No complex equipment configured")

    # -------- Motor Groups --------

    def set_values_motors(self, motors_positions_list, simultaneous=True, timeout=None):
        """Move specified motors to the requested positions
        Args:
            motors_positions_list (list): list of tuples (motor role, target value).
            simultaneous (bool): Move the motors simultaneously (True - default) or not.
            timeout (float): optional - timeout [s],
                             If timeout = 0: return at once and do not wait
                             if timeout is None: wait forever (default).
        Raises:
            TimeoutError: Timeout
            KeyError: The name does not correspond to an existing motor
        """
        motor_hwobj = []
        for motor in motors_positions_list:
            try:
                motor_hwobj.append(self.motors_hwobj[motor[0]])
            except KeyError:
                raise RuntimeError(f"Invalid motor name {motor[0]}")

            if simultaneous:
                self.motors_hwobj[motor[0]].set_value(motor[1], timeout=0)
            else:
                self.motors_hwobj[motor[0]].set_value(motor[1], timeout=timeout)

            # now wait for the end of all the move of all the motors if needed
            if simultaneous:
                for mot in motors_positions_list:
                    self.motors_hwobj[mot[0]].wait_ready(timeout)

    def get_values_motors(self, motors_list=None):
        """ Get the positions of diffractometer motors. If the motors_list is
            empty, return the positions of all the available motors.
        Args:
            motors_list (list): List of motor roles (optional).
        Returns:
            (list): list of tuples (motor role, position)
        """
        mot_pos_list = []
        if motors_list:
            for motor in motors_list:
                try:
                    mot_pos_list.append(
                        (str(motor), float(self.motors_hwobj[motor].get_value()))
                    )
                except KeyError:
                    logging.getLogger("HWR").error("Invalid motor name (%s)", motor)
        else:
            for role, motor in self.motors_hwobj.items():
                mot_pos_list.append((role, float(motor.get_value())))

        return mot_pos_list

    # -------- Head Type and Modes --------

    @property
    def get_head_type(self):
        """Get the head type
        Returns:
            (Enum): DiffractometerPhase value.
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

    # -------- phases --------

    def set_phase(self, phase, timeout=None):
        """Sets diffractometer to selected phase.
        Args:
            phase (Enum): DiffractometerPhase value.
            timeout (float): optional - timeout [s],
                             If timeout = 0: return at once and do not wait;
                             if timeout is None: wait forever (default).
        """
        if isinstance(phase, DiffractometerPhase):
            self.current_phase = phase
        if self.current_phase:
            self._set_phase(self.current_phase)
            self.update_phase()
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
            (Enum): DiffractometerPhase value.
        """
        return self.current_phase

    def update_phase(self, value=None):
        """Check if the phase has changed. Emit signal valueChanged.
        Args:
            value (Enum): DiffractometerPhase value (optional).
        """
        if value is None:
            value = self.get_phase()
        self.emit("valueChanged", (value,))

    # -------- data acquisition scans --------
    def do_oscillation_scan(self, *args, **kwargs):
        """ Do an oscillation scan. """
        raise NotImplementedError

    def do_line_scan(self, *args, **kwargs):
        """ Do a line (helical) scan. """
        raise NotImplementedError

    def do_mesh_scan(self, *args, **kwargs):
        """ Do a mesh scan. """
        raise NotImplementedError

    def do_still_scan(self, *args, **kwargs):
        """ Do a zero oscillation acquisition. """
        raise NotImplementedError

    def do_characterisation_scan(self, *args, **kwargs):
        """ Do characterisation. """
        raise NotImplementedError

    # -------- auxilarly methods --------

    def value_to_enum(self, value, which_enum):
        """Tranform a value to Enum
        Args:
           value(str, int, float, tuple): value
           which_enum (Enum): The enum to be checked.
        Returns:
            (Enum): Enum member, corresponding to the value or UNKNOWN.
        """
        try:
            return which_enum(value)
        except ValueError:
            for evar in which_enum.__members__.values():
                if isinstance(evar.value, tuple) and (value in evar.value):
                    return evar
        return which_enum.UNKNOWN
