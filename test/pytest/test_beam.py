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

    def test_get_defined_beam_size(self, test_object):
        """Check the defined beam size values for each definer type"""
        if test_object.definer:
            test_object._definer_type = "definer"
            _vals = test_object.get_defined_beam_size()
            _list = test_object.definer.get_predefined_positions_list()
            assert _vals["label"] == _list

        if test_object.aperture:
            test_object._definer_type = "aperture"
            _vals = test_object.get_defined_beam_size()
            _list = test_object.aperture.get_diameter_size_list()
            assert _vals["label"] == _list

        if test_object.slits:
            test_object._definer_type = "slits"
            _range = test_object.get_defined_beam_size()
            assert _range["label"] == ["low", "high"]
            _low_w, _low_h = test_object.slits.get_min_limits()
            _high_w, _high_h = test_object.slits.get_max_limits()
            assert _range["size"] == [[_low_w, _low_h], [_high_w, _high_h]]

    def test_get_available_size(self, test_object):
        """Check the available beam size values for each definer type"""
        if test_object.definer:
            test_object._definer_type = "definer"
            _vals = test_object.get_available_size()
            _list = test_object.definer.get_predefined_positions_list()
            assert _vals["type"][0] == "definer"
            assert _vals["values"] == _list

        if test_object.aperture:
            test_object._definer_type = "aperture"
            _vals = test_object.get_available_size()
            _list = test_object.aperture.get_diameter_size_list()
            assert _vals["type"][0] == "aperture"
            assert _vals["values"] == _list

        if test_object.slits:
            test_object._definer_type = "slits"
            _vals = test_object.get_available_size()
            assert _vals["type"] == ["width", "height"]
            _low_w, _low_h = test_object.slits.get_min_limits()
            _high_w, _high_h = test_object.slits.get_max_limits()
            assert _vals["values"] == [_low_w, _high_w, _low_h, _high_h]

    def test_evaluate_beam_size(self, test_object):
        """
        The apertutre and the slits have the same size,
        slits are the beam definer type.
        Slits are bigger than the aperture, slits are the beam definer type.
        """
        if test_object.aperture:
            _list = []
            for val in test_object.aperture.get_diameter_size_list():
                _list.append(int(test_object.aperture.VALUES[val].value[0]))
            max_diameter = max(_list)
            test_object.aperture.set_value(
                test_object.aperture.VALUES[f"A{max_diameter}"], timeout=2
            )
            target_width = target_height = max_diameter / 1000.0

        if test_object.slits is not None:
            target_width = 0.1
            target_height = 0.1
            test_object.slits.set_horizontal_gap(target_width)
            test_object.slits.set_vertical_gap(target_height)

        beam_width, beam_height, beam_shape, beam_label = test_object.get_value()
        assert target_width == beam_width
        assert target_height == beam_height
        if beam_label == "slits":
            assert beam_shape == BeamShape.RECTANGULAR
        else:
            assert beam_shape == BeamShape.ELLIPTICAL
            if test_object._definer_type == "aperture":
                assert beam_label == f"A{max_diameter}"

        if test_object.slits is not None:
            test_object.slits.set_horizontal_gap(0.2)
            test_object.slits.set_vertical_gap(0.2)
        beam_width, beam_height, beam_shape, beam_label = test_object.get_value()
        target_width = target_height = max_diameter / 1000.0
        assert target_width == beam_width
        assert target_height == beam_height
        if beam_label == "slits":
            assert beam_shape == BeamShape.RECTANGULAR
        else:
            assert beam_shape == BeamShape.ELLIPTICAL
            if test_object._definer_type == "aperture":
                assert beam_label == f"A{max_diameter}"

    def test_set_aperture_diameters(self, test_object):
        """
        Set large slit gaps and in the sequence select all aperture diameters.
        Beam shape is elliptical and size defined by the selected aperture.
        """
        if test_object.aperture is None:
            return

        test_object._definer_type = "aperture"
        if test_object.slits is not None:
            test_object.slits.set_horizontal_gap(1)
            test_object.slits.set_vertical_gap(1)

        for aperture_diameter in test_object.aperture.get_diameter_size_list():
            _val = test_object.aperture.VALUES[aperture_diameter]
            test_object.aperture.set_value(_val, timeout=2)

            beam_width, beam_height, beam_shape, beam_label = test_object.get_value()
            # get_value returns size in mm, aperture diameters are in microns
            assert beam_width == beam_height == _val.value[0] / 1000.0
            assert beam_shape == BeamShape.ELLIPTICAL
            assert beam_label == aperture_diameter

    def test_set_slit_gaps(self, test_object):
        """
        Set slits smaller as the largest aperture diameter.
        In this case beam size and shape is defined by slits.
        Test get_beam_size and get_beam_shape instead of get_value
        """
        if test_object.slits is None:
            return

        test_object._definer_type = "slits"

        if test_object.aperture:
            _list = []
            for val in test_object.aperture.get_diameter_size_list():
                _list.append(int(test_object.aperture.VALUES[val].value[0]))
            max_diameter = max(_list)
            test_object.aperture.set_value(
                test_object.aperture.VALUES[f"A{max_diameter}"], timeout=2
            )

        # slit size in mm, aperture diameters are in microns
        target_width = target_height = max_diameter / 2000.0
        test_object.set_value([target_width, target_height])
        # beam_width, beam_height, beam_shape, _ = test_object.get_value()
        beam_width, beam_height = test_object.get_beam_size()
        assert target_width == beam_width
        assert target_height == beam_height
        beam_shape = test_object.get_beam_shape()
        assert beam_shape == BeamShape.RECTANGULAR

    def test_set_definer_size(self, test_object):
        """
        Set large slit gaps and max aperture size.
        Beam shape is elliptical and size defined by the selected definer.
        """
        if test_object.definer is None:
            return

        test_object._definer_type = "definer"
        if test_object.slits is not None:
            test_object.slits.set_horizontal_gap(1)
            test_object.slits.set_vertical_gap(1)

        if test_object.aperture:
            _list = []
            for val in test_object.aperture.get_diameter_size_list():
                _list.append(int(test_object.aperture.VALUES[val].value[0]))
            max_diameter = max(_list)
            test_object.aperture.set_value(
                test_object.aperture.VALUES[f"A{max_diameter}"], timeout=2
            )

        for dsize in test_object.definer.VALUES:
            if dsize.name != "UNKNOWN":
                test_object.definer.set_value(dsize, timeout=2)

                (
                    beam_width,
                    beam_height,
                    beam_shape,
                    beam_label,
                ) = test_object.get_value()
                assert beam_width == dsize.value[0]
                assert beam_height == dsize.value[1]
                assert beam_shape == BeamShape.ELLIPTICAL
                assert beam_label == dsize.name
