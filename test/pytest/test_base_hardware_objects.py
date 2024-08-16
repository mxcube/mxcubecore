import copy
import pytest
from typing import (
    Any,
    Union,
    TYPE_CHECKING,
    Iterator,
    Generator,
    Dict,
    Tuple,
    List,
)
from logging import Logger
from unittest.mock import MagicMock
from mxcubecore.BaseHardwareObjects import (
    ConfiguredObject,
    PropertySet,
    HardwareObjectNode,
    HardwareObjectMixin,
    HardwareObject,
    HardwareObjectYaml,
)

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


@pytest.fixture(scope="function")
def configured_object() -> Generator[ConfiguredObject, None, None]:
    """Pytest fixture to instanciate a new "ConfiguredObject" object.

    Yields:
        Generator[ConfiguredObject, None, None]: New object instance.
    """

    configured_object = ConfiguredObject(name="RootObject")
    yield configured_object


@pytest.fixture(scope="function")
def property_set() -> Generator[PropertySet, None, None]:
    """Pytest fixture to instanciate a new "PropertySet" object.

    Yields:
        Generator[PropertySet, None, None]: New object instance.
    """

    property_set = PropertySet()
    yield property_set


@pytest.fixture(scope="function")
def hw_obj_node() -> Generator[HardwareObjectNode, None, None]:
    """Pytest fixture to instanciate a new "HardwareObjectNode" object.

    Yields:
        Generator[HardwareObjectNode, None, None]: New object instance.
    """

    hw_obj_node = HardwareObjectNode(node_name="test_node")
    yield hw_obj_node


@pytest.fixture(scope="function")
def hw_obj_mixin() -> Generator[HardwareObjectMixin, None, None]:
    """Pytest fixture to instanciate a new "HardwareObjectMixin" object.

    Yields:
        Generator[HardwareObjectMixin, None, None]: New object instance.
    """

    hw_obj_mixin = HardwareObjectMixin()
    yield hw_obj_mixin


@pytest.fixture(scope="function")
def hardware_object() -> Generator[HardwareObject, None, None]:
    """Pytest fixture to instanciate a new "HardwareObject" object.

    Yields:
        Generator[HardwareObject, None, None]: New object instance.
    """

    hardware_object = HardwareObject(rootName="RootObject")
    yield hardware_object


@pytest.fixture(scope="function")
def hw_obj_yml() -> Generator[HardwareObjectYaml, None, None]:
    """Pytest fixture to instanciate a new "HardwareObjectYaml" object.

    Yields:
        Generator[HardwareObjectYaml, None, None]: New object instance.
    """

    hw_obj_yml = HardwareObjectYaml(name="RootObject")
    yield hw_obj_yml


class TestConfiguredObject:
    """Run tests for "ConfiguredObject" class"""

    def test_configured_object_setup(self, configured_object: ConfiguredObject):
        """Test initial object setup.

        Args:
            configured_object (ConfiguredObject): Object instance.
        """

        assert configured_object is not None and isinstance(
            configured_object,
            ConfiguredObject,
        )


