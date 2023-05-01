import pytest
from typing import Generator, TYPE_CHECKING
from mxcubecore.CommandContainer import ConnectionError, CommandObject, ChannelObject, CommandContainer

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


@pytest.fixture(scope="function")
def cmd_object() -> Generator[CommandObject, None, None]:
    """Pytest fixture to instanciate a new "CommandObject" object.

    Yields:
        Generator[CommandObject, None, None]: New object instance.
    """

    cmd_object = CommandObject(name="test_command")
    yield cmd_object


@pytest.fixture(scope="function")
def channel_object() -> Generator[ChannelObject, None, None]:
    """Pytest fixture to instanciate a new "ChannelObject" object.

    Yields:
        Generator[ChannelObject, None, None]: New object instance.
    """

    channel_object = ChannelObject(name="test_channel", test1=True, test2=False)
    yield channel_object


@pytest.fixture(scope="function")
def cmd_container() -> Generator[CommandContainer, None, None]:
    """Pytest fixture to instanciate a new "CommandContainer" object.

    Yields:
        Generator[CommandContainer, None, None]: New object instance.
    """

    cmd_container = CommandContainer()
    yield cmd_container


class TestCommandObject:
    """Run tests for "CommandObject" class"""

    def test_cmd_object_setup(self, cmd_object: CommandObject):
        """Test initial object setup.

        Args:
            cmd_object (CommandObject): Object instance.
        """

        assert cmd_object is not None and isinstance(cmd_object, CommandObject)

    # def test_init(self): ...

    # def test_set_argument_json_schema(self): ...

    # def test_name(self): ...

    # def test_connect(self): ...

    # def test_emit(self): ...

    # def test_add_argument(self): ...

    # def test_get_arguments(self): ...

    # def test_get_combo_argument_items(self): ...

    # def test_username(self): ...

    # def test_is_connected(self): ...


class TestChannelObject:
    """Run tests for "ChannelObject" class"""

    def test_channel_object_setup(self, channel_object: ChannelObject):
        """Test initial object setup.

        Args:
            channel_object (ChannelObject): Object instance.
        """

        assert channel_object is not None and isinstance(channel_object, ChannelObject)

    # def test_init(self): ...

    # def test_name(self): ...

    # def test_connect_signal(self): ...

    # def test_disconnect_signal(self): ...

    # def test_connect_notify(self): ...

    # def test_emit(self): ...

    # def test_username(self): ...

    # def test_is_connected(self): ...

    # def test_update(self): ...

    # def test_get_value(self): ...


class TestCommandContainer:
    """Run tests for "CommandContainer" class"""

    def test_cmd_container_setup(self, cmd_container: CommandContainer):
        """Test initial object setup.

        Args:
            cmd_container (CommandContainer): Object instance.
        """

        assert cmd_container is not None and isinstance(cmd_container, CommandContainer)

    # def test_getattr(self): ...

    # def test_get_channel_object(self): ...

    # def test_get_channel_names_list(self): ...

    # def test_add_channel(self): ...

    # def test_set_channel_value(self): ...

    # def test_get_channel_value(self): ...

    # def test_get_channels(self): ...

    # def test_get_command_object(self): ...

    # def test_get_commands(self): ...

    # def test_get_command_names_list(self): ...

    # def test_add_command(self): ...

    # def test_add_channels_and_commands(self): ...

    # def test_execute_command(self): ...
