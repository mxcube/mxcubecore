import ast
import time
from mxcubecore.HardwareObjects.NState import NState


class P11BeamStop(NState):
    def init(self):
        """Initialize the beamstop motors and load positions from configuration."""
        super().init()

        # Load motors based on the XML configuration
        self.x_motor = self.get_object_by_role("bstopx")
        self.y_motor = self.get_object_by_role("bstopy")  # Uncomment if used in config
        self.z_motor = self.get_object_by_role("bstopz")  # Uncomment if used in config

        # Load and print available positions
        self.load_positions()

    def load_positions(self):
        """Load predefined positions from the XML configuration."""
        self.log.info("Loading beamstop positions from config")
        positions_str = self.get_property("values")

        # Convert the string to a dictionary using ast.literal_eval
        try:
            self.positions = ast.literal_eval(positions_str)
            if isinstance(self.positions, dict):
                self.log.info(f"Available beamstop positions: {self.positions}")
            else:
                raise ValueError("Positions data is not a dictionary")
        except (SyntaxError, ValueError) as e:
            self.log.error(f"Error parsing beamstop positions: {e}")
            raise ValueError("Invalid beamstop positions format in the configuration.")

    def set_value(self, value):
        """Move the beamstop motors to the position corresponding to the given state."""
        if value not in self.positions:
            raise ValueError(f"Invalid position: {value}")

        # Retrieve positions from loaded configuration
        position = self.positions.get(value)

        if position is None:
            raise ValueError(f"No position found for {value}")

        # Move each motor to the desired position
        x_position = position.get("bstopx")
        y_position = position.get("bstopy")  # Optional
        z_position = position.get("bstopz")  # Optional

        # Move motors to respective positions
        if x_position is not None:
            self.x_motor._set_value(x_position)
        # if y_position is not None:
        #    self.y_motor._set_value(y_position)
        # if z_position is not None:
        #    self.z_motor._set_value(z_position)

        # Wait for all motors to reach their positions
        self.wait_for_position()

    def get_value(self):
        """Get the current position of the beamstop (based on the x-axis motor)."""
        return self.x_motor.get_value()  # Return position from primary motor

    def wait_for_position(self):
        """Wait for all motors to reach their target positions."""
        self.log.info("Waiting for beamstop motors to reach their positions")
        while any(
            motor.get_state() != "ON"
            for motor in [self.x_motor, self.y_motor, self.z_motor]
        ):
            time.sleep(0.1)
        self.log.info("Beamstop motors have reached their positions")
