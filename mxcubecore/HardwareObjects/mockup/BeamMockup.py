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
BeamMockup class - methods to define the size and shape of he beam.

Example xml configuration:

.. code-block:: xml

  <object class="BeamMockup">
    <object href="/beam_definer" role="definer"/>
    <!-- accepted definer_type values: aperture, slits, definer -->
    <definer_type>definer</definer_type>
    <beam_divergence_vertical>0</beam_divergence_vertical>
    <beam_divergence_horizontal>0</beam_divergence_horizontal>
  </object>
"""

__copyright__ = """ Copyright © by MXCuBE Collaboration """
__license__ = "LGPLv3+"

from ast import literal_eval

from mxcubecore.HardwareObjects.abstract.AbstractBeam import AbstractBeam


class BeamMockup(AbstractBeam):
    """Beam Mockup class"""

    def __init__(self, name):
        super().__init__(name)
        self._definer_type = None

    def init(self):
        """Initialize hardware"""
        super().init()

        self._aperture = self.get_object_by_role("aperture")
        if self._aperture:
            _definer_type = "aperture"
            self._aperture.connect("valueChanged", self.aperture_diameter_changed)

        self._slits = self.get_object_by_role("slits")
        if self._slits:
            _definer_type = "slits"
            self._slits.connect("valueChanged", self.slits_gap_changed)

        self._definer = self.get_object_by_role("definer")
        if self._definer:
            _definer_type = "definer"
            self._definer.connect("valueChanged", self._re_emit_values)

        self._definer_type = self.get_property("definer_type") or _definer_type

        self._beam_position_on_screen = literal_eval(
            self.get_property("beam_position", "[318, 238]")
        )

        self.re_emit_values()
        self.emit("beamPosChanged", (self._beam_position_on_screen,))

    def _re_emit_values(self, *args, **kwargs):
        self.re_emit_values()

    def _get_aperture_value(self):
        """Get the size and the label of the aperture in place.
        Returns:
            (list, str): Size [mm] (width, height), label.
        """
        _size = self.aperture.get_value().value[0]
        try:
            _label = self.aperture.get_value().name
        except AttributeError:
            _label = str(_size)
        _size /= 1000.0

        return [_size, _size], _label

    def _get_definer_value(self):
        """Get the size and the name of the definer in place.
        Returns:
            (list, str): Size [mm] (width, height), label.
        """
        try:
            value = self.definer.get_value()
            if isinstance(value, tuple):
                return [value[1], value[1]], value[0]
            return list(value.value), value.name
        except AttributeError:
            return [-1, -1], "UNKNOWN"

    def _get_slits_value(self):
        """Get the size of the slits in place.
        Returns:
             (list, str): Size [mm] (width, height), label.
        """
        _size = self.slits.get_gaps()
        return _size, "slits"

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

        if self.slits:
            _size, _name = self._get_slits_value()
            self._beam_size_dict.update({"slits": _size})
            labels.update({"slits": _name})

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

    def aperture_diameter_changed(self, aperture):
        """
        Method called when the aperture diameter changes
        Args:
            aperture (aperture(Enum)): Aperture enum.
        """

        size = aperture.value[0]
        self.aperture.update_value(aperture)
        self._beam_size_dict["aperture"] = [size, size]
        self.evaluate_beam_info()
        self._beam_info_dict["label"] = aperture.name
        self.re_emit_values()

    def slits_gap_changed(self, size):
        """
        Method called when the slits gap changes
        Args:
            size (tuple): two floats indicates beam size in microns
        """
        self._beam_size_dict["slits"] = size
        self._beam_info_dict["label"] = "slits"
        self.evaluate_beam_info()
        self.re_emit_values()

    def set_beam_position_on_screen(self, beam_x_y):
        """Sets beam mark position on screen
        #TODO move method to sample_view
        Args:
            beam_x_y (list): Position [x, y] [pixel]
        """
        self._beam_position_on_screen = beam_x_y
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
        if self.slits:
            self.slits.set_horizontal_gap(width_microns / 1000.0)
            self.slits.set_vertical_gap(height_microns / 1000.0)

    def get_aperture_pos_name(self):
        """
        Returns (str): name of current aperture position
        """
        return self.aperture.get_current_pos_name()

    def get_defined_beam_size(self):
        """Get the predefined beam labels and size.
        Returns:
            (dict): Dictionary with lists of avaiable beam size labels
                    and the corresponding size (width,height) tuples.
                    {"label": [str, str, ...], "size": [(w,h), (w,h), ...]}
        """
        labels = []
        values = []
        if self._definer_type == "slits":
            return {
                "label": ["low", "high"],
                "size": [self.slits.get_min_limits(), self.slits.get_max_limits()],
            }

        if self._definer_type == "aperture":
            _enum = self.aperture.VALUES
        elif self._definer_type == "definer":
            _enum = self.definer.VALUES

        for value in _enum:
            _nam = value.name
            if _nam not in ["IN", "OUT", "UNKNOWN"]:
                labels.append(_nam)
                if self._definer_type == "aperture":
                    values.append((value.value[0] / 1000.0, value.value[0] / 1000.0))
                else:
                    values.append(value.value)
        return {"label": labels, "size": values}

    def get_available_size(self):
        """Get the available predefined beam definer configuration.
        Returns:
            (dict): {"type": ["apertures"], "values": [labels]} or
                    {"type": ["definer"], "values": [labels]} or
                    {"type": ["width", "height"], "values":
                             [low_lim_w, high_lim_w, low_lim_h, high_lim_h]}

        """
        if self._definer_type == "aperture":
            # get list of the available apertures
            return {
                "type": ["aperture"],
                "values": self.aperture.get_diameter_size_list(),
            }

        if self._definer_type == "definer":
            # get list of the available definer positions
            return {
                "type": ["definer"],
                "values": self.definer.get_predefined_positions_list(),
            }

        if self._definer_type == "slits":
            # get the list of the slits motors range
            _low_w, _low_h = self.slits.get_min_limits()
            _high_w, _high_h = self.slits.get_max_limits()
            return {
                "type": ["width", "height"],
                "values": [_low_w, _high_w, _low_h, _high_h],
            }

        return {}

    def set_value(self, size=None):
        """Set the beam size
        Args:
            size (list): Width, heigth or
                  (str): Aperture or definer definer name.
        Raises:
            RuntimeError: Beam definer not configured
                          Size out of the limits.
            TypeError: Wrong size type.
        """
        if self._definer_type in (self.slits, "slits"):
            if not isinstance(size, list):
                raise TypeError("Incorrect input value for slits")
            self.slits.set_horizontal_gap(size[0])
            self.slits.set_vertical_gap(size[1])

        if self._definer_type in (self.aperture, "aperture"):
            if not isinstance(size, str):
                raise TypeError("Incorrect input value for aperture")
            self.aperture.set_value(self.aperture.VALUES[size], timeout=2)

        if self._definer_type in (self.definer, "definer"):
            if not isinstance(size, str):
                raise TypeError("Incorrect input value for definer")
            self.definer.set_value(self.definer.VALUES[size], timeout=2)
