import pytest
from nicos_connection import (
    NICOSConnection,
    connect_to_nicos,
)

HOST = "localHOST"
PORT = "1301"
USER = "guest"
PW = "any"
DEVICE_NAME = "sim_motor_1"


def test_connection_class():
    nicos_cli = connect_to_nicos(HOST, PORT, USER, PW)
    assert type(nicos_cli) == NICOSConnection
    nicos_cli.disconnect()


def test_is_connected():
    nicos_cli = connect_to_nicos(HOST, PORT, USER, PW)
    ret = nicos_cli.is_connected()
    assert ret == True
    nicos_cli.disconnect()


def test_is_disconnected():
    nicos_cli = connect_to_nicos(HOST, PORT, USER, PW)
    ret1 = nicos_cli.is_connected()
    nicos_cli.disconnect()
    ret2 = nicos_cli.is_connected()
    assert ret1 == True and ret2 == False
    nicos_cli.disconnect()


def test_get_param_value():
    nicos_cli = connect_to_nicos(HOST, PORT, USER, PW)
    readback_val = nicos_cli.get_dev_param_value(DEVICE_NAME)
    print(readback_val)
    assert readback_val != None
    nicos_cli.disconnect()


def test_process_command():
    """Test process_command by moving a motor."""
    nicos_cli = connect_to_nicos(HOST, PORT, USER, PW)
    readback_val = nicos_cli.get_dev_param_value(DEVICE_NAME)
    print(readback_val)
    target = float(readback_val) + 1
    line = "move('{}', {})".format(DEVICE_NAME, target)
    ret = nicos_cli.process_command(line)
    print(ret)
