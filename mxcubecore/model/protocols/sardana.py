from typing import (
    Dict,
    Iterable,
    Optional,
    Tuple,
)

from pydantic import (
    BaseModel,
    RootModel,
)


class Command(BaseModel):
    """Sardana command configuration."""

    # name of the Sardana command
    name: Optional[str] = None


class Door(BaseModel):
    """Configuration of a Sardana door."""

    commands: Optional[Dict[str, Optional[Command]]] = None

    def get_commands(self) -> Iterable[Tuple[str, Command]]:
        """Get all commands configured for this door.

        This method will fill in optional configuration properties for commands.
        """
        if self.commands is None:
            return []

        for command_name, command_config in self.commands.items():
            if command_config is None:
                command_config = Command()  # noqa: PLW2901

            if command_config.name is None:
                command_config.name = command_name

            yield command_name, command_config


class SardanaConfig(RootModel[Dict[str, Door]]):
    """The 'sardana' section of the hardware object's YAML configuration file."""

    def get_doors(self) -> Iterable[Tuple[str, Door]]:
        """Get all Sardana doors specified in this section."""
        return list(self.root.items())
