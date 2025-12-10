"""Provides standard loggers.

Defines MXCuBE-core standard loggers.

  `hwr_log` for logging to HWR log
  `user_log` for logging to user_level_log log
"""

from logging import getLogger

hwr_log = getLogger("HWR")
user_log = getLogger("user_level_log")
