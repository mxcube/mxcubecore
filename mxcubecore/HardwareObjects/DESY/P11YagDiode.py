import ast
from mxcubecore.HardwareObjects.NState import NState
from collections import OrderedDict
from mxcubecore.BaseHardwareObjects import HardwareObjectState


class P11YagDiode(NState):
    def init(self):
        """Initialize the YAG diode motors and load positions from configuration."""
        super().init()

        self.z_motor = self.get_object_by_role("yagz")
        self.x_motor = self.get_object_by_role("yagx")

        self.load_positions()
        self.load_deltas()

        self.set_value("down")

        # Set _positions for UI access
        self._positions = OrderedDict()
        self._positions = self.positions

        self.log.info(f"YAG/Diode Z Motor initialized: {self.z_motor}")
        self.log.info(f"YAG/Diode X Motor initialized: {self.x_motor}")

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

    def load_deltas(self):
        """Load individual motor deltas from the XML configuration explicitly."""
        self.log.info("Loading deltas from config")

        # Fetch individual deltas for each motor
        delta_x = self.get_property("delta_yagmotorx")
        delta_z = self.get_property("delta_yagmotorz")

        # If a delta is not specified, fallback to a default delta value
        self.deltas = {
            "yagx": float(delta_x) if delta_x is not None else self.default_delta,
            "yagz": float(delta_z) if delta_z is not None else self.default_delta,
        }

        # Log the deltas for each motor
        for motorname, delta in self.deltas.items():
            self.log.info(f"Delta for {motorname}: {delta}")

    def set_value(self, value):
        """Set the yag/diode to the specified position."""

        if value not in self.positions:
            raise ValueError(f"Invalid state value: {value}")

        x_position = self.positions[value]["yagx"]
        z_position = self.positions[value]["yagz"]

        # Move the motors
        self.x_motor._set_value(x_position)
        self.z_motor._set_value(z_position)
        self.log.info(f"Setting collimator to position: {value}")

    def get_value(self):
        """Get the current pinhole position based on the motor positions."""
        current_x = self.x_motor.get_value()
        current_z = self.z_motor.get_value()

        for position_name, position in self.positions.items():
            if self.is_within_deltas(
                position.get("yagx"), current_x, "yagx"
            ) and self.is_within_deltas(position.get("yagz"), current_z, "yagz"):
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
