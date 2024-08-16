import copy
import json
import weakref
import pytest
from typing import Generator, TYPE_CHECKING, Any, Dict, Union, List, Tuple, Optional
from typing_extensions import Annotated
from logging import Logger
from unittest.mock import MagicMock
from mxcubecore.CommandContainer import (
    ARGUMENT_TYPE_LIST,
    ARGUMENT_TYPE_JSON_SCHEMA,
    CommandObject,
    ChannelObject,
    CommandContainer,
)

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

    @pytest.mark.parametrize(
        "schema",
        (
            json.dumps(
                {
                    "test1": 2.5,
                    "test2": {
                        "test3": "Test.",
                    },
                },
            ),
            {
                "test1": 2.5,
                "test2": {
                    "test3": "Test.",
                },
            },
        ),
    )
    def test_set_argument_json_schema(
        self,
        cmd_object: CommandObject,
        schema: Union[str, Dict[str, Any]],
    ):
        """Test "set_argument_json_schema" method.

        Args:
            cmd_object (CommandObject): Object instance.
            schema (Union[str, Dict[str, Any]]): JSON schema.
        """

        # Check initial state, should be an empty list
        assert cmd_object.argument_type == ARGUMENT_TYPE_LIST
        assert isinstance(cmd_object._arguments, list) and not cmd_object._arguments

        # Call method
        cmd_object.set_argument_json_schema(json_schema_str=schema)

        # Validate expected changes happend
        assert cmd_object.argument_type == ARGUMENT_TYPE_JSON_SCHEMA
        assert cmd_object._arguments == schema

    @pytest.mark.parametrize(
        "name",
        ("test1", "test2"),
    )
    def test_name(
        self,
        mocker: "MockerFixture",
        cmd_object: CommandObject,
        name: str,
    ):
        """Test "name" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_object (CommandObject): Object instance.
            name (str): Name.
        """

        # Patch "cmd_object._name" to test with known values
        mocker.patch.object(cmd_object, "_name", new=name)

        # Call method
        res = cmd_object.name()

        # Check that correct patched value was returned
        assert res == name

    @pytest.mark.parametrize(
        "signal_name",
        ("position", "state", "move_done"),
    )
    def test_connect(
        self,
        mocker: "MockerFixture",
        cmd_object: CommandObject,
        signal_name: str,
    ):
        """Test "connect" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_object (CommandObject): Object instance.
            signal_name (str): Signal name.
        """

        # Patch dispatcher methods to test in isolation
        disconnect_patch = mocker.patch("mxcubecore.dispatcher.dispatcher.disconnect")
        connect_patch = mocker.patch("mxcubecore.dispatcher.dispatcher.connect")

        # Call method
        _callable_func = MagicMock()
        cmd_object.connect(signal_name=signal_name, callable_func=_callable_func)

        # Check that patched dispatcher methods were called with expected parameters
        disconnect_patch.assert_called_once_with(
            *(_callable_func, signal_name, cmd_object),
        )
        connect_patch.assert_called_once_with(
            *(_callable_func, signal_name, cmd_object),
        )

    @pytest.mark.parametrize(
        "signal_name",
        ("position", "state", "move_done"),
    )
    @pytest.mark.parametrize(
        ("in_args", "out_args"),
        (
            (("test1", 2.5, None), ("test1", 2.5, None)),
            ((False, None), (False, None)),
            ((("test2", None),), ("test2", None)),
            ((("test3", 10, False), None), (("test3", 10, False), None)),
            (("test4",), ("test4",)),
        ),
    )
    def test_emit(
        self,
        mocker: "MockerFixture",
        cmd_object: CommandObject,
        signal_name: str,
        in_args: tuple,
        out_args: tuple,
    ):
        """Test "emit" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_object (CommandObject): Object instance.
            signal_name (str): Signal name.
            in_args (tuple): Initial arguments.
            out_args (tuple): Output arguments.
        """

        # Patch "dispatcher.send" method to test in isolation
        send_patch = mocker.patch("mxcubecore.dispatcher.dispatcher.send")

        # Call method
        cmd_object.emit(signal_name, *in_args)

        # Check expected args passed to patched "dispatcher.send" method
        send_patch.assert_called_once_with(signal_name, cmd_object, *out_args)

    @pytest.mark.parametrize(
        ("arg_name", "arg_type", "onchange", "valuefrom"),
        (
            ("test1", "test1", None, None),
            ("test2", "test2", None, None),
            ("test3", "test3", None, None),
        ),
    )
    @pytest.mark.parametrize(
        "initial_arguments",
        ([("test1", "test1", None, None), ("test2", "test2", None, None)],),
    )
    @pytest.mark.parametrize(
        "combo_items",
        (
            {"value1": 0, "value2": 1},
            None,
        ),
    )
    def test_add_argument(
        self,
        mocker: "MockerFixture",
        cmd_object: CommandObject,
        arg_name: str,
        arg_type: str,
        initial_arguments: List[Tuple[str, str, Any, Any]],
        combo_items: Any,
        onchange: Any,
        valuefrom: Any,
    ):
        """Test "add_argument" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_object (CommandObject): Object instance.
            arg_name (str): Argument name.
            arg_type (str): Argument type.
            initial_arguments (List[Tuple[str, str, Any, Any]]): Initial arguments.
            combo_items (Any): Combo argument items.
            onchange (Any): Onchange.
            valuefrom (Any): Value from.
        """

        # Patch "_arguments" and "_combo_arguments_items" with known values
        mocker.patch.object(
            cmd_object, "_arguments", new=copy.deepcopy(initial_arguments)
        )
        mocker.patch.object(cmd_object, "_combo_arguments_items", new={})

        # Call method
        cmd_object.add_argument(
            argName=arg_name,
            argType=arg_type,
            combo_items=combo_items,
            onchange=onchange,
            valuefrom=valuefrom,
        )

        # Method we're testing calls "append", so "_arguments" should be a list type
        assert isinstance(cmd_object._arguments, list) and len(cmd_object._arguments)

        # Check output to "_arguments" matches expectations
        if arg_name not in [arg[0] for arg in initial_arguments]:
            # List should have been appended with new values
            assert cmd_object._arguments[-1] == (
                arg_name,
                arg_type.lower(),
                onchange,
                valuefrom,
            )
        else:
            # If "arg_name" was already present, initial args should match output args
            assert cmd_object._arguments == initial_arguments

        # Check output to "_combo_arguments_items"
        if combo_items is not None:
            assert cmd_object._combo_arguments_items.get(arg_name) is not None

    @pytest.mark.parametrize(
        "initial_arguments",
        ([("Time [s]", "float", None, None), ("Count", "int", None, None)],),
    )
    def test_get_arguments(
        self,
        mocker: "MockerFixture",
        cmd_object: CommandObject,
        initial_arguments: List[Tuple[str, str, Any, Any]],
    ):
        """Test "get_arguments" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_object (CommandObject): Object instance.
            initial_arguments (List[Tuple[str, str, Any, Any]]): Initial arguments.
        """

        # Patch "cmd_object._arguments" with known values
        mocker.patch.object(cmd_object, "_arguments", new=initial_arguments)

        # Call method
        res = cmd_object.get_arguments()

        # Check output matches initial known values
        assert res == initial_arguments

    @pytest.mark.parametrize(
        "arg_name",
        ("time", "count"),
    )
    @pytest.mark.parametrize(
        "initial_combo_args",
        (
            {
                "time": {"value1": 2.5, "value2": 3.0},
                "count": {"value1": 256, "value2": 1033},
            },
        ),
    )
    def test_get_combo_argument_items(
        self,
        mocker: "MockerFixture",
        cmd_object: CommandObject,
        arg_name: str,
        initial_combo_args: Dict[str, Any],
    ):
        """Test "get_combo_argument_items" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_object (CommandObject): Object instance.
            arg_name (str): Argument name.
            initial_combo_args (Dict[str, Any]): Initial combo arguments.
        """

        # Patch "cmd_object._combo_arguments_items" with known values
        mocker.patch.object(
            cmd_object, "_combo_arguments_items", new=initial_combo_args
        )

        # Call method
        res = cmd_object.get_combo_argument_items(argName=arg_name)

        # Check output matches expectations
        assert res == initial_combo_args[arg_name]

    @pytest.mark.parametrize(
        "username",
        ("test_username1", None),
    )
    @pytest.mark.parametrize(
        "name",
        ("test1", "test2"),
    )
    def test_username(
        self,
        mocker: "MockerFixture",
        cmd_object: CommandObject,
        username: Union[str, None],
        name: str,
    ):
        """Test "userName" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_object (CommandObject): Object instance.
            username (Union[str, None]): Username.
            name (str): Name.
        """

        # Patch "_username" and "_name" to test with known values
        mocker.patch.object(cmd_object, "_username", new=username)
        mocker.patch.object(cmd_object, "_name", new=name)

        # Call method
        res = cmd_object.userName()

        # Check output matches expectations
        if username is None:
            assert res == name
        else:
            assert res == username

    def test_is_connected(self, cmd_object: CommandObject):
        """Test "is_connected" method.

        Args:
            cmd_object (CommandObject): Object instance.
        """

        # Call method
        res = cmd_object.is_connected()

        # Check output is boolean, always returns False
        assert isinstance(res, bool) and not res


