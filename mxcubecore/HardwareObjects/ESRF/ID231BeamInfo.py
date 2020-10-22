"""
[Name] BeamInfo

[Description]
BeamInfo hardware object is used to define final beam size and shape.
It can include aperture, slits and/or other beam definer (lenses or other eq.)

[Emited signals]
beamInfoChanged

[Included Hardware Objects]
-----------------------------------------------------------------------
| name            | signals          | functions
-----------------------------------------------------------------------
 aperture_HO	    apertureChanged
 slits_HO
 beam_definer_HO
-----------------------------------------------------------------------
"""

import logging
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository import HardwareRepository as HWR


class BeamInfo(Equipment):
    def __init__(self, *args):
        Equipment.__init__(self, *args)

        self.beam_size_slits = [9999, 9999]
        self.beam_size_aperture = [9999, 9999]
        self.beam_size_definer = [9999, 9999]
        self.beam_position = [0, 0]

        self.aperture_HO = None
        self.slits_HO = None
        self.beam_info_dict = {}

    def init(self):
        try:
            self.aperture_HO = HWR.get_hardware_repository().get_hardware_object(
                self.get_property("aperture")
            )
            self.connect(self.aperture_HO, "apertureChanged", self.aperture_pos_changed)
        except Exception:
            logging.getLogger("HWR").debug("BeamInfo: aperture not defined correctly")
        try:
            self.slits_HO = HWR.get_hardware_repository().get_hardware_object(
                self.get_property("slits")
            )
            self.connect(self.slits_HO, "gapSizeChanged", self.slits_gap_changed)
        except Exception:
            logging.getLogger("HWR").debug("BeamInfo: slits not defined correctly")
        try:
            self.connect(
                HWR.beamline.beam.beam_definer,
                "definerPosChanged",
                self.definer_pos_changed,
            )
        except Exception:
            logging.getLogger("HWR").debug(
                "BeamInfo: beam definer not defined correctly"
            )

        self.beam_position_hor = self.get_channel_object("beam_position_hor")
        self.beam_position_hor.connect_signal("update", self.beam_pos_hor_changed)
        self.beam_position_ver = self.get_channel_object("beam_position_ver")
        self.beam_position_ver.connect_signal("update", self.beam_pos_ver_changed)
        self.chan_beam_size_microns = self.get_channel_object("beam_size_microns")
        self.chan_beam_shape_ellipse = self.get_channel_object("beam_shape_ellipse")

    def beam_pos_hor_changed(self, value):
        self.beam_position[0] = value
        self.emit("beamPosChanged", (self.beam_position,))

    def beam_pos_ver_changed(self, value):
        self.beam_position[1] = value
        self.emit("beamPosChanged", (self.beam_position,))

    def get_beam_position(self):
        return self.beam_position

    def set_beam_position(self, beam_x, beam_y):
        self.beam_position = [beam_x, beam_y]
        self.beam_position_hor.set_value(int(beam_x))
        self.beam_position_ver.set_value(int(beam_y))

    def aperture_pos_changed(self, nameList, name, size):
        self.beam_size_aperture = size
        self.evaluate_beam_info()
        self.re_emit_values()

    def slits_gap_changed(self, size):
        self.beam_size_slits = size
        self.evaluate_beam_info()
        self.re_emit_values()

    def definer_pos_changed(self, name, size):
        self.beam_size_definer = size
        self.evaluate_beam_info()
        self.re_emit_values()

    def get_beam_info(self):
        return self.evaluate_beam_info()

    def get_beam_size(self):
        """
        Description: returns beam size in microns
        Resturns: list with two integers
        """
        self.evaluate_beam_info()
        return (
            int(self.beam_info_dict["size_x"] * 1000),
            int(self.beam_info_dict["size_y"] * 1000),
        )

    def get_beam_shape(self):
        self.evaluate_beam_info()
        return self.beam_info_dict["shape"]

    def get_slits_gap(self):
        self.evaluate_beam_info()
        return self.beam_size_slits

    def evaluate_beam_info(self):
        """
        Description: called if aperture, slits or focusing has been changed
        Returns: dictionary, {size_x: 0.1, size_y: 0.1, shape: "rectangular"}
        """
        size_x = min(
            self.beam_size_aperture[0],
            self.beam_size_slits[0],
            self.beam_size_definer[0],
        )
        size_y = min(
            self.beam_size_aperture[1],
            self.beam_size_slits[1],
            self.beam_size_definer[1],
        )

        self.beam_info_dict["size_x"] = size_x
        self.beam_info_dict["size_y"] = size_y

        if self.beam_size_aperture < self.beam_size_slits:
            self.beam_info_dict["shape"] = "ellipse"
        else:
            self.beam_info_dict["shape"] = "rectangular"

        return self.beam_info_dict

    def re_emit_values(self):
        if (
            self.beam_info_dict["size_x"] != 9999
            and self.beam_info_dict["size_y"] != 9999
        ):
            self.emit(
                "beamSizeChanged",
                ((self.beam_info_dict["size_x"], self.beam_info_dict["size_y"]),),
            )
            self.emit("beamInfoChanged", (self.beam_info_dict,))
            if self.chan_beam_size_microns is not None:
                self.chan_beam_size_microns.set_value(
                    (
                        self.beam_info_dict["size_x"] * 1000,
                        self.beam_info_dict["size_y"] * 1000,
                    )
                )
            if self.chan_beam_shape_ellipse is not None:
                self.chan_beam_shape_ellipse.set_value(
                    self.beam_info_dict["shape"] == "ellipse"
                )
