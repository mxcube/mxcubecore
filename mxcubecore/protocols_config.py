"""
Provides an API to add Command and Channel objects to hardware objects,
as specified in it's YAML configuration file.

See setup_commands_channels() function for details.
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Callable,
    Iterable,
)

if TYPE_CHECKING:
    from mxcubecore.BaseHardwareObjects import HardwareObject


def _setup_tango_commands_channels(hwobj: HardwareObject, tango_config: dict):
    """Set up Tango Command and Channel objects.

    parameters:
        tango: the 'tango' section of the hardware object's configuration
    """
    from mxcubecore.model.protocols.tango import (
        Device,
        TangoConfig,
    )

    def setup_tango_device(device_name: str, device_config: Device):
        #
        # set-up commands
        #
        for command_name, command_config in device_config.get_commands():
            attrs = {"type": "tango", "name": command_name, "tangoname": device_name}
            hwobj.add_command(attrs, command_config.name)

        #
        # set-up channels
        #
        for channel_name, channel_config in device_config.get_channels():
            attrs = {"type": "tango", "name": channel_name, "tangoname": device_name}

            if channel_config.polling_period:
                attrs["polling"] = channel_config.polling_period

            if channel_config.timeout:
                attrs["timeout"] = channel_config.timeout

            hwobj.add_channel(attrs, channel_config.attribute)

    tango_cfg = TangoConfig.model_validate(tango_config)
    for device_name, device_config in tango_cfg.get_tango_devices():
        setup_tango_device(device_name, device_config)


def _setup_exporter_commands_channels(hwobj: HardwareObject, exporter_config: dict):
    from mxcubecore.model.protocols.exporter import (
        Address,
        ExporterConfig,
    )

    def setup_address(address: str, address_config: Address):
        #
        # set-up commands
        #
        for command_name, command_config in address_config.get_commands():
            attrs = {
                "type": "exporter",
                "exporter_address": address,
                "name": command_name,
            }
            hwobj.add_command(attrs, command_config.name)

        #
        # set-up channels
        #
        for channel_name, channel_config in address_config.get_channels():
            attrs = {
                "type": "exporter",
                "exporter_address": address,
                "name": channel_name,
            }
            hwobj.add_channel(attrs, channel_config.attribute)

    exp_cfg = ExporterConfig.model_validate(exporter_config)
    for address, address_config in exp_cfg.get_addresses():
        setup_address(address, address_config)


def _setup_epics_channels(hwobj: HardwareObject, epics_config: dict):
    from mxcubecore.model.protocols.epics import (
        EpicsConfig,
        Prefix,
    )

    def setup_prefix(prefix: str, prefix_config: Prefix):
        #
        # set-up channels
        #
        for channel_name, channel_config in prefix_config.get_channels():
            attrs = {"type": "epics", "name": channel_name}
            if channel_config.polling_period:
                attrs["polling"] = channel_config.polling_period

            pv_name = f"{prefix}{channel_config.suffix}"
            hwobj.add_channel(attrs, pv_name)

    epics_cfg = EpicsConfig.model_validate(epics_config)
    for prefix, prefix_config in epics_cfg.get_prefixes():
        setup_prefix(prefix, prefix_config)


def _protocol_handles():
    return {
        "tango": _setup_tango_commands_channels,
        "exporter": _setup_exporter_commands_channels,
        "epics": _setup_epics_channels,
    }


def _get_protocol_names() -> Iterable[str]:
    """Get names of all supported protocols."""
    return _protocol_handles().keys()


def _get_protocol_handler(protocol_name: str) -> Callable:
    """Get the callable that will set up commands and channels for a specific
    protocol.
    """
    return _protocol_handles()[protocol_name]


def _setup_protocol(hwobj: HardwareObject, config: dict, protocol: str):
    """Add the Command and Channel objects configured in the specified protocol section.

    parameters:
        protocol: name of the protocol to handle
    """
    protocol_config = config.get(protocol)
    if protocol_config is None:
        # no configuration for this protocol
        return

    _get_protocol_handler(protocol)(hwobj, protocol_config)


def setup_commands_channels(hwobj: HardwareObject, config: dict):
    """Add the Command and Channel objects to a hardware object, as specified i
       the config.

    parameters:
        hwobj: hardware object where to add Command and Channel objects
        config: the complete hardware object configuration, i.e. parsed YAML file
                as dict
    """
    for protocol in _get_protocol_names():
        _setup_protocol(hwobj, config, protocol)
