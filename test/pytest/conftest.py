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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.
"""Tests configuration"""

import os
import sys

import pytest
from gevent import monkey

from mxcubecore import HardwareRepository as HWR

monkey.patch_all(thread=False)


TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

sys.path.insert(0, ROOT_DIR)

print("DEBUG TESTS")
print(sys.path)


# hwr_path = os.path.join(HWR_DIR, "configuration/test")
# HWR.init_hardware_repository(hwr_path)
# hwr = HWR.get_hardware_repository()
# hwr.connect()


# This coding gives a new beamline load for each function call
# This can easily be changed by chaging the scope,
# but we may need to provide cleanup / object reloading in order to do that.
# @pytest.fixture(scope="session")
@pytest.fixture(scope="function")
def beamline():
    """Define the beamline mock-up classes configuration directories"""
    hwr_path = "%s%s%s" % (
        os.path.join(ROOT_DIR, "mxcubecore/configuration/mockup"),
        ":",
        os.path.join(ROOT_DIR, "mxcubecore/configuration/mockup/test"),
    )
    HWR._instance = HWR.beamline = None
    HWR.init_hardware_repository(hwr_path)
    hwr = HWR.get_hardware_repository()
    hwr.connect()
    return HWR.beamline