class TestPropertySet:
    """Run tests for "PropertySet" class"""

    def test_property_set_setup(self, property_set: PropertySet):
        """Test initial object setup.

        Args:
            property_set (PropertySet): Property Set.
        """

        assert property_set is not None and isinstance(property_set, PropertySet)
        assert isinstance(getattr(property_set, "_PropertySet__properties_path"), dict)
        assert isinstance(
            getattr(property_set, "_PropertySet__properties_changed"),
            dict,
        )

    @pytest.mark.parametrize(("name", "path"), (("test", "test/path"),))
    def test_set_property_path(
        self,
        property_set: PropertySet,
        name: Union[str, Any],
        path: Union[str, Any],
    ):
        """Test "set_property_path" method.

        Args:
            property_set (PropertySet): Property Set.
            name (Union[str, Any]): Name.
            path (Union[str, Any]): Path.
        """

        # Call method
        property_set.set_property_path(name=name, path=path)

        # Verify path set against "__properties_path" attribute
        _properties_path: dict = getattr(property_set, "_PropertySet__properties_path")
        assert _properties_path.get(name) == path

    @pytest.mark.parametrize("values", ({"test": "test/path"},))
    def test_get_properties_path(
        self,
        mocker: "MockerFixture",
        property_set: PropertySet,
        values: Dict[str, Any],
    ):
        """Test "get_properties_path" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            property_set (PropertySet): Property Set.
            values (dict[str, Any]): Initial values.
        """

        # Patch "__properties_path" to known value
        mocker.patch.dict(
            in_dict=getattr(property_set, "_PropertySet__properties_path"),
            values=values,
            clear=True,
        )

        # Call method
        res = property_set.get_properties_path()

        # Verify result matches expectations
        assert isinstance(res, Iterator)
        assert len(tuple(res)) == len(values.keys())

    @pytest.mark.parametrize(
        ("name", "path", "initial_value", "new_value"),
        (("test", "test/path", 2.6, 5.8),),
    )
    def test_get_changes(
        self,
        property_set: PropertySet,
        name: Union[str, Any],
        path: Union[str, Any],
        initial_value: Union[int, float, str, bool, None],
        new_value: Union[int, float, str, bool, None],
    ):
        """Test "get_changes" method.

        Args:
            property_set (PropertySet): Property Set.
            name (Union[str, Any]): Name.
            path (Union[str, Any]): Path.
            initial_value (Union[int, float, str, bool, None]): Initial value.
            new_value (Union[int, float, str, bool, None]): New value.
        """

        # Set initial state
        property_set[name] = initial_value
        property_set.set_property_path(name=name, path=path)

        # Update value
        property_set[name] = new_value

        # Verify change recorded in "__properties_changed"
        _properties_changed: dict = getattr(
            property_set,
            "_PropertySet__properties_changed",
        )
        assert _properties_changed.get(name) == str(new_value)

        # Call method
        res = property_set.get_changes()

        # Method should have returned a generator object
        assert isinstance(res, Generator)

        # Verify result matches expectations
        res = tuple(res)
        assert len(res) == 1 and len(res[0]) == 2
        assert res[0][0] == path and res[0][1] == str(new_value)

        # Make sure "__properties_changed" was cleared as it should be
        assert not getattr(property_set, "_PropertySet__properties_changed")


