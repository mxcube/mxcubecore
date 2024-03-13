"""
Contains code shared between BioMAX and MicroMAX for implementing
a data collection hardware object.
"""

from typing import Callable
import gevent
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractCollect import AbstractCollect
from mxcubecore.HardwareObjects import TangoShutter
import socket


# max time we wait for safety shutter to open, in seconds
SAFETY_SHUTTER_TIMEOUT = 5.0


def _poll_until(condition: Callable, timeout: float, timeout_error_messge: str):
    """
    poll until condition() returns True, give up after timeout seconds
    """
    with gevent.Timeout(timeout, Exception(timeout_error_messge)):
        while not condition():
            gevent.sleep(0.01)


def open_tango_shutter(shutter: TangoShutter, timeout: float, name: str):
    def wait_until_open():
        _poll_until(
            lambda: shutter.is_open,
            timeout,
            f"could not open the {name}",
        )

    shutter.open()
    wait_until_open()


def close_tango_shutter(shutter: TangoShutter, timeout: float, name: str):
    def wait_until_closed():
        _poll_until(
            lambda: not shutter.is_open,
            timeout,
            f"could not close the {name}",
        )

    shutter.close()
    wait_until_closed()


class DataCollect(AbstractCollect, HardwareObject):
    def open_safety_shutter(self):
        """
        send 'open' request to safety shutter and wait until it's open
        """
        self.log.info("Opening the safety shutter.")
        open_tango_shutter(
            self.safety_shutter_hwobj, SAFETY_SHUTTER_TIMEOUT, "safety shutter"
        )

    def close_safety_shutter(self):
        """
        send 'close' request to safety shutter and wait until it's closed
        """
        self.log.info("Closing the safety shutter.")
        close_tango_shutter(
            self.safety_shutter_hwobj, SAFETY_SHUTTER_TIMEOUT, "safety shutter"
        )

    def get_mxcube_server_ip(self):
        """
        get the ip address of the mxcube server
        """
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
