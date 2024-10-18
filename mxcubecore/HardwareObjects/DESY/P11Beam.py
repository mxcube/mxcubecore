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
        """Implements the abstract method to set the beam size."""
        if isinstance(size, list):
            self._beam_width, self._beam_height = size
        elif isinstance(size, str):
            matching_size = next(
                (v for k, v in self.focus_sizes.items() if v["label"] == size), None
            )
            if matching_size:
                self._beam_width, self._beam_height = matching_size["size"]
        self.evaluate_beam_info()

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

        self.update_state(self._convert_tango_state(state))

    def _convert_tango_state(self, state):
        str_state = str(state)

        if str_state == "ON":
            _state = self.STATES.READY
        elif str_state == "MOVING":
            _state = self.STATES.BUSY
        else:
            _state = self.STATES.FAULT
        return _state

    def mirror_idx_changed(self, value=None):
        if value is None:
            value = self.mirror_idx_ch.get_value()

        self.log.debug(f"P11Beam - mirror idx changed. now is {value}")

        if value not in self.focus_sizes:
            value = -1
            self.log.debug(f"    - UNKNOWN mirror index")

        curr_size_item = self.focus_sizes[value]
        self.log.debug(
            f"    current mirror focus is {curr_size_item['label']}: {curr_size_item['size']}"
        )

        self._beam_size_dict["aperture"] = curr_size_item["size"]

        self.evaluate_beam_info()
        self.re_emit_values()

    def get_pinhole_size(self):
        # Keep it default as the pinhole and beamsize interaction is locked for now
        return 200

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
