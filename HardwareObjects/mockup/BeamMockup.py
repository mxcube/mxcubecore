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

import logging

from HardwareRepository.HardwareObjects.abstract.AbstractBeam import AbstractBeam


class BeamMockup(AbstractBeam):

    def __init__(self, name):
        AbstractBeam.__init__(self, name)

        self._size_dict["slits"] = [9999, 9999]
        self._size_dict["aperture"] = [9999, 9999]
        self._screen_position = [318, 238]
        self._divergence = (0, 0)

    def init(self):
        self._aperture = self.getObjectByRole("aperture")
        if self._aperture is not None:
            self.connect(
                self._aperture,
                "diameterIndexChanged",
                self.aperture_diameter_changed,
            )

            ad = self._aperture.get_diameter_size() / 1000.0
            self._size_dict["aperture"] = [ad, ad]

        self._slits = self.getObjectByRole("slits")
        if self._slits is not None:
            self.connect(self._slits, "valueChanged", self.slits_gap_changed)

            sx, sy = self._slits.get_gaps()
            self._size_dict["slits"] = [sx, sy]

        self.emit("beamPosChanged", (self._screen_position,))

    def aperture_diameter_changed(self, name, size):
        self._size_dict["aperture"] = [size, size]
        self.evaluate_beam_info()
        self.emit_beam_info_change()

    def slits_gap_changed(self, size):
        self._size_dict["slits"] = size
        self.evaluate_beam_info()
        self.emit_beam_info_change()

    def set_beam_position(self, beam_x, beam_y):
        self._screen_position = (beam_x, beam_y)
        self.emit("beamPosChanged", (self._screen_position,))

    def get_info_dict(self):
        return self.evaluate_beam_info()

    def get_value(self):
        """
        Description: returns beam size in microns
        Returns: list with two integers
        """
        self.evaluate_beam_info()
        return float(self._info_dict["size_x"]), float(self._info_dict["size_y"])
        

    def get_shape(self):
        self.evaluate_beam_info()
        return self._info_dict["shape"]

    def get_slits_gap(self):
        self.evaluate_beam_info()
        return self._size_dict["slits"]

    def set_slits_gap(self, width_microns, height_microns):
        if self._slits:
            self._slits.set_horizontal_gap(width_microns / 1000.0)
            self._slits.set_vertical_gap(height_microns / 1000.0)

    def evaluate_beam_info(self):
        """
        Description: called if aperture, slits or focusing has been changed
        Returns: dictionary, {size_x: 0.1, size_y: 0.1, shape: "rectangular"}
        """
        size_x = min(
            self._size_dict["aperture"][0],
            self._size_dict["slits"][0],
        )
        size_y = min(
            self._size_dict["aperture"][1],
            self._size_dict["slits"][1],
        )

        self._info_dict["size_x"] = size_x
        self._info_dict["size_y"] = size_y

        if tuple(self._size_dict["aperture"]) < tuple(self._size_dict["slits"]):
            self._info_dict["shape"] = "ellipse"
        else:
            self._info_dict["shape"] = "rectangular"

        return self._info_dict

    def emit_beam_info_change(self):
        if (
            self._info_dict["size_x"] != 9999
            and self._info_dict["size_y"] != 9999
        ):
            self.emit(
                "beamSizeChanged",
                ((self._info_dict["size_x"], self.beam_info_dict["size_y"]),),
            )
            self.emit("beamInfoChanged", (self._info_dict,))

    def get_aperture_pos_name(self):
        if self._aperture:
            return self._aperture.get_current_pos_name()

    def get_focus_mode(self):
        return