class TestChannelObject:
    """Run tests for "ChannelObject" class"""

    def test_channel_object_setup(self, channel_object: ChannelObject):
        """Test initial object setup.

        Args:
            channel_object (ChannelObject): Object instance.
        """

        assert channel_object is not None and isinstance(channel_object, ChannelObject)

    @pytest.mark.parametrize(
        "name",
        ("test1", "test2"),
    )
    def test_name(
        self,
        mocker: "MockerFixture",
        channel_object: ChannelObject,
        name: str,
    ):
        """Test "name" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            channel_object (ChannelObject): Object instance.
            name (str): Name.
        """

        # Patch "channel_object._name" to test with known values
        mocker.patch.object(channel_object, "_name", new=name)

        # Call method
        res = channel_object.name()

        # Check that correct patched value was returned
        assert res == name

    @pytest.mark.parametrize(
        "signal_name",
        ("position", "state", "move_done"),
    )
    def test_connect_signal(
        self,
        mocker: "MockerFixture",
        channel_object: ChannelObject,
        signal_name: str,
    ):
        """Test "connect_signal" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            channel_object (ChannelObject): Object instance.
            signal_name (str): Signal name.
        """

        # Patch dispatcher methods to test in isolation
        disconnect_patch = mocker.patch("mxcubecore.dispatcher.dispatcher.disconnect")
        connect_patch = mocker.patch("mxcubecore.dispatcher.dispatcher.connect")

        # Call method
        _callable_func = MagicMock()
        channel_object.connect_signal(
            signalName=signal_name,
            callableFunc=_callable_func,
        )

        # Check that patched dispatcher methods were called with expected parameters
        disconnect_patch.assert_called_once_with(
            *(_callable_func, signal_name, channel_object),
        )
        connect_patch.assert_called_once_with(
            *(_callable_func, signal_name, channel_object),
        )

    @pytest.mark.parametrize(
        "signal_name",
        ("position", "state", "move_done"),
    )
    def test_disconnect_signal(
        self,
        mocker: "MockerFixture",
        channel_object: ChannelObject,
        signal_name: str,
    ):
        """Test "disconnect_signal" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            channel_object (ChannelObject): Object instance.
            signal_name (str): Signal name.
        """

        # Patch "dispatcher.disconnect" to test in isolation
        disconnect_patch = mocker.patch("mxcubecore.dispatcher.dispatcher.disconnect")

        # Call method
        _callable_func = MagicMock()
        channel_object.disconnect_signal(
            signalName=signal_name,
            callableFunc=_callable_func,
        )

        # Check "dispatcher.disconnect" patch was called with expected parameters
        disconnect_patch.assert_called_once_with(
            *(_callable_func, signal_name, channel_object),
        )

    @pytest.mark.parametrize(
        "signal_name",
        ("position", "state", "move_done", "update"),
    )
    @pytest.mark.parametrize(
        "is_connected",
        (True, False),
    )
    def test_connect_notify(
        self,
        mocker: "MockerFixture",
        channel_object: ChannelObject,
        signal_name: str,
        is_connected: bool,
    ):
        """Test "connect_notify" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            channel_object (ChannelObject): Object instance.
            signal_name (str): Signal name.
            is_connected (bool): Is connected.
        """

        # Patch "is_connected" method to return known value
        mocker.patch.object(channel_object, "is_connected", return_value=is_connected)

        # Patch "emit" and "get_value" methods to test in isolation
        emit_patch = mocker.patch.object(channel_object, "emit")
        get_value_patch = mocker.patch.object(channel_object, "get_value")

        # Call method
        channel_object.connect_notify(signal=signal_name)

        # Check method behaviour matches expectations
        if signal_name == "update" and is_connected:
            emit_patch.assert_called_once_with(
                *(signal_name, get_value_patch.return_value),
            )
        else:
            emit_patch.assert_not_called()

    @pytest.mark.parametrize(
        "signal_name",
        ("position", "state", "move_done"),
    )
    @pytest.mark.parametrize(
        ("in_args", "out_args"),
        (
            (("test1", 2.5, None), ("test1", 2.5, None)),
            ((False, None), (False, None)),
            ((("test2", None),), ("test2", None)),
            ((("test3", 10, False), None), (("test3", 10, False), None)),
            (("test4",), ("test4",)),
        ),
    )
    def test_emit(
        self,
        mocker: "MockerFixture",
        channel_object: ChannelObject,
        signal_name: str,
        in_args: tuple,
        out_args: tuple,
    ):
        """Test "emit" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            channel_object (ChannelObject): Object instance.
            signal_name (str): Signal name.
            in_args (tuple): Input arguments.
            out_args (tuple): Output arguments.
        """

        # Patch "dispatcher.send" method to test in isolation
        send_patch = mocker.patch("mxcubecore.dispatcher.dispatcher.send")

        # Call method
        channel_object.emit(signal_name, *in_args)

        # Check expected args passed to patched "dispatcher.send" method
        send_patch.assert_called_once_with(signal_name, channel_object, *out_args)

    @pytest.mark.parametrize(
        "username",
        ("test_username1", None),
    )
    @pytest.mark.parametrize(
        "name",
        ("test1", "test2"),
    )
    def test_username(
        self,
        mocker: "MockerFixture",
        channel_object: ChannelObject,
        username: Union[str, None],
        name: str,
    ):
        """Test "userName" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            channel_object (ChannelObject): Object instance.
            username (Union[str, None]): Username.
            name (str): Name.
        """

        # Patch "_username" and "_name" to test with known values
        mocker.patch.object(channel_object, "_username", new=username)
        mocker.patch.object(channel_object, "_name", new=name)

        # Call method
        res = channel_object.userName()

        # Check output matches expectations
        if username is None:
            assert res == name
        else:
            assert res == username

    def test_is_connected(self, channel_object: ChannelObject):
        """Test "is_connected" method.

        Args:
            channel_object (ChannelObject): Object instance.
        """

        # Call method
        res = channel_object.is_connected()

        # Check output is boolean, always returns False
        assert isinstance(res, bool) and not res

    @pytest.mark.parametrize("first_update", (True, False))
    @pytest.mark.parametrize(
        "onchange",
        (
            None,
            ("test1", ...),
        ),
    )
    @pytest.mark.parametrize(
        "command_object",
        (..., None),
    )
    @pytest.mark.parametrize("value", ("test1", "test2", "test3"))
    def test_update(
        self,
        mocker: "MockerFixture",
        channel_object: ChannelObject,
        first_update: bool,
        onchange: Union[Tuple[str, Union["ellipsis", None]], None],
        command_object: Union["ellipsis", None],
        value: str,
    ):
        """Test "update" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            channel_object (ChannelObject): Object instance.
            first_update (bool): First update.
            onchange (Union[Tuple[str, Union[ellipsis, None]], None]): On change.
            command_object (Union[ellipsis, None]): Command object instance.
            value (str): Value.
        """

        # Patch "__first_update" to test in isolation
        mocker.patch.object(
            channel_object,
            "_ChannelObject__first_update",
            new=first_update,
        )

        # Patch and handle mocks for "_on_change"
        _onchange_ref: Union[MagicMock, None] = None
        _command_object: Union[MagicMock, None] = None
        get_command_object_patch: Union[MagicMock, None] = None
        if onchange is not None and onchange[1] is Ellipsis:
            _onchange_ref = MagicMock(spec=CommandContainer)
            if command_object is Ellipsis:
                _command_object = MagicMock(spec=CommandObject)
            else:
                _command_object = command_object
            get_command_object_patch: MagicMock = getattr(
                _onchange_ref,
                "get_command_object",
            )
            get_command_object_patch.return_value = _command_object
        elif onchange is not None:
            _onchange_ref = onchange[1]

        # Second parameter of "_on_change" should be an instance of "weakref"
        if onchange is not None:
            onchange = (onchange[0], weakref.ref(_onchange_ref))

        mocker.patch.object(channel_object, "_on_change", new=onchange)

        # Call method
        channel_object.update(value=value)

        if first_update:
            # Check "__first_update" is now False
            assert getattr(channel_object, "_ChannelObject__first_update") == False
        elif onchange is not None:
            if get_command_object_patch is not None:
                # Check "get_command_object" method patch was called
                get_command_object_patch.assert_called_once_with(*(onchange[0],))

                if _command_object is not None:
                    # Check returned "CommandObject" instance called once with value
                    _command_object.assert_called_once_with(*(value,))

    @pytest.mark.parametrize("force", (True, False))
    def test_get_value(self, channel_object: ChannelObject, force: bool):
        """Test "get_value" method.

        Args:
            channel_object (ChannelObject): Object instance.
            force (bool): Force get value.
        """

        # Method call will always raise an implementation error
        with pytest.raises(NotImplementedError):
            channel_object.get_value(force=force)


