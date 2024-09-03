import math
import pytest
from gevent.event import Event
from tango.server import Device, attribute, command
from tango.test_context import MultiDeviceTestContext
from mxcubecore.HardwareObjects.MAXIV.MachInfo import MachInfo


class _Billboard(Device):
    @attribute(name="R3Mode", dtype=str)
    def r3_mode(self):
        return "Delivery: Top-Up"

    @attribute(name="OperatorMessage", dtype=str)
    def operator_message(self):
        return "roses are blue"

    @attribute(name="R3NextInjection", dtype=str)
    def r3_next_injection(self):
        return "2024-06-12 14:00:00"

    @attribute(name="MachineMessage", dtype=str)
    def machine_message(self):
        return "<b>R3:</b> Shutdown<br><b>R1:</b> Shutdown<br><b>Linac:</b> Shutdown"


class _Dcct(Device):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._lifetime = 33627.44279505807

    @attribute(name="Current", dtype=float)
    def current(self):
        return 0.39518965682844615

    @attribute(name="Lifetime", dtype=float)
    def lifetime(self):
        return self._lifetime

    #
    # special command, that is not present in a normal tango device,
    # it is used by the tests to emulate the situation when there is
    # no current in the storage ring and thus lifetime is 'n/a'
    #
    @command
    def set_no_lifetime(self):
        self._lifetime = math.nan


@pytest.fixture
def mach_info():
    #
    # start our test proxy tango devices
    #
    devices_info = (
        {
            "class": _Billboard,
            "devices": [
                {"name": "test/device/billboard"},
            ],
        },
        {
            "class": _Dcct,
            "devices": [
                {
                    "name": "test/device/dcct",
                },
            ],
        },
    )
    dev_ctx = MultiDeviceTestContext(devices_info, host="127.0.0.1", process=True)
    dev_ctx.start()

    mach_info = MachInfo("/machine_info")

    mach_info._config = mach_info.HOConfig(
        mach_info=dev_ctx.get_device_access("test/device/billboard"),
        current=dev_ctx.get_device_access("test/device/dcct"),
        parameters="['current', 'fillmode', 'message', 'lifetime', 'injection', 'status']",
    )

    # listen for 'valueChanged' signal
    signal_sent = Event()
    mach_info.connect("valueChanged", lambda *_, **__: signal_sent.set())

    mach_info.init()
    yield mach_info

    #
    # wait with tearing down the tango devices until the 'valueChanged' signal is sent,
    # otherwise the emitting code can fail when it tries to read tango attributes
    #
    signal_sent.wait()

    #
    # clean-up
    #
    dev_ctx.stop()
    dev_ctx.join()


def test_read_all(mach_info: MachInfo):
    assert mach_info.get_current() == "395.19 mA"
    assert mach_info.get_fillmode() == "Delivery: Top-Up"
    assert mach_info.get_message() == "roses are blue"
    assert mach_info.get_lifetime() == "9.34 h"
    assert mach_info.get_injection() == "2024-06-12 14:00:00"
    assert mach_info.get_status() == "R3: Shutdown R1: Shutdown Linac: Shutdown"


def test_no_lifetime(mach_info: MachInfo):
    mach_info.mach_curr.set_no_lifetime()
    assert mach_info.get_lifetime() == "n/a"
