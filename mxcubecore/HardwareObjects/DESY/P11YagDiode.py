import ast
from mxcubecore.HardwareObjects.NState import NState


class P11YagDiode(NState):
    def init(self):
        """Initialize the YAG diode motors and load positions from configuration."""
        super().init()

        # Load motors based on the XML configuration
        self.z_motor = self.get_object_by_role("yagmotorz")
        self.x_motor = self.get_object_by_role(
            "yagmotorx"
        )  # Uncomment if used in config

        self.log.info(f"YAG/Diode Z Motor initialized: {self.z_motor}")
        self.log.info(f"YAG/Diode X Motor initialized: {self.x_motor}")

        # Load and print available positions
        self.load_positions()

    def load_positions(self):
        """Load predefined positions from the XML configuration."""
        self.log.info("Loading YAG/Diode positions from config")
        positions_str = self.get_property("values")

        # Convert the string to a dictionary using ast.literal_eval
        try:
            self.positions = ast.literal_eval(positions_str)
            if isinstance(self.positions, dict):
                self.log.info(f"Available YAG/Diode positions: {self.positions}")
            else:
                raise ValueError("Positions data is not a dictionary")
        except (SyntaxError, ValueError) as e:
            self.log.error(f"Error parsing YAG/Diode positions: {e}")
            raise ValueError("Invalid YAG/Diode positions format in the configuration.")

    def set_value(self, value):
        """Move the YAG diode motors to the position corresponding to the given state."""
        if value not in self.positions:
            raise ValueError(f"Invalid position: {value}")

        # Retrieve positions from loaded configuration
        position = self.positions.get(value)

        if position is None:
            raise ValueError(f"No position found for {value}")

        # Move each motor to the desired position
        x_position = self.positions[value]["yagmotorx"]
        z_position = self.positions[value]["yagmotorz"]

        # Move motors to respective positions
        self.x_motor._set_value(x_position)
        self.z_motor._set_value(z_position)
        self.log.info(f"Setting  Yag/Diode to position: {value}")

    def get_value(self):
        """Get the current position of the YAG diode (based on the z-axis motor)."""
        return self.z_motor.get_value()  # Return position from primary motor
