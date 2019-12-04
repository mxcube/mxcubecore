import pytest
import sys
import os

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
MXCUBE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
HWR_DIR = os.path.join(MXCUBE_DIR, "HardwareRepository")

sys.path.insert(0, MXCUBE_DIR)

from HardwareRepository import HardwareRepository as HWR

hwr_qt_path = os.path.join(HWR_DIR, "configuration/test")
HWR.init_hardware_repository(hwr_qt_path)
hwr_qt = HWR.getHardwareRepository()
hwr_qt.connect()

@pytest.fixture(scope="session")
def beamline():
    return HWR.beamline
