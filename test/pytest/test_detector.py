#! /usr/bin/env python
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
# along with MXCuBE. If not, see <https://www.gnu.org/licenses/>.
"""
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import math
from test.pytest import TestHardwareObjectBase
import pytest

__copyright__ = """ Copyright © 2016 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


@pytest.fixture
def test_object(beamline):
    """Use the detector object from beamline"""
    result = beamline.detector
    yield result
    # Cleanup code here - restores starting state for next call:
    # NBNB TODO


class TestDetector(TestHardwareObjectBase.TestHardwareObjectBase):
    def test_detector_atributes(self, test_object):
        assert (
            test_object is not None
        ), "Detector hardware object is None (not initialized)"
        exp_time_limits = test_object.get_exposure_time_limits()
        has_shutterless = test_object.has_shutterless()

    def test_get_beam_position(self, test_object):
        bx = test_object.get_metadata()["bx"]
        by = test_object.get_metadata()["by"]
        ax = test_object.get_metadata()["ax"]
        ay = test_object.get_metadata()["ay"]

        for _d in range(0, 100):
            val = test_object.get_beam_position(distance=_d)
            beam_position = (_d * ax + bx, _d * ay + by)

            assert beam_position == val, "Beam position should be slightly off center"

    def test_get_radius(self, test_object):
        for _d in range(0, 100):
            val = test_object.get_radius(distance=_d)
            pixel_x, pixel_y = test_object.get_pixel_size()
            bx, by = test_object.get_beam_position(_d)

            rrx = min(test_object.width - bx, bx) * pixel_x
            rry = min(test_object.height - by, by) * pixel_y

            assert min(rrx, rry) == val, "Radius incorrect"

    def test_get_outer_radius(self, test_object):
        for _d in range(0, 100):
            val = test_object.get_outer_radius(distance=_d)
            pixel_x, pixel_y = test_object.get_pixel_size()

            bx, by = test_object.get_beam_position(_d)

            max_delta_x = max(bx, test_object.width - bx) * pixel_x
            max_delta_y = max(by, test_object.height - by) * pixel_y

            outer_radius = math.sqrt(
                max_delta_x * max_delta_x + max_delta_y * max_delta_y
            )

            assert outer_radius == val, "Outer radius incorrect"
