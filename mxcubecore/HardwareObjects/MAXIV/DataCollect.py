"""
Contains code shared between BioMAX and MicroMAX for implementing
a data collection hardware object.
"""

from typing import Callable
import gevent
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractCollect import AbstractCollect


# max time we wait for safety shutter to open, in seconds
SAFETY_SHUTTER_TIMEOUT = 5.0


def _poll_until(condition: Callable, timeout_error_messge: str):
    with gevent.Timeout(SAFETY_SHUTTER_TIMEOUT, Exception(timeout_error_messge)):
        while not condition():
            gevent.sleep(0.01)


class DataCollect(AbstractCollect, HardwareObject):
    def open_safety_shutter(self):
        """
        send 'open' request to safety shutter and wait until it's open
        """

        def wait_until_open():
            _poll_until(
                lambda: self.safety_shutter_hwobj.is_open,
                "could not open the safety shutter",
            )

        self.log.info("Opening the safety shutter.")
        self.safety_shutter_hwobj.open()
        wait_until_open()

    def close_safety_shutter(self):
        """
        send 'close' request to safety shutter and wait until it's closed
        """

        def wait_until_closed():
            _poll_until(
                lambda: not self.safety_shutter_hwobj.is_open,
                "could not close the safety shutter",
            )

        self.log.info("Closing the safety shutter.")
        self.safety_shutter_hwobj.close()
        wait_until_closed()
