from typing import Callable

import pytest
from gevent.queue import Queue
from tango import (
    DeviceProxy,
    Except,
)
from tango.server import (
    Device,
    attribute,
    command,
)
from tango.test_context import DeviceTestContext

from mxcubecore.HardwareObjects.ISARAMaint import ISARAMaint

"""
Test the HardwareObjects.ISARAMaint sample changer maintenance hardware object.
"""


class _ISARA(Device):
    """
    A small tango device used for testing ISARAMaint hardware object.

    It mimics a small subset of attributes and commands of the real
    ISARA tango device, required to run the tests.
    """

    def __init__(self, *a, **k):
        self._remote_mode = True  # toggle for 'remote' and 'manual' modes
        self._is_powered = True
        self._position = "HOME"
        super().__init__(*a, **k)

    def _check_remote_mode(self):
        """
        raise tango exception if the device is not in remote mode
        """
        if not self._remote_mode:
            Except.throw_exception("ISARACommandError", "Remote mode requested", "")

    @attribute(name="Powered", dtype=bool)
    def _powered(self):
        return self._is_powered

    @attribute(name="PositionName", dtype=str)
    def _position_name(self):
        return self._position

    @attribute(name="Message", dtype=str)
    def _message(self):
        return "test message"

    @command(dtype_out=str)
    def PowerOn(self):
        self._check_remote_mode()
        self._is_powered = True
        return "on"

    @command(dtype_out=str)
    def PowerOff(self):
        self._check_remote_mode()
        self._is_powered = False
        return "off"

    @command(dtype_out=str)
    def Home(self):
        self._position = "HOME"
        return "home"

    @command(dtype_out=str)
    def Soak(self):
        self._position = "SOAK"
        return "soak"

    @command(dtype_out=str)
    def Dry(self):
        self._position = "DRY"
        return "dry"

    #
    # special command, that is not present in a normal tango device,
    # it is used by the tests to emulate the situation when the
    # robot is in 'manual mode'
    #
    @command
    def disable_remote_mode(self):
        self._remote_mode = False


def _disconnect_channels(maint: ISARAMaint):
    """
    disconnect signal callbacks from tango attribute pollers

    We need to disconnect signals, otherwise we'll get exceptions
    when shut down the tango device, while tearing down text fixture.
    """

    # the hard-coded list of attribute poller callbacks
    callbacks = {
        "Powered": maint._powered_updated,
        "PositionName": maint._position_name_updated,
        "Message": maint._message_updated,
    }

    for ch in maint.get_channels():
        ch.stop_polling()
        ch.disconnect_signal("update", callbacks[ch.name()])


@pytest.fixture
def isara_maint():
    #
    # start our test ISARA tango device
    #
    dev_ctx = DeviceTestContext(_ISARA, host="127.0.0.1", process=True)
    dev_ctx.start()

    #
    # create ISARAMaint hardware object
    #
    maint = ISARAMaint("/sc_maint")
    maint._config = maint.HOConfig(tangoname=dev_ctx.get_device_access())

    # make polling faster, to speed up the tests
    maint.polling = 10

    yield maint

    #
    # clean-up fixture
    #
    _disconnect_channels(maint)
    dev_ctx.stop()
    dev_ctx.join()


class CallbackTracker:
    def __init__(self):
        self._received_callbacks = Queue()

    def callback(self, *a, **k):
        self._received_callbacks.put((a, k))

    def wait_for_callback(self):
        return self._received_callbacks.get()

    def wait_until(self, condition: Callable):
        while received_callback := self.wait_for_callback():
            if condition(received_callback):
                # specified condition is fulfilled
                return


def test_power_on_home(isara_maint: ISARAMaint):
    """
    test the state of ISARAMain when the robot is:

      * powered on
      * the arm is in home position
    """
    cb_tracker = CallbackTracker()

    isara_maint.connect("globalStateChanged", cb_tracker.callback)
    isara_maint.init()

    # wait until all tango attributes have been read from tango device
    cb_tracker.wait_for_callback()

    #
    # check that get_cmd_info() seems to give us something reasonable
    #
    cmd_info = isara_maint.get_cmd_info()

    # check that we got the expected command section names
    cmd_section_names = set()
    for cmd_section in cmd_info:
        cmd_section_names.add(cmd_section[0])
    assert cmd_section_names == {"Power", "Abort", "Lid", "Positions", "Recovery"}

    #
    # check that commands state is correct
    #
    _, commands_state, message = isara_maint.get_global_state()
    assert commands_state == {
        "PowerOn": False,
        "PowerOff": True,
        "openLid": True,
        "closeLid": True,
        "home": False,
        "dry": True,
        "soak": True,
        "clearMemory": True,
        "reset": True,
        "back": True,
        "abort": True,
    }
    assert message == "test message"


