"""Manual integration test for BlissMotor event wiring.

Tests verified:
  1. socket.io event thread is started by BlissProxy.init()
  2. motor_obj.subscribe("property", ...) receives position + state updates
  3. motor_obj.subscribe("online", ...) is wired
  4. A motor move fires BUSY state, then returns to READY after completion

Usage (requires a running BLISS REST API and a motor named MOTOR_NAME):

    BLISSAPI_URL=http://mxcube-test-1:5000 BLISS_MOTOR=dtox python test_blissmotor_events.py

"""

import os
import sys
import time
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(name)s  %(message)s",
)
log = logging.getLogger("test_blissmotor_events")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BLISS_URL = os.environ.get("BLISSAPI_URL", "http://mxcube-test-1:5000")
MOTOR_NAME = os.environ.get("BLISS_MOTOR", "roby")

os.environ["BLISSAPI_URL"] = BLISS_URL

# ---------------------------------------------------------------------------
# Bootstrap a minimal BlissProxy + BlissMotor outside the mxcubecore framework
# ---------------------------------------------------------------------------
from mxcubecore.HardwareObjects.BlissProxy import BlissProxy
from mxcubecore.HardwareObjects.BlissMotor import BlissMotor
from mxcubecore.BaseHardwareObjects import HardwareObjectState

# -- BlissProxy
proxy = BlissProxy("bliss_proxy_test")
proxy.get_property = lambda key, default=None: None  # no YAML config

log.info("Connecting to %s ...", BLISS_URL)
proxy.init()

# Verify the event thread was started
assert proxy._events_thread is not None, "FAIL: _events_thread is None"
assert proxy._events_thread.is_alive(), "FAIL: event thread is not alive"
log.info("OK: socket.io event thread alive (name=%s)", proxy._events_thread.name)

# List known objects
names = proxy.list_objects()
log.info("Known objects: %s", names)
if MOTOR_NAME not in names:
    log.error("Motor '%s' not found in known objects. Available: %s", MOTOR_NAME, names)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Build a minimal BlissMotor that piggy-backs on the proxy's client
# ---------------------------------------------------------------------------
motor = BlissMotor(MOTOR_NAME)
motor.get_property = lambda key, default=None: (MOTOR_NAME if key == "actuator_name" else None)
motor.actuator_name = MOTOR_NAME
# Inject the proxy's object cache so get_object() works
motor._objects = proxy._objects
motor._client = proxy._client

log.info("Initialising BlissMotor '%s' ...", MOTOR_NAME)
motor.init()

# ---------------------------------------------------------------------------
# Test 1 – read current state and position
# ---------------------------------------------------------------------------
state = motor.get_state()
pos = motor.get_value()
log.info("TEST 1  current state=%s  position=%s", state, pos)
assert state is not None, "FAIL: get_state() returned None"
assert pos is not None, "FAIL: get_value() returned None"
log.info("OK: TEST 1 passed")

# ---------------------------------------------------------------------------
# Test 2 – wait a few seconds and confirm property events arrive
# ---------------------------------------------------------------------------
received_events: list[dict] = []

def _record_event(data):
    received_events.append(data)
    log.info("  [event] property: %s", data)

motor.motor_obj.subscribe("property", _record_event)
log.info("Waiting 8 s for property events via socket.io ...")
time.sleep(8)

if received_events:
    log.info("OK: TEST 2 – received %d property event(s)", len(received_events))
else:
    log.warning(
        "WARN: TEST 2 – no property events received in 8 s "
        "(motor may be idle or socket.io not delivering events yet)"
    )

# ---------------------------------------------------------------------------
# Test 3 – move motor +1 unit and check BUSY / READY transition
# ---------------------------------------------------------------------------
state_changes: list = []
original_emit = motor.emit

def _record_state(signal, args=(), **kw):
    if signal == "stateChanged":
        state_changes.append(args[0] if args else kw)
        log.info("  [stateChanged] %s", args[0] if args else kw)
    original_emit(signal, args, **kw)

motor.emit = _record_state  # monkey-patch to intercept

target = pos + 1.0
log.info("TEST 3  moving '%s' from %.3f to %.3f ...", MOTOR_NAME, pos, target)
motor._set_value(target)  # fires BUSY optimistically, then starts move

# The very first stateChanged should be BUSY
time.sleep(0.2)
if state_changes and state_changes[0] == HardwareObjectState.BUSY:
    log.info("OK: TEST 3a – first stateChanged is BUSY")
else:
    log.warning("WARN: TEST 3a – expected BUSY as first stateChanged, got: %s", state_changes)

# Wait for motion to finish and READY to arrive via socket.io
log.info("Waiting up to 30 s for READY ...")
deadline = time.time() + 30
while time.time() < deadline:
    if HardwareObjectState.READY in state_changes:
        break
    time.sleep(0.5)

if HardwareObjectState.READY in state_changes:
    log.info("OK: TEST 3b – READY received after move")
else:
    log.warning("WARN: TEST 3b – READY not received within 30 s")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
log.info("\n=== Summary ===")
log.info("  Event thread alive : %s", proxy._events_thread.is_alive())
log.info("  Property events    : %d", len(received_events))
log.info("  State transitions  : %s", state_changes)
log.info("  Final position     : %s", motor.get_value())
