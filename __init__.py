import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import HardwareRepository

#
# Add path to root BlissFramework directory
#
hwrpath = os.path.dirname(__file__)
sys.path.insert(0, hwrpath)

#
# this makes it possible for Hardware Objects to import
# standard Hardware Objects easily
#


def getStdHardwareObjectsPath():
    import HardwareObjects  # first looks in containing package

    return os.path.dirname(HardwareObjects.__file__)


sys.path.insert(0, getStdHardwareObjectsPath())

hwobj_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HardwareObjects")
mockup_dir = os.path.join(hwobj_dir, "mockup")

HardwareRepository.addHardwareObjectsDirs([hwobj_dir, mockup_dir])

#
# create the HardwareRepository logger
#
_hwr_logger = logging.getLogger("HWR")
_hwr_logger.setLevel(logging.DEBUG)
_oldLevel = logging.DEBUG
_hwr_formatter = logging.Formatter("%(asctime)s |%(levelname)-7s| %(message)s")

if len(logging.root.handlers) == 0:
    #
    # log to stdout
    #
    _hdlr = logging.StreamHandler(sys.stdout)
    _hdlr.setFormatter(_hwr_formatter)
    _hwr_logger.addHandler(_hdlr)


def removeLoggingHandlers():
    for handler in _hwr_logger.handlers:
        _hwr_logger.removeHandler(handler)


def setLoggingOff():
    global _oldLevel
    _oldLevel = _hwr_logger.getEffectiveLevel()
    _hwr_logger.setLevel(
        1000
    )  # disable all logging events less severe than 1000 (CRITICAL is 50...)


def setLoggingOn():
    _hwr_logger.setLevel(_oldLevel)


def addLoggingHandler(handler):
    _hwr_logger.addHandler(handler)


def setLoggingHandler(handler):
    global _hdlr

    removeLoggingHandlers()  # _logger.removeHandler(_hdlr)

    _hdlr = handler
    addLoggingHandler(_hdlr)


def setLogFile(filename):
    #
    # log to rotating files
    #
    hdlr = RotatingFileHandler(filename, "a", 1048576, 5)  # 1 MB by file, 5 files max.
    hdlr.setFormatter(_hwr_formatter)

    setLoggingHandler(hdlr)
