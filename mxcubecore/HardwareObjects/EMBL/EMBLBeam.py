#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
EMBLBeamInfo
Hardware object is used to define final beam size and shape.
It can include aperture, slits and/or beam focusing hwobj
"""
import ast
import sys
import logging

from mxcubecore.HardwareObjects.abstract.AbstractBeam import AbstractBeam


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


class EMBLBeam(AbstractBeam):
    """Hardware object is used to define final beam size and shape"""

    def __init__(self, *args):
        """Defines all variables"""

        AbstractBeam.__init__(self, *args)

        self.focus_mode = None
        self.aperture_pos_name = None
        self.default_beam_divergence = None

        self.chan_beam_position_hor = None
        self.chan_beam_position_ver = None
        self.chan_beam_size_microns = None
        self.chan_beam_shape_ellipse = None

    def init(self):
        """Initialized all variables"""

        self._beam_info_dict["size_x"] = 9999
        self._beam_info_dict["size_y"] = 9999

        self._aperture = self.get_object_by_role("aperture")
        if self._aperture is not None:
            self.connect(
                self._aperture,
                "diameterIndexChanged",
                self.aperture_diameter_changed,
            )
        else:
            logging.getLogger("HWR").debug("BeamInfo: Aperture hwobj not defined")

        self._slits = self.get_object_by_role("slits")
        if self._slits is not None:
            self.connect(self._slits, "valueChanged", self.slits_gap_changed)
        else:
            logging.getLogger("HWR").debug("BeamInfo: Slits hwobj not defined")

        self._definer = self.get_object_by_role("beam_focusing")
        if self._definer is not None:
            (
                focus_mode_name,
                self._beam_size_dict["definer"],
            ) = self._definer.get_active_focus_mode()
            self.connect(
                self._definer,
                "focusingModeChanged",
                self.focusing_mode_changed,
            )
        else:
            logging.getLogger("HWR").debug("BeamInfo: Beam focusing hwobj not defined")

        self.chan_beam_position_hor = self.get_channel_object("BeamPositionHorizontal")
        if self.chan_beam_position_hor:
            self.chan_beam_position_hor.connect_signal(
                "update", self.beam_pos_hor_changed
            )
            self.beam_pos_hor_changed(self.chan_beam_position_hor.get_value())
        self.chan_beam_position_ver = self.get_channel_object("BeamPositionVertical")
        if self.chan_beam_position_ver:
            self.chan_beam_position_ver.connect_signal(
                "update", self.beam_pos_ver_changed
            )
        self.chan_beam_size_microns = self.get_channel_object("BeamSizeMicrons")
        self.chan_beam_shape_ellipse = self.get_channel_object("BeamShapeEllipse")
        self.default_beam_divergence = ast.literal_eval(
            self.get_property("defaultBeamDivergence")
        )

    def get_beam_divergence_hor(self):
        """Returns beam horizontal beam divergence

        :return: float
        """
        beam_divergence_hor = None

        if self._definer is not None:
            beam_divergence_hor = self._definer.get_divergence_hor()
        else:
            beam_divergence_hor = self.default_beam_divergence[0]

        return beam_divergence_hor

    def get_beam_divergence_ver(self):
        """Returns vertical beam divergence

        :return: float
        """
        beam_divergence_ver = None

        if self._definer is not None:
            beam_divergence_ver = self._definer.get_divergence_ver()
        else:
            beam_divergence_ver = self.default_beam_divergence[1]

        return beam_divergence_ver

    def beam_pos_hor_changed(self, value):
        """Updates horizontal beam position

        :param value: horizontal beam position
        :type value: float
        :return: None
        """
        self._beam_position_on_screen[0] = value
        print("hor ", value)
        self.emit("beamPosChanged", (self._beam_position_on_screen,))

    def beam_pos_ver_changed(self, value):
        """Updates vertical beam position

        :param value: vertical beam position
        :type value: float
        :return: None
        """
        self._beam_position_on_screen[1] = value
        print("ver ", value)
        self.emit("beamPosChanged", (self._beam_position_on_screen,))

    def get_beam_position(self):
        """Returns beam mark position

        :return: [float, float]
        """
        if self.chan_beam_position_hor and self.chan_beam_position_ver:
            self._beam_position_on_screen = [
                self.chan_beam_position_hor.get_value(),
                self.chan_beam_position_ver.get_value(),
            ]
        return self._beam_position_on_screen

    def set_beam_position(self, beam_x, beam_y):
        """Sets the beam mark position

        :param beam_x: horizontal beam mark position
        :type beam_x: int
        :param beam_y: vertical beam mark position
        :type beam_y: int
        :return: None
        """
        self._beam_position_on_screen = [beam_x, beam_y]

        if self.chan_beam_position_hor and self.chan_beam_position_ver:
            self.chan_beam_position_hor.set_value(int(beam_x))
            self.chan_beam_position_ver.set_value(int(beam_y))
        else:
            self.emit("beamPosChanged", (self._beam_position_on_screen,))

    def aperture_diameter_changed(self, name, size):
        """Method called when aperture changed. Evaluates beam mark position

        :param name: position name
        :type name: str
        :param size: diameter size
        :type size: float
        :return: None
        """
        self._beam_size_dict["aperture"] = [size, size]
        self.aperture_pos_name = name
        self.update_beam_info()
        self.re_emit_values()

    def get_aperture_pos_name(self):
        """Returns current aperture position

        :return: position name as str
        """
        return self._aperture.get_current_pos_name()

    def slits_gap_changed(self, size):
        """Method when slits gap changes. Evaluates beam mark position

        :param size: gap size
        :type size: list of two floats
        :return: None
        """
        self._beam_size_dict["slits"] = size
        self.update_beam_info()
        self.re_emit_values()

    def focusing_mode_changed(self, name, size):
        """Updates beam mark size when beam focusing changes

        :param name: focusing name
        :type name: str
        :param size: beam size
        :type size: float
        :return: None
        """
        self.focus_mode = name
        self._beam_size_dict["definer"] = size
        self.update_beam_info()
        self.re_emit_values()

    def get_beam_size(self):
        """Returns beam size in microns

        :return: Tuple(int, int)
        """
        self.update_beam_info()
        return (self._beam_info_dict["size_x"], self._beam_info_dict["size_y"])

    def get_beam_shape(self):
        """Returns beam shape

        :return: beam shape as str
        """
        self.update_beam_info()
        return self._beam_info_dict["shape"]

    def get_slits_gap(self):
        """Returns slits gap

        :return: list of two floats
        """
        self.update_beam_info()
        slits_gap = [None, None]

        if self._beam_size_dict["slits"] != [sys.float_info.max, sys.float_info.max]:
            slits_gap = self._beam_size_dict["slits"]

        return slits_gap

    def set_slits_gap(self, width_microns, height_microns):
        """Sets slits gaps

        :param width_microns: width in microns
        :type width_microns: float
        :param height_microns: height in microns
        :type height_microns: float
        :return: None
        """
        if self.focus_mode == "Double":
            logging.getLogger("GUI").warning(
                "Slits are disabled in the Double focus mode"
            )
        else:
            self._slits.set_horizontal_gap(width_microns / 1000.0)
            self._slits.set_vertical_gap(height_microns / 1000.0)

    def update_beam_info(self):
        """Called if aperture, slits or focusing has been changed

        :return: dictionary,{size_x:0.1, size_y:0.1, shape:"rectangular"}
        """
        size_x = min(
            self._beam_size_dict["aperture"][0],
            self._beam_size_dict["slits"][0],
            self._beam_size_dict["definer"][0],
        )
        size_y = min(
            self._beam_size_dict["aperture"][1],
            self._beam_size_dict["slits"][1],
            self._beam_size_dict["definer"][1],
        )

        if size_x == 9999 or size_y == 9999:
            return

        if (
            abs(size_x - self._beam_info_dict.get("size_x", 0)) > 1e-3
            or abs(size_y - self._beam_info_dict.get("size_y", 0)) > 1e-3
        ):
            self._beam_info_dict["size_x"] = size_x
            self._beam_info_dict["size_y"] = size_y

            if self._beam_size_dict["aperture"] <= [size_x, size_y]:
                self._beam_info_dict["shape"] = "ellipse"
            else:
                self._beam_info_dict["shape"] = "rectangular"

            if (
                self.chan_beam_size_microns is not None
                and self._beam_info_dict["size_x"] < 1.3
                and self._beam_info_dict["size_y"] < 1.3
            ):
                self.chan_beam_size_microns.set_value(
                    (
                        self._beam_info_dict["size_x"] * 1000,
                        self._beam_info_dict["size_y"] * 1000,
                    )
                )
            if self.chan_beam_shape_ellipse:
                self.chan_beam_shape_ellipse.set_value(
                    self._beam_info_dict["shape"] == "ellipse"
                )

    def re_emit_values(self):
        """Emits signals

        :return: None
        """
        if (
            self._beam_info_dict["size_x"] != sys.float_info.max
            and self._beam_info_dict["size_y"] != sys.float_info.max
        ):
            self.emit(
                "beamSizeChanged",
                (
                    (
                        self._beam_info_dict["size_x"] * 1000,
                        self._beam_info_dict["size_y"] * 1000,
                    ),
                ),
            )
            self.emit("beamInfoChanged", (self._beam_info_dict,))

    def get_beam_info(self):
        """Returns beam info

        :return: dict
        """
        self.update_beam_info()
        return self._beam_info_dict

    def re_emit_values(self):
        """Reemits all signals

        :return: None
        """
        self.emit("beamInfoChanged", (self._beam_info_dict,))
        self.emit("beamPosChanged", (self._beam_position_on_screen,))

    def move_beam(self, direction, step=1):
        """Moves beam mark

        :param direction: direction
        :type direction: str
        :param step: step in pixels
        :type step: int
        :return: None
        """
        if direction == "left":
            self.chan_beam_position_hor.set_value(
                self._beam_position_on_screen[0] - step
            )
        elif direction == "right":
            self.chan_beam_position_hor.set_value(
                self._beam_position_on_screen[0] + step
            )
        elif direction == "up":
            self.chan_beam_position_ver.set_value(
                self._beam_position_on_screen[1] - step
            )
        elif direction == "down":
            self.chan_beam_position_ver.set_value(
                self._beam_position_on_screen[1] + step
            )

    def get_focus_mode(self):
        """Returns current focusing mode

        :return: str
        """
        focus_mode = None

        if self._definer is not None:
            focus_mode = self._definer.get_focus_mode()

        return focus_mode