def test_power_off(isara_maint: ISARAMaint):
    """
    test running 'power off' command
    """

    def power_is_off(callback_args):
        data, _ = callback_args
        state, _ = data

        return state["PowerOn"]

    cb_tracker = CallbackTracker()

    isara_maint.connect("globalStateChanged", cb_tracker.callback)
    isara_maint.init()

    # wait until all tango attributes have been read from tango device
    cb_tracker.wait_for_callback()

    # issue 'power off' command
    isara_maint.send_command("PowerOff")

    # wait until command 'propagates'
    cb_tracker.wait_until(power_is_off)

    #
    # check that commands state is correct
    #
    _, commands_state, _ = isara_maint.get_global_state()
    assert commands_state == {
        "PowerOn": True,
        "PowerOff": False,
        "openLid": True,
        "closeLid": True,
        "home": False,
        "dry": False,
        "soak": False,
        "clearMemory": True,
        "reset": True,
        "back": True,
        "abort": True,
    }


def test_change_positions(isara_maint: ISARAMaint):
    """
    test moving robot between different positions,
    using commands
    """

    def get_state(callback_args):
        data, _ = callback_args
        state, _ = data

        return state

    def is_in_soak(callback_args):
        return not get_state(callback_args)["soak"]

    def is_in_dry(callback_args):
        return not get_state(callback_args)["dry"]

    def is_in_home(callback_args):
        return not get_state(callback_args)["home"]

    cb_tracker = CallbackTracker()

    isara_maint.connect("globalStateChanged", cb_tracker.callback)
    isara_maint.init()

    # wait until all tango attributes have been read from tango device
    cb_tracker.wait_for_callback()

    # check that the state of commands is correct 'home' position
    _, commands_state, _ = isara_maint.get_global_state()
    assert not commands_state["home"]
    assert commands_state["dry"]
    assert commands_state["soak"]

    #
    # move to 'soak' position
    #
    isara_maint.send_command("soak")
    cb_tracker.wait_until(is_in_soak)

    # check that the state of commands is correct 'soak' position
    _, commands_state, _ = isara_maint.get_global_state()
    assert commands_state["home"]
    assert commands_state["dry"]
    assert not commands_state["soak"]

    #
    # move to 'dry' position
    #
    isara_maint.send_command("dry")
    cb_tracker.wait_until(is_in_dry)

    # check that the state of commands is correct 'dry' position
    _, commands_state, _ = isara_maint.get_global_state()
    assert commands_state["home"]
    assert not commands_state["dry"]
    assert commands_state["soak"]

    #
    # move to 'home' position
    #
    isara_maint.send_command("home")
    cb_tracker.wait_until(is_in_home)

    # check that the state of commands is correct 'home' position
    _, commands_state, _ = isara_maint.get_global_state()
    assert not commands_state["home"]
    assert commands_state["dry"]
    assert commands_state["soak"]


def test_manual_mode_error(isara_maint: ISARAMaint):
    """
    test that when robot is in 'manual mode', issuing power on/off command
    raises an 'not in remote mode' error
    """
    cb_tracker = CallbackTracker()

    isara_maint.connect("globalStateChanged", cb_tracker.callback)
    isara_maint.init()

    # wait until all tango attributes have been read from tango device
    cb_tracker.wait_for_callback()

    # put robot into 'manual mode'
    DeviceProxy(isara_maint.get_property("tangoname")).disable_remote_mode()

    #
    # trying to power on or off the robot, should generate an appropriate error message
    #
    with pytest.raises(RuntimeError, match="power off .*not in remote mode"):
        isara_maint.send_command("PowerOff")

    with pytest.raises(RuntimeError, match="power on .*not in remote mode"):
        isara_maint.send_command("PowerOn")
