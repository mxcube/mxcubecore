from __future__ import absolute_import

import functools
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from colorama import (
    Back,
    Fore,
    Style,
)

from mxcubecore import BaseHardwareObjects as BHWO
from mxcubecore import HardwareRepository as HWR
from mxcubecore import __version__

__version__ = __version__.__version__

hwrpath = os.path.dirname(__file__)
sys.path.insert(0, hwrpath)

#
# this makes it possible for Hardware Objects to import
# standard Hardware Objects easily
#


class ColorFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: "\033[1m" + "%s" + Style.RESET_ALL,
        logging.INFO: Fore.BLUE + "%s" + Style.RESET_ALL,
        logging.WARNING: Fore.YELLOW + "%s" + Style.RESET_ALL,
        logging.ERROR: "\033[1m" + Fore.RED + "%s" + Style.RESET_ALL,
        logging.CRITICAL: "\033[1m" + Fore.RED + "%s" + Style.RESET_ALL,
    }

    def format(self, record):
        formatter = logging.Formatter(self.FORMATS.get(record.levelno) % self._fmt)
        return formatter.format(record)


def trace_call_log(_func=None, *, level: int = logging.DEBUG):
    def decorator_wrapper(func):
        @functools.wraps(func)
        def fun_wrapper(*args, **kwargs):
            if len(args) == 0 or (not isinstance(args[0], BHWO.HardwareObject)):
                err_msg = (
                    "Not valid method. Decorator can be applied to an"
                    " HardwareObject instance's methods only"
                )
                raise TypeError(err_msg)
            args = list(args)
            self = args.pop(0)
            hwo_name = f" ({self.name.strip('/')})" if self.name else ""
            # Remove named parameters which are not in the signature of the method
            code_obj = func.__code__
            kwargs = {
                k: v
                for k, v in kwargs.items()
                if k in code_obj.co_varnames[: code_obj.co_argcount]
            }

            args_str = ",".join([str(arg) for arg in args])
            kwargs_str = ",".join(["%s=%s" % (k, v) for k, v in kwargs.items()])
            params_str = f"{args_str}{', ' if args and kwargs else ''}{kwargs_str}"
            method_name = func.__name__
            signature = f"{method_name}({params_str})"
            self.log.log(level, f"{hwo_name} In {signature}")
            return func(self, *args, **kwargs)

        return fun_wrapper

    if _func is None:
        return decorator_wrapper
    return decorator_wrapper(_func)


def getStdHardwareObjectsPath():
    import HardwareObjects  # first looks in containing package

    return os.path.dirname(HardwareObjects.__file__)


sys.path.insert(0, getStdHardwareObjectsPath())

hwobj_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HardwareObjects")
hwobj_dir_list = [hwobj_dir]
for subdir in ("sample_changer", "mockup"):
    hwobj_dir_list.append(os.path.join(hwobj_dir, subdir))
HWR.add_hardware_objects_dirs(hwobj_dir_list)

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
    _hdlr.setFormatter(ColorFormatter("%(asctime)s |%(levelname)-7s| %(message)s"))
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
