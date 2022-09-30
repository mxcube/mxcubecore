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
import pytest
from test.pytest import TestHardwareObjectBase

__copyright__ = """ Copyright © 2016 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"
__author__ = "rhfogh"
__date__ = "08/04/2020"


@pytest.fixture
def test_object(beamline):
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
        # Beam position for detector distance 0 (at sample)
        # should give widht / 2 and height /2
        val = test_object.get_beam_position(distance=0)

        assert (
            test_object.width / 2.0,
            test_object.height / 2.0,
        ) == val, "Beam position should be in the middle of the detector"

        # Also check linear regression and that the slope values
        # are read correctly
        val = test_object.get_beam_position(distance=1)

        ax = test_object.get_metadata()["ax"]
        ay = test_object.get_metadata()["ay"]

        assert (
            (test_object.width / 2.0) + ax,
            (test_object.height / 2.0) + ay,
        ) == val, "Beam position should be slightly off center"

    def test_get_radius(self, test_object):
        # Beam position for detector distance 0 (at sample)
        # should give width / 2 and height /2 so the radius should
        # be min(width / 2, height / 2)
        val = test_object.get_radius(distance=0)
        pixel_x, pixel_y = test_object.get_pixel_size()

        assert (
            min(test_object.width / 2 * pixel_x, test_object.height / 2 * pixel_y)
            == val
        ), "Radius should be min(width / 2, height / 2)"

    def test_get_outer_radius(self, test_object):
        # Beam position for detector distance 0 (at sample)
        # should give width / 2 and height /2 so the radius should
        # be min(width / 2, height / 2)
        val = test_object.get_outer_radius(distance=0)
        pixel_x, pixel_y = test_object.get_pixel_size()

        max_delta_x = (test_object.width / 2) * pixel_x
        max_delta_y = (test_object.height / 2) * pixel_y
        outer_radius = math.sqrt(max_delta_x * max_delta_x + max_delta_y * max_delta_y)

        assert (
            outer_radius == val
        ), "Radius should be math.sqrt(max_delta_x * max_delta_x + max_delta_y * max_delta_y)"
