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

"""Test suite for BeamDefiner hardware object.
"""

import pytest
from test.pytest.TestAbstractNStateBase import TestAbstractNStateBase

__copyright__ = """ Copyright © by MXCuBE Collaboration """
__license__ = "LGPLv3+"


@pytest.fixture
def test_object(beamline):
    """Use the beam object from beamline"""
    result = beamline.beam.definer
    yield result


class TestBeamDefiner(TestAbstractNStateBase):
    """TestBeam class"""

    def test_beam_atributes(self, test_object):
        """Test if object exists."""
        assert test_object is not None, "Beam hardware object is None (not initialized)"
