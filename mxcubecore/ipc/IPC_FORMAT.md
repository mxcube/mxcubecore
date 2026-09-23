# MXCuBE IPC infrastrucure and format

This documents the format used by `mxcubecore.ipc` to let third-party
clients call a whitelisted set of `HardwareObject` methods and receive
events, over either a JSON-RPC/TCP transport or a NanoMQ (MQTT) transport.
Both transports carry the exact same envelope; only framing differs.

The underlaying message format used is JSON-RPC, at the time of writing
version 2.0.

JSON-RPC primarily defines data structures and the rules around their
processing. It is transport agnostic meaning that its decoupled from the
communication protocol/channel used. The format was chosen because it simple
and lightweight.

Status: version 0.0.1 (`mxcubecore.ipc.constants.IPC_FORMAT_VERSION`).

## 1. Envelope

Every message is a single JSON object, JSON-RPC 2.0 shaped
(`mxcubecore/ipc/models.py`):

```json
{"jsonrpc": "2.0", "id": 1, "method": "diffractometer.move_motor", "params": {...}}
```

- `IPCRequest` (client -> server): `id`, `method`, `params` (an object matching
  the target method's request model - see section 4).
- `IPCResponse` (server -> client): `id` echoes the request's `id`; exactly one
  of `result` / `error` is set.
- `IPCEvent` (server -> client, unsolicited): no `id`; `method` names the
  event, `params` its payload. Used both for the auth/session layer's own
  notices and for HardwareObject signals forwarded per the `events:` config
  (section 5).

```json
{"jsonrpc": "2.0", "id": 1, "result": {"position": 12.3}}
{"jsonrpc": "2.0", "id": 1, "error": {"code": -32001, "message": "Method not whitelisted: ..."}}
{"jsonrpc": "2.0", "method": "diffractometer.stateChanged", "params": {"args": ["READY"]}}
```

## 2. Error codes (`mxcubecore.ipc.constants.ErrorCode`)

Codes in the range -32700 to -32600, the JSON-RPC 2.0 reserved range. Like this a
any JSON-RPC client can interpret the messages . Codes at -32000 and below are
MXCuBE-specific ("server error" range, per the JSON-RPC 2.0 spec):

| Code   | Name                       | Meaning                                                     |
| ------ | -------------------------- | ----------------------------------------------------------- |
| -32700 | `PARSE_ERROR`              | Request body wasn't valid IPCRequest JSON                   |
| -32603 | `INTERNAL_ERROR`           | Unexpected server-side failure                              |
| -32000 | `NOT_AUTHENTICATED`        | No/failed `_auth` handshake yet                             |
| -32001 | `METHOD_NOT_WHITELISTED`   | `method` isn't in `allowed_methods`                         |
| -32002 | `VALIDATION_ERROR`         | `params` didn't validate against the method's request model |
| -32003 | `CLIENT_ALREADY_CONNECTED` | Only one client may be connected at a time                  |

## 3. Authentication handshake

Before any whitelisted method can be called, the client must send one
`IPCRequest` to the reserved method `_auth`:

```json
{"jsonrpc": "2.0", "id": 0, "method": "_auth", "params": {"token": "<shared secret>"}}
```

The server compares the token against `IPCServer`'s configured `auth_token`
and, on success, binds this session as *the* active client. Any other session's
calls (including a concurrent `_auth`) are rejected with `CLIENT_ALREADY_CONNECTED`
until the current client disconnects.

On the NanoMQ transport, since MQTT has no inherent notion of "a connection", every
message (not just `_auth`) must additionally carry a transport-level `_client_id`
field alongside the envelope:

```json
{"jsonrpc": "2.0", "id": 1, "method": "diffractometer.move_motor", "params": {...}, "_client_id": "..."}
```

`_client_id` is stripped before the JSON is parsed as an `IPCRequest` (extra fields
are ignored). It exists purely so the transport can tell which messages belong to
the currently-bound client.

A client may optionally also add `_client_host` (e.g. `"my-laptop (192.168.1.5)"`)
to the first message it sends, logged for anyone reading the `HWR.ipc` logger.
Unlike the JSON-RPC/TCP transport's peer address (read straight off the accepted
socket), NanoMQ's `IPCServer` never sees a per-client connection. It only handles
messages relayed through the broker meaning that `_client_host` is purely
self-reported, at the same trust level as `_client_id` itself: useful for diagnostics,
not for anything security-relevant.

Freeing the slot on the NanoMQ transport needs an explicit event, since MQTT never
tells a broker's *other* clients when one of them goes away. A client releases its
session by publishing `{"_client_id": "..."}` to `<topic_prefix>/disconnect`. The
same way it must for graceful shutdown *and* register as its own MQTT Last Will
(`client.will_set(...)`, so the broker publishes it automatically if the client
disconnects uncleanly, e.g. a crash or network loss). Without either, the slot stays
held until the whole `IPCServer` is stopped. See `test_ipc_nanomq_client.py` for a
worked example of both.

## 4. The whitelist

