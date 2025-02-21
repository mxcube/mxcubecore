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
from mxcubecore import HardwareRepository as HWR


class P11Pinhole(NState):
    def init(self):
        """Initialize the pinhole motors and load positions."""
        super().init()

        # Load the predefined pinhole positions from the XML
        self.load_positions()

        # Load the motors
        self.y_motor = self.get_object_by_role("pinholey")
        self.z_motor = self.get_object_by_role("pinholez")

        # Log motor initialization
        self.log.info(f"Pinhole Y Motor initialized: {self.y_motor}")
        self.log.info(f"Pinhole Z Motor initialized: {self.z_motor}")

        # Load deltas for each motor
        self.load_deltas()

        # Set _positions for UI access
        self._positions = self.positions

    def load_positions(self):
        """Load predefined positions from the XML configuration."""
        self.log.info("Loading pinhole positions from config")
        positions_str = self.get_property("values")

        # Log the retrieved positions string
        self.log.info(f"Retrieved positions: {positions_str}")

        # Check if positions_str is None or empty
        if positions_str is None:
            self.log.error(
                "No values for pinhole positions found in the configuration."
            )
            raise ValueError("No pinhole positions found in configuration")

        # Convert the string to a dictionary using ast.literal_eval
        try:
            self.positions = ast.literal_eval(positions_str)
            if isinstance(self.positions, dict):
                self.log.info(f"Available pinhole positions: {self.positions}")
            else:
                raise ValueError("Positions data is not a dictionary")
        except (SyntaxError, ValueError) as e:
            self.log.error(f"Error parsing pinhole positions: {e}")
            raise ValueError("Invalid pinhole positions format in the configuration.")

    def load_deltas(self):
        """Load individual motor deltas from the XML configuration."""
        self.log.info("Loading deltas from config")

        # Fetch individual deltas for each motor
        delta_y = self.get_property("delta_pinholey")
        delta_z = self.get_property("delta_pinholez")

        # If a delta is not specified, fallback to a default delta value
        self.deltas = {
            "pinholey": float(delta_y) if delta_y is not None else self.default_delta,
            "pinholez": float(delta_z) if delta_z is not None else self.default_delta,
        }

        # Log the deltas for each motor
        for motorname, delta in self.deltas.items():
            self.log.info(f"Delta for {motorname}: {delta}")

    
    def set_value(self, value):
        """Move the pinhole motors and update UI state until movement stops."""
        if value not in self.positions:
            raise ValueError(f"Invalid value {value}, not in available positions")
    
        position = self.positions[value]
    
        # Emit BUSY state before moving
        self.update_state(HardwareObjectState.BUSY)
        self.emit("stateChanged", HardwareObjectState.BUSY)  # Notify UI (Beam Size Brick)
    
        # Move motors
        self.y_motor._set_value(position.get("pinholey"))
        self.z_motor._set_value(position.get("pinholez"))
    
        # Wait for movement to stop
        while self.is_moving():
            self.log.debug("Pinhole is still moving, keeping UI yellow.")
            self.emit("stateChanged", HardwareObjectState.BUSY)  # Keep UI yellow
            time.sleep(0.2)
    
        # Update beam size after movement stops
        if hasattr(self, "beam_hwobj") and self.beam_hwobj:
            self.beam_hwobj.update_beam_size()
    
        # Set state back to READY when movement stops
        self.update_state(HardwareObjectState.READY)
        self.emit("stateChanged", HardwareObjectState.READY)  # Notify UI (Beam Size Brick)
    

#    def set_value(self, value):
#        """Move the pinhole motors and keep UI yellow until movement stops."""
#        if value not in self.positions:
#            raise ValueError(f"Invalid value {value}, not in available positions")
#    
#        position = self.positions[value]
#    
#        # Set state to BUSY before moving
#        self.update_state(HardwareObjectState.BUSY)
#        self.emit("stateChanged", HardwareObjectState.BUSY)  # Notify UI
#    
#        # Move motors
#        self.y_motor._set_value(position.get("pinholey"))
#        self.z_motor._set_value(position.get("pinholez"))
#    
#        # Wait until motors stop moving
#        while self.is_moving():
#            self.log.debug("Pinhole is still moving...")
#            time.sleep(0.2)
#    
#        # Update beam size when movement stops
#        if hasattr(self, "beam_hwobj") and self.beam_hwobj:
#            self.beam_hwobj.update_beam_size()
#    
#        # Set state back to READY when movement stops
#        self.update_state(HardwareObjectState.READY)
#        self.emit("stateChanged", HardwareObjectState.READY)  # Notify UI
#         
    def get_value(self):
        """Get the current pinhole position based on the motor positions."""
        current_y = self.y_motor.get_value()
        current_z = self.z_motor.get_value()
    
        for position_name, position in self.positions.items():
            if self.is_within_deltas(
                position.get("pinholey"), current_y, "pinholey"
            ) and self.is_within_deltas(
                position.get("pinholez"), current_z, "pinholez"
            ):
                return position_name  # Return the matching position name
    
        self.log.warning("No exact pinhole position match found, returning closest match.")
    
        # Fallback: Return the closest position instead of None
        closest_position = self.get_closest_position(current_y, current_z)
        return closest_position if closest_position else "UNKNOWN"
    
    def get_closest_position(self, current_y, current_z):
        """Find the closest pinhole position if an exact match is not found."""
        closest_position = None
        min_distance = float("inf")
    
        for position_name, position in self.positions.items():
            target_y = position.get("pinholey", float("inf"))
            target_z = position.get("pinholez", float("inf"))
    
            distance = abs(current_y - target_y) + abs(current_z - target_z)
            if distance < min_distance:
                min_distance = distance
                closest_position = position_name
    
        return closest_position
    
    def is_within_deltas(self, target_value, current_value, motor_name):
        """Check if the current motor position is within the delta tolerance for that specific motor."""
        delta = self.deltas.get(motor_name)
        if target_value is None or delta is None:
            return False
        return abs(current_value - target_value) <= delta

    def get_position_list(self):
        """Return the list of available pinhole positions."""
        return list(self.positions.keys())

    def is_moving(self):
        """Return True if either pinhole motor is moving."""
        state_y = self.y_motor.get_state()
        state_z = self.z_motor.get_state()
    
        self.log.debug(f"Checking pinhole movement: Y={state_y}, Z={state_z}")
    
        return state_y in ["MOVING", "ON"] or state_z in ["MOVING", "ON"]
    
    def get_state(self):
        """Determine the overall state of the pinhole motor system."""
        if self.is_moving():
            return HardwareObjectState.BUSY
        else:
            return HardwareObjectState.READY

    def get_pinhole_size(self):
        """Returns the currently selected pinhole size label."""
        try:
            current_pos = self.get_value()
            for size_label, pos in self.values.items():
                if pos == current_pos:
                    return size_label
        except Exception as e:
            self.log.error(f"Failed to get pinhole size: {e}")
    
        return "UNKNOWN"  # Fallback if no match is found
    