class TestHardwareObjectNode:
    """Run tests for "HardwareObjectNode" class"""

    def test_hardware_object_node_setup(self, hw_obj_node: HardwareObjectNode):
        """Test initial object setup.

        Args:
            hw_obj_node (HardwareObjectNode): Object instance.
        """

        assert hw_obj_node is not None and isinstance(hw_obj_node, HardwareObjectNode)

    @pytest.mark.parametrize(
        ("initial_path", "new_path"),
        (("/mnt/data/user_path", "/mnt/data/new_path"),),
    )
    def test_set_user_file_directory(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        initial_path: str,
        new_path: str,
    ):
        """Test "set_user_file_directory" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            initial_path (str): Initial path.
            new_path (str): New path.
        """

        # Patch "file_directory_patch" on class, so as not to pollute the other tests
        mocker.patch.object(
            HardwareObjectNode,
            "user_file_directory",
            new=initial_path,
            create=True,
        )

        # Call method
        hw_obj_node.set_user_file_directory(user_file_directory=new_path)

        # Validate attribute changed at the class level, not just the instance level
        assert HardwareObjectNode.user_file_directory == new_path
        assert hw_obj_node.user_file_directory == new_path

    @pytest.mark.parametrize(
        ("initial_path", "new_path"),
        (("/mnt/data/old_path", "/mnt/data/new_path"),),
    )
    def test_set_path(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        initial_path: str,
        new_path: str,
    ):
        """Test "set_path" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            initial_path (str): Initial path.
            new_path (str): New path.
        """

        # Patch "_path" attribute to set known values
        mocker.patch.object(
            hw_obj_node,
            "_path",
            new=initial_path,
            create=True,
        )

        # Call method
        hw_obj_node.set_path(path=new_path)

        # Validate path updated
        assert hw_obj_node._path == new_path

    @pytest.mark.parametrize(
        ("objects", "count"),
        (
            ([[None]], 1),
            ([[None], [None], [None]], 3),
            ([[None, None], [None, None, None]], 5),
        ),
    )
    def test_iter(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        objects: List[List[Union[HardwareObject, None]]],
        count: int,
    ):
        """Test "__iter__" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            objects (List[List[Union[HardwareObject, None]]]): Iterable objects.
            count (int): Expected count of objects returned.
        """

        # Patch "__objects_names" and "__objects" attributes to test with known values
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
            new=["None" for _ in range(len(objects))],
        )
        mocker.patch.object(hw_obj_node, "_HardwareObjectNode__objects", new=objects)

        # Call method
        res = iter(hw_obj_node)

        # Validate output matches expectations
        assert isinstance(res, Generator)
        assert len(tuple(res)) == count

    @pytest.mark.parametrize(
        ("objects", "count"),
        (
            ([[None]], 1),
            ([[None], [None], [None]], 3),
            ([[None, None], [None, None, None]], 5),
        ),
    )
    def test_len(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        objects: List[List[Union[HardwareObject, None]]],
        count: int,
    ):
        """Test "__len__" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            objects (List[List[Union[HardwareObject, None]]]): Iterable objects.
            count (int): Expected count of objects returned.
        """

        # Patch "__objects" attribute to set known values
        mocker.patch.object(hw_obj_node, "_HardwareObjectNode__objects", new=objects)

        # Check "len" matches expected count
        assert len(hw_obj_node) == count

    def test_setattr(self, hw_obj_node: HardwareObjectNode):
        """Test "__setattr__" method.

        Args:
            hw_obj_node (HardwareObjectNode): Object instance.
        """

        # Create a value, where the attribute does not exist
        hw_obj_node.test1 = 1

        # Check that key/value was assigned to "__dict__"
        assert "test1" in hw_obj_node.__dict__.keys()
        assert getattr(hw_obj_node, "test1") == 1
        assert "test1" not in hw_obj_node._property_set.keys()

        # Assign a key/value to "_property_set"
        hw_obj_node._property_set["test2"] = 0

        # Set a new value against the value we just added
        setattr(hw_obj_node, "test2", 1)

        # Check that the key/value was not assigned to "__dict__"
        assert "test2" not in hw_obj_node.__dict__.keys()

        # Check that the value returned is correct
        assert getattr(hw_obj_node, "test2") == 1
        assert hw_obj_node._property_set["test2"] == 1

    @pytest.mark.parametrize(
        "key",
        ("key1", "key2", "key3", "key4", 0, 1, 2, 3, 4, None),
    )
    @pytest.mark.parametrize(
        ("initial_obj_names", "initial_objects"),
        ((["key1", "key2", "key3"], [[None, None], [None, None, None], [None]]),),
    )
    def test_getitem(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        key: Union[str, int, Any],
        initial_obj_names: List[str],
        initial_objects: List[Union[List[Union[HardwareObject, None]], None]],
    ):
        """Test "__getitem__" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            key (Union[str, int, Any]): Item key.
            initial_obj_names (List[str]): Initial object names.
            initial_objects (List[Union[List[Union[HardwareObject, None]], None]]):
            Initial objects.
        """

        # Patch "__objects_names" and "__objects" to test with known values
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
            new=initial_obj_names,
        )
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects",
            new=initial_objects,
        )

        _object_names: List[str] = getattr(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
        )
        _objects: List[Union[List[Union[HardwareObject, None]], None]] = getattr(
            hw_obj_node,
            "_HardwareObjectNode__objects",
        )
        if isinstance(key, str):
            if key not in _object_names:
                # Key doesn't exist in "__objects_names", expected to raise "KeyError"
                with pytest.raises(KeyError):
                    hw_obj_node[key]
            else:
                _value = _objects[_object_names.index(key)]
                _actual_val = hw_obj_node[key]
                if _value and len(_value) > 1:
                    # Should be returning list, with multiple items
                    assert isinstance(_actual_val, list) and len(_actual_val) > 1
                else:
                    # Return should be a single item
                    assert not isinstance(_actual_val, list)
        elif isinstance(key, int):
            if _object_names and key < len(_object_names):
                _value = _objects[key]
                _actual_val = hw_obj_node[key]
                if _value and len(_value) > 1:
                    # Should be returning list, with multiple items
                    assert isinstance(_actual_val, list) and len(_actual_val) > 1
                else:
                    # Return should be a single item
                    assert not isinstance(_actual_val, list)
            else:
                # Index out of range, expect to raise "IndexError"
                with pytest.raises(IndexError):
                    hw_obj_node[key]
        else:
            # Unexpected type, expect to raise "TypeError"
            with pytest.raises(TypeError):
                hw_obj_node[key]

    @pytest.mark.parametrize(
        ("name", "reference", "role"),
        (
            (
                "test",
                "test_ref",
                "session",
            ),
        ),
    )
    @pytest.mark.parametrize(
        ("initial_obj_names", "initial_objects"),
        (
            ([], []),
            (["key1", "test", "key3"], [[], [], []]),
        ),
    )
    def test_add_reference(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        name: str,
        reference: str,
        role: str,
        initial_obj_names: List[str],
        initial_objects: List[List[Union[HardwareObject, None]]],
    ):
        """Test "add_reference" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            name (str): Name.
            reference (str): Reference.
            role (str): Role.
            initial_obj_names (List[str]): Initial object names.
            initial_objects (List[List[Union[HardwareObject, None]]]): Initial objects.
        """

        # Patch "__objects_names" and "__objects" to test with known values
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
            new=initial_obj_names,
        )
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects",
            new=initial_objects,
        )

        # Call method
        hw_obj_node.add_reference(name=name, reference=reference, role=role)

        _objects_names: List[str] = getattr(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
        )
        _objects: List[List[Union[HardwareObject, None]]] = getattr(
            hw_obj_node,
            "_HardwareObjectNode__objects",
        )

        if name not in initial_obj_names:
            # Last item in both "__objects_names" and "__objects" expected to be None
            assert _objects_names[-1] is None and _objects[-1] is None
        else:
            # Last item in "__objects" expected to be None
            assert _objects[_objects_names.index(name)][-1] is None

        # Check that item was added to "__references" and item values are as expected
        _references = getattr(hw_obj_node, "_HardwareObjectNode__references")
        assert len(_references) and len(_references[-1]) == 6
        assert all([isinstance(val, str) for val in _references[-1][:3]])
        assert all([isinstance(val, int) for val in _references[-1][3:]])

    @pytest.mark.parametrize(
        ("initial_refs", "initial_obj_names", "initial_objects"),
        (
            ([("/session", "object", "session", 0, 0, -1)], ["object"], [None]),
            ([("/session", None, "session", -1, 0, 0)], [], [[None]]),
        ),
    )
    @pytest.mark.parametrize("initial_hw_object", (MagicMock(), None))
    def test_resolve_references(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        initial_refs: List[Tuple[str, str, str, int, int, int]],
        initial_obj_names: List[str],
        initial_objects: List[Union[List[None], None]],
        initial_hw_object: Union[MagicMock, None],
    ):
        """Test "resolve_references" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            initial_refs (List[Tuple[str, str, str, int, int, int]]):
            Initial references.
            initial_obj_names (List[str]): Initial object names.
            initial_objects (List[Union[List[None], None]]): Initial objects.
            initial_hw_object (Union[MagicMock, None]): Initial hardware object.
        """

        role = initial_refs[0][2]
        objects_names_index = initial_refs[0][3]

        # Patch "__references", "__objects_names" and "__objects" with known values
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__references",
            new=copy.deepcopy(initial_refs),
        )
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
            new=copy.deepcopy(initial_obj_names),
        )
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects",
            new=copy.deepcopy(initial_objects),
        )

        # Mock "__HardwareRepositoryClient" to modify output of "get_hardware_object"
        hardware_object = MagicMock(
            get_hardware_object=lambda *args, **kwargs: initial_hw_object,
        )

        # Patch "get_hardware_repository" to return our mock and avoid having
        # to fully initialise the hardware repository.
        hardware_repository = mocker.patch(
            "mxcubecore.HardwareRepository.get_hardware_repository",
            return_value=hardware_object,
        )

        # Call method
        hw_obj_node.resolve_references()

        # Check that the "get_hardware_repository" was called
        hardware_repository.assert_called_once()

        _objects_names: List[str] = getattr(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
        )
        _objects: List[List[Union[HardwareObject, None]]] = getattr(
            hw_obj_node,
            "_HardwareObjectNode__objects",
        )

        # Verify "hw_obj_node" is in expected state
        if initial_hw_object is not None:
            assert hw_obj_node._objects_by_role.get(role) == initial_hw_object
            assert len(_objects) and _objects[0] == [initial_hw_object]
            if objects_names_index >= 0:
                assert len(_objects_names) and _objects_names[0] == role
        else:
            assert len(_objects_names) == 0 and len(_objects) == 0

    @pytest.mark.parametrize("name", ("key1", "key2", "key3", "key4"))
    @pytest.mark.parametrize("hw_object", (None, HardwareObject(rootName="TestHWObj")))
    @pytest.mark.parametrize("role", (None, "session"))
    @pytest.mark.parametrize(
        ("initial_obj_names", "initial_objects"),
        (
            ([], []),
            (["key1", "key2", "key3"], [[], [], []]),
            (["key1", "key2", "key3"], [[None], [None], [None]]),
        ),
    )
    def test_add_object(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        name: str,
        hw_object: Union[HardwareObject, None],
        role: Union[str, None],
        initial_obj_names: List[str],
        initial_objects: List[List[Union[HardwareObject, None]]],
    ):
        """Test "_add_object" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            name (str): Name.
            hw_object (Union[HardwareObject, None]): Hardware object to add.
            role (Union[str, None]): Role.
            initial_obj_names (List[str]): Initial object names.
            initial_objects (List[List[Union[HardwareObject, None]]]): Initial objects.
        """

        # Patch "__objects_names" and "__objects" to test with known values
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
            new=initial_obj_names,
        )
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects",
            new=initial_objects,
        )

        _objects_names: List[str] = getattr(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
        )
        _objects: List[List[Union[HardwareObject, None]]] = getattr(
            hw_obj_node,
            "_HardwareObjectNode__objects",
        )

        _initial_value: Union[List[Union[HardwareObject, None]], None]
        if name in _objects_names:
            _initial_value = tuple(_objects[_objects_names.index(name)])
        else:
            _initial_value = None

        # Call method
        hw_obj_node._add_object(name=name, hw_object=hw_object, role=role)

        _objects_names: List[str] = getattr(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
        )
        _objects: List[List[Union[HardwareObject, None]]] = getattr(
            hw_obj_node,
            "_HardwareObjectNode__objects",
        )

        if hw_object is not None:
            # Check that "name" exists in "_objects_names"
            assert name in _objects_names

            # Check that "_objects_names" and "_objects" are the same length
            assert _objects_names and _objects and len(_objects_names) == len(_objects)

        if hw_object is None:
            if isinstance(role, str):
                # Check object not present in "_objects_by_role"
                assert not hw_obj_node._objects_by_role.get(role.lower())
        elif isinstance(role, str):
            # Check object is present in "_objects_by_role"
            assert hw_obj_node._objects_by_role.get(role.lower())
            assert hw_obj_node._objects_by_role[role.lower()] == hw_object

            # Check that role was defined on hardware object "__role"
            assert getattr(hw_object, "_HardwareObjectNode__role") == role.lower()

        if hw_object is not None and _initial_value is not None:
            _value = _objects[_objects_names.index(name)]

            # Check value of "hw_object" appended to existing list
            assert len(_initial_value) < len(_value)

            # Last value in list should be value of "hw_object"
            assert _value[-1] == hw_object
        elif hw_object is not None:
            # Last key in "_objects_names" should match "name"
            assert _objects_names[-1] == name

            # Index key in "_objects_names" should point to last item in "_objects"
            assert _objects_names.index(name) == len(_objects) - 1

    @pytest.mark.parametrize(
        ("name", "initial_obj_names", "in_names"),
        (
            ("key1", ["key1", "key2", "key3"], True),
            ("key4", ["key1", "key2", "key3"], False),
        ),
    )
    def test_has_object(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        name: str,
        initial_obj_names: List[str],
        in_names: bool,
    ):
        """Test "has_object" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            name (str): Name.
            initial_obj_names (List[str]): Initial object names.
            in_names (bool): Result expected from method.
        """

        # Patch "__objects_names" to test with known values
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
            new=initial_obj_names,
        )

        # Call method
        res = hw_obj_node.has_object(object_name=name)

        # Check result matches expectations
        assert res == in_names

    @pytest.mark.parametrize("name", ("key1", "key2", "key3", "key4"))
    @pytest.mark.parametrize(
        ("initial_obj_names", "initial_objects"),
        (
            ([], []),
            (["key1", "key2", "key3"], [[], [], []]),
            (["key1", "key2", "key3"], [[None], [None], [None]]),
        ),
    )
    def test_get_objects(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        name: str,
        initial_obj_names: List[str],
        initial_objects: List[List[Union[HardwareObject, None]]],
    ):
        """Test "_get_objects" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            name (str): Name.
            initial_obj_names (List[str]): Initial object names.
            initial_objects (List[List[Union[HardwareObject, None]]]): Initial objects.
        """

        # Patch "__objects_names" and "__objects" to test with known values
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
            new=initial_obj_names,
        )
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects",
            new=initial_objects,
        )

        _objects_names: List[str] = getattr(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
        )
        _objects: List[List[Union[HardwareObject, None]]] = getattr(
            hw_obj_node,
            "_HardwareObjectNode__objects",
        )

        # Call method
        res = list(hw_obj_node._get_objects(object_name=name))

        if name in _objects_names:
            # Check output list matches expectations
            assert res == _objects[_objects_names.index(name)]
        else:
            # Name is not in list, expect an empty list to be returned
            assert len(res) == 0

    @pytest.mark.parametrize("role", ("session", "beam"))
    @pytest.mark.parametrize(
        ("initial_obj_names", "initial_objects"),
        (
            (
                ["key1", "key2"],
                [
                    [(HardwareObject(rootName="TestHWObj1"), "session")],
                    [HardwareObject(rootName="TestHWObj2")],
                ],
            ),
        ),
    )
    @pytest.mark.parametrize("sub_obj_role", ("beam", None))
    def test_get_object_by_role(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        role: str,
        initial_obj_names: List[str],
        initial_objects: List[
            List[Union[Tuple[HardwareObject, str], HardwareObject, None]]
        ],
        sub_obj_role: Union[str, None],
    ):
        """Test "get_object_by_role" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            role (str): Role.
            initial_obj_names (List[str]): Initial object names.
            initial_objects (List[ List[Union[Tuple[HardwareObject, str], HardwareObject, None]] ]):
            Initial objects.
            sub_obj_role (Union[str, None]): Sub object role.
        """

        # Patch "__objects_names" and "__objects" to test with known values
        _initial_objects: List[List[Union[HardwareObject, None]]] = []
        for item in initial_objects:
            _item_objs: List[Union[HardwareObject, None]] = []
            for sub_item in item:
                if isinstance(sub_item, Tuple):
                    hw_obj_node._objects_by_role[sub_item[1]] = sub_item[0]
                    _item_objs.append(sub_item[0])
                else:
                    _item_objs.append(sub_item)
                    if sub_obj_role and isinstance(sub_item, HardwareObject):
                        sub_item._objects_by_role[sub_obj_role] = HardwareObject(
                            rootName="TestHWObj3",
                        )
            _initial_objects.append(_item_objs)
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
            new=copy.deepcopy(initial_obj_names),
        )
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects",
            new=_initial_objects,
        )

        _objects: List[List[Union[HardwareObject, None]]] = getattr(
            hw_obj_node,
            "_HardwareObjectNode__objects",
        )

        # Call method
        if None in _objects and not role.lower() in hw_obj_node._objects_by_role:
            with pytest.raises(AttributeError):
                hw_obj_node.get_object_by_role(role=role)
            res = None
        else:
            res = hw_obj_node.get_object_by_role(role=role)

        #
        if role.lower() in hw_obj_node._objects_by_role:
            assert res == hw_obj_node._objects_by_role[role.lower()]
        elif not None in _objects and sub_obj_role:
            assert isinstance(res, HardwareObject) and res.name() == "TestHWObj3"
        # else:
        #     assert res is None

    @pytest.mark.parametrize(
        "initial_obj_names",
        (
            ["key1", "key2"],
            ["key1", "key2", "key3"],
            ["session"],
        ),
    )
    def test_objects_names(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        initial_obj_names: List[str],
    ):
        """Test "objects_names" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            initial_obj_names (List[str]): Initial object names.
        """

        # Patch "__objects_names" to test with known values
        mocker.patch.object(
            hw_obj_node,
            "_HardwareObjectNode__objects_names",
            new=initial_obj_names,
        )

        # Call method and verify output matches initial values
        assert hw_obj_node.objects_names() == initial_obj_names

    @pytest.mark.parametrize(
        ("name", "value", "output_value"),
        (
            (0, 1, 1),
            (1, "1", 1),
            (2, 2.5, 2.5),
            (3, "2.5", 2.5),
            ("test4", "Test", "Test"),
            ("test5", "None", None),
            ("test6", None, None),
            ("test7", "True", True),
            ("test8", True, True),
            ("test9", "False", False),
            ("test10", False, False),
        ),
    )
    def test_set_property(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        name: Any,
        value: Any,
        output_value: Union[str, int, float, bool],
    ):
        """Test "_set_property" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            name (Any): Property name.
            value (Any): Property value.
            output_value (Union[str, int, float, bool]): Actual output value.
        """

        # Patch "PropertySet.__setitem__" and "PropertySet.set_property_path"
        setitem_patch = mocker.patch.object(PropertySet, "__setitem__")
        set_property_path_patch = mocker.patch.object(PropertySet, "set_property_path")

        # Call method, always returns None
        hw_obj_node._set_property(name=name, value=value)

        # Check "PropertySet.__setitem__" patch was called with expected value
        setitem_patch.assert_called_once_with(*(str(name), output_value))

        # Check "PropertySet.set_property_path" was called with name and path
        set_property_path_patch.assert_called_once_with(
            *(str(name), f"{hw_obj_node._path}/{name}")
        )

    @pytest.mark.parametrize(
        ("name", "default"),
        (
            ("test1", "Default"),
            ("test2", False),
            ("test3", True),
            ("test4", None),
            ("test5", ...),
        ),
    )
    def test_get_property(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        name: str,
        default: Union[Any, None],
    ):
        """Test "get_property" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            name (str): Name.
            default (Union[Any, None]): Default value.
        """

        # Patch "PropertySet.get" to test in isolation
        property_set_get_patch = mocker.patch.object(PropertySet, "get")

        # Call method, verify output returned
        res = hw_obj_node.get_property(name=name, default_value=default)
        assert res is not None and res == property_set_get_patch.return_value

        # Check patch called once with expected parameters
        property_set_get_patch.assert_called_once_with(*(name, default))

    @pytest.mark.parametrize(
        "initial_properties",
        (
            {"test": True},
            {"key1": None, "Key2": None, "Key3": None},
        ),
    )
    def test_get_properties(
        self,
        hw_obj_node: HardwareObjectNode,
        initial_properties: Dict[str, Any],
    ):
        """Test "get_properties" method.

        Args:
            hw_obj_node (HardwareObjectNode): Object instance.
            initial_properties (Dict[str, Any]): Initial properties.
        """

        # Update "_property_set" to test with known values
        hw_obj_node._property_set.update(initial_properties)

        # Call method and verify output matches initial values
        assert hw_obj_node.get_properties() == initial_properties

    @pytest.mark.parametrize(
        "level",
        (
            "debug",
            "error",
            "warning",
            "info",
            "flange",
        ),
    )
    def test_print_log(
        self,
        mocker: "MockerFixture",
        hw_obj_node: HardwareObjectNode,
        level: str,
    ):
        """Test "print_log" method.

        Args:
            mocker (MockerFixture): Instance of the Pytest mocker fixture.
            hw_obj_node (HardwareObjectNode): Object instance.
            level (str): Logging level.
        """

        # Patch "logging.getLogger" to intercept calls
        logger_patch = MagicMock(spec=Logger)
        get_logger_patch = mocker.patch("logging.getLogger", return_value=logger_patch)

        _log_type = f"{level.upper()}_TEST"
        _message = f"Test {level.capitalize()} Entry."

        # Call method, output is always going to be "None"
        hw_obj_node.print_log(log_type=_log_type, level=level, msg=_message)

        # All tests should make at least one call to patched "logging.getLogger"
        get_logger_patch.assert_called_with(*(_log_type,))

        logger_level_patch: Union[MagicMock, None] = getattr(logger_patch, level, None)
        if logger_level_patch is not None:
            # If the logging level exists, check that it was called with our message
            logger_level_patch: MagicMock
            logger_level_patch.assert_called_once_with(*(_message,))


