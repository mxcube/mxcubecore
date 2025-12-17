#  Project name: MXCuBE
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Test suite for AbstractDiffractometer"""

import pytest

from test.TestHardwareObjectBase import TestHardwareObjectBase

_copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


@pytest.fixture
def test_object(beamline):
    """Use the diffractometer object from beamline"""
    return beamline.diffractometer


class TestDiffarctometer(TestHardwareObjectBase):
    def test_diffractometer_atributes(self, test_object):
        assert test_object is not None, (
            "Diffractometer hardware objects is None (not initialized)"
        )

        # test if all the predefined motor roles are set
        for role in ("omega", "focus", "phiy", "phiz", "sampx", "sampy"):
            assert hasattr(test_object, role)

        # test if all the predefined nstate roles are set
        for role in (
            "fshutter",
            "beamstop",
            "backlightswitch",
            "frontlightswitch",
            "aperture",
            "zoom",
        ):
            assert hasattr(test_object, role)

    def test_get_set_phase(self, test_object):
        phase_enum = test_object.get_phase_enum
        # in the mockup we set the initial phase to CENTRE
        assert test_object.get_phase() == phase_enum.CENTRE
        test_object.set_phase(phase_enum.COLLECT, timeout=0)
        assert test_object.get_phase() == phase_enum.COLLECT

    def test_get_phase_list(self, test_object):
        phase_enum = test_object.get_phase_enum
        # subtract one for the UNKNOWN
        assert len(phase_enum) - 1 == len(test_object.get_phase_list())

    def test_get_head_type(self, test_object):
        head_enum = test_object.get_head_enum
        # in the mockup we set the head to be minikappa
        assert test_object.get_head_type == head_enum.MINI_KAPPA
        assert test_object.in_kappa_mode
        assert not test_object.in_plate_mode

    def test_get_set_constraint(self, test_object):
        constraint_enum = test_object.get_constraint_enum
        # in the mockup we set the initial constraint RELEASE
        assert test_object.get_constraint() == constraint_enum.RELEASE
        test_object.set_constraint(constraint_enum.STILL)
        assert test_object.get_constraint() == constraint_enum.STILL
