import pytest
import sys
import os

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
MXCUBE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
HWR = os.path.join(MXCUBE, "HardwareRepository")

sys.path.insert(0, MXCUBE)

from HardwareRepository import HardwareRepository as HWR

# The below can NOT have worked - getHardwareRepository sets the hardcware_repository
# only if it is not set already. It would have returned the xml-qt repository in both
# cases
#
# I have modified it to explicitly test only the xml version (as it already did)
# The owner of the test must rewrite it.
#
# Apologies, rhfogh

# # There are two different mockup configurations for qt and web
# # An issue #335 to join the configuration is open
# # Meanwhile we create two hardware repositories and do tests
# # against both of them.
# # After solving the issue #355 there should be just one hardware repository
#

hwr_qt_path = os.path.join(HWR, "configuration/xml-qt")
# hwr_web_path = os.path.join(HWR, "configuration/xml-web")
HWR.init_hardware_repository(hwr_qt_path)
hwr_qt = HWR.getHardwareRepository()
# hwr_web = HardwareRepository.getHardwareRepository(hwr_web_path)
hwr_qt.connect()
# hwr_web.connect()


@pytest.fixture(scope="session")
def energy_list():
    return (
        hwr_qt.getHardwareObject("energy-mockup"),
        # hwr_web.getHardwareObject("energy-mockup")
    )


@pytest.fixture(scope="session")
def shutter_list():
    return (
        hwr_qt.getHardwareObject("shutter-mockup"),
        # hwr_web.getHardwareObject("shutter-mockup")
    )

@pytest.fixture(scope="session")
def detector_list():
    return (
        hwr_qt.getHardwareObject("detector-mockup"),
        # hwr_web.getHardwareObject("detector-mockup")
    )