class TestHardwareObjectMixin:
    """Run tests for "HardwareObjectMixin" class"""

    def test_hardware_object_mixin_setup(self, hw_obj_mixin: HardwareObjectMixin):
        """Test initial object setup.

        Args:
            hw_obj_mixin (HardwareObjectMixin): Object instance.
        """

        assert hw_obj_mixin is not None and isinstance(
            hw_obj_mixin,
            HardwareObjectMixin,
        )

    # def test_misc(self):
    #     """ """

    #     # __bool__
    #     # __nonzero__
    #     # _init
    #     # init
    #     # pydantic_model
    #     # exported_attributes

    # def test_get_type_annotations(self): ...

    # def test_execute_exported_command(self): ...

    # def test_abort(self): ...

    # def test_stop(self): ...

    # def test_get_state(self): ...

    # def test_get_specific_state(self): ...

    # def test_wait_ready(self): ...

    # def test_is_ready(self): ...

    # def test_update_state(self): ...

    # def test_update_specific_state(self): ...

    # def test_re_emit_values(self): ...

    # def test_force_emit_signals(self): ...

    # def test_clear_gevent(self): ...

    # def test_emit(self): ...

    # def test_connect(self): ...

    # def test_disconnect(self): ...


class TestHardwareObject:
    """Run tests for "HardwareObject" class"""

    def test_hardware_object_setup(self, hardware_object: HardwareObject):
        """Test initial object setup.

        Args:
            hardware_object (HardwareObject): Object instance.
        """

        assert hardware_object is not None and isinstance(
            hardware_object,
            HardwareObject,
        )

    # def test_misc(self):
    #     """ """

    #     # exported_attributes
    #     # __getstate__

    # def test_init(self): ...

    # def test_setstate(self): ...

    # def test_getattr(self): ...

    # def test_commit_changes(self): ...

    # def test_rewrite_xml(self): ...

    # def test_xml_source(self): ...


class TestHardwareObjectYaml:
    """Run tests for "HardwareObjectYaml" class"""

    def test_hardware_object_yaml_setup(self, hw_obj_yml: HardwareObjectYaml):
        """Test initial object setup.

        Args:
            hw_obj_yml (HardwareObjectYaml): Object instance.
        """

        assert hw_obj_yml is not None and isinstance(hw_obj_yml, HardwareObjectYaml)

    # def test_user_name(self): ...

    # def test_gui(self): ...
