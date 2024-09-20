from mxcubecore.HardwareObjects.NState import NState
import ast
from mxcubecore.BaseHardwareObjects import HardwareObjectState


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
        """Move the pinhole motors to the given position."""
        if value not in self.positions:
            raise ValueError(f"Invalid value {value}, not in available positions")

        position = self.positions[value]

        # Move each motor to the desired position
        self.y_motor._set_value(position.get("pinholey"))
        self.z_motor._set_value(position.get("pinholez"))

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
        """Return True if any motor is moving."""
        return self.y_motor.is_moving() or self.z_motor.is_moving()

    def get_state(self):
        """Determine the overall state of the pinhole motor system."""
        if self.is_moving():
            return HardwareObjectState.BUSY
        else:
            return HardwareObjectState.READY
