#! /usr/bin/env python
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

"""Test suite for Beam hardware object.
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

from test.pytest import TestHardwareObjectBase
from mxcubecore.HardwareObjects.abstract.AbstractBeam import BeamShape

import pytest

__copyright__ = """ Copyright © 2016 - 2022 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


@pytest.fixture
def test_object(beamline):
    """Use the beam object from beamline"""
    result = beamline.beam
    yield result
    # Cleanup code here - restores starting state for next call:
    # NBNB TODO


class TestBeam(TestHardwareObjectBase.TestHardwareObjectBase):
    """TestBeam class"""

    def test_beam_atributes(self, test_object):
        """Test if object exists."""
        assert test_object is not None, "Beam hardware object is None (not initialized)"

    def test_get(self, test_object):
        """
        Test get methods
        """
        beam_div_hor, beam_div_ver = test_object.get_beam_divergence()
        assert isinstance(
            beam_div_hor, (int, float)
        ), "Horizontal beam divergence has to be int or float"
        assert isinstance(
            beam_div_ver, (int, float)
        ), "Vertical beam divergence has to be int or float"
        beam_shape = test_object.get_beam_shape()
        assert isinstance(
            beam_shape, BeamShape
        ), "Beam shape should be defined in BeamShape Enum"

        beam_width, beam_height = test_object.get_beam_size()
        assert isinstance(
            beam_width, (int, float)
        ), "Horizontal beam size has to be int or float"
        assert isinstance(
            beam_height, (int, float)
        ), "Vertical beam size has to be int or float"

    def test_set(self, test_object):
        """
        Test set methods
        """
        max_diameter = max(
            list(map(int, test_object.aperture.get_diameter_size_list()))
        )
        test_object.aperture.set_value(test_object.aperture.VALUES[f"A{max_diameter}"])

        target_width = 0.01
        target_height = 0.01
        test_object.set_beam_size_shape(
            target_width, target_height, BeamShape.RECTANGULAR
        )

        beam_width, beam_height = test_object.get_beam_size()
        assert target_width == beam_width
        assert target_height == beam_height

        beam_shape = test_object.get_beam_shape()
        assert beam_shape == BeamShape.RECTANGULAR

    def test_set_aperture_diameters(self, test_object):
        """
        Set large slit gaps and in the sequence select all aperture diameters.
        Beam shape is eliptical and size defined by the selected aperture
        """
        test_object.slits.set_horizontal_gap(1)
        test_object.slits.set_vertical_gap(1)
        for aperture_diameter in test_object.aperture.get_diameter_size_list():
            test_object.aperture.set_value(
                test_object.aperture.VALUES[f"A{aperture_diameter}"], timeout=2
            )
            print(f"Slits ---> {test_object.slits.get_gaps()}")
            print(f"Aperture ---> {test_object.aperture.get_value()}")
            beam_width, beam_height = test_object.get_beam_size()
            # TODO get_beam_size returns size in mm, but aperture diameters
            # are in microns. Use microns in all beam related hwobj
            assert beam_width == beam_height == int(aperture_diameter) / 1000.0

            beam_shape = test_object.get_beam_shape()
            assert beam_shape == BeamShape.ELIPTICAL

    def test_set_slit_gaps(self, test_object):
        """
        Set slits smaller as the largest aperture diameter.
        In this case beam size and shape is defined by slits
        """
        max_diameter = max(
            list(map(int, test_object.aperture.get_diameter_size_list()))
        )
        test_object.aperture.set_value(test_object.aperture.VALUES[f"A{max_diameter}"])

        target_width = 0.01
        target_height = 0.01
        test_object.slits.set_horizontal_gap(target_width)
        test_object.slits.set_vertical_gap(target_height)

        beam_width, beam_height = test_object.get_beam_size()
        assert target_width == beam_width
        assert target_height == beam_height

        beam_shape = test_object.get_beam_shape()
        assert beam_shape == BeamShape.RECTANGULAR
