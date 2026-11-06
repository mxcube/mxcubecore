import pytest
from pydantic import (
    BaseModel,
    ValidationError,
)

from mxcubecore.ipc.whitelist import (
    IPCWhitelistError,
    build_whitelist,
    describe,
    dispatch,
    ipc_method,
)


def test_self_describing_method_is_eligible(beamline):
    registry = build_whitelist(beamline, ["ipc_gateway.ping"])

    assert "ipc_gateway.ping" in registry
    entry = registry["ipc_gateway.ping"]
    assert entry.role == "ipc_gateway"
    assert entry.method_name == "ping"


def test_nested_role_path_is_eligible(beamline):
    # "omega" is only reachable as diffractometer's own sub-role (its
    # `motors:` config), not as one of beamline's own top-level roles.
    registry = build_whitelist(
        beamline,
        ["diffractometer.omega.set_value", "diffractometer.omega.get_value"],
    )

    entry = registry["diffractometer.omega.set_value"]
    assert entry.role == "diffractometer.omega"
    assert entry.method_name == "set_value"

    # timeout=None blocks until the move is done (set_value's own
    # default, 0, returns at once).
    result = dispatch(
        beamline,
        registry,
        "diffractometer.omega.set_value",
        {"value": 42.0, "timeout": None},
    )
    assert result is None
    assert dispatch(beamline, registry, "diffractometer.omega.get_value", {}) == 42.0


def test_nested_role_path_unknown_sub_role_raises(beamline):
    with pytest.raises(IPCWhitelistError, match="no such beamline role"):
        build_whitelist(beamline, ["diffractometer.no_such_motor.set_value"])


def test_unknown_role_raises(beamline):
    with pytest.raises(IPCWhitelistError, match="no such beamline role"):
        build_whitelist(beamline, ["no_such_role.some_method"])


def test_unknown_method_raises(beamline):
    with pytest.raises(IPCWhitelistError, match="no callable method"):
        build_whitelist(beamline, ["procedure.no_such_method"])


def test_non_eligible_method_raises(beamline):
    # AbstractProcedure.start() does not take a single pydantic.BaseModel
    # argument, so it isn't self-describing and isn't @ipc_method-decorated.
    with pytest.raises(IPCWhitelistError, match="not IPC-eligible"):
        build_whitelist(beamline, ["procedure.start"])


def test_malformed_entry_raises(beamline):
    with pytest.raises(IPCWhitelistError, match="expected 'role.method'"):
        build_whitelist(beamline, ["not_a_role_dot_method"])


def test_dispatch_calls_method_and_returns_json(beamline):
    registry = build_whitelist(beamline, ["ipc_gateway.ping"])

    result = dispatch(beamline, registry, "ipc_gateway.ping", {"message": "hello"})

    assert result == "pong: hello"


def test_dispatch_validates_params(beamline):
    registry = build_whitelist(beamline, ["ipc_gateway.ping"])

    with pytest.raises(ValidationError):
        # "message" must be a string - passing a nested object should fail
        # pydantic validation.
        dispatch(beamline, registry, "ipc_gateway.ping", {"message": {"a": 1}})


def test_dispatch_rejects_non_whitelisted_method(beamline):
    registry = build_whitelist(beamline, ["ipc_gateway.ping"])

    with pytest.raises(IPCWhitelistError, match="not whitelisted"):
        dispatch(beamline, registry, "procedure.start", {})


def test_describe_returns_schema_pair_per_entry(beamline):
    registry = build_whitelist(beamline, ["ipc_gateway.ping"])

    description = describe(registry)

    assert set(description) == {"ipc_gateway.ping"}
    entry_description = description["ipc_gateway.ping"]
    assert entry_description["request_schema"]["title"] == "PingRequest"
    # ping returns a bare str, not a pydantic.BaseModel - its
    # "response_schema" comes from a TypeAdapter(str) instead, no title.
    assert entry_description["response_schema"] == {"type": "string"}
    assert "message" in entry_description["request_schema"]["properties"]


def test_ipc_method_decorator_supplies_explicit_models(beamline):
    class Req(BaseModel):
        x: int

    class Resp(BaseModel):
        y: int

    class Target:
        @ipc_method(request_model=Req, response_model=Resp)
        def not_self_describing(self, x, y=0):
            # Deliberately untyped (no `x: int`) to prove the decorator
            # alone is enough to make this eligible. dispatch() unpacks
            # Req's own fields as kwargs, exactly like an auto-built
            # request model's are - not_self_describing(x=...), never
            # not_self_describing(Req(...)).
            return Resp(y=x + y)

    beamline.not_self_describing_target = Target()

    registry = build_whitelist(
        beamline, ["not_self_describing_target.not_self_describing"]
    )
    entry = registry["not_self_describing_target.not_self_describing"]

    assert entry.request_model is Req
    assert entry.response_model is Resp

    result = dispatch(
        beamline,
        registry,
        "not_self_describing_target.not_self_describing",
        {"x": 5},
    )
    assert result == {"y": 5}
