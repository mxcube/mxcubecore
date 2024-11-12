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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

__copyright__ = """Copyright The MXCuBE Collaboration"""
__license__ = "LGPLv3+"

import ast
import time

from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.NState import NState


class P11BeamStop(NState):
    default_delta = 0.1

    def init(self):
        """Initialize the BeamStop motors and load positions."""
        super().init()

        self.x_motor = self.get_object_by_role("bstopx")

        self.load_positions()
        self.load_deltas()

        self.log.debug(f"Beamstop X Motor initialized: {self.x_motor}")
        self.log.debug(f"Beamstop Y Motor not used")
        self.log.debug(f"Beamstop Z Motor not used")

    def load_positions(self):
        """Load predefined positions from the XML configuration."""
        self.log.info("Loading BeamStop positions from config")
        positions_str = self.get_property("values")

        if not positions_str:
            self.log.error(
                "No values for BeamStop positions found in the configuration."
            )
            raise ValueError("No BeamStop positions found in configuration")

        # Convert the string to a dictionary using ast.literal_eval
        try:
            self.positions = ast.literal_eval(positions_str)
            if isinstance(self.positions, dict):
                self.log.info(f"Available BeamStop positions: {self.positions}")
            else:
                raise ValueError("Positions data is not a dictionary")
        except (SyntaxError, ValueError) as e:
            self.log.error(f"Error parsing BeamStop positions: {e}")
            raise ValueError("Invalid BeamStop positions format in the configuration.")

    def load_deltas(self):
        """Load individual motor deltas from the XML configuration explicitly."""
        self.log.info("Loading deltas from config")

        # Fetch individual deltas for each motor
        delta_bstopx = self.get_property("delta_bstopx")

        # If a delta is not specified, fallback to a default delta value
        self.deltas = {
            "bstopx": (
                float(delta_bstopx) if delta_bstopx is not None else self.default_delta
            ),
        }

        # Log the deltas for each motor
        for motorname, delta in self.deltas.items():
            self.log.info(f"Delta for {motorname}: {delta}")

    def set_value(self, value):
        """Move the BeamStop motors to the given position."""
        if value not in self.positions:
            raise ValueError(f"Invalid value {value}, not in available positions")

        position = self.positions[value]

        self.x_motor._set_value(position.get("bstopx"))

    def get_value(self):
        """Get the current BeamStop position based on the motor positions."""
        current_x = self.x_motor.get_value()

        for position_name, position in self.positions.items():
            if self.is_within_deltas(position.get("bstopx"), current_x, "bstopx"):
                return position_name  # Return the matching position name

    def is_within_deltas(self, target_value, current_value, motor_name):
        """Check if the current motor position is within the delta tolerance for that specific motor."""
        delta = self.deltas.get(motor_name)
        if target_value is None or delta is None:
            return False
        return abs(current_value - target_value) <= delta

    def get_position_list(self):
        """Return a list of available positions."""
        return list(self.positions.keys())

    def wait_for_position(self):
        """Wait for motors to reach their target positions."""
        while any(motor.get_state() != "ON" for motor in [self.x_motor]):
            time.sleep(0.1)

    def is_moving(self):
        """
        Descript. : True if the motor is currently moving
        """
        return self.get_state() == HardwareObjectState.BUSY
