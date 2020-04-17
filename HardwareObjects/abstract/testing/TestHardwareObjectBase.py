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
# along with MXCuBE.  If not, see <https://www.gnu.org/licenses/>.
"""
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

__copyright__ = """ Copyright © 2020 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"
__author__ = "rhfogh"
__date__ = "09/04/2020"


import abc
import pytest
from HardwareRepository.BaseHardwareObjects import HardwareObjectState


@pytest.fixture
def test_object(beamline):
    """Default fixture. Must be overridden"""
    result = beamline.some.dotted.path
    yield result
    # Cleanup code here - restores starting state for next call:
    # NBNB TODO


class TestHardwareObjectBase:
    """Tests for HardwareObjectMixin subclasses"""

    __metaclass__ = abc.ABCMeta

    def tets_state_getting(self, test_object):

        test_object._state = test_object.STATES.BUSY
        assert test_object.get_state() is test_object.STATES.BUSY, (
            "Setting %s._state is not reflected in get_state()"
            % test_object.__class__.__name__
        )

    def test_state_enumeration(self, test_object):

        for ho_state in HardwareObjectState:
            name = ho_state.name
            assert (
                getattr(test_object.STATES, name) is ho_state
            ), "state %s does not match HardwareObjectState.%s" % (name, name)

    def test_update_state(self, test_object):
        test_object._state = test_object.STATES.BUSY
        for ho_state in HardwareObjectState:
            test_object.update_state(ho_state)
            assert test_object.get_state() is ho_state, (
                "update_state(HardwareObjectState.%s) is not reflected in result"
                % ho_state.name
            )
            if ho_state is HardwareObjectState.READY:
                assert (
                    test_object.is_ready()
                ), "is_ready=False does not reflect state READY"
            else:
                assert not test_object.is_ready(), (
                    "is_ready=True does not reflect state %s" % ho_state.name
                )

    def test_update_state_2(self, test_object):
        state = test_object.get_state()
        test_object.update_state()
        assert (
            state is test_object.get_state()
        ), "update_state() does not match get_state() "

    def test_wait_ready(self, test_object):
        test_object.update_state(test_object.STATES.READY)
        test_object.wait_ready(timeout=1)

        test_object.update_state(test_object.STATES.BUSY)
        with pytest.raises(BaseException):
            test_object.wait_ready(timeout=0.01)
