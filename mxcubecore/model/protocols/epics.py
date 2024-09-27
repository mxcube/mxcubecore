"""Models the `epics` section of YAML hardware configuration file.

Provides an API to read configured EPICS channels.
"""
from typing import Optional, Iterable, Tuple, Dict
from pydantic import BaseModel


class Channel(BaseModel):
    """EPICS channel configuration."""

    suffix: Optional[str]
    poll: Optional[int]


class Prefix(BaseModel):
    """Configuration of an EPICS prefix section."""

    channels: Optional[Dict[str, Optional[Channel]]]

    def get_channels(self) -> Iterable[Tuple[str, Channel]]:
        """Get all channels configured for prefix.

        This method will fill in optional configuration properties for a channel.
        """

        if self.channels is None:
            return []

        for channel_name, channel_config in self.channels.items():
            if channel_config is None:
                channel_config = Channel()

            if channel_config.suffix is None:
                channel_config.suffix = channel_name

            yield channel_name, channel_config


class EpicsConfig(BaseModel):
    """The 'epics' section of the hardware object's YAML configuration file."""

    __root__: Dict[str, Prefix]

    def get_prefixes(self) -> Iterable[Tuple[str, Prefix]]:
        """Get all prefixes specified in this section."""
        return list(self.__root__.items())
