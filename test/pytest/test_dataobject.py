import jsonschema

from mxcubecore.utils.dataobject import DataObject


class MockDataObject(DataObject):
    _SCHEMA = {
        "type": "object",
        "properties": {"value": {"type": "number"}, "limit": {"type": "number"}},
    }


def test_object_creation():
    do = MockDataObject({"value": 2, "limit": 4})

    assert do.value == 2 and do.limit == 4


def test_validation_not_valid():
    # Limit should be a number so this should raise a ValidationError
    try:
        MockDataObject({"value": 2, "limit": "2"})
    except jsonschema.exceptions.ValidationError:
        assert True
    else:
        assert False


def test_validation_valid():
    try:
        MockDataObject({"value": 2, "limit": 2})
    except jsonschema.exceptions.ValidationError:
        assert False
    else:
        assert True


def test_dangerously_set_valid():
    do = MockDataObject({"value": 2, "limit": 2})

    do.dangerously_set("value", 4)

    assert do.value == 4


def test_dangerously_set_not_valid():
    # Limit should be a number so this should raise a ValidationError
    try:
        do = MockDataObject({"value": 2, "limit": 2})
        do.dangerously_set("value", "4")

    except jsonschema.exceptions.ValidationError:
        assert do.value == 2
    else:
        assert False


def test_to_mutable():
    do = MockDataObject({"value": 2, "limit": 2})

    do_mutable = do.to_mutable()

    do_mutable["value"] = 4

    assert do.value != do_mutable["value"]
