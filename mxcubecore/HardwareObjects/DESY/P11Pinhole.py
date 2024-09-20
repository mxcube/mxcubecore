from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState
import ast
import time


class P11Pinhole(AbstractNState):
    def init(self):
        """Initialize the pinhole motors and load positions."""
        super().init()

        # Load the predefined pinhole positions from the XML
        self.load_positions()

        # Load the motors
        self.y_motor = self.get_object_by_role("pinholey")
        self.z_motor = self.get_object_by_role("pinholez")

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

    def set_value(self, value):
        """Move the pinhole motors to the given position."""
        if value not in self.positions:
            raise ValueError(f"Invalid value {value}, not in available positions")

        position = self.positions[value]

        # Move each motor to the desired position
        self.y_motor._set_value(position.get("pinholey"))
        self.z_motor._set_value(position.get("pinholez"))

        # Wait for the motors to reach their positions
        #self.wait_for_position()

    def get_value(self):
        """Get the current pinhole position based on the primary motor."""
        return self.y_motor.get_value()

    def wait_for_position(self):
        """Wait for motors to reach their target positions."""
        while any(motor.get_state() != "ON" for motor in [self.y_motor, self.z_motor]):
            time.sleep(0.1)
