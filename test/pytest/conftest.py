import pytest
import sys
import os

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
MXCUBE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
HWR = os.path.join(MXCUBE, "HardwareRepository")

sys.path.insert(0, MXCUBE)

@pytest.fixture(scope="session")
def hwr_qt():
    return os.path.join(HWR, "configuration/xml-qt")

@pytest.fixture(scope="session")
def hwr_web():
    return os.path.join(HWR, "configuration/xml-web")
