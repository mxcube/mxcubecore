from typing import Callable
import pytest
import gevent
from gevent import Timeout
from tango import DeviceProxy, DevState
from tango.server import Device, command
from tango.test_context import DeviceTestContext
from mxcubecore.HardwareObjects import TangoShutter

"""
Test the HardwareObjects.TangoShutter shutter hardware object.
"""


VALUES_JSON = """
{"OPEN": "OPEN", "CLOSED": "CLOSE", "MOVING" : "MOVING"}
"""


class Shutter(Device):
    """
    Very simple tango shutter device, that only goes between 'open' and 'close' states.
    """

    def __init__(self, *args, **kwargs):
        self._is_open = False
        super().__init__(*args, **kwargs)

    @command()
    def Open(self):
        self._is_open = True

    @command()
    def Close(self):
        self._is_open = False

    def dev_state(self):
        return DevState.OPEN if self._is_open else DevState.CLOSE


@pytest.fixture
def shutter():
    tangods_test_context = DeviceTestContext(Shutter, process=True)
    tangods_test_context.start()

    #
    # set up the TangoShutter hardware object
    #
    hwo_shutter = TangoShutter.TangoShutter("/random_name")
    hwo_shutter.tangoname = tangods_test_context.get_device_access()
    hwo_shutter.set_property("values", VALUES_JSON)
    hwo_shutter.add_channel(
        {
            "name": "State",
            "type": "tango",
        },
        "State",
        True,
    )
    hwo_shutter.add_command(
        {
            "name": "Open",
            "type": "tango",
        },
        "Open",
        True,
    )
    hwo_shutter.add_command(
        {
            "name": "Close",
            "type": "tango",
        },
        "Close",
        True,
    )

    hwo_shutter.init()

    yield hwo_shutter

    tangods_test_context.stop()
    tangods_test_context.join()


def _wait_until(condition: Callable, condition_desc: str):
    with Timeout(1.2, Exception(f"timed out while waiting for {condition_desc}")):
        while not condition():
            gevent.sleep(0.01)


def test_open(shutter):
    """
    test opening the shutter
    """
    dev = DeviceProxy(shutter.tangoname)

    assert dev.State() == DevState.CLOSE
    assert not shutter.is_open

    shutter.open()

    _wait_until(lambda: shutter.is_open, "shutter to open")
    assert dev.State() == DevState.OPEN


def test_close(shutter):
    """
    test closing the shutter
    """
    dev = DeviceProxy(shutter.tangoname)
    dev.Open()

    assert dev.State() == DevState.OPEN
    assert shutter.is_open

    shutter.close()

    _wait_until(lambda: not shutter.is_open, "shutter to close")
    assert dev.State() == DevState.CLOSE