`IPCServer` is configured with a flat list of `"role.method"` strings
(`allowed_methods`) - the *entire* global whitelist lives in this one list,
not scattered across every object's own configuration, so that its easy to
get an overview. The last dot-separated segment is always the method name.
Every segment before it is a role, resolved one hop at a time starting from
`HWR.beamline` (`mxcubecore.ipc.whitelist.resolve_role_path()`), the same
way `get_object_by_role()` resolves any role elsewhere in this codebase.
`"diffractometer.omega.set_value"` means: `beamline`'s `diffractometer`
role, that object's own `omega` sub-role (e.g. from its `motors:` config),
then call `set_value` on it - `omega` doesn't need to *also* be one of
beamline's own top-level roles just to be whitelistable.

A whitelisted method's parameters is validated against a pydantic model
built from the parameter type hints.

```python
def move_motor(self, value: float, timeout: Optional[float] = None) -> float: ...
```

- every parameter (besides `self`) has a type hint so we can build a pydantic
  model

- The decorator `@ipc_method(request_model=..., response_model=...)`, can be used
  when the signature itself isn't annotated precisely enough (e.g. untyped parameters,
  forward references, or wanting stricter validation.

The return value works the same way in reverse: if the method's return
type hint (or an explicit `response_model=`) is a `pydantic.BaseModel`
subclass, the method must return an instance of it. Otherwise, the bare
return value (a `float`, `None`, a `dict`, ...) is used directly as the JSON
result, best-effort (`mxcubecore.ipc.jsonable.to_jsonable`).

Satisifying these requirements does **not** expose a method autmoatically, it
also needs to be whitelisted `allowed_methods`.

## 5. Event forwarding

`IPCServer`'s `events:` config lists HardwareObject signals to forward as
`IPCEvent`s:

```yaml
events:
  - role: diffractometer
    signal: stateChanged
    method: diffractometer.stateChanged
  - role: diffractometer.omega
    signal: valueChanged
    method: diffractometer.omega.valueChanged
    args: [float]                # optional, see below
```

`role` is resolved the same way as in section 4, via`resolve_role_path()`).

The whole list is resolved once at startup
(`mxcubecore.ipc.events.build_events()`) and fails fast like the method
whitelist: an unresolvable `role`, an invalid `args`, or two entries with
the same `method` stops the IPCServer from starting.

### Declaring event arguments

HardwareObject signals aren't declared anywhere - `emit()` can pass
anything - so an event's payload can't be introspected the way a method's
signature can. `args` declares it explicitly instead: one Python type
expression per positional signal argument, in order. Accepted names are
`Any`, `None`, `bool`, `int`, `float`, `str`, `bytes`, `list`, `dict`,
`tuple`, `List`, `Dict`, `Tuple`, `Optional` and `Union`, subscripted
(`dict[str, Any]`, `Optional[float]`) or joined with `|` (`int | None`);
anything else must be a fully-qualified importable path
(`mxcubecore.model.foo.Bar`).

An entry without `args` is forwarded unchanged and described with
`"args": null, "args_schema": null`.

## 6. Self-description

A client can discover the whole whitelist - what's callable and the shape
of its arguments/return value - without hardcoding any of it, by calling
the reserved method `_describe` (like `_auth`, requires the session to
already be authenticated):

```json
{"jsonrpc": "2.0", "id": 1, "method": "_describe", "params": {}}
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "methods": {
      "ipc_gateway.ping": {
        "request_schema": {"title": "PingRequest", "type": "object", "properties": {"message": {"type": "string", "default": ""}}},
        "response_schema": {"type": "string"}
      }
    },
    "events": {
      "diffractometer.omega.valueChanged": {
        "role": "diffractometer.omega",
        "signal": "valueChanged",
        "args": ["float"],
        "args_schema": {"type": "array", "prefixItems": [{"type": "number"}], "minItems": 1, "maxItems": 1}
      }
    }
  }
}
```

One entry per whitelisted `"role.method"`, built by
`mxcubecore.ipc.whitelist.describe()` from each entry's
`request_model.model_json_schema()`.

`events` has one entry per configured event (section 5), keyed by its
`method`, built by `mxcubecore.ipc.events.describe_events()`. `args` and
`args_schema` are `null` when the entry doesn't declare `args`.

`MXCuBEIPCClient`, from the separate `mxcube-ipc-client` package, is the
reference consumer: it calls `_auth` then `_describe` during construction
and builds one proxy per role from the result (`client.ipc_gateway.ping(...)`),
so it never has to hardcode a beamline's whitelist either. The `events`
half is kept as `client.events`.

## 7. Debug bypass (off by default, insecure)

\*\*Enabling this means any authenticated client can invoke any method on
any resolvable role with any arguments. No white list or input validation.
\*\*It exists for exploring/debugging only.

Debug mode is Off unless `IPCServer`'s `allow_debug_calls: true` is set
explicitly. In which case a `WARNING`-level line is logged at startup saying
so, and every debug call is logged in full (method, args, result) at `WARNING`
for an audit trail. Requires the same `_auth` handshake as everything else;
with the flag off, all three methods below fail with
`DEBUG_CALLS_DISABLED` (`-32004`) regardless of authentication.
