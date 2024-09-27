"""
Test mxcubecore.protocols_config.setup_commands_channels() function.

Check that setting up command and channel objects using Tango,
exporter and EPICS works.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import mock
import pytest

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareRepository import yaml as yaml_parser
from mxcubecore.protocols_config import setup_commands_channels


@dataclass
class _MockedAttribute:
    name: str


class _MockedDeviceProxy:
    def __init__(self, _name):
        pass

    def ping(self):
        pass

    def set_timeout_millis(self, _timeout):
        pass

    def attribute_list_query(self):
        return [
            _MockedAttribute("simple"),
            _MockedAttribute("tango_attr"),
            _MockedAttribute("red"),
            _MockedAttribute("green"),
            _MockedAttribute("cyan"),
        ]


@dataclass
class _MockedEpicsCommand:
    pv_name: str
    arg_list = None

    def poll(self, *_, **__):
        pass


class _TestHardwareObject(HardwareObject):
    pass


def _get_data_path(filename: str) -> Path:
    return Path(Path(__file__).parent, "data", filename)


def _parse_yaml_config(filename: str):

    with _get_data_path(filename).open() as f:
        return yaml_parser.load(f)


@pytest.fixture
def test_hwo():
    return _TestHardwareObject("test")


@dataclass
class _TangoCh:
    """describes expected tango channel object"""

    device_name: str
    attribute_name: str
    polling: Optional[int] = None
    timeout: Optional[int] = None


@dataclass
class _TangoCmd:
    """describes expected tango command object"""

    device_name: str
    command: str


@dataclass
class _ExporterCh:
    """describes expected exporter channel object"""

    attribute_name: str


@dataclass
class _ExporterCmd:
    """describes expected exporter command object"""

    command: str


@dataclass
class _EpicsCh:
    """describes expected EPICS channel object"""

    pv_name: str
    polling: Optional[int] = None


def test_no_commands_channels(test_hwo):
    """test loading a config that does not specify any command or channels"""
    config = _parse_yaml_config("no_commands_channels.yaml")
    setup_commands_channels(test_hwo, config)

    # there should be no channels nor commands setup
    assert list(test_hwo.get_channels()) == []
    assert list(test_hwo.get_commands()) == []


def _assert_tango_channels(channels, expected_channels):
    channels = {channel.name(): channel for channel in channels}

    # check by name that we got all the expected channels
    assert channels.keys() == expected_channels.keys()

    # check the details of each channel
    for name, channel in channels.items():
        expected = expected_channels[name]

        assert channel.device_name == expected.device_name
        assert channel.attribute_name == expected.attribute_name
        assert channel.polling == expected.polling
        if expected.timeout is not None:
            assert channel.timeout == expected.timeout


def _assert_tango_commands(commands, expected_commands):
    commands = {command.name(): command for command in commands}

    # check by name that we got all the expected channels
    assert commands.keys() == expected_commands.keys()

    # check the details of each channel
    for name, command in commands.items():
        expected = expected_commands[name]
        assert command.device_name == expected.device_name
        assert command.command == expected.command


def test_tango_commands_channels(test_hwo):
    """test loading config with some tango commands and channels"""
    dev_name = "my/test/device"

    config = _parse_yaml_config("tango_commands_channels.yaml")

    with mock.patch("mxcubecore.Command.Tango.DeviceProxy", _MockedDeviceProxy):
        setup_commands_channels(test_hwo, config)

    expected_channels = {
        "simple": _TangoCh(dev_name, "simple"),
        "delux": _TangoCh(dev_name, "tango_attr", polling=52, timeout=123),
    }
    _assert_tango_channels(test_hwo.get_channels(), expected_channels)

    expected_commands = {
        "plain": _TangoCmd(dev_name, "plain"),
        "fancy": _TangoCmd(dev_name, "tango_cmd"),
    }
    _assert_tango_commands(test_hwo.get_commands(), expected_commands)


def test_tango_commands(test_hwo):
    """test loading config with tango commands but no channels"""

    dev_name = "my/commands/device"

    config = _parse_yaml_config("tango_commands.yaml")

    with mock.patch("mxcubecore.Command.Tango.DeviceProxy", _MockedDeviceProxy):
        setup_commands_channels(test_hwo, config)

    # there should be no channels
    assert list(test_hwo.get_channels()) == []

    expected_commands = {
        "Go": _TangoCmd(dev_name, "Go"),
        "Stop": _TangoCmd(dev_name, "Stop"),
        "Abort": _TangoCmd(dev_name, "Abort"),
    }
    _assert_tango_commands(test_hwo.get_commands(), expected_commands)


def test_tango_channels(test_hwo):
    """test loading config with tango channels but no commands"""

    dev_name = "my/channels/device"

    config = _parse_yaml_config("tango_channels.yaml")

    with mock.patch("mxcubecore.Command.Tango.DeviceProxy", _MockedDeviceProxy):
        setup_commands_channels(test_hwo, config)

    # there should be no commands
    assert list(test_hwo.get_commands()) == []

    expected_channels = {
        "red": _TangoCh(dev_name, "red"),
        "green": _TangoCh(dev_name, "green"),
        "cyan": _TangoCh(dev_name, "cyan"),
    }
    _assert_tango_channels(
        test_hwo.get_channels(),
        expected_channels,
    )


def test_tango_duo(test_hwo):
    """test loading config with channels and commands from two tango devices"""

    first_dev = "my/first/device"
    second_dev = "my/second/device"

    config = _parse_yaml_config("tango_duo.yaml")

    with mock.patch("mxcubecore.Command.Tango.DeviceProxy", _MockedDeviceProxy):
        setup_commands_channels(test_hwo, config)

    expected_channels = {
        "simple": _TangoCh(first_dev, "simple"),
        "cyan": _TangoCh(first_dev, "cyan"),
        "red": _TangoCh(second_dev, "red"),
        "green": _TangoCh(second_dev, "green"),
    }
    _assert_tango_channels(test_hwo.get_channels(), expected_channels)

    expected_commands = {
        "firstDevCmd1": _TangoCmd(first_dev, "firstDevCmd1"),
        "firstDevCmd2": _TangoCmd(first_dev, "firstDevCmd2"),
        "secondDevCmd1": _TangoCmd(second_dev, "secondDevCmd1"),
        "secondDevCmd2": _TangoCmd(second_dev, "secondDevCmd2"),
    }
    _assert_tango_commands(test_hwo.get_commands(), expected_commands)


def _assert_exporter_channels(channels, expected_channels):
    channels = {channel.name(): channel for channel in channels}

    # check by name that we got all the expected channels
    assert channels.keys() == expected_channels.keys()

    # check the details of each channel
    for name, channel in channels.items():
        expected = expected_channels[name]
        assert channel.attribute_name == expected.attribute_name


def _assert_exporter_commands(commands, expected_commands):
    commands = {command.name(): command for command in commands}

    # check by name that we got all the expected channels
    assert commands.keys() == expected_commands.keys()

    # check the details of each channel
    for name, command in commands.items():
        expected = expected_commands[name]
        assert command.command == expected.command


def test_exporter(test_hwo):
    """test loading config with some exporter commands and channels"""
    config = _parse_yaml_config("exporter_commands_channels.yaml")

    with mock.patch("mxcubecore.Command.Exporter.start_exporter") as start_exporter:
        setup_commands_channels(test_hwo, config)

        # check that we connected to correct exporter address
        start_exporter.assert_called_with("example.com", 8844, mock.ANY)

    expected_channels = {
        "simple": _ExporterCh("simple"),
        "delux": _ExporterCh("exporter_attr"),
    }

    _assert_exporter_channels(test_hwo.get_channels(), expected_channels)

    expected_commands = {
        "plain": _ExporterCmd("plain"),
        "fancy": _ExporterCmd("exporter_cmd"),
    }
    _assert_exporter_commands(test_hwo.get_commands(), expected_commands)


def test_exporter_commands(test_hwo):
    """test loading config with exporter commands but no channels"""

    config = _parse_yaml_config("exporter_commands.yaml")

    with mock.patch("mxcubecore.Command.Exporter.start_exporter") as start_exporter:
        setup_commands_channels(test_hwo, config)

        # check that we connected to correct exporter address
        start_exporter.assert_called_with("example.com", 4321, mock.ANY)

    # there should be no channels
    assert list(test_hwo.get_channels()) == []

    expected_commands = {
        "Plain": _ExporterCmd("Plain"),
        "Fancy": _ExporterCmd("spicy"),
        "Third": _ExporterCmd("Third"),
    }
    _assert_exporter_commands(test_hwo.get_commands(), expected_commands)


def test_exporter_channels(test_hwo):
    """test loading config with exporter channels but no commands"""
    config = _parse_yaml_config("exporter_channels.yaml")

    with mock.patch("mxcubecore.Command.Exporter.start_exporter") as start_exporter:
        setup_commands_channels(test_hwo, config)

        # check that we connected to correct exporter address
        start_exporter.assert_called_with("kiwi.com", 54321, mock.ANY)

    expected_channels = {
        "cairo": _ExporterCh("cairo"),
        "luxor": _ExporterCh("luxor"),
        "quena": _ExporterCh("quena"),
    }
    _assert_exporter_channels(test_hwo.get_channels(), expected_channels)

    # there should be no commands
    assert list(test_hwo.get_commands()) == []


def test_exporter_duo(test_hwo):
    """test loading config with channels and commands from two exporter addresses"""
    config = _parse_yaml_config("exporter_duo.yaml")

    with mock.patch("mxcubecore.Command.Exporter.start_exporter") as start_exporter:
        setup_commands_channels(test_hwo, config)

        # check that we connected to correct exporter address
        start_exporter.assert_any_call("example1.com", 1111, mock.ANY)
        start_exporter.assert_any_call("example2.com", 2222, mock.ANY)

    expected_channels = {
        "Ex1One": _ExporterCh("Ex1One"),
        "Ex1Two": _ExporterCh("Ex1Two"),
        "Ex2One": _ExporterCh("Ex2One"),
        "Ex2Two": _ExporterCh("Ex2Two"),
    }

    _assert_exporter_channels(test_hwo.get_channels(), expected_channels)

    expected_commands = {
        "Ex1Plain": _ExporterCmd("Ex1Plain"),
        "Ex1Vanilla": _ExporterCmd("Ex1Vanilla"),
        "Ex2Plain": _ExporterCmd("Ex2Plain"),
        "Ex2Vanilla": _ExporterCmd("Ex2Vanilla"),
    }
    _assert_exporter_commands(test_hwo.get_commands(), expected_commands)


def _assert_epics_channels(channels, expected_channels):
    channels = {channel.name(): channel for channel in channels}

    # check by name that we got all the expected channels
    assert channels.keys() == expected_channels.keys()

    # check the details of each channel
    for name, channel in channels.items():
        expected = expected_channels[name]
        assert channel.polling == expected.polling
        assert channel.command.pv_name == expected.pv_name


def test_epics(test_hwo):
    """test loading config with EPICS channels"""

    def _make_mocked_cmd(_, pv_name, *__, **___):
        return _MockedEpicsCommand(pv_name)

    pv_prefix = "test:pre:fix:"

    config = _parse_yaml_config("epics_channels.yaml")

    with mock.patch("mxcubecore.Command.Epics.EpicsCommand", _make_mocked_cmd):
        setup_commands_channels(test_hwo, config)

    expected_channels = {
        "simple": _EpicsCh(f"{pv_prefix}simple", None),
        "fancy": _EpicsCh(f"{pv_prefix}epics_suffix", 1234),
    }

    _assert_epics_channels(test_hwo.get_channels(), expected_channels)
