import ast
from mxcubecore.HardwareObjects.NState import NState
from collections import OrderedDict
from mxcubecore.BaseHardwareObjects import HardwareObjectState


class P11Collimator(NState):
    """Collimator hardware object class"""

    def init(self):
        """Initialize the collimator with its motors and positions."""
        super().init()

        # Retrieve motors using their roles
        self.y_motor = self.get_object_by_role("collimatory")  # Y-axis motor
        self.z_motor = self.get_object_by_role("collimatorz")  # Z-axis motor

        self.log.info(f"Collimator Y Motor initialized: {self.y_motor}")
        self.log.info(f"Collimator Z Motor initialized: {self.z_motor}")

        # Load positions from XML configuration
        self.load_positions()

        # Load deltas for each motor
        self.load_deltas()

        # Set _positions for UI access
        self._positions = OrderedDict()
        self._positions = self.positions

    def load_positions(self):
        """Load predefined positions from the XML configuration."""
        self.log.info("Loading collimator positions from config")
        positions_str = self.get_property("values")

        # Convert the string to a dictionary using ast.literal_eval
        try:
            self.positions = ast.literal_eval(positions_str)
            if isinstance(self.positions, dict):
                self.log.info(f"Available collimator positions: {self.positions}")
            else:
                raise ValueError("Positions data is not a dictionary")
        except (SyntaxError, ValueError) as e:
            self.log.error(f"Error parsing collimator positions: {e}")
            raise ValueError(
                "Invalid collimator positions format in the configuration."
            )

    def load_deltas(self):
        """Load individual motor deltas from the XML configuration explicitly."""
        self.log.info("Loading deltas from config")

        # Fetch individual deltas for each motor
        delta_y = self.get_property("delta_collimatory")
        delta_z = self.get_property("delta_collimatorz")

        # If a delta is not specified, fallback to a default delta value
        self.deltas = {
            "collimatory": float(delta_y)
            if delta_y is not None
            else self.default_delta,
            "collimatorz": float(delta_z)
            if delta_z is not None
            else self.default_delta,
        }

        # Log the deltas for each motor
        for motorname, delta in self.deltas.items():
            self.log.info(f"Delta for {motorname}: {delta}")

    def set_value(self, value):
        """Set the collimator to the specified position."""
        if value not in self.positions:
            raise ValueError(f"Invalid state value: {value}")

        y_position = self.positions[value]["collimatory"]
        z_position = self.positions[value]["collimatorz"]

        # Move the motors
        self.y_motor._set_value(y_position)
        self.z_motor._set_value(z_position)
        self.log.info(f"Setting collimator to position: {value}")

    def get_position_list(self):
        """Return the list of available collimator positions."""
        return list(self.positions.keys())

    def get_value(self):
        """Get the current collimator position based on the motor positions."""
        current_y = self.y_motor.get_value()
        current_z = self.z_motor.get_value()

        for position_name, position in self.positions.items():
            if self.is_within_deltas(
                position.get("collimatory"), current_y, "collimatory"
            ) and self.is_within_deltas(
                position.get("collimatorz"), current_z, "collimatorz"
            ):
                return position_name  # Return the matching position name

    def is_within_deltas(self, target_value, current_value, motor_name):
        """Check if the current motor position is within the delta tolerance for that specific motor."""
        delta = self.deltas.get(motor_name)
        if target_value is None or delta is None:
            return False
        return abs(current_value - target_value) <= delta

    def is_moving(self):
        """
        Descript. : True if the motor is currently moving

        """
        return self.z_motor.get_state() == HardwareObjectState.BUSY
