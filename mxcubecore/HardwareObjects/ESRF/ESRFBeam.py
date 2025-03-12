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
Beam ESRF implementation class - methods to define the size and shape of the beam.
"""

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


import logging

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractBeam import AbstractBeam, BeamShape


class ESRFBeam(AbstractBeam):
    """Beam ESRF implementation"""

    unit = "mm"

    def __init__(self, name) -> None:
        super().__init__(name)
        self._beam_check_obj = None
        self._monitorbeam_obj = None

    def init(self) -> None:
        """Initialize hardware"""
        super().init()

        _definer_type = []
        self._aperture = self.get_object_by_role("aperture")
        if self._aperture:
            _definer_type.append("aperture")

        _slits = self.get_property("slits")
        _bliss_obj = self.get_object_by_role("bliss")
        if _slits:
            self._slits = {}
            _definer_type.append("slits")
            for name in _slits.split():
                _key, _val = name.split(":")
                self._slits.update({_key: _bliss_obj.getattribute(_val)})

        self._definer = self.get_object_by_role("definer")
        if self._definer:
            _definer_type.append("definer")

        if len(_definer_type) == 1:
            self._definer_type = _definer_type[0]
        else:
            self._definer_type = None

        self._definer_type = self.get_property("definer_type") or self._definer_type

        beam_position = self.get_property("beam_position")

        if beam_position:
            self._beam_position_on_screen = tuple(map(float, beam_position.split()))

        if self._aperture:
            self._aperture.connect("valueChanged", self._re_emit_values)
            self._aperture.connect("stateChanged", self._re_emit_values)

        if self._definer:
            self._definer.connect("valueChanged", self._re_emit_values)
            self._definer.connect("stateChanged", self._re_emit_values)

        self._monitorbeam_obj = self.get_object_by_role("monitor_beam")

        beam_check = self.get_property("beam_check_name")
        if beam_check and _bliss_obj:
            self._beam_check_obj = getattr(_bliss_obj, beam_check)

    def _re_emit_values(self, value):
        # redefine as re_emit_values takes no arguments
        self.re_emit_values()

    def _get_aperture_value(self) -> tuple[list[float, float], str]:
        """Get the size and the label of the aperture in place.

        Returns:
            Size [mm] [width, height], label.
        """
        _size = self.aperture.get_value().value[1]
        try:
            _label = self.aperture.get_value().name
        except AttributeError:
            _label = str(_size)
        _size /= 1000.0

        return [_size, _size], _label

    def _get_definer_value(self) -> tuple[list[float, float], str]:
        """Get the size and the name of the definer in place.

        Returns:
            Size [mm] [width, height], label.
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

    def _get_slits_size(self) -> dict[str, float]:
        """Get the size of the slits in place.

        Returns:
            ``{"width": float, "heigth": float}``.
        """
        beam_size = {}
        for _key, _val in self.slits:
            beam_size.update({_key: abs(_val.position)})
        return beam_size

    def _get_value(self) -> tuple[float, float, BeamShape, str]:
        """Get the size (width and heigth) of the beam, its shape and
           its label. The size is in milimeters.

        Retunrs:
            Four-item tuple: width, heigth, shape, name.
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

    def get_value_xml(self) -> tuple[float, float, str, str]:
        """XMLRPC does not handle Enum, the shape is transformed to string.
        Retunrs:
            Four-item tuple: width, heigth, shape, name
        """
        beamsize = self.get_value()
        return beamsize[0], beamsize[1], beamsize[2].value, beamsize[3]

    def get_available_size(self) -> dict:
        """Get the available predefined beam definer configuration.
        Returns:
            ``{"type": ["aperture"], "values": [labels]}`` or
            ``{"type": ["definer"], "values": [labels]}`` or
            ``{"type": ["width", "height"], "values":
                     [low_lim_w, high_lim_w, low_lim_h, high_lim_h]}``
        """
        if self._definer_type == "aperture":
            return {
                "type": ["aperture"],
                "values": self.aperture.get_diameter_size_list(),
            }

        if self._definer_type == "definer":
            return {
                "type": ["definer"],
                "values": self.definer.get_predefined_positions_list(),
            }

        if self._definer_type in (self.slits, "slits"):
            # get the list of the slits motors range
            _low_w, _high_w = self.slits["width"].get_limits()
            _low_h, _high_h = self.slits["height"].get_limits()
            return {
                "type": ["width", "height"],
                "values": [_low_w, _high_w, _low_h, _high_h],
            }

        return {}

    def get_defined_beam_size(self) -> dict:
        """Get the predefined beam labels and size.

        Returns:
            Dictionary wiith list of avaiable beam size labels and
            the corresponding size (width,height) tuples.
            ``{"label": [str, str, ...], "size": [(w,h), (w,h), ...]}``
        """
        labels = []
        values = []

        if self._definer_type == "slits":
            # get the list of the slits motors range
            _low_w, _high_w = self.slits["width"].get_limits()
            _low_h, _high_h = self.slits["height"].get_limits()
            return {
                "label": ["low", "high"],
                "size": [(_low_w, _low_h), (_high_w, _high_h)],
            }

        if self._definer_type == "aperture":
            _enum = self.aperture.VALUES
        elif self._definer_type == "definer":
            _enum = self.definer.VALUES

        for value in _enum:
            _nam = value.name
            if _nam not in ["IN", "OUT", "UNKNOWN"]:
                labels.append(_nam)
                if isinstance(value.value, tuple):
                    values.append(value.value)
                else:
                    values.append(value.value[0])
        return {"label": labels, "size": values}

    def _set_slits_size(self, size: list[float, float]):
        """Move the slits to the desired position.

        Args:
            Two-items list:  width, heigth in milimeters.

        Raises:
            RuntimeError: Size out of the limits.
               TypeError: Invalid size
        """

        if not isinstance(size, list):
            msg = "Incorrect input value for slits"
            raise TypeError(msg)
        w_lim = self.slits["width"].get_limits()
        h_lim = self.slits["heigth"].get_limits()
        try:
            msg = "Size out of the limits"
            if min(w_lim) > size[0] > max(w_lim):
                raise RuntimeError(msg)
            if min(h_lim) > size[1] > max(h_lim):
                raise RuntimeError(msg)
            self.slits["width"].set_value(size[0])
            self.slits["heigth"].set_value(size[1])
        except TypeError as err:
            raise TypeError("Invalid size") from err

    def _set_aperture_size(self, size: str):
        """Move the aperture to the desired size.

        Args:
            The position name.

        Raises:
            TypeError
        """
        if not isinstance(size, str):
            msg = "Incorrect input value for aperture"
            raise TypeError(msg)

        try:
            _ap = self.aperture.VALUES[size]
        except KeyError:
            _ap = self.aperture.VALUES[f"A{size}"]

        self.aperture.set_value(_ap)

    def _set_definer_size(self, size: str):
        """Move the definer to the desired size.

        Args:
            The position name.

        Raises:
            TypeError: Invalid size.
        """
        if not isinstance(size, str):
            msg = "Incorrect input value for definer"
            raise TypeError(msg)

        self._definer.set_value(self.definer.VALUES[size])

    def set_value(self, size: list[float] | str | None = None):
        """Set the beam size.

        Args:
            Two-items list: width and heigth for slits or
            aperture or definer name.

        Raises:
            RuntimeError: Beam definer not configured
                          Size out of the limits.
        """
        if self._definer_type in (self.slits, "slits"):
            self._set_slits_size(size)

        if self._definer_type in (self.aperture, "aperture"):
            self._set_aperture_size(size)

        if self._definer_type in (self.definer, "definer"):
            self._set_definer_size(size)

    def get_beam_position_on_screen(self) -> list[int, int]:
        """Get the beam position.

        Returns:
            X and Y coordinates of the beam position in pixels.
        """
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

    def get_beam_size(self) -> tuple[float, float]:
        """Get the beam size.

        Returns:
            Two-item tuple: width and height.
        """
        beam_value = self.get_value()
        return beam_value[0], beam_value[1]

    def _is_beam(self) -> bool:
        """Check if there is beam.

        Returns:
            ``True`` if beam present, ``False`` otherwise
        """
        return self._beam_check_obj.is_beam()

    def wait_for_beam(self, timeout: float | None = None):
        """Wait until beam present.

        Args:
            Optional - timeout in seconds,
            If timeout == 0: return at once and do not wait.
            if timeout is None: wait forever (default).

        Raises:
            RuntileError if no beam after the specified timeout.
        """
        if self._monitorbeam_obj:
            try:
                timeout = timeout or self._beam_check_obj.timeout
                if self._monitorbeam_obj.get_value().value:
                    return self._beam_check_obj.wait_for_beam(timeout)
            except AttributeError:
                return True
        return True
