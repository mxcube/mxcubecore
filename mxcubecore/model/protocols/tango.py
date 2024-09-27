"""Models the `tango` section of YAML hardware configuration file.

Provides an API to read configured tango channels and commands.
"""
from typing import Optional, Iterable, Tuple, Dict
from pydantic import BaseModel


class Command(BaseModel):
    """Tango command configuration."""

    # name of the tango device command
    name: Optional[str]


class Channel(BaseModel):
    """Tango channel configuration."""

    attribute: Optional[str]
    polling_period: Optional[int]
    timeout: Optional[int]


class Device(BaseModel):
    """Configuration of a tango device."""

    commands: Optional[Dict[str, Optional[Command]]]
    channels: Optional[Dict[str, Optional[Channel]]]

    def get_commands(self) -> Iterable[Tuple[str, Command]]:
        """Get all commands configured for this device.

        This method will fill in optional configuration properties for commands.
        """
        if self.commands is None:
            return []

        for command_name, command_config in self.commands.items():
            if command_config is None:
                command_config = Command()

            if command_config.name is None:
                command_config.name = command_name

            yield command_name, command_config

    def get_channels(self) -> Iterable[Tuple[str, Channel]]:
        """Get all channels configured for this device.

        This method will fill in optional configuration properties for a channel.
        """
        if self.channels is None:
            return []

        for channel_name, channel_config in self.channels.items():
            if channel_config is None:
                channel_config = Channel()

            if channel_config.attribute is None:
                channel_config.attribute = channel_name

            yield channel_name, channel_config


class TangoConfig(BaseModel):
    """The 'tango' section of the hardware object's YAML configuration file."""

    __root__: Dict[str, Device]

    def get_tango_devices(self) -> Iterable[Tuple[str, Device]]:
        """Get all tango devices specified in this section."""
        return list(self.__root__.items())
