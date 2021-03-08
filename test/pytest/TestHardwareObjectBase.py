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

__copyright__ = """ Copyright © 2020 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"
__date__ = "09/04/2020"


import abc
import pytest
import gevent.event
from mxcubecore.BaseHardwareObjects import HardwareObjectState


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
        """Test that get_state reflects _state"""

        test_object._state = test_object.STATES.BUSY
        assert test_object.get_state() is test_object.STATES.BUSY, (
            "Setting %s._state is not reflected in get_state()"
            % test_object.__class__.__name__
        )

    def test_state_enumeration(self, test_object):
        """Test that STATES match HardwareObjectState"""

        for ho_state in HardwareObjectState:
            name = ho_state.name
            assert (
                getattr(test_object.STATES, name) is ho_state
            ), "state %s does not match HardwareObjectState.%s" % (name, name)

    def test_update_state(self, test_object):
        """Test that update_state works for all states
        that is_ready reflects the state,
        and that get_state() reflects _state"""
        test_object._state = test_object.STATES.BUSY
        for ho_state in HardwareObjectState:
            test_object.update_state(ho_state)
            result = test_object.get_state()
            assert result is ho_state, (
                "update_state(HardwareObjectState.%s) is not reflected in result"
                % ho_state.name
            )
            assert test_object._state is ho_state, (
                "get_state does not reflect _state for %s" % ho_state.name
            )
            if ho_state is HardwareObjectState.READY:
                assert (
                    test_object.is_ready()
                ), "is_ready=False does not reflect state READY"
            else:
                assert not test_object.is_ready(), (
                    "is_ready=True does not reflect state %s" % ho_state.name
                )
            test_object.update_state()
            assert (
                test_object._state is result
            ), "update_state() does not set state to current state"

    def test_wait_ready(self, test_object):
        test_object.update_state(test_object.STATES.READY)
        test_object.wait_ready(timeout=1.0e-6)

        test_object.update_state(test_object.STATES.BUSY)
        with pytest.raises(RuntimeError):
            test_object.wait_ready(timeout=1.0e-6)

    def test_signal_state_changed(self, test_object):
        catcher = SignalCatcher()
        test_object.update_state(test_object.STATES.READY)
        test_object.connect("stateChanged", catcher.catch)
        try:
            test_object.update_state(test_object.STATES.BUSY)
            # Timeout to guard against waiting foreer if signal is not sent)
            with gevent.Timeout(1.0):
                catcher.async_result.get()
        finally:
            test_object.disconnect("stateChanged", catcher.catch)


class SignalCatcher(object):
    """Utility class to test emissoi of signals

    Connect the catch function ot the signal, and use async_result.get()
    to get the value passed back by the signal.
    NB consider timeout ot avoid waiting forever"""

    def __init__(self,):
        self.async_result = gevent.event.AsyncResult()

    def catch(self, value):
        self.async_result.set(value)
