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
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
BeamDefiner ESRF implementation class - methods to define the size and shape of
the beam.
"""

__copyright__ = """ Copyright © 2023 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


import logging

from mxcubecore.HardwareObjects.abstract.AbstractBeam import (
    AbstractBeam,
    BeamShape,
)
from mxcubecore import HardwareRepository as HWR


class ESRFBeam(AbstractBeam):
    """Beam ESRF implementation"""

    def __init__(self, name):
        super().__init__(name)
        self._aperture = None
        self._slits = {}
        self._complex = None
        self._definer_type = None
        self.beam_height = None
        self.beam_width = None

    def init(self):
        """Initialize hardware"""
        super().init()
        # self._definer_type = self.get_property("definer")

        self._aperture = self.get_object_by_role("aperture")
        if self._aperture:
            self._definer_type = "aperture"

        _slits = self.get_property("slits")
        if _slits:
            self._definer_type = "slits"
            _bliss_obj = self.get_object_by_role("bliss")
            for name in _slits.split():
                _key, _val = name.split(":")
                self._slits.update({_key: _bliss_obj.__getattribute__(_val)})

        self._complex = self.get_object_by_role("complex")
        if self._complex:
            self._definer_type = "complex"

        beam_position = self.get_property("beam_position")

        if beam_position:
            self._beam_position_on_screen = tuple(map(float, beam_position.split()))

        if self._aperture:
            self._aperture.connect("valueChanged", self._re_emit_values)
            self._aperture.connect("stateChanged", self._re_emit_values)

        if self._complex:
            self._complex.connect("valueChanged", self._re_emit_values)
            self._complex.connect("stateChanged", self._re_emit_values)

    def _re_emit_values(self, *args, **kwargs):
        self.re_emit_values()

    def _get_aperture_size(self):
        """Get the size and the label of the aperture in place.
        Returns:
            (float, str): Size [mm], label.
        """
        _size = self._aperture.get_value().value[1]

        try:
            _label = self._aperture.get_value().value[1]
        except AttributeError:
            _label = str(_size)

        return _size / 1000.0, _label

    def _get_complex_size(self):
        """Get the size and the name of the definer in place.
        Returns:
            (float, str): Size [mm], label.
        """
        try:
            value = self._complex.get_value()
            return value.value[1], value.name
        except AttributeError:
            logging.getLogger("HWR").info("Could not read beam size")
            return (-1, -1), "UNKNOWN"

    def _get_complex_size_old(self):
        """Get the size and the name of the definer in place.
        Returns:
            (float, str): Size [mm], label.
        """
        try:
            _size = self._complex.size_by_name[
                self._complex.get_current_position_name()
            ]
            _name = self._complex.get_current_position_name()
        except KeyError:
            logging.getLogger("HWR").info("Could not read beam size")
            _size, _name = (-1, -1), "UNKNOWN"

        return _size, _name

    def _get_slits_size(self):
        """Get the size of the slits in place.
        Returns:
            (dict): {"width": float, "heigth": float}.
        """
        beam_size = {}
        for _key, _val in self._slits:
            beam_size.update({_key: abs(_val.position)})
        return beam_size

    def get_value(self):
        """Get the size (width and heigth) of the beam and its shape.
            The size is in mm.
        Retunrs:
            (tuple): Dictionary (width, heigth, shape, name), with types
                               (float, float, Enum, str)
        """
        _shape = BeamShape.UNKNOWN

        _beamsize_dict = {}
        if self._aperture:
            _size, _name = self._get_aperture_size()
            _beamsize_dict.update({_name: [_size]})
            _shape = BeamShape.ELIPTICAL

        if self._complex:
            _size, _name = self._get_complex_size()
            _beamsize_dict.update({_name: _size})
            _shape = BeamShape.ELIPTICAL

        if self._slits:
            _beamsize_dict.update({"slits": self._get_slits_size().values()})

        def _beam_size_compare(size):
            return size[0]

        # find which device has the minimum size
        try:
            _val = min(_beamsize_dict.values(), key=_beam_size_compare)

            _key = [k for k, v in _beamsize_dict.items() if v == _val]

            _name = _key[0]
            self.beam_width = _val[0]

            if "slits" in _key:
                self.beam_height = _val[1]
                _shape = BeamShape.RECTANGULAR
            elif len(_val) > 1:
                self.beam_height = _val[1]
            else:
                self.beam_height = _val[0]
        except (ValueError, TypeError):
            return None, None, _shape, "none"

        return self.beam_width, self.beam_height, _shape, _name

    def get_available_size(self):
        """Get the available predefined beam definer configuration.
        Returns:
            (dict): apertures {name: dimension} or
                    slits {"width": motor object, "heigth", motor object} or
                    complex definer {name: dimension}.
        """
        _type = "enum"
        if self._definer_type in (self._aperture, "aperture"):
            # get list of the available apertures
            aperture_list = self._aperture.get_diameter_size_list()
            return {"type": [_type], "values": aperture_list}

        if self._definer_type in (self._complex, "complex"):
            # return {"type": [_type], "values": self._complex.size_list}
            return {
                "type": [_type],
                "values": self._complex.get_predefined_positions_list(),
            }

        if self._definer_type in (self._slits, "slits"):
            # get the list of the slits motors range
            _low_w, _high_w = self._slits["width"].get_limits()
            _low_h, _high_h = self._slits["height"].get_limits()
            return {
                "type": ["range", "range"],
                "values": [_low_w, _high_w, _low_h, _high_h],
            }

        return []

    def _set_slits_size(self, size=None):
        """Move the slits to the desired position.
        Args:
            size (list): Width, heigth [mm].
        Raises:
            RuntimeError: Size out of the limits.
               TypeError: Invalid size
        """
        w_lim = self._slits["width"].get_limits()
        h_lim = self._slits["heigth"].get_limits()
        try:
            if min(w_lim) > size[0] > max(w_lim):
                raise RuntimeError("Size out of the limits")
            if min(h_lim) > size[1] > max(h_lim):
                raise RuntimeError("Size out of the limits")
            self._slits["width"].set_value(size[0])
            self._slits["heigth"].set_value(size[1])
        except TypeError:
            raise TypeError("Invalid size")

    def _set_aperture_size(self, size=None):
        """Move the aperture to the desired size.
        Args:
            size (str): The position name.
        """
        try:
            _enum = getattr(self._aperture.VALUES, "A" + size)
        except AttributeError:
            _enum = getattr(self._aperture.VALUES, size)

        self._aperture.set_value(_enum)

    def _set_complex_size(self, size=None):
        """Move the complex definer to the desired size.
        Args:
            size (str): The position name.
        """
        self._complex.set_value(size)

    def set_value(self, size=None):
        """Set the beam size
        Args:
            size (list): Width, heigth or
                  (str): Aperture or complex definer name.
        Raises:
            RuntimeError: Beam definer not configured
                          Size out of the limits.
        """
        if self._definer_type in (self._slits, "slits"):
            self._set_slits_size(size)

        if self._definer_type in (self._aperture, "aperture"):
            self._set_aperture_size(size)

        if self._definer_type in (self._complex, "complex"):
            self._set_complex_size(size)

    def get_beam_position_on_screen(self):
        if self._beam_position_on_screen == (0, 0):
            try:
                _beam_position_on_screen = (
                    HWR.beamline.config.diffractometer.get_beam_position()
                )
            except AttributeError:
                _beam_position_on_screen = (
                    HWR.beamline.config.sample_view.camera.get_width() / 2,
                    HWR.beamline.config.sample_view.camera.get_height() / 2,
                )
            self._beam_position_on_screen = _beam_position_on_screen
        return self._beam_position_on_screen

    def get_beam_size(self):
        beam_value = self.get_value()
        return (beam_value[0], beam_value[1])
