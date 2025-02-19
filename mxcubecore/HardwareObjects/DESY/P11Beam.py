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

__copyright__ = """Copyright The MXCuBE Collaboration"""
__license__ = "LGPLv3+"
__credits__ = ["DESY P11"]
__category__ = "General"

import numpy as np

from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.abstract.AbstractBeam import (
    AbstractBeam,
    BeamShape,
)


class P11Beam(AbstractBeam):
    def init(self):
        self.pinhole_hwobj = self.get_object_by_role("pinhole")
        self._beam_position_on_screen = [340, 256]

        self.focus_sizes = {
            -1: {"label": "unknown", "size": [0.2, 0.2]},
            0: {"label": "flat", "size": [0.2, 0.2]},
            1: {"label": "200x200", "size": [0.2, 0.2]},
            2: {"label": "100x100", "size": [0.1, 0.1]},
            3: {"label": "50x50", "size": [0.05, 0.05]},
            4: {"label": "20x20", "size": [0.02, 0.02]},
            5: {"label": "4x9", "size": [0.009, 0.004]},
        }

        self.mirror_idx_ch = self.get_channel_object("beamsize")
        self.mirror_state_ch = self.get_channel_object("state")

        if self.mirror_idx_ch is not None:
            self.mirror_idx_ch.connect_signal("update", self.mirror_idx_changed)
        if self.mirror_state_ch is not None:
            self.mirror_state_ch.connect_signal("update", self.mirror_state_changed)

        self.mirror_idx_changed()
        self.mirror_state_changed()

    def get_available_size(self):
        """Returns available beam sizes based on the current configuration."""
        return {"type": ["focus"], "values": [self.focus_sizes]}

    def get_defined_beam_size(self):
        """Implements the abstract method to return defined beam sizes."""
        return {
            "label": [item["label"] for item in self.focus_sizes.values()],
            "size": [item["size"] for item in self.focus_sizes.values()],
        }

    def set_value(self, size=None):
        """Sets the beam size with error handling."""
        try:
            if isinstance(size, list):
                self._beam_width, self._beam_height = size
            elif isinstance(size, str):
                matching_size = next(
                    (v for k, v in self.focus_sizes.items() if v["label"] == size), None
                )
                if matching_size:
                    self._beam_width, self._beam_height = matching_size["size"]
                else:
                    raise ValueError(f"Invalid beam size: {size}")

            self.evaluate_beam_info()
            self.log.debug(
                f"Beam size set to: {self._beam_width} x {self._beam_height}"
            )
        except Exception as e:
            self.log.error(f"Error setting beam size: {e}")

    def set_beam_position_on_screen(self, beam_x_y):
        """Sets the beam position on the screen."""
        self._beam_position_on_screen = beam_x_y
        self.re_emit_values()

    def get_beam_info_state(self):
        if self.mirror_state_ch is not None:
            tango_state = self.mirror_state_ch.get_value()
            return self._convert_tango_state(tango_state)

        return self.STATES.READY

    def get_slits_gap(self):
        return None, None

    def mirror_state_changed(self, state=None):
        if state is None:
            state = self.get_beam_info_state()

        converted_state = self._convert_tango_state(state)

        if converted_state == self.STATES.BUSY:
            self.log.debug("Beam movement detected, waiting for READY state...")
            self.emit("userMessage", "Beam is moving...")

        if converted_state == self.STATES.READY:
            self.log.debug("Beam movement stopped, setting UI to READY.")
            self.emit("userMessage", "Beam is ready.")
            self.emit("stateChanged", self.STATES.READY)  # Ensure UI updates

        self.update_state(converted_state)

    def get_beam_size(self):
        """
        Returns the effective beam size, determined by the minimum of
        the pinhole size and the mirror focus size.
        """
        # Get current pinhole size
        pinhole_size = self.pinhole_hwobj.get_value() if self.pinhole_hwobj else None

        # Ensure pinhole size is a float
        try:
            pinhole_size = float(pinhole_size) if pinhole_size is not None else None
        except ValueError:
            self.log.error(f"Invalid pinhole size: {pinhole_size}")
            pinhole_size = None

        # Get current mirror focus size
        mirror_index = self.mirror_idx_ch.get_value()
        mirror_size = self.focus_sizes.get(mirror_index, {"size": [None, None]})["size"]

        # Ensure mirror sizes are floats
        try:
            mirror_size_x = (
                float(mirror_size[0]) if mirror_size[0] is not None else None
            )
            mirror_size_y = (
                float(mirror_size[1]) if mirror_size[1] is not None else None
            )
        except ValueError:
            self.log.error(f"Invalid mirror size: {mirror_size}")
            mirror_size_x, mirror_size_y = None, None

        # Take the minimum size between pinhole and mirror, handling None values
        effective_size_x = (
            min(filter(None, [pinhole_size, mirror_size_x]))
            if pinhole_size or mirror_size_x
            else 0.2
        )
        effective_size_y = (
            min(filter(None, [pinhole_size, mirror_size_y]))
            if pinhole_size or mirror_size_y
            else 0.2
        )

        self.log.debug(
            f"Effective beam size determined: {effective_size_x} x {effective_size_y}"
        )

        return effective_size_x, effective_size_y

    def _convert_tango_state(self, state):
        """Converts Tango state to MXCuBE state."""
        if isinstance(state, str):
            str_state = state.upper()
        else:
            str_state = str(state)

        if str_state in ["ON", "READY"]:
            return self.STATES.READY
        elif str_state in ["MOVING", "BUSY"]:
            return self.STATES.BUSY
        elif str_state in ["FAULT", "ERROR"]:
            return self.STATES.FAULT
        else:
            return self.STATES.UNKNOWN

    #    def _convert_tango_state(self, state):
    #        str_state = str(state)
    #
    #        if str_state == "ON":
    #            _state = self.STATES.READY
    #        elif str_state == "MOVING":
    #            _state = self.STATES.BUSY
    #        else:
    #            _state = self.STATES.FAULT
    #        return _state
    #
    def mirror_idx_changed(self, value=None):
        if value is None:
            value = self.mirror_idx_ch.get_value()

        if value not in self.focus_sizes:
            value = -1  # Fallback to UNKNOWN

        curr_size_item = self.focus_sizes[value]
        self._beam_size_dict["definer"] = curr_size_item["size"]

        self.evaluate_beam_info()
        self.re_emit_values()

        # Emit full beam info
        beam_info = {
            "size_x": curr_size_item["size"][0],
            "size_y": curr_size_item["size"][1],
            "shape": "ellipse",
            "label": curr_size_item["label"],
        }
        self.emit("beamInfoChanged", beam_info)

    def get_beam_position_on_screen(self):
        """Returns the beam position on the screen, defaulting to center if unknown."""
        if self._beam_position_on_screen == [0, 0]:
            try:
                self._beam_position_on_screen = (
                    HWR.beamline.sample_view.camera.get_width() / 2,
                    HWR.beamline.sample_view.camera.get_height() / 2,
                )
            except AttributeError:
                self._beam_position_on_screen = [320, 240]  # Default center
        return self._beam_position_on_screen

    def get_pinhole_size(self):
        if self.pinhole_hwobj is not None:
            return self.pinhole_hwobj.get_value()  # Fetch from pinhole object
        return None  # Return None if no pinhole object found

    def get_beam_focus_label(self):
        value = self.mirror_idx_ch.get_value()

        if value not in self.focus_sizes:
            value = -1
            return "UNKNOWN mirror index"
        else:
            curr_size_item = self.focus_sizes[value]
            self.log.debug(
                f"    current mirror focus is {curr_size_item['label']}: {curr_size_item['size']}"
            )

            return curr_size_item["label"]

    def get_active_focus_mode(self):
        """Returns the currently active focus mode and corresponding beam size."""

        # Read the current beam size index from Tango
        current_index = self.mirror_idx_ch.get_value()

        if current_index not in self.focus_sizes:
            current_index = -1  # Fallback to 'unknown'

        focus_label = self.focus_sizes[current_index]["label"]
        focus_size = self.focus_sizes[current_index]["size"]

        self.log.debug(f"Active focus mode: {focus_label}, Beam size: {focus_size}")

        return focus_label, focus_size

    def get_focus_mode_names(self):
        """Returns the list of available focus modes (beam sizes)."""
        return [self.focus_sizes[k]["label"] for k in sorted(self.focus_sizes.keys())]

    def get_focus_mode_message(self, focus_mode_name):
        """Returns a message describing the selected focus mode."""

        # Find the focus mode in the dictionary
        matching_mode = next(
            (v for k, v in self.focus_sizes.items() if v["label"] == focus_mode_name),
            None,
        )

        if matching_mode:
            message = f"Beam focus mode: {focus_mode_name}, Size: {matching_mode['size'][0]} x {matching_mode['size'][1]} mm"
        else:
            message = f"Unknown focus mode: {focus_mode_name}"

        self.log.debug(f"get_focus_mode_message: {message}")

        return message

    def set_focus_mode(self, focus_mode_name):
        """Sets the focus mode by updating the BeamSize attribute in Tango."""

        try:
            self.emit("userMessage", f"Changing focus mode to {focus_mode_name}...")
            self.log.debug(f"Setting focus mode to {focus_mode_name}")

            # Find the corresponding beam size index
            matching_index = next(
                (
                    k
                    for k, v in self.focus_sizes.items()
                    if v["label"] == focus_mode_name
                ),
                None,
            )

            if matching_index is None:
                raise ValueError(f"Invalid focus mode: {focus_mode_name}")

            # Update Tango attribute
            self.log.debug(f"Updating Tango attribute BeamSize = {matching_index}")
            self.mirror_idx_ch.set_value(matching_index)

            # Force a read to confirm the change
            new_value = self.mirror_idx_ch.get_value()
            self.log.debug(f"BeamSize successfully set to {new_value}")

            # Update internal state
            self.mirror_idx_changed(new_value)

            # Notify UI that the mode has changed
            self.emit("focusModeChanged", focus_mode_name)
            self.emit("beamInfoChanged", self.get_beam_info_dict())

            self.log.info(f"Focus mode successfully set to {focus_mode_name}")
            self.emit("userMessage", f"Focus mode changed to {focus_mode_name}.")

        except Exception as e:
            self.log.error(f"Failed to set focus mode: {e}")
            self.emit("userMessage", f"Error changing focus mode: {e}")
