import pytest
from pydantic import BaseModel, ValidationError

from mxcubecore.ipc import debug


class _EchoRequest(BaseModel):
    value: float
    timeout: float = 0.0


class _EchoTarget:
    """A role with a method that still takes a single pydantic.BaseModel
    parameter - most mockup ipc_* methods no longer do (they take real
    parameters directly, auto-eligible for the whitelist), but a method
    can still be written this way, and debug_call() should still be able
    to reach it with a plain JSON object - see the coercion tests below.
    """

    def echo(self, request: _EchoRequest) -> float:
        return request.value


def test_list_roles_of_beamline_itself(beamline):
    result = debug.list_roles(beamline)
    assert "procedure" in result["roles"]
    assert "diffractometer" in result["roles"]
    assert result["class"] == "Beamline"


def test_list_roles_of_nested_role(beamline):
    result = debug.list_roles(beamline, "diffractometer")
    assert "omega" in result["roles"]


def test_list_roles_unknown_role_raises(beamline):
    with pytest.raises(ValueError, match="No such role"):
        debug.list_roles(beamline, "no_such_role")


def test_describe_role_lists_methods_and_sub_roles(beamline):
    result = debug.describe_role(beamline, "diffractometer.omega")
    assert result["class"] == "MotorMockup"
    assert "get_value" in result["methods"]
    assert "set_value" in result["methods"]


def test_describe_role_includes_schema_when_buildable(beamline):
    result = debug.describe_role(beamline, "diffractometer.omega")
    set_value = result["methods"]["set_value"]
    assert set_value["signature"].startswith("(value: Any")
    assert set_value["schema"]["required"] == ["value"]
    assert "value" in set_value["schema"]["properties"]
    assert "timeout" in set_value["schema"]["properties"]


def test_describe_role_survives_a_parameter_pydantic_cannot_handle_at_all(beamline):
    # Regression: a parameter type-hinted with a plain (non-pydantic,
    # non-BaseModel) class - unlike a Callable-typed parameter, pydantic
    # can't even build a core schema for this one, so it fails inside
    # build_request_model() itself (create_model()), not just later in
    # model_json_schema() - describe_role() must not let that exception
    # escape and take out every other method's description with it.
    class Unschemaable:
        pass

    class Target:
        def uses_arbitrary_type(self, thing: Unschemaable) -> None:
            pass

        def get_value(self) -> float:
            return 1.0

    beamline.unschemaable_target = Target()

    result = debug.describe_role(beamline, "unschemaable_target")
    assert result["methods"]["uses_arbitrary_type"]["schema"] is None
    assert result["methods"]["get_value"]["schema"] == {
        "properties": {},
        "title": "GetValueRequest",
        "type": "object",
    }


def test_debug_call_invokes_arbitrary_method(beamline):
    result = debug.debug_call(beamline, "diffractometer.omega", "get_value")
    assert isinstance(result, float)


def test_debug_call_with_args_and_kwargs(beamline):
    # timeout=None blocks until the (simulated) move completes - set_value's
    # own default (timeout=0) is fire-and-forget, so get_value() right after
    # could still see the pre-move value.
    result = debug.debug_call(
        beamline,
        "diffractometer.omega",
        "set_value",
        kwargs={"value": 33.0, "timeout": None},
    )
    assert result is None  # set_value itself returns None

    value = debug.debug_call(beamline, "diffractometer.omega", "get_value")
    assert value == 33.0


def test_debug_call_unknown_method_raises(beamline):
    with pytest.raises(ValueError, match="no callable method"):
        debug.debug_call(beamline, "diffractometer.omega", "no_such_method")


def test_debug_call_rejects_non_list_args(beamline):
    # e.g. a client that JSON-quoted its whole args field by mistake,
    # sending a plain string instead of an array - args or [] blindly
    # star-unpacked would otherwise iterate the string's characters as
    # individual positional arguments, one of the most confusing failure
    # modes this bypass can produce.
    with pytest.raises(TypeError, match="args must be a JSON array"):
        debug.debug_call(
            beamline, "diffractometer.omega", "set_value", args="{value: 2}"
        )


def test_debug_call_rejects_non_dict_kwargs(beamline):
    with pytest.raises(TypeError, match="kwargs must be a JSON object"):
        debug.debug_call(
            beamline, "diffractometer.omega", "set_value", kwargs="{value: 2}"
        )


def test_debug_call_result_is_json_safe_for_pydantic_return(beamline):
    class Target:
        def get_response(self):
            return _EchoRequest(value=12.0)

    beamline.pydantic_return_target = Target()

    result = debug.debug_call(beamline, "pydantic_return_target", "get_response")
    assert result == {"value": 12.0, "timeout": 0.0}


def test_debug_call_coerces_dict_kwarg_to_pydantic_request(beamline):
    beamline.echo_target = _EchoTarget()

    # A plain JSON object for a pydantic.BaseModel-typed parameter - as a
    # caller who doesn't already know _EchoRequest's Python class would
    # naturally send - should work the same as passing the model directly.
    result = debug.debug_call(
        beamline, "echo_target", "echo", kwargs={"request": {"value": 45.0}}
    )
    assert result == 45.0


def test_debug_call_coerces_positional_dict_to_pydantic_request(beamline):
    beamline.echo_target = _EchoTarget()

    result = debug.debug_call(beamline, "echo_target", "echo", args=[{"value": 50.0}])
    assert result == 50.0


def test_debug_call_dict_coercion_validation_error_propagates(beamline):
    beamline.echo_target = _EchoTarget()

    with pytest.raises(ValidationError):
        debug.debug_call(
            beamline,
            "echo_target",
            "echo",
            # missing the required "value" field
            kwargs={"request": {"timeout": 1.0}},
        )
