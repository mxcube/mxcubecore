# encoding: utf-8
#
# This file is part of MXCuBE.
#
# MXCuBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MXCuBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with MXCuBE.  If not, see <https://www.gnu.org/licenses/>.
"""Unattended collect: the hardware side of the unattended collect queue tasks."""

import abc
import math

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © by MXCuBE Collaboration """
__license__ = "LGPLv3+"


class AbstractUnattendedCollect(HardwareObject):
    """One method per task of the unattended collect pipeline.

    Each method receives the context dictionary of its task group, which is how
    the tasks of one sample pass information to each other. A method returns
    False when it found nothing to go on with (no loop, no spots).

    The data collection itself is a standard DataCollection queue entry, done
    at context["centred_position"] when context["found_spots"] is set.

    An optional "murko" object (see Murko.py) can be used for loop detection.
    """

    @property
    def murko(self):
        return self.get_object_by_role("murko")

    @abc.abstractmethod
    def optical_centring(self, context: dict, zoom: int) -> bool:
        """Centre the loop optically at the given zoom step (1: low, 2: high)."""

    @abc.abstractmethod
    def grid_scan(self, context: dict) -> bool:
        """Draw the grid, scan it and set context["found_spots"]."""

    @abc.abstractmethod
    def line_scan(self, context: dict, index: int) -> bool:
        """Run line scan number index."""

    @abc.abstractmethod
    def finalize_centring(self, context: dict) -> bool:
        """Move to the position found by the scans and register it (add_point)."""

    def unmount(self, context: dict, unload: bool = True) -> None:
        """Clear the shapes and unload the sample, unless another one follows."""
        HWR.beamline.sample_view.clear_all()
        HWR.beamline.sample_view.emit("shapesChanged")

        if unload and HWR.beamline.sample_changer.has_loaded_sample():
            HWR.beamline.sample_changer.unload(wait=True)

    def detect_loop(self) -> tuple | None:
        """Bounding box of the loop (x1, y1, x2, y2) in pixels, from murko."""
        image = HWR.beamline.sample_view.get_snapshot(return_as_array=True)
        prediction = self.murko.predict(image)

        if prediction is None:
            return None

        height, width = image.shape[:2]
        x1, y1, x2, y2 = prediction["box"]
        return x1 * width, y1 * height, x2 * width, y2 * height

    def add_grid(self, context: dict, box: tuple):
        """Add a grid of beam sized cells covering box (x1, y1, x2, y2) in pixels."""
        sample_view = HWR.beamline.sample_view
        x1, y1, x2, y2 = box
        ppm_x, ppm_y = HWR.beamline.diffractometer.get_pixels_per_mm()
        beam_width, beam_height = HWR.beamline.beam.get_beam_size()
        cell_width, cell_height = beam_width * ppm_x, beam_height * ppm_y
        num_cols = max(1, math.ceil((x2 - x1) / cell_width))
        num_rows = max(1, math.ceil((y2 - y1) / cell_height))
        width, height = num_cols * cell_width, num_rows * cell_height

        mpos = [
            sample_view.get_centred_point_from_coord(x, y, return_by_names=True)
            for x, y in ((x1, y1), (x1 + width / 2, y1 + height / 2))
        ]
        grid = sample_view.add_shape_from_mpos(mpos, (x1, y1), "G")
        grid.update_from_dict(
            {
                "width": width,
                "height": height,
                "cell_width": cell_width,
                "cell_height": cell_height,
                "num_cols": num_cols,
                "num_rows": num_rows,
                "pixels_per_mm": (ppm_x, ppm_y),
                "beam_pos": tuple(HWR.beamline.beam.get_beam_position_on_screen()),
                "beam_width": beam_width,
                "beam_height": beam_height,
            }
        )
        sample_view.emit("shapesChanged")
        context["grid_id"] = grid.id
        return grid

    def add_point(self, context: dict):
        """Register the current position as the centred point."""
        sample_view = HWR.beamline.sample_view
        positions = sample_view.get_positions()
        point = sample_view.add_shape_from_mpos(
            [positions], sample_view.motor_positions_to_screen(positions), "P"
        )
        sample_view.emit("shapesChanged")
        context["centred_position"] = positions
        context["point_id"] = point.id
        return point
