import logging
from logging.handlers import RotatingFileHandler
import os
import sys

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
    stdhardwareobjectspkg = __import__('HardwareRepository.HardwareObjects', {}, {}, [''])

    return os.path.dirname(stdhardwareobjectspkg.__file__)

sys.path.insert(0, getStdHardwareObjectsPath())

#
# create the HardwareRepository logger
#
_logger = logging.getLogger('HWR')
_logger.setLevel(logging.DEBUG)
_oldLevel = logging.DEBUG
_formatter = logging.Formatter('* [%(name)s] %(levelname)s %(asctime)s %(message)s')

if len(logging.root.handlers) == 0:
    #
    # log to stdout
    #
    _hdlr = logging.StreamHandler(sys.stdout)
    _hdlr.setFormatter(_formatter)
    _logger.addHandler(_hdlr)
    

def removeLoggingHandlers():
    for handler in _logger.handlers:
        _logger.removeHandler(handler)


def setLoggingOff():
    global _oldLevel
    _oldLevel = _logger.getEffectiveLevel()
    _logger.setLevel(1000) #disable all logging events less severe than 1000 (CRITICAL is 50...)


def setLoggingOn():
    _logger.setLevel(_oldLevel)
    

def addLoggingHandler(handler):
    _logger.addHandler(handler)

    
def setLoggingHandler(handler):
    global _hdlr
    
    removeLoggingHandlers() #_logger.removeHandler(_hdlr)

    _hdlr = handler
    addLoggingHandler(_hdlr)


def setLogFile(filename):
    #
    # log to rotating files
    #
    hdlr = RotatingFileHandler(filename, 'a', 1048576, 5) #1 MB by file, 5 files max.           
    hdlr.setFormatter(_formatter)
    
    setLoggingHandler(hdlr)






