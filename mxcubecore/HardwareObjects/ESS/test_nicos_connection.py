from time import sleep

import pytest
from nicos_connection import (
    NICOSConnection,
    connect_to_nicos,
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


def test_connection_class():
    nicos_cli = connect_to_nicos(HOST, PORT, USER, PW)
    assert type(nicos_cli) == NICOSConnection
    nicos_cli.disconnect()


def test_is_connected():
    nicos_cli = connect_to_nicos(HOST, PORT, USER, PW)
    ret = nicos_cli.is_connected()
    assert ret == True
    nicos_cli.disconnect()


def test_disconnection():
    nicos_cli = connect_to_nicos(HOST, PORT, USER, PW)
    ret1 = nicos_cli.is_connected()
    nicos_cli.disconnect()
    ret2 = nicos_cli.is_connected()
    assert ret1 == True and ret2 == False
    nicos_cli.disconnect()


def test_get_dev_value():
    nicos_cli = connect_to_nicos(HOST, PORT, USER, PW)
    readback_val = nicos_cli.get_dev_value(DEVICE_NAME[0])
    print("current value = " + str(readback_val))
    assert readback_val != None
    nicos_cli.disconnect()


def test_get_dev_param_from_cache():
    nicos_cli = connect_to_nicos(HOST, PORT, USER, PW)
    readback_val = nicos_cli.get_dev_param_from_cache(DEVICE_NAME[0])
    print("cache value = " + str(readback_val))
    assert readback_val != None
    nicos_cli.disconnect()


def test_run_command():
    """Test run_command by moving a motor to a short distance."""
    nicos_cli = connect_to_nicos(HOST, PORT, USER, PW)
    readback_val = nicos_cli.get_dev_value(DEVICE_NAME[0])
    target = float(readback_val) + 1
    nicos_cli.run_command(f"move({DEVICE_NAME[0]}, {target})")
    sleep(3)
    new_val = nicos_cli.get_dev_value(DEVICE_NAME[0])
    assert new_val == target
    nicos_cli.disconnect()


def test_run_command_for_3_devices():
    """Test run_command by moving 3 motors in parallel."""
    nicos_cli = connect_to_nicos(HOST, PORT, USER, PW)

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
    nicos_cli = connect_to_nicos(HOST, PORT, "invalid_user", PW)
    ret = nicos_cli.is_connected()
    assert ret == False
    # Try to mess up anyway
    val = nicos_cli.get_dev_value(DEVICE_NAME[0])
    assert val == None
    some_val = 5
    nicos_cli.run_command(f"move({DEVICE_NAME[0]}, {some_val})")
    val = nicos_cli.get_dev_value(DEVICE_NAME[0])
    assert val == None


def test_get_dev_status__idle():
    nicos_cli = connect_to_nicos(HOST, PORT, USER, PW)
    code_1, txt1 = nicos_cli.get_dev_status(DEVICE_NAME[0])
    code_2, txt2 = nicos_cli.get_dev_status(DEVICE_NAME[3])
    assert code_1 == 200 and code_2 == 200
    assert "idle" in txt1 and txt2 == ""
    nicos_cli.disconnect()


def test_get_dev_status__moving():
    nicos_cli = connect_to_nicos(HOST, PORT, USER, PW)

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
