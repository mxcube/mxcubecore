import pytest
import sys
import os

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
MXCUBE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
HWR_OBJECT_DIR = os.path.join(MXCUBE, "HardwareObjects")
HWR_XML_FILES = os.path.join(MXCUBE, "HardwareRepository/test/xml-qt")

sys.path.insert(0, MXCUBE)

print ("MXCuBE root: %s" % MXCUBE)
print ("Config path: %s" % HWR_XML_FILES)

hwobj_dirs = [HWR_OBJECT_DIR]
for subdir in ('abstract', 'mockup', 'sample_changer'):
    hwobj_dirs.append(os.path.join(HWR_OBJECT_DIR, subdir))

from HardwareRepository.HardwareRepository import getHardwareRepository

@pytest.fixture(scope="session")
def hwr():
    hwr = getHardwareRepository(HWR_XML_FILES)
    hwr.connect()
    return hwr

@pytest.fixture(scope="session")
def blsetup(hwr):
    return hwr.getHardwareObject("beamline-setup")
