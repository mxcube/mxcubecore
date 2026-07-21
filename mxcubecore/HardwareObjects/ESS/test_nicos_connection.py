from time import sleep

import pytest
from nicos_connection import (
    NICOSConnection,
    get_nicos_connected,
)

HOST = "localhost"
PORT = "1301"
USER = "guest"
PW = "any"
DEVICE_NAME = [
    "virtual_motor_1",
    "virtual_motor_2",
    "virtual_motor_3",
    "ioc_actuator_1",
]
# Note: Make sure your devices are in a good start position (e.g., zero) to avoid limit issues.


@pytest.fixture(autouse=True)
def nicos_cli():
    nicos_cli = get_nicos_connected(HOST, PORT, USER, PW)
    yield nicos_cli
    nicos_cli.disconnect()


def test_connection_class(nicos_cli):
    assert type(nicos_cli) == NICOSConnection


def test_is_connected(nicos_cli):
    assert nicos_cli.is_connected()


def test_disconnection(nicos_cli):
    ret1 = nicos_cli.is_connected()
    nicos_cli.disconnect()
    ret2 = nicos_cli.is_connected()
    assert ret1 == True and ret2 == False


def test_get_dev_value(nicos_cli):
    readback_val = nicos_cli.get_dev_value(DEVICE_NAME[0])
    print("current value = " + str(readback_val))
    assert readback_val != None
    nicos_cli.disconnect()


def test_run_command(nicos_cli):
    """Test run_command by moving a motor to a short distance."""
    readback_val = nicos_cli.get_dev_value(DEVICE_NAME[0])
    target = float(readback_val) + 1
    nicos_cli.run_command(f"move({DEVICE_NAME[0]}, {target})")
    sleep(3)
    new_val = nicos_cli.get_dev_value(DEVICE_NAME[0])
    assert new_val == target
    nicos_cli.disconnect()


def test_run_command_for_3_devices(nicos_cli):
    """Test run_command by moving 3 motors in parallel."""
    target = []
    for i in range(len(DEVICE_NAME)):
        val = nicos_cli.get_dev_value(DEVICE_NAME[i])
        target.append(val + 1)

    for i in range(len(DEVICE_NAME)):
        nicos_cli.run_command(f"move({DEVICE_NAME[i]}, {target[i]})")
        sleep(0.1)
    sleep(3)

    for i in range(len(DEVICE_NAME)):
        new_val = nicos_cli.get_dev_value(DEVICE_NAME[i])
        assert new_val == target[i]
    nicos_cli.disconnect()


def test_invalid_login():
    # Bypass the autouse-fixture
    nicos_cli = get_nicos_connected(HOST, PORT, "invalid_user", PW)
    ret = nicos_cli.is_connected()
    assert ret == False
    # Try to mess up anyway
    val = nicos_cli.get_dev_value(DEVICE_NAME[0])
    assert val == None
    some_val = 5
    nicos_cli.run_command(f"move({DEVICE_NAME[0]}, {some_val})")
    val = nicos_cli.get_dev_value(DEVICE_NAME[0])
    assert val == None


def test_get_dev_status__idle(nicos_cli):
    code_1, txt1 = nicos_cli.get_dev_status(DEVICE_NAME[0])
    code_2, txt2 = nicos_cli.get_dev_status(DEVICE_NAME[3])
    assert code_1 == 200 and code_2 == 200
    assert "idle" in txt1 and txt2 == ""
    nicos_cli.disconnect()


def test_get_dev_status__moving(nicos_cli):
    val = nicos_cli.get_dev_value(DEVICE_NAME[0])
    nicos_cli.run_command(f"move({DEVICE_NAME[0]}, {val + 5})")
    val = nicos_cli.get_dev_value(DEVICE_NAME[3])
    nicos_cli.run_command(f"move({DEVICE_NAME[3]}, {val + 5})")
    sleep(2)

    code_1, txt1 = nicos_cli.get_dev_status(DEVICE_NAME[0])
    code_2, txt2 = nicos_cli.get_dev_status(DEVICE_NAME[3])
    assert code_1 == 220 and code_2 == 220
    assert "moving" in txt1 and "moving" in txt2
    nicos_cli.disconnect()
