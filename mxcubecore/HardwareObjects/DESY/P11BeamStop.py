from mxcubecore.HardwareObjects.NState import NState

class P11BeamStop(NState):
    def __init__(self, name):
        super().__init__(name)
        self._positions = {}  # Initialize the positions dictionary

    def init(self):
        """Initialize the beamstop positions."""
        super().init()
        self.load_positions()

    def load_positions(self):
        """Load predefined beamstop positions."""
        self._positions = {
            "In": {"bstopx": 27000, "bstopy": -136, "bstopz": -135},
            "Out": {"bstopx": 69000, "bstopy": -136, "bstopz": -135},
        }

    def get_position_list(self):
        """Return a list of available positions."""
        return list(self._positions.keys())

    def get_value(self):
        """Return the current beamstop position."""
        return self._positions

    def _set_value(self, value):
        """Set the beamstop motors to the new position."""
        if value in self._positions:
            bstopx = self._positions[value]["bstopx"]
            bstopy = self._positions[value]["bstopy"]
            bstopz = self._positions[value]["bstopz"]
            self.motor_hwobjs['bstopx'].set_value(bstopx)
            self.motor_hwobjs['bstopy'].set_value(bstopy)
            self.motor_hwobjs['bstopz'].set_value(bstopz)
