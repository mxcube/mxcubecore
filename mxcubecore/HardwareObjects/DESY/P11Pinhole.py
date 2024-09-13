from mxcubecore.HardwareObjects.NState import NState
from configparser import ConfigParser
import copy


class P11Pinhole(NState):
    def __init__(self, name):
        super().__init__(name)
        self._config_file = None
        self._positions = {}  # Initialize the positions dictionary

    def init(self):
        """Initialize the predefined values"""
        self._config_file = self.get_property("config_file")
        super().init()
        self.load_positions()

    def load_positions(self):
        config = ConfigParser()
        config.read(self._config_file)

        if "Pinholes" not in config:
            return

        names = config["Pinholes"]["pinholesizelist"].split(",")
        names[0] = "Down"

        posnames = copy.copy(names)
        posnames[1:] = [f"{posname}um" for posname in posnames[1:]]

        yposlist = map(int, config["Pinholes"]["pinholeyposlist"].split(","))
        zposlist = map(int, config["Pinholes"]["pinholezposlist"].split(","))

        for name, posname, ypos, zpos in zip(names, posnames, yposlist, zposlist):
            self._positions[name] = {
                "pinholey": ypos,
                "pinholez": zpos,
                "posname": posname,
            }

    def get_position_list(self):
        """Return the list of available positions."""
        return list(self._positions.keys())

    def get_value(self):
        """Override get_value to return the current position."""
        return self._positions

    def _set_value(self, value):
        """Override _set_value to change motor positions."""
        if value in self._positions:
            ypos = self._positions[value]["pinholey"]
            zpos = self._positions[value]["pinholez"]
            self.motor_hwobjs["pinholey"].set_value(ypos)
            self.motor_hwobjs["pinholez"].set_value(zpos)
