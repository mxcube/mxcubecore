# encoding: utf-8
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
BeamMockup class
"""

__copyright__ = """ Copyright © 2016 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


from HardwareRepository.HardwareObjects.abstract.AbstractBeam import (
    BeamShape,
    AbstractBeam,
)


class BeamMockup(AbstractBeam):
    def __init__(self, name):
        AbstractBeam.__init__(self, name)

        self._beam_size_dict["slits"] = [9999, 9999]
        self._beam_size_dict["aperture"] = [9999, 9999]
        self._beam_position_on_screen = [318, 238]
        self._beam_divergence = (0, 0)

    def init(self):
        self._aperture = self.get_object_by_role("aperture")
        if self._aperture is not None:
            self.connect(
                self._aperture, "diameterIndexChanged", self.aperture_diameter_changed,
            )

            ad = self._aperture.get_diameter_size() / 1000.0
            self._beam_size_dict["aperture"] = [ad, ad]

        self._slits = self.get_object_by_role("slits")
        if self._slits is not None:
            self.connect(self._slits, "valueChanged", self.slits_gap_changed)

            sx, sy = self._slits.get_gaps()
            self._beam_size_dict["slits"] = [sx, sy]

        self.evaluate_beam_info()
        self.emit_beam_info_change()
        self.emit("beamPosChanged", (self._beam_position_on_screen,))

    def aperture_diameter_changed(self, name, size):
        """
        Method called when the aperture diameter changes
        Args:
            name (str): diameter name - not used.
            size (float): diameter size in microns
        """
        self._beam_size_dict["aperture"] = [size, size]
        self.evaluate_beam_info()
        self.emit_beam_info_change()

    def slits_gap_changed(self, size):
        """
        Method called when the slits gap changes
        Args:
            size (tuple): two floats indicates beam size in microns
        """
        self._beam_size_dict["slits"] = size
        self.evaluate_beam_info()
        self.emit_beam_info_change()

    def set_beam_position_on_screen(self, beam_x, beam_y):
        """
        Sets beam mark position on screen
        #TODO move method to sample_view
        Args:
            beam_x (int): horizontal position in pixels
            beam_y (int): vertical position in pixels
        """
        self._beam_position_on_screen = (beam_x, beam_y)
        self.emit("beamPosChanged", (self._beam_position_on_screen,))

    def get_slits_gap(self):
        """
        Returns: tuple with beam size in microns
        """
        self.evaluate_beam_info()
        return self._beam_size_dict["slits"]

    def set_slits_gap(self, width_microns, height_microns):
        """
        Sets slits gap in microns
        Args:
            width_microns (int):
            height_microns (int):
        """
        if self._slits:
            self._slits.set_horizontal_gap(width_microns / 1000.0)
            self._slits.set_vertical_gap(height_microns / 1000.0)

    def get_aperture_pos_name(self):
        """
        Returns (str): name of current aperture position
        """
        if self._aperture:
            return self._aperture.get_current_pos_name()
