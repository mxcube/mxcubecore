import logging
from mxcubecore.HardwareObjects.abstract.AbstractActuator import AbstractActuator

"""You may need to import monkey when you test standalone"""
# from gevent import monkey
# monkey.patch_all(thread=False)

class BIOMAXAperture(AbstractActuator):
    """Aperture calss to change the diameter and emmiting messages"""
    POSITIONS = ("BEAM", "OFF", "PARK")

    def __init__(self, *args):
        AbstractActuator.__init__(self, *args)

    def init(self):
        super().init()

        self.motor_name = self.get_property("motor_name")
        self.username = self.get_property("username")

        self.aperture_position = self.add_channel(
            {"type": "exporter", "name": "AperturePosition"}, "AperturePosition"
        )
        self.connect(
                    self.aperture_position, "update", self.position_changed
                )

        self.aperture_diameters = self.add_channel(
            {"type": "exporter", "name": "ApertureDiameters"}, "ApertureDiameters"
        )

        self._diameter_size_list = self.aperture_diameters.get_value()

        self.current_aperture_diameters = self.add_channel(
            {"type": "exporter", "name": "CurrentApertureDiameterIndex"}, 
            "CurrentApertureDiameterIndex"
        )
        self.connect(
                    self.current_aperture_diameters, "update", self.diameter_changed
                )

        self.diameter_list = self.aperture_diameters.get_value()
        self.set_position = self.move_to_position
    
    def set_diameter_size(self, diameter_size):
        """Setting new size for aperture diameter.

        Args:
            diameter_size (str): new size for aperture.

        Returns:
            None
        """
        if int(diameter_size) in self._diameter_size_list:
            self.current_aperture_diameters.set_value(
                self._diameter_size_list.index(int(diameter_size))
                )
            self._current_diameter_index = self.current_aperture_diameters.get_value()
            self._diameter_size_list = self.aperture_diameters.get_value()
            self.emit(
                "diameterIndexChanged",
                self._current_diameter_index,
                self._diameter_size_list[self._current_diameter_index] / 1000.0,
            )

    def get_diameter_size(self):
        """getting the size of aperture diameter.
        
        Args:
            None

        Returns:
            int: size of aperture diameter
        """
        self._diameter_size_list = self.aperture_diameters.get_value()
        self._current_diameter_index = self.current_aperture_diameters.get_value()
        return self._diameter_size_list[self._current_diameter_index]
    
    def get_diameter_size_list(self):
        """getting the list of available diameter sizes for aperture.
        
        Args:
            None

        Returns:
            List of int: diameter sizes of aperture
        """
        return self.aperture_diameters.get_value()

    def move_to_position(self, position_name):
        """changing to the new position, "BEAM", "OFF" or "PARK".
        
        Args:
            position name

        Returns:
            None
        """
        logging.getLogger().debug(
            "%s: trying to move %s to %s:%f",
            self.name(),
            self.motor_name,
            position_name,
        )
        if position_name == "Outbeam":
            self.aperture_position.set_value("OFF")
        else:
            try:
                self.aperture_position.set_value("BEAM")
            except Exception:
                logging.getLogger("HWR").exception(
                    "Cannot move motor %s: invalid position name.", self.username
                )
            if self.aperture_position.get_value() != "BEAM":
                self.aperture_position.set_value("BEAM")

    def get_position_list(self):
        """getting the available aperture positions.
        
        Args:
            None

        Returns:
            tuple: ("BEAM", "OFF", "PARK")
        """
        return BIOMAXAperture.POSITIONS

    def get_position_name(self):
        """getting the position of aperture.

        Returns:
            str: current position as str
        """
        return self.aperture_position.get_value()

    def position_changed(self, position):
        self.emit("valueChanged", position)
    
    def diameter_changed(self, diameter):
        self._current_diameter_index = diameter
        self.emit("valueChanged", diameter)
        self.emit(
            "diameterIndexChanged",
            self._current_diameter_index,
            self._diameter_size_list[self._current_diameter_index] / 1000.0,
        )