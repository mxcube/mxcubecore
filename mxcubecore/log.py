"""Provides standard loggers.

Defines MXCuBE-core standard loggers.

  `hwr_log` for logging to HWR log
  `user_log` for logging to user_level_log log
  `ipc_log` for logging from the IPC layer (`mxcubecore.ipc`)
"""

from logging import getLogger

hwr_log = getLogger("HWR")
user_log = getLogger("user_level_log")
ipc_log = hwr_log.getChild("ipc")
