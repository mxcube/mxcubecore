import ast
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState


class P11Collimator(AbstractNState):
    """Collimator hardware object class"""

    def init(self):
        """Initialize the collimator with its motors and positions."""
        super().init()

        # Retrieve motors using their roles
        self.y_motor = self.get_object_by_role("collimatory")  # Y-axis motor
        self.z_motor = self.get_object_by_role("collimatorz")  # Z-axis motor

        self.log.info(f"Y Motor initialized: {self.y_motor}")
        self.log.info(f"Z Motor initialized: {self.z_motor}")

        # Load positions from XML configuration
        self.load_positions()

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
