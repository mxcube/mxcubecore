from mxcubecore.HardwareObjects.NState import NState

class P11Yag(NState):
    def __init__(self, name):
        super().__init__(name)
        self._positions = {}  # Initialize the positions dictionary

    def init(self):
        """Initialize the YAG positions."""
        super().init()
        self.load_positions()

    def load_positions(self):
        """Load predefined YAG positions."""
        self._positions = {
            "Diode": {"yagx": 30, "yagz": 13900},
            "YagIn": {"yagx": 1200, "yagz": 11080},
            "Out": {"yagx": -50, "yagz": -12550},
        }

    def get_position_list(self):
        """Return a list of available positions."""
        return list(self._positions.keys())

    def get_value(self):
        """Return the current position."""
        return self._positions

    def _set_value(self, value):
        """Set the motors to the new position."""
        if value in self._positions:
            yagx = self._positions[value]["yagx"]
            yagz = self._positions[value]["yagz"]
            self.motor_hwobjs['yagx'].set_value(yagx)
            self.motor_hwobjs['yagz'].set_value(yagz)
