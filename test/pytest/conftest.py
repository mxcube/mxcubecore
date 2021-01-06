from mx3core import HardwareRepository as HWR
import pytest
import sys
import os

from gevent import monkey

monkey.patch_all(thread=False)

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
MXCUBE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
HWR_DIR = os.path.join(MXCUBE_DIR, "mx3core")

sys.path.insert(0, MXCUBE_DIR)


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
    hwr_path = "%s%s%s" % (
        os.path.join(HWR_DIR, "configuration/mockup"),
        os.path.pathsep,
        os.path.join(HWR_DIR, "configuration/mockup/test")
    )
    HWR._instance = HWR.beamline = None
    HWR.init_hardware_repository(hwr_path)
    hwr = HWR.get_hardware_repository()
    hwr.connect()
    return HWR.beamline
