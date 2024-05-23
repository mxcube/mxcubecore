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


import unittest
import logging
from mxcubecore.BaseHardwareObjects import HardwareObject

BEAMLINE = None


class TestException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class TestMethods(unittest.TestCase):
    def test_has_channels(self):
        logging.getLogger("HWR").debug("UnitTest: Testing has channels...")

    def test_get_value(self):
        logging.getLogger("HWR").debug("UnitTest: Testing return values...")
        self.assertIn(
            type(BEAMLINE.config.energy.get_value()),
            (float, int),
            "Energy hwobj | get_current_energy() returns float",
        )

        logging.getLogger("HWR").debug("UnitTest: Testing transmission hwobj")
        self.assertIn(
            type(BEAMLINE.config.transmission.get_value()),
            (float, int),
            "Transmission hwobj | get_value() returns float",
        )

        logging.getLogger("HWR").debug("UnitTest: Testing aperture hwobj")
        self.assertIn(
            type(BEAMLINE.config.beam.aperture.get_diameter_size()),
            (float, int),
            "Aperture | get_diameter_size() returns float",
        )
        self.assertIn(
            type(BEAMLINE.config.beam.aperture.get_diameter_size_list()),
            (list, tuple),
            "Aperture | get_diameter_size_list() returns list or tuple",
        )
        self.assertIn(
            type(BEAMLINE.config.beam.aperture.get_position_list()),
            (list, tuple),
            "Aperture | get_position_list() returns list or tuple",
        )

    def test_get_limits(self):
        logging.getLogger("HWR").debug("UnitTest: Testing limits...")
        self.assertIsInstance(
            BEAMLINE.config.energy.get_limits(),
            list,
            "Energy hwobj | get_energy_limits() returns list with two floats",
        )

    def test_get_state(self):
        logging.getLogger("HWR").debug("UnitTest: Testing states...")
        self.assertIsInstance(
            BEAMLINE.config.transmission.getAttState(),
            str,
            "Transmission hwobj | getAttState() returns int",
        )


class UnitTest(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

    def init(self):
        global BEAMLINE
        from mxcubecore import HardwareRepository as HWR

        BEAMLINE = HWR.beamline

        suite = unittest.TestLoader().loadTestsFromTestCase(TestMethods)
        test_result = unittest.TextTestRunner(verbosity=3).run(suite)

        # test_result.errors
        # test_result.failures
        # test_result.skipped
