import logging
from mxcubecore.HardwareObjects import BeamInfo
from mxcubecore.HardwareObjects.abstract import AbstractBeam
from mxcubecore import HardwareRepository as HWR
from enum import Enum, unique

"""You may need to import monkey when you test standalone"""
# from gevent import monkey
# monkey.patch_all(thread=False)


@unique
class BeamShape(Enum):
    """Beam shape definitions"""

    UNKNOWN = "unknown"
    RECTANGULAR = "rectangular"
    ELIPTICAL = "ellipse"


class BIOMAXBeamInfo(BeamInfo.BeamInfo, AbstractBeam.AbstractBeam):
    """Beam information"""

    def __init__(self, *args):
        BeamInfo.BeamInfo.__init__(self, *args)
        self.beam_position = (0, 0)
        self._beam_width = None
        self._beam_height = None
        self._beam_shape = None
        self._beam_label = None
        self._beam_divergence = (None, None)
        self._beam_position_on_screen = [None, None]  # TODO move to sample_view
        self.beam_size_hor = None
        self.beam_size_ver = None
        self._beam_size_dict = {}
        self._beam_info_dict ={}

    def init(self):
        BeamInfo.BeamInfo.init(self)
        self._beam_size_dict["aperture"] = [9999, 9999]
        self._beam_size_dict["slits"] = [9999, 9999]
        self._beam_position_on_screen = (687, 519)
        self._beam_divergence = (0, 0)
        self.beam_position = (0, 0)

        self.aperture_hwobj = self.get_object_by_role("aperture")

        if self.aperture_hwobj is not None:
            self.connect(
                self.aperture_hwobj,
                "diameterIndexChanged",
                self.aperture_diameter_changed,
            )
            ad = self.aperture_hwobj.get_diameter_size() / 1000.0
            self._beam_size_dict["aperture"] = [ad, ad]
            self._beam_info_dict["label"] = self.aperture_hwobj.get_diameter_size()
        else:
            logging.getLogger("HWR").warning("BeamInfo: Aperture hwobj not defined")

        self.beam_size_hor = self.get_object_by_role("beam_size_hor")
        self.beam_size_ver = self.get_object_by_role("beam_size_ver")

        if self.beam_size_hor and self.beam_size_ver:
            self.beam_size_hor.connect("valueChanged", self.beam_size_hor_changed)
            self.beam_size_ver.connect("valueChanged", self.beam_size_ver_changed)
            self.beam_size_ver.connect("stateChanged", self.beam_size_state_changed)
            self._beam_info_dict["size_y"] = self.beam_size_ver.get_value() / 1000
            self._beam_info_dict["size_x"] = self.beam_size_hor.get_value() / 1000

        self.evaluate_beam_info()
        self.re_emit_values()
        self.emit("beamPosChanged", (self._beam_position_on_screen,))

    def get_beam_info_dict(self):
        """getting beam information

        Returns:
            dict: copy of beam_info_dict
        """
        self.evaluate_beam_info()
        if self.beam_size_hor and self.beam_size_ver:
            self._beam_info_dict["size_x"] = self.beam_size_hor.get_value() / 1000
            self._beam_info_dict["size_y"] = self.beam_size_ver.get_value() / 1000
        self._beam_info_dict["label"] = self.aperture_hwobj.get_diameter_size()
        self.get_beam_shape()
        return self._beam_info_dict.copy()

    def aperture_diameter_changed(self, name, size):
        """Method called when the aperture diameter changes

        Args:
            name (str): diameter name - not used.
            size (float): diameter size in microns
        """
        self._beam_size_dict["aperture"] = [size, size]
        self._beam_info_dict["label"] = int(size * 1000)
        self.evaluate_beam_info()
        self.re_emit_values()

    def beam_size_hor_changed(self, value):
        """Method called when the beam size changes

        Args:
            value (float):
        """
        self._beam_info_dict["size_x"] = value
        self.evaluate_beam_info()
        self.re_emit_values()

    def beam_size_ver_changed(self, value):
        """Method called when the beam size changes

        Args:
            value (float):
        """
        self._beam_info_dict["size_y"] = value
        self.evaluate_beam_info()
        self.re_emit_values()

    def beam_size_state_changed(self, value):
        """called if aperture, slits or focusing has been changed"""
        self.re_emit_values()
        self.get_beam_info_dict()

        if self._beam_size_dict["aperture"] < self._beam_size_dict["slits"]:
            self._beam_info_dict["shape"] = "ellipse"
        else:
            self._beam_info_dict["shape"] = "rectangular"
        return self._beam_info_dict

    def get_slits_gap(self):
        """
        Returns: tuple with beam size in microns
        """
        self.evaluate_beam_info()
        return self._beam_size_dict["slits"]

    def get_value(self):
        """getting beam information, used by frontend

        Returns:
            list out of {size_x:0.1, size_y:0.1, shape:"rectangular"}
        """
        # return list(self.get_beam_info_dict().values())
        current_aperture = float(self.aperture_hwobj.get_diameter_size()) / 1000

        return current_aperture, current_aperture, BeamShape.ELIPTICAL, current_aperture

    def get_available_size(self):
        """getting the list of available diameter sizes for aperture.

        Args:
            None

        Returns:
            enum: diameter sizes of aperture
        """
        aperture_list = self.aperture_hwobj.get_diameter_size_list()
        return {"type": "enum", "values": aperture_list}

    def get_aperture_pos_name(self):
        """getting the position of aperture.

        Returns:
            str: current position as str
        """
        if self.aperture_hwobj:
            return self.aperture_hwobj.get_position_name()

    def get_beam_position(self):
        """getting beam position

        Args:
            None

        Returns:
            Tuple: beam position
        """

        return self.beam_position

    def get_motors_states(self):
        # (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,2,3,4,5)
        _st1 = self.beam_size_hor.get_state()
        _st2 = self.beam_size_ver.get_state()
        # motor always unusable on start since the motor is always off
        if _st1 == 1:
            _st1 = 2
        if _st2 == 1:
            _st2 = 2
        motors_states = {"mot01": _st1, "mot02": _st2}
        return motors_states

    def set_value(self, value):
        """Setting new size for aperture diameter.

        Args:
            diameter_size (str): new size for aperture.

        Returns:
            None
        """
        self.aperture_hwobj.set_diameter_size(value)

    def set_beam_size(self, size_x, size_y):
        """Setting beam size in millimeters

        Returns:
            None
        """
        logging.getLogger("HWR").info("Beamfocus moving to %s x %s" % (size_x, size_y))
        size_x = int(size_x)
        size_y = int(size_y)
        if not (
            (size_x == 20 and size_y == 5)
            or (size_x == 50 and size_y == 50)
            or (size_x == 100 and size_y == 100)
        ):
            logging.getLogger("user_level_log").error(
                "Beamfocus value is not a valid size."
            )
            raise Exception("The value is not a valid size.")
        try:
            self.beam_size_hor._set_value(size_x)
            self.beam_size_ver._set_value(size_y)
            self.evaluate_beam_info()
            self.re_emit_values()

        except Exception as ex:
            logging.getLogger("user_level_log").error("Beamfocus moving error")
            logging.getLogger("HWR").error("Beamfocus moving error, %s" % ex)

        # now we adapt the aperture
        if size_x == 20 and size_y == 5:
            logging.getLogger("HWR").info("Changing aperture to 10 um")
            self.aperture_hwobj.set_diameter_size("10")
            self.evaluate_beam_info()
            self.re_emit_values()
        elif size_x == 50 and size_y == 50:
            logging.getLogger("HWR").info("Changing aperture to 50 um")
            self.aperture_hwobj.set_diameter_size("50")
            self.evaluate_beam_info()
            self.re_emit_values()
        elif size_x == 100 and size_y == 100:
            logging.getLogger("HWR").info("Changing aperture to 100 um")
            self.aperture_hwobj.set_diameter_size("100")
            self.evaluate_beam_info()
            self.re_emit_values()
        else:
            logging.getLogger("HWR").warning(
                "Beamfocus, suitable aperture value not found."
            )

    def get_beam_size(self):
        """getting beam size in millimeters

        Returns:
            list with two integers
        """
        self.evaluate_beam_info()
        _ap = self.aperture_hwobj.get_diameter_size()
        return _ap, _ap

    def set_beam_position_on_screen(self, beam_x, beam_y):
        """Setting beam mark position on screen

        Args:
            beam_x (int): horizontal position in pixels
            beam_y (int): vertical position in pixels
        """
        self._beam_position_on_screen = (beam_x, beam_y)
        self.emit("beamPosChanged", (self._beam_position_on_screen,))
