"""Quick test script to verify BlissProxy connectivity to mxcube-test-1"""

import os
import sys
import time

os.environ["BLISSAPI_URL"] = "http://mxcube-test-1:5000"

try:
    from blissclient import BlissClient
except ImportError:
    print("ERROR: blissclient not installed. Run: pip install blissclient")
    sys.exit(1)

print(f"Connecting to BLISS API at {os.environ['BLISSAPI_URL']} ...")

client = BlissClient()
client.create_connect()

# Wait for socketio events to populate hardware.available
# (server auto-registers objects with 5s delay + up to 3 retries of 5s each)
print("Waiting for hardware objects to be registered", end="", flush=True)
timeout = 30
for _ in range(timeout * 10):
    if hardware := client.hardware:
        try:
            names = hardware.available
            if names:
                break
        except Exception:
            pass
    print(".", end="", flush=True)
    time.sleep(0.1)
print()

session = client.session
hardware = client.hardware

# ---- Session info ----
print("\n--- Session info ---")
print(f"  name: {session.name}")

# ---- SCAN_SAVING ----
print("\n--- SCAN_SAVING ---")
try:
    scan_saving = session.scan_saving
    print(f"  base_path:     {scan_saving.base_path}")
    print(f"  proposal_name: {scan_saving.proposal_name}")
    print(f"  data_path:     {scan_saving.data_path}")
except Exception as e:
    print(f"  ERROR: {e}")

# ---- All session objects from hardware.available ----
print("\n--- All session objects (hardware.available) ---")
try:
    all_obj_names = sorted(hardware.available)
    print(f"  Found {len(all_obj_names)} objects")
except Exception as e:
    print(f"  ERROR: {e}")
    all_obj_names = []

ok, failed = 0, 0

# Build a map of type_name -> schema for callables/properties lookup
type_schema_map = {}
try:
    for schema in hardware._object_types.results:
        type_schema_map[schema.type] = schema
except Exception:
    pass

for obj_name in all_obj_names:
    try:
        obj = hardware.get(obj_name)
        obj_bliss_type = getattr(obj, "type", "?")
        pos = acc = state = "N/A"
        try:
            pos = obj.position
        except Exception:
            pass
        try:
            acc = obj.acceleration
        except Exception:
            pass
        try:
            state = obj.state
        except Exception:
            pass

        # Get properties and callables from the type schema
        schema = type_schema_map.get(obj_bliss_type)
        if schema:
            props = list(schema.properties.keys())
            callables = list(schema.callables.keys())
        else:
            props = [a for a in dir(obj) if not a.startswith("_") and not callable(getattr(obj, a, None))]
            callables = [a for a in dir(obj) if not a.startswith("_") and callable(getattr(obj, a, None))]

        print(f"  {obj_name} [type={obj_bliss_type}]: state={state}, position={pos}, acceleration={acc}")
        if props:
            print(f"    properties : {', '.join(props)}")
        if callables:
            print(f"    callables  : {', '.join(callables)}")
        ok += 1
    except Exception as e:
        print(f"  {obj_name}: FAILED ({type(e).__name__}: {e})")
        failed += 1

print(f"\nOK: {ok}/{ok + failed} objects successfully retrieved.")

print("\nDone.")
print("     obj = hardware.get('robx'); obj.position; obj.move(1.0)")



