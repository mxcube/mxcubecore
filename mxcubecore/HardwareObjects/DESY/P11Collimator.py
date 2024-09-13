from mxcubecore.HardwareObjects.NState import NState


class P11Collimator(NState):
    def __init__(self, name):
        super().__init__(name)
        self._positions = {}  # Initialize the positions dictionary

    def init(self):
        """Initialize the collimator positions."""
        super().init()
        self.load_positions()

    def load_positions(self):
        """Load predefined collimator positions."""
        self._positions = {
            "Up": {"collimy": 561, "collimz": 9141},
            "Down": {"collimy": 550, "collimz": -12000},
        }

    def get_position_list(self):
        """Return a list of available positions."""
        return list(self._positions.keys())

    def get_value(self):
        """Return the current collimator position."""
        return self._positions

    def _set_value(self, value):
        """Set the collimator motors to the new position."""
        if value in self._positions:
            collimy = self._positions[value]["collimy"]
            collimz = self._positions[value]["collimz"]
            self.motor_hwobjs["collimy"].set_value(collimy)
            self.motor_hwobjs["collimz"].set_value(collimz)
