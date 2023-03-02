import pytest
from typing import Any, Union, TYPE_CHECKING, Iterator, Generator, Dict, Tuple
from mxcubecore.CommandContainer import CommandContainer

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


@pytest.fixture(scope="function")
def cmd_container() -> Generator[CommandContainer, None, None]:
    """Pytest fixture to instanciate a new "CommandContainer" object.

    Yields:
        Generator[CommandContainer, None, None]: New object instance.
    """

    cmd_container = CommandContainer()
    yield cmd_container


class TestCommandContainer:
    """Run tests for "CommandContainer" class"""

    def test_cmd_container_setup(self, cmd_container: CommandContainer):
        """ """

        assert cmd_container is not None and isinstance(cmd_container, CommandContainer)
