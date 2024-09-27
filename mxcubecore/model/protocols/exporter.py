"""Models the `exporter` section of YAML hardware configuration file.

Provides an API to read configured exporter channels and commands.
"""
from typing import Optional, Iterable, Tuple, Dict
from pydantic import BaseModel


class Command(BaseModel):
    """Exporter command configuration."""

    # name of the exporter device command
    name: Optional[str]


class Channel(BaseModel):
    """Exporter channel configuration."""

    attribute: Optional[str]


class Address(BaseModel):
    """Configuration of an exporter end point."""

    commands: Optional[Dict[str, Optional[Command]]]
    channels: Optional[Dict[str, Optional[Channel]]]

    def get_commands(self) -> Iterable[tuple[str, Command]]:
        """Get all commands configured for this exporter address.

        This method will fill in optional configuration properties the commands.
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
        """Get all channels configured for this exporter address.

        This method will fill in optional configuration properties for channels.
        """
        if self.channels is None:
            return []

        for channel_name, channel_config in self.channels.items():
            if channel_config is None:
                channel_config = Channel()

            if channel_config.attribute is None:
                channel_config.attribute = channel_name

            yield channel_name, channel_config


class ExporterConfig(BaseModel):
    """The 'exporter' section of the hardware object's YAML configuration file."""

    __root__: Dict[str, Address]

    def get_addresses(self) -> Iterable[Tuple[str, Address]]:
        """Get all exporter addresses specified in this section."""
        return list(self.__root__.items())
