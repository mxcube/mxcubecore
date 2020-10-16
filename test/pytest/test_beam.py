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
"""
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import pytest
from HardwareRepository.test.pytest import TestHardwareObjectBase
from HardwareRepository.HardwareObjects.abstract.AbstractBeam import BeamShape

__copyright__ = """ Copyright © 2016 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


@pytest.fixture
def obj_to_test(beamline):
    result = beamline.beam
    yield result
    # Cleanup code here - restores starting state for next call:
    # NBNB TODO

def test_beam_atributes(self, obj_to_test):
    assert test_object is not None, "Beam hardware object is None (not initialized)"

    

def test_get(self, obj_to_test):
    """
    Test get methods
    """
    if True:
        beam_div_hor, beam_div_ver = obj_to_test.get_beam_divergence()
        assert isinstance(
            beam_div_hor, (int, float)
        ), "Horizontal beam divergence has to be int or float"
        assert isinstance(
            beam_div_ver, (int, float)
        ), "Vertical beam divergence has to be int or float"
        beam_shape = obj_to_test.get_beam_shape()
        assert isinstance(
            beam_shape, BeamShape
        ), "Beam shape should be defined in BeamShape Enum"

        beam_width, beam_height = obj_to_test.get_beam_size()
        assert isinstance(
            beam_width, (int, float)
        ), "Horizontal beam size has to be int or float"
        assert isinstance(
            beam_height, (int, float)
        ), "Vertical beam size has to be int or float"

def test_set(self, obj_to_test):
    if True:
        max_diameter = max(obj_to_test.aperture.get_diameter_size_list())
        obj_to_test.aperture.set_diameter_size(max_diameter)

        target_width = 0.01
        target_height = 0.01
        obj_to_test.set_beam_size_shape(
            target_width, target_height, BeamShape.RECTANGULAR
        )

        beam_width, beam_height = obj_to_test.get_beam_size()
        assert target_width == beam_width
        assert target_height == beam_height

        beam_shape = obj_to_test.get_beam_shape()
        assert beam_shape == BeamShape.RECTANGULAR

def test_set_aperture_diameters(self, obj_to_test):
    """
    Set large slit gaps and in the sequence select all aperture diameters.
    Beam shape is eliptical and size defined by the selected aperture
    """
    if True:
        obj_to_test.slits.set_horizontal_gap(1)
        obj_to_test.slits.set_vertical_gap(1)
        for aperture_diameter in obj_to_test.aperture.get_diameter_size_list():
            obj_to_test.aperture.set_diameter_size(aperture_diameter)
            beam_width, beam_height = obj_to_test.get_beam_size()
            # TODO get_beam_size returns size in mm, but aperture diameters are in microns
            # Use microns in all beam related hwobj
            assert beam_width == beam_height == aperture_diameter / 1000.0

            beam_shape = obj_to_test.get_beam_shape()
            assert beam_shape == BeamShape.ELIPTICAL

def test_set_slit_gaps(self, obj_to_test):
    """
    Set slits smaller as the largest aperture diameter.
        In this case beam size and shape is defined by slits
    """
    if True:
        max_diameter = max(obj_to_test.aperture.get_diameter_size_list())
        obj_to_test.aperture.set_diameter_size(max_diameter)

        target_width = 0.01
        target_height = 0.01
        obj_to_test.slits.set_horizontal_gap(target_width)
        obj_to_test.slits.set_vertical_gap(target_height)

        beam_width, beam_height = obj_to_test.get_beam_size()
        assert target_width == beam_width
        assert target_height == beam_height

        beam_shape = obj_to_test.get_beam_shape()
        assert beam_shape == BeamShape.RECTANGULAR
