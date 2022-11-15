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

import pytest

__copyright__ = """ Copyright © 2016 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"

@pytest.fixture
def test_object(beamline):
    result = beamline
    yield result

class TestBeamlineHoId():
    def test_beamline_id(self, test_object):
        
        # Test if we can retrive a object located directly on 
        # the beamline object
        ho = test_object.get_hardware_object("diffractometer")
        ho_id = test_object.get_id(ho)
        assert("diffractometer" == ho_id)

        # Test if we can get an object further down the strucutre
        ho = test_object.get_hardware_object("diffractometer.sampx")
        ho_id = test_object.get_id(ho)
        assert("diffractometer.sampx" == ho_id)

