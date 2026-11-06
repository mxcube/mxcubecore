from typing import (
    Any,
    Dict,
    Optional,
    Union,
)
from unittest.mock import patch

import pytest

from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.dispatcher import dispatcher
from mxcubecore.ipc import events as ipc_events
from mxcubecore.ipc.dispatcher_bridge import DispatcherBridge
from mxcubecore.ipc.events import (
    build_events,
    describe_events,
    parse_type,
)
from mxcubecore.ipc.whitelist import IPCWhitelistError

OMEGA_VALUE_CHANGED = {
    "role": "diffractometer.omega",
    "signal": "valueChanged",
    "method": "diffractometer.omega.valueChanged",
    "args": ["float"],
}


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("float", float),
        ("Any", Any),
        ("Optional[float]", Optional[float]),
        ("dict[str, Any]", dict[str, Any]),
        ("Dict[str, int]", Dict[str, int]),
        ("int | None", Union[int, None]),
        (
            "mxcubecore.BaseHardwareObjects.HardwareObjectState",
            HardwareObjectState,
        ),
    ],
)
def test_parse_type(expression, expected):
    assert parse_type(expression) == expected


@pytest.mark.parametrize(
    "expression",
    ["os", "__import__('os')", "float(", "lambda: 1", "no.such.module.Thing"],
)
def test_parse_type_rejects_anything_else(expression):
    with pytest.raises(ValueError):
        parse_type(expression)


def test_build_events_with_declared_args(beamline):
    entries = build_events(beamline, [OMEGA_VALUE_CHANGED])

    entry = entries["diffractometer.omega.valueChanged"]
    assert entry.sender is beamline.diffractometer.omega
    assert entry.args == ("float",)
    assert entry.args_schema() == {
        "type": "array",
        "prefixItems": [{"type": "number"}],
        "minItems": 1,
        "maxItems": 1,
    }


def test_build_events_without_args(beamline):
    entries = build_events(
        beamline,
        [{"role": "procedure", "signal": "test_signal", "method": "procedure.test"}],
    )

    assert entries["procedure.test"].args is None
    assert entries["procedure.test"].args_schema() is None


def test_build_events_with_empty_args(beamline):
    entries = build_events(beamline, [{**OMEGA_VALUE_CHANGED, "args": []}])

    schema = entries["diffractometer.omega.valueChanged"].args_schema()
    assert schema["maxItems"] == 0


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"role": "no_such_role"}, "no such beamline role"),
        ({"signal": None}, "missing"),
        ({"args": "float"}, "must be a list"),
        ({"args": ["NotAType"]}, "invalid 'args'"),
    ],
)
def test_build_events_fails_fast(beamline, override, match):
    with pytest.raises(IPCWhitelistError, match=match):
        build_events(beamline, [{**OMEGA_VALUE_CHANGED, **override}])


def test_build_events_rejects_duplicate_method(beamline):
    with pytest.raises(IPCWhitelistError, match="more than once"):
        build_events(beamline, [OMEGA_VALUE_CHANGED, OMEGA_VALUE_CHANGED])


def test_describe_events(beamline):
    entries = build_events(
        beamline,
        [
            OMEGA_VALUE_CHANGED,
            {"role": "procedure", "signal": "test_signal", "method": "procedure.test"},
        ],
    )

    description = describe_events(entries)

    assert description["diffractometer.omega.valueChanged"]["role"] == (
        "diffractometer.omega"
    )
    assert description["diffractometer.omega.valueChanged"]["signal"] == (
        "valueChanged"
    )
    assert description["diffractometer.omega.valueChanged"]["args"] == ["float"]
    assert description["procedure.test"] == {
        "role": "procedure",
        "signal": "test_signal",
        "args": None,
        "args_schema": None,
    }


def test_mismatched_emission_warns_but_is_still_forwarded(beamline):
    # A signal nothing else listens to - omega's own valueChanged has other
    # receivers on the mockup beamline that react (and re-emit) on it.
    entry = build_events(
        beamline,
        [{**OMEGA_VALUE_CHANGED, "signal": "ipcTestSignal", "method": "test"}],
    )["test"]
    forwarded = []
    bridge = DispatcherBridge(lambda method, params: forwarded.append(params))
    bridge.subscribe(entry.sender, entry.signal, entry.method, entry.check_args)
    try:
        with patch.object(ipc_events.logger, "warning") as warning:
            dispatcher.send("ipcTestSignal", entry.sender, 12.5)
            warning.assert_not_called()

            dispatcher.send("ipcTestSignal", entry.sender, "not a float")
            warning.assert_called_once()
    finally:
        bridge.unsubscribe_all()

    assert forwarded == [{"args": [12.5]}, {"args": ["not a float"]}]
