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
Example yml configuration:

.. code-block:: yaml

 class: ESRF.ESRFBeam.ESRFBeam
 configuration:
   beam_divergence_horizontal: 104
   beam_divergence_vertical: 6.5
   definer_type: definer   # could be also aperture or slits
 objects:
   aperture: udiff_aperture.yml
   definer: beam_definer.yml
"""

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


import logging

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractBeam import AbstractBeam


class ESRFBeam(AbstractBeam):
    """Beam ESRF implementation"""

    unit = "mm"

    def init(self):
        """Initialize the definer type and connect to the hardware"""
        super().init()

        if not self.definer_type:
            _definer_type = []
            if self.aperture:
                _definer_type.append("aperture")

                if self.definer:
                    _definer_type.append("definer")

            self.definer_type = _definer_type
            if len(_definer_type) == 1:
                self.definer_type = _definer_type[0]

        beam_position = self.get_property("beam_position")
        if beam_position:
            self._beam_position_on_screen = tuple(map(float, beam_position.split()))

        if self.aperture:
            self.aperture.connect("valueChanged", self._re_emit_values)
            self.aperture.connect("stateChanged", self._re_emit_values)

        if self.definer:
            self.definer.connect("valueChanged", self._re_emit_values)
            self.definer.connect("stateChanged", self._re_emit_values)

    def _re_emit_values(self, value):
        """Redefine as re_emit_values takes no arguments"""
        self.re_emit_values()

    def _get_aperture_value(self):
        """Get the size and the label of the aperture in place.
        Returns:
            (list, str): Size [mm] [width, height], label.
        """
        _size = self.aperture.get_value().value[1]
        try:
            _label = self.aperture.get_value().name
        except AttributeError:
            _label = str(_size)
        _size /= 1000.0

        return [_size, _size], _label

    def _get_definer_value(self):
        """Get the size and the name of the definer in place.
        Returns:
            (list, str): Size [mm] [width, height], label.
        """
        try:
            value = self.definer.get_value()
            if isinstance(value, tuple):
                return [value[1], value[1]], value[0]
            if value.name != "UNKNOWN":
                return list(value.value), value.name
        except AttributeError:
            logging.getLogger("HWR").info("Could not read beam size")
        return [-1, -1], "UNKNOWN"

    def get_value(self):
        """Get the size (width and heigth) of the beam, its shape and
           its label. The size is in mm.
        Retunrs:
            (tuple): (width, heigth, shape, name), with types
                     (float, float, Enum, str)
        """
        labels = {}
        _label = "UNKNOWN"
        if self.aperture:
            _size, _name = self._get_aperture_value()
            self._beam_size_dict.update({"aperture": _size})
            labels.update({"aperture": _name})

        if self.definer:
            _size, _name = self._get_definer_value()
            self._beam_size_dict.update({"definer": _size})
            labels.update({"definer": _name})

        info_dict = self.evaluate_beam_info()

        try:
            _label = labels[info_dict["label"]]
            self._beam_info_dict["label"] = _label
        except KeyError:
            _label = info_dict["label"]

        return self._beam_width, self._beam_height, self._beam_shape, _label

    def get_value_xml(self):
        """XMLRPC does not handle Enum, the shape is transformed to string"""
        beamsize = self.get_value()
        return beamsize[0], beamsize[1], beamsize[2].value, beamsize[3]

    def get_available_size(self):
        """Get the available predefined beam definer configuration.
        Returns:
            (dict): {"type": ["apertures"], "values": [labels]} or
                    {"type": ["definer"], "values": [labels]} or
                    {"type": ["width", "height"], "values":
                             [low_lim_w, high_lim_w, low_lim_h, high_lim_h]}
        """
        if self.definer_type == "aperture":
            return {
                "type": ["aperture"],
                "values": self.aperture.get_diameter_size_list(),
            }

        if self.definer_type == "definer":
            return {
                "type": ["definer"],
                "values": self.definer.get_predefined_positions_list(),
            }

        return {}

    def get_defined_beam_size(self):
        """Get the predefined beam labels and size.
        Returns:
            (dict): Dictionary wiith list of avaiable beam size labels
                    and the corresponding size (width,height) tuples.
                    {"label": [str, str, ...], "size": [(w,h), (w,h), ...]}
        """
        labels = []
        values = []

        if "definer" in self.definer_type:
            _enum = self.definer.VALUES
        elif "aperture" in self.definer_type:
            _enum = self.aperture.VALUES

        for value in _enum:
            _nam = value.name
            if _nam not in ["IN", "OUT", "UNKNOWN"]:
                labels.append(_nam)
                if isinstance(value.value, tuple):
                    values.append(value.value)
                else:
                    values.append(value.value[0])
        return {"label": labels, "size": values}

    def _set_aperture_size(self, size=None):
        """Move the aperture to the desired size.
        Args:
            size (str): The position name.
        Raises:
            TypeError
        """
        if not isinstance(size, str):
            raise TypeError("Incorrect input value for aperture")

        try:
            _ap = self.aperture.VALUES[size]
        except KeyError:
            _ap = self.aperture.VALUES[f"A{size}"]

        self.aperture.set_value(_ap)

    def _set_definer_size(self, size=None):
        """Move the definer to the desired size.
        Args:
            size (str): The position name.
        Raises:
            TypeError: Invalid size.
        """
        if not isinstance(size, str):
            raise TypeError("Incorrect input value for definer")

        self.definer.set_value(self.definer.VALUES[size])

    def set_value(self, size=None):
        """Set the beam size
        Args:
            size (list): Width, heigth or
                  (str): Aperture or definer name.
        Raises:
            RuntimeError: Beam definer not configured
                          Size out of the limits.
        """
        if self.definer_type == "aperture":
            self._set_aperture_size(size)

        if self.definer_type == "definer":
            self._set_definer_size(size)

    def get_beam_position_on_screen(self):
        if self._beam_position_on_screen == [0, 0]:
            try:
                _beam_position_on_screen = (
                    HWR.beamline.diffractometer.get_beam_position()
                )
            except AttributeError:
                _beam_position_on_screen = (
                    HWR.beamline.sample_view.camera.get_width() / 2,
                    HWR.beamline.sample_view.camera.get_height() / 2,
                )
            self._beam_position_on_screen = _beam_position_on_screen
        return self._beam_position_on_screen

    def get_beam_size(self):
        beam_value = self.get_value()
        return (beam_value[0], beam_value[1])