class TestCommandContainer:
    """Run tests for "CommandContainer" class"""

    def test_cmd_container_setup(self, cmd_container: CommandContainer):
        """Test initial object setup.

        Args:
            cmd_container (CommandContainer): Object instance.
        """

        assert cmd_container is not None and isinstance(cmd_container, CommandContainer)

    @pytest.mark.parametrize("attr_name", ("test1", "test2", "test3"))
    @pytest.mark.parametrize(
        "initial_commands",
        (
            {
                "test1": MagicMock(spec=CommandObject),
                "test2": MagicMock(spec=CommandObject),
            },
        ),
    )
    def test_getattr(
        self,
        mocker: "MockerFixture",
        cmd_container: CommandContainer,
        attr_name: str,
        initial_commands: Dict[str, Annotated[CommandObject, MagicMock]],
    ):
        """Test "__getattr__" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_container (CommandContainer): Object instance.
            attr_name (str): Attribute name.
            initial_commands (Dict[str, Annotated[CommandObject, MagicMock]]): Initial commands.
        """

        # Patch "__commands" with known values to test
        mocker.patch.object(
            cmd_container,
            "_CommandContainer__commands",
            new=initial_commands,
        )

        if attr_name in initial_commands.keys():
            # Check "getattr" returns expected value
            res = getattr(cmd_container, attr_name)
            assert res == initial_commands[attr_name]
        else:
            # Check "getattr" raises exception on non-existing attribute
            with pytest.raises(AttributeError):
                getattr(cmd_container, attr_name)

    @pytest.mark.parametrize("channel_name", ("test1", "test2", "test3", "test4"))
    @pytest.mark.parametrize(
        "initial_channels",
        (
            {
                "test1": MagicMock(spec=ChannelObject),
                "test2": MagicMock(spec=ChannelObject),
                "test3": None,
            },
        ),
    )
    @pytest.mark.parametrize("optional", (True, False))
    def test_get_channel_object(
        self,
        mocker: "MockerFixture",
        cmd_container: CommandContainer,
        channel_name: str,
        initial_channels: Dict[str, Union[Annotated[ChannelObject, MagicMock], None]],
        optional: bool,
    ):
        """Test "get_channel_object" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_container (CommandContainer): Object instance.
            channel_name (str): Channel name.
            initial_channels (Dict[str, Union[Annotated[ChannelObject, MagicMock], None]]): Initial channels.
            optional (bool): Whether an error should be logged where no result is returned.
        """

        # Patch "id" to test in isolation
        mocker.patch.object(cmd_container, "id", create=True, return_value="test")

        # Patch "__channels" with known values to test
        mocker.patch.object(
            cmd_container,
            "_CommandContainer__channels",
            new=initial_channels,
        )

        # Patch "logging.getLogger" to intercept calls
        logger_patch = MagicMock(spec=Logger)
        get_logger_patch = mocker.patch("logging.getLogger", return_value=logger_patch)

        # Call method
        res = cmd_container.get_channel_object(
            channel_name=channel_name,
            optional=optional,
        )

        # Check result matches expected
        assert res == initial_channels.get(channel_name, None)

        if res is None and not optional:
            # Check logger called when not optional and None result
            get_logger_patch.assert_called_once()
        elif res is not None or optional:
            # Check logger was not called unnecessarily
            get_logger_patch.assert_not_called()

    @pytest.mark.parametrize(
        "initial_channels",
        (
            {
                "test1": MagicMock(spec=ChannelObject),
                "test2": MagicMock(spec=ChannelObject),
                "test3": None,
            },
            {
                "test1": None,
            },
        ),
    )
    def test_get_channel_names_list(
        self,
        mocker: "MockerFixture",
        cmd_container: CommandContainer,
        initial_channels: Dict[str, Union[Annotated[ChannelObject, MagicMock], None]],
    ):
        """Test "get_channel_names_list" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_container (CommandContainer): Object instance.
            initial_channels (Dict[str, Union[Annotated[ChannelObject, MagicMock], None]]): Initial channels.
        """

        # Patch "__channels" with known values to test
        mocker.patch.object(
            cmd_container,
            "_CommandContainer__channels",
            new=initial_channels,
        )

        # Call method
        res = cmd_container.get_channel_names_list()

        # Check result matches expectations
        assert isinstance(res, list) and res == list(initial_channels.keys())

    @pytest.mark.parametrize(
        "attributes_dict",
        (
            # {
            #     "name": "test1",
            #     "type": "spec",
            # },
            # {
            #     "name": "test2",
            #     "type": "spec",
            #     "version": "test_version",
            # },
            # {
            #     "name": "test3",
            #     "type": "taco",
            # },
            # {
            #     "name": "test4",
            #     "type": "taco",
            #     "taconame": "test_taconame",
            # },
            {
                "name": "test5",
                "type": "tango",
            },
            {
                "name": "test6",
                "type": "tango",
                "tangoname": "test_tangoname",
            },
            {
                "name": "test7",
                "type": "exporter",
            },
            {
                "name": "test8",
                "type": "exporter",
                "exporter_address": "localhost:9000",
            },
            {
                "name": "test9",
                "type": "epics",
            },
            # {
            #     "name": "test10",
            #     "type": "tine",
            # },
            # {
            #     "name": "test11",
            #     "type": "tine",
            #     "tinename": "test_tinename",
            # },
            # {
            #     "name": "test12",
            #     "type": "sardana",
            # },
            # {
            #     "name": "test13",
            #     "type": "sardana",
            #     "taurusname": "test_taurusname",
            # },
            {
                "name": "test14",
                "type": "mockup",
            },
            {
                "name": "test15",
                "type": "mockup",
                "default_value": "1",
            },
        ),
    )
    @pytest.mark.parametrize("channel", ("test1", "test2", "test3"))
    @pytest.mark.parametrize("add_now", (True, False))
    @pytest.mark.parametrize("onchange", (None, "test1"))
    @pytest.mark.parametrize("valuefrom", (None, "test1"))
    @pytest.mark.parametrize("channel_exists", (True, False))
    @pytest.mark.parametrize("raise_attr_error", (True, False))
    def test_add_channel(
        self,
        mocker: "MockerFixture",
        cmd_container: CommandContainer,
        attributes_dict: Dict[str, Any],
        channel: str,
        add_now: bool,
        onchange: Union[str, None],
        valuefrom: Union[str, None],
        channel_exists: bool,
        raise_attr_error: bool,
    ):
        """Test "add_channel" method.

        NOTE: Tests covers all code paths as was reasonable to reach.
              Some code paths cannot be reached due to import errors.
              This method should probably be simplified and code split out.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_container (CommandContainer): Object instance.
            attributes_dict (Dict[str, Any]): Channel attributes.
            channel (str): Channel.
            add_now (bool): Whether to add the channel now.
            onchange (Union[str, None]): On change.
            valuefrom (Union[str, None]): Value from.
            channel_exists (bool): If channel should be treated as existing.
            raise_attr_error (bool): If missing attribute should raise an exeption.
        """

        _attributes = copy.deepcopy(attributes_dict)

        # Patch "logging.getLogger" to intercept calls
        logger_patch = MagicMock(spec=Logger)
        get_logger_patch = mocker.patch("logging.getLogger", return_value=logger_patch)

        # Patch imports to test in isolation
        # mocker.patch("mxcubecore.Command.Spec.SpecChannel")
        # mocker.patch("mxcubecore.Command.Taco.TacoChannel")
        mocker.patch("mxcubecore.Command.Tango.TangoChannel")
        mocker.patch("mxcubecore.Command.Exporter.ExporterChannel")
        mocker.patch("mxcubecore.Command.Epics.EpicsChannel")
        # mocker.patch("mxcubecore.Command.Tine.TineChannel")
        # mocker.patch("mxcubecore.Command.Sardana.SardanaChannel")
        mocker.patch("mxcubecore.Command.Mockup.MockupChannel")

        # Reset logger patch to remove calls from mock imports
        logger_patch.reset_mock()
        get_logger_patch.reset_mock()

        if not raise_attr_error:
            # Patch missing attributes
            mocker.patch.object(cmd_container, "name", create=True)
            mocker.patch.object(cmd_container, "specversion", create=True)
            mocker.patch.object(cmd_container, "taconame", create=True)
            mocker.patch.object(cmd_container, "tangoname", create=True)
            mocker.patch.object(
                cmd_container,
                "exporter_address",
                new="localhost:9000",
                create=True,
            )
            mocker.patch.object(cmd_container, "tine_name", create=True)
            mocker.patch.object(cmd_container, "taurusname", create=True)
            mocker.patch.object(cmd_container, "default_value", create=True)

        # Patch "__channels" to test with known values
        _existing_channel_mock: Union[Annotated[ChannelObject, MagicMock], None] = None
        if channel_exists:
            _existing_channel_mock = MagicMock(spec=ChannelObject)
            mocker.patch.object(
                cmd_container,
                "_CommandContainer__channels",
                new={_attributes["name"]: _existing_channel_mock},
            )
        else:
            mocker.patch.object(
                cmd_container,
                "_CommandContainer__channels",
                new={},
            )

        # Patch "__channels_to_add" to test with known values
        mocker.patch.object(
            cmd_container,
            "_CommandContainer__channels_to_add",
            new=[],
        )

        # Add "onchange" and "valuefrom" values to "_attributes"
        _attributes["onchange"] = onchange
        _attributes["valuefrom"] = valuefrom

        res: Union[ChannelObject, None] = None
        _channels_to_add: Union[List[Tuple[Dict[str, Any], str]], None] = None
        if not add_now:
            # Call method
            res = cmd_container.add_channel(
                attributes_dict=_attributes,
                channel=channel,
                add_now=add_now,
            )
            _channels_to_add = getattr(
                cmd_container, "_CommandContainer__channels_to_add"
            )

            # Result should be none as no channel has yet been added
            assert res is None

            # Check "__channels_to_add" updated
            assert isinstance(_channels_to_add, list) and len(_channels_to_add) == 1

            # Check list item added as expected
            _item_added = _channels_to_add[0]
            assert isinstance(_item_added, tuple) and len(_item_added) == 2
            assert _item_added[0] == _attributes and _item_added[1] == channel
        elif channel_exists:
            res = cmd_container.add_channel(
                attributes_dict=_attributes,
                channel=channel,
                add_now=add_now,
            )

            # Result should be mock added to channels list
            assert res is not None and res == _existing_channel_mock
        else:
            # Channel should be added now

            if raise_attr_error:
                if (
                    _attributes["type"] == "exporter"
                    and "exporter_address" not in _attributes
                ):
                    # Class lacks a "exporter_address" attribute, expecting exception
                    with pytest.raises(KeyError):
                        cmd_container.add_channel(
                            attributes_dict=_attributes,
                            channel=channel,
                            add_now=add_now,
                        )
                else:
                    res = cmd_container.add_channel(
                        attributes_dict=_attributes,
                        channel=channel,
                        add_now=add_now,
                    )

                    assert res is not None

                    # Check that "__channels_to_add" was not updated
                    _channels_to_add = getattr(
                        cmd_container, "_CommandContainer__channels_to_add"
                    )
                    assert (
                        isinstance(_channels_to_add, list)
                        and len(_channels_to_add) == 0
                    )
            else:
                res = cmd_container.add_channel(
                    attributes_dict=_attributes,
                    channel=channel,
                    add_now=add_now,
                )

                assert res is not None

                # Check that "__channels_to_add" was not updated
                _channels_to_add = getattr(
                    cmd_container, "_CommandContainer__channels_to_add"
                )
                assert isinstance(_channels_to_add, list) and len(_channels_to_add) == 0

    @pytest.mark.parametrize(
        "initial_channels",
        (
            {
                "test1": MagicMock(spec=ChannelObject),
                "test2": MagicMock(spec=ChannelObject),
            },
        ),
    )
    @pytest.mark.parametrize("channel_name", ("test1", "test2", "test3"))
    @pytest.mark.parametrize("value", ("Test", 100, 5.15, None))
    def test_set_channel_value(
        self,
        mocker: "MockerFixture",
        cmd_container: CommandContainer,
        initial_channels: Dict[str, Annotated[ChannelObject, MagicMock]],
        channel_name: str,
        value: Any,
    ):
        """Test "set_channel_value" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_container (CommandContainer): Object instance.
            initial_channels (Dict[str, Annotated[ChannelObject, MagicMock]]): Initial channels.
            channel_name (str): Channel name.
            value (Any): Value.
        """

        # Patch "__channels" with known values to test
        mocker.patch.object(
            cmd_container,
            "_CommandContainer__channels",
            new=initial_channels,
        )

        if not channel_name in initial_channels.keys():
            # Check non-existing key raises exception
            with pytest.raises(KeyError):
                cmd_container.set_channel_value(channel_name=channel_name, value=value)
        else:
            # All other calls should raise an exception as "set_value" isn't defined
            with pytest.raises(AttributeError):
                cmd_container.set_channel_value(channel_name=channel_name, value=value)

    @pytest.mark.parametrize(
        "initial_channels",
        (
            {
                "test1": MagicMock(spec=ChannelObject),
                "test2": MagicMock(spec=ChannelObject),
            },
        ),
    )
    @pytest.mark.parametrize("channel_name", ("test1", "test2", "test3"))
    def test_get_channel_value(
        self,
        mocker: "MockerFixture",
        cmd_container: CommandContainer,
        initial_channels: Dict[str, Annotated[ChannelObject, MagicMock]],
        channel_name: str,
    ):
        """Test "get_channel_value" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_container (CommandContainer): Object instance.
            initial_channels (Dict[str, Annotated[ChannelObject, MagicMock]]): Initial channels.
            channel_name (str): Channel name.
        """

        # Patch "__channels" with known values to test
        mocker.patch.object(
            cmd_container,
            "_CommandContainer__channels",
            new=initial_channels,
        )

        if not channel_name in initial_channels.keys():
            # Check exception is raised for non-existant key
            with pytest.raises(KeyError):
                cmd_container.get_channel_value(channel_name=channel_name)
        else:
            # Call method
            res = cmd_container.get_channel_value(channel_name=channel_name)

            # Check result matches expectations
            _get_value_mock: MagicMock = getattr(
                initial_channels[channel_name], "get_value"
            )
            _get_value_mock.assert_called_once()
            assert res == _get_value_mock.return_value

            # Reset mock to clear calls for next test
            _get_value_mock.reset_mock(return_value=True)

    @pytest.mark.parametrize(
        "initial_channels",
        (
            {
                "test1": MagicMock(spec=ChannelObject),
                "test2": MagicMock(spec=ChannelObject),
                "test3": None,
            },
            {
                "test1": None,
            },
        ),
    )
    def test_get_channels(
        self,
        mocker: "MockerFixture",
        cmd_container: CommandContainer,
        initial_channels: Dict[str, Union[Annotated[ChannelObject, MagicMock], None]],
    ):
        """Test "get_channels" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_container (CommandContainer): Object instance.
            initial_channels (Dict[str, Union[Annotated[ChannelObject, MagicMock], None]]): Initial channels.
        """

        # Patch "__channels" with known values to test
        mocker.patch.object(
            cmd_container,
            "_CommandContainer__channels",
            new=initial_channels,
        )

        # Call method
        res = cmd_container.get_channels()

        # Check results match expectation
        assert isinstance(res, Generator)
        assert list(res) == list(initial_channels.values())

    @pytest.mark.parametrize(
        "initial_commands",
        (
            {
                "test1": MagicMock(spec=CommandObject),
                "test2": MagicMock(spec=CommandObject),
            },
        ),
    )
    @pytest.mark.parametrize("command_name", ("test1", "test2", "test3"))
    def test_get_command_object(
        self,
        mocker: "MockerFixture",
        cmd_container: CommandContainer,
        initial_commands: Dict[str, Annotated[CommandObject, MagicMock]],
        command_name: str,
    ):
        """Test "get_command_object" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_container (CommandContainer): Object instance.
            initial_commands (Dict[str, Annotated[CommandObject, MagicMock]]): Initial commands.
            command_name (str): Command name.
        """

        # Patch "__commands" with known values to test
        mocker.patch.object(
            cmd_container,
            "_CommandContainer__commands",
            new=initial_commands,
        )

        # Call method
        res = cmd_container.get_command_object(cmd_name=command_name)

        # Check result matches expectations
        if command_name in initial_commands.keys():
            assert res is not None
        else:
            assert res is None

    @pytest.mark.parametrize(
        "initial_commands",
        (
            {
                "test1": MagicMock(spec=CommandObject),
                "test2": MagicMock(spec=CommandObject),
            },
        ),
    )
    def test_get_commands(
        self,
        mocker: "MockerFixture",
        cmd_container: CommandContainer,
        initial_commands: Dict[str, Annotated[CommandObject, MagicMock]],
    ):
        """Test "get_commands" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_container (CommandContainer): Object instance.
            initial_commands (Dict[str, Annotated[CommandObject, MagicMock]]): Initial commands.
        """

        # Patch "__commands" with known values to test
        mocker.patch.object(
            cmd_container,
            "_CommandContainer__commands",
            new=initial_commands,
        )

        # Call method
        res = cmd_container.get_commands()

        # Check results match expectation
        assert isinstance(res, Generator)
        assert list(res) == list(initial_commands.values())

    @pytest.mark.parametrize(
        "initial_commands",
        (
            {
                "test1": MagicMock(spec=CommandObject),
                "test2": MagicMock(spec=CommandObject),
            },
        ),
    )
    def test_get_command_names_list(
        self,
        mocker: "MockerFixture",
        cmd_container: CommandContainer,
        initial_commands: Dict[str, Annotated[CommandObject, MagicMock]],
    ):
        """Test "get_command_names_list" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_container (CommandContainer): Object instance.
            initial_commands (Dict[str, Annotated[CommandObject, MagicMock]]): Initial commands.
        """

        # Patch "__commands" with known values to test
        mocker.patch.object(
            cmd_container,
            "_CommandContainer__commands",
            new=initial_commands,
        )

        # Call method
        res = cmd_container.get_command_names_list()

        # Check results match expectations
        assert isinstance(res, list) and res == list(initial_commands.keys())

    @pytest.mark.parametrize(
        "arg1",
        (
            # {"name": "test1", "type": "spec"},
            # {"name": "test2", "type": "spec", "version": "test_version"},
            # {"name": "test3", "type": "taco"},
            # {"name": "test4", "type": "taco", "taconame": "test_taconame"},
            {"name": "test5", "type": "tango"},
            {"name": "test6", "type": "tango", "tangoname": "test_tangoname"},
            {"name": "test7", "type": "tango", "polling": 500},
            {
                "name": "test8",
                "type": "tango",
                "tangoname": "test_tangoname",
                "polling": 500,
            },
            {"name": "test9", "type": "tango", "timeout": 8000},
            {
                "name": "test10",
                "type": "tango",
                "tangoname": "test_tangoname",
                "timeout": 8000,
            },
            {
                "name": "test11",
                "type": "tango",
                "polling": 500,
                "timeout": 8000,
            },
            {
                "name": "test12",
                "type": "tango",
                "tangoname": "test_tangoname",
                "polling": 500,
                "timeout": 8000,
            },
            {"name": "test13", "type": "exporter"},
            {
                "name": "test14",
                "type": "exporter",
                "exporter_address": "localhost:9000",
            },
            {"name": "test15", "type": "epics"},
            # {"name": "test16", "type": "tine"},
            # {"name": "test17", "type": "tine", "tinename": "test_tinename"},
            # {"name": "test18", "type": "sardana"},
            # {"name": "test19", "type": "sardana", "taurusname": "test_taurusname"},
            {"name": "test20", "type": "mockup"},
            {"name": "test21", "type": "mockup", "default_value": "1"},
        ),
    )
    @pytest.mark.parametrize("arg2", ("test1", "test2", "test3", None))
    @pytest.mark.parametrize("add_now", (True, False))
    @pytest.mark.parametrize("onchange", (None, "test1"))
    @pytest.mark.parametrize("valuefrom", (None, "test1"))
    @pytest.mark.parametrize("raise_attr_error", (True, False))
    def test_add_command(
        self,
        mocker: "MockerFixture",
        cmd_container: CommandContainer,
        arg1: Dict[str, Any],
        arg2: Optional[str],
        add_now: bool,
        onchange: Union[str, None],
        valuefrom: Union[str, None],
        raise_attr_error: bool,
    ):
        """Test "add_command" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_container (CommandContainer): Object instance.
            arg1 (Dict[str, Any]): Command attributes.
            arg2 (Optional[str]): Command.
            add_now (bool): Whether to add the channel now.
            onchange (Union[str, None]): On change.
            valuefrom (Union[str, None]): Value from.
            raise_attr_error (bool): If missing attribute should raise an exeption.
        """

        _attributes = copy.deepcopy(arg1)

        # Patch "logging.getLogger" to intercept calls
        logger_patch = MagicMock(spec=Logger)
        get_logger_patch = mocker.patch("logging.getLogger", return_value=logger_patch)

        # Patch imports to test in isolation
        # mocker.patch("mxcubecore.Command.Spec.SpecCommand")
        # mocker.patch("mxcubecore.Command.Taco.TacoCommand")
        mocker.patch("mxcubecore.Command.Tango.TangoCommand")
        mocker.patch("mxcubecore.Command.Exporter.ExporterCommand")
        mocker.patch("mxcubecore.Command.Epics.EpicsCommand")
        # mocker.patch("mxcubecore.Command.Sardana.SardanaCommand")
        # mocker.patch("mxcubecore.Command.Sardana.SardanaMacro")
        # mocker.patch("mxcubecore.Command.Pool.PoolCommand")
        # mocker.patch("mxcubecore.Command.Tine.TineCommand")
        mocker.patch("mxcubecore.Command.Mockup.MockupCommand")

        # Reset logger patch to remove calls from mock imports
        logger_patch.reset_mock()
        get_logger_patch.reset_mock()

        # Patch "__commands_to_add" to test with known values
        mocker.patch.object(
            cmd_container,
            "_CommandContainer__commands_to_add",
            new=[],
        )

        # Add "onchange" and "valuefrom" values to "_attributes"
        _attributes["onchange"] = onchange
        _attributes["valuefrom"] = valuefrom

        if not raise_attr_error:
            # Patch missing attributes
            mocker.patch.object(cmd_container, "name", create=True)
            mocker.patch.object(cmd_container, "specversion", create=True)
            mocker.patch.object(cmd_container, "taconame", create=True)
            mocker.patch.object(cmd_container, "tangoname", create=True)
            mocker.patch.object(
                cmd_container,
                "exporter_address",
                new="localhost:9000",
                create=True,
            )
            mocker.patch.object(cmd_container, "tine_name", create=True)
            mocker.patch.object(cmd_container, "taurusname", create=True)
            mocker.patch.object(cmd_container, "default_value", create=True)

        if not add_now:
            # Call should add "arg1" and "arg2" to "__commands_to_add"
            res = cmd_container.add_command(
                arg1=_attributes,
                arg2=arg2,
                add_now=add_now,
            )

            # Check return value is "None" as no command object should be created
            assert res is None

            _commands_to_add = getattr(
                cmd_container,
                "_CommandContainer__commands_to_add",
            )

            # Check "__commands_to_add" now contains command arguments
            assert len(_commands_to_add) == 1
            _command_args = _commands_to_add[0]
            assert isinstance(_command_args, tuple) and len(_command_args) == 2
            assert _command_args[0] == _attributes and _command_args[1] == arg2
        else:
            # Command should be added now
            if raise_attr_error:
                if (
                    _attributes["type"] == "exporter"
                    and "exporter_address" not in _attributes
                ):
                    # Class lacks a "exporter_address" attribute, expecting exception
                    with pytest.raises(KeyError):
                        cmd_container.add_command(
                            arg1=_attributes, arg2=arg2, add_now=add_now
                        )
                else:
                    res = cmd_container.add_command(
                        arg1=_attributes, arg2=arg2, add_now=add_now
                    )

                    assert res is not None

                    # Check that "__commands_to_add" was not updated
                    _commands_to_add = getattr(
                        cmd_container, "_CommandContainer__commands_to_add"
                    )
                    assert (
                        isinstance(_commands_to_add, list)
                        and len(_commands_to_add) == 0
                    )
            else:
                res = cmd_container.add_command(
                    arg1=_attributes, arg2=arg2, add_now=add_now
                )

                assert res is not None

                # Check that "__commands_to_add" was not updated
                _commands_to_add = getattr(
                    cmd_container, "_CommandContainer__commands_to_add"
                )
                assert isinstance(_commands_to_add, list) and len(_commands_to_add) == 0

    @pytest.mark.parametrize(
        "channels_to_add",
        (
            [
                (
                    {
                        "name": "test1",
                        "type": "tango",
                    },
                    "test1",
                ),
                (
                    {
                        "name": "test2",
                        "type": "tango",
                        "tangoname": "test_tangoname",
                    },
                    "test2",
                ),
            ],
            [],
        ),
    )
    @pytest.mark.parametrize(
        "commands_to_add",
        (
            [
                {
                    "name": "test1",
                    "type": "tango",
                },
                {
                    "name": "test2",
                    "type": "tango",
                    "tangoname": "test_tangoname",
                },
            ],
            [],
        ),
    )
    def test_add_channels_and_commands(
        self,
        mocker: "MockerFixture",
        cmd_container: CommandContainer,
        channels_to_add: List[Tuple[Dict[str, Any], str]],
        commands_to_add: List[Tuple[Dict[str, Any], Union[str, None]]],
    ):
        """Test "_add_channels_and_commands" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_container (CommandContainer): Object instance.
            channels_to_add (List[Tuple[Dict[str, Any], str]]): Channels to be added.
            commands_to_add (List[Tuple[Dict[str, Any], Union[str, None]]]): Commands to be added.
        """

        # Patch "__channels_to_add" and "__commands_to_add" to test with known values
        mocker.patch.object(
            cmd_container,
            "_CommandContainer__channels_to_add",
            new=copy.deepcopy(channels_to_add),
        )
        mocker.patch.object(
            cmd_container,
            "_CommandContainer__commands_to_add",
            new=copy.deepcopy(commands_to_add),
        )

        # Patch "add_channel" and "add_command" to test in isolation
        _add_channel_patch = mocker.patch.object(cmd_container, "add_channel")
        _add_command_patch = mocker.patch.object(cmd_container, "add_command")

        # Call command
        cmd_container._add_channels_and_commands()

        if channels_to_add and len(channels_to_add):
            # Check that all channels were passed to "add_channel"
            assert _add_channel_patch.call_count == len(channels_to_add)

        if commands_to_add and len(commands_to_add):
            # Check that all commands were passed to "add_command"
            assert _add_command_patch.call_count == len(commands_to_add)

        _channels_to_add = getattr(cmd_container, "_CommandContainer__channels_to_add")
        _commands_to_add = getattr(cmd_container, "_CommandContainer__commands_to_add")

        # Check that all channels and commands have been processed
        assert isinstance(_channels_to_add, list) and len(_channels_to_add) == 0
        assert isinstance(_commands_to_add, list) and len(_commands_to_add) == 0

    @pytest.mark.parametrize("command_name", ("test1", "test2", "test3"))
    @pytest.mark.parametrize(
        "initial_commands",
        (
            {
                "test1": MagicMock(spec=CommandObject),
                "test2": MagicMock(spec=CommandObject),
            },
        ),
    )
    @pytest.mark.parametrize(
        ("cmd_args", "cmd_kwargs"),
        (
            ((None, "Test", 2.5), {"test1": None, "test2": 13, "test3": 8.5}),
            (tuple(), dict()),
        ),
    )
    def test_execute_command(
        self,
        mocker: "MockerFixture",
        cmd_container: CommandContainer,
        command_name: str,
        initial_commands: Dict[str, Annotated[CommandObject, MagicMock]],
        cmd_args: tuple,
        cmd_kwargs: Dict[str, Any],
    ):
        """Test "execute_command" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            cmd_container (CommandContainer): Object instance.
            command_name (str): Command name.
            initial_commands (Dict[str, Annotated[CommandObject, MagicMock]]): Initial commands.
            cmd_args (tuple): Command arguments.
            cmd_kwargs (Dict[str, Any]): Named command arguments.
        """

        # Patch "__commands" with known values to test
        mocker.patch.object(
            cmd_container,
            "_CommandContainer__commands",
            new=initial_commands,
        )

        if not command_name in initial_commands.keys():
            # Check exception raised when command name does not exist
            with pytest.raises(AttributeError):
                cmd_container.execute_command(
                    command_name,
                    *cmd_args,
                    **cmd_kwargs,
                )
        else:
            # Call method
            res = cmd_container.execute_command(
                command_name,
                *cmd_args,
                **cmd_kwargs,
            )

            # Get mock from "initial_commands"
            _mock: MagicMock = initial_commands[command_name]

            # Check result is "return_value" of the mock
            assert res == _mock.return_value

            # Check mock was called with expected parameters
            _mock.assert_called_once()
            assert isinstance(_mock.call_args, type(mocker.call))
            assert _mock.call_args[0] == cmd_args
            assert _mock.call_args[1] == cmd_kwargs

            # Reset mock to clear calls for next test
            _mock.reset_mock(return_value=True)
