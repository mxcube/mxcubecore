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
"""Mockup of the unattended collect tasks."""

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractUnattendedCollect import (
    AbstractUnattendedCollect,
)

__copyright__ = """ Copyright © by MXCuBE Collaboration """
__license__ = "LGPLv3+"


class UnattendedCollectMockup(AbstractUnattendedCollect):
    """Configuration properties: task_time (s) and found_spots."""

    GRID_SIZE = 0.2  # mm

    def init(self):
        super().init()
        self.task_time = self.get_property("task_time", 2)
        self.found_spots = self.get_property("found_spots", True)

    def _wait(self):
        gevent.sleep(self.task_time)

    def optical_centring(self, context, zoom):
        self._wait()
        return True

    def grid_scan(self, context):
        beam_x, beam_y = HWR.beamline.beam.get_beam_position_on_screen()
        ppm_x, ppm_y = HWR.beamline.diffractometer.get_pixels_per_mm()
        half_x, half_y = self.GRID_SIZE * ppm_x / 2, self.GRID_SIZE * ppm_y / 2
        self.add_grid(
            context,
            (beam_x - half_x, beam_y - half_y, beam_x + half_x, beam_y + half_y),
        )
        self._wait()
        context["found_spots"] = self.found_spots
        return context["found_spots"]

    def line_scan(self, context, index):
        self._wait()
        return True

    def finalize_centring(self, context):
        self.add_point(context)
        return True
