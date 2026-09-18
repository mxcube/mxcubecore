# Queue client JSON format

This documents the MXCuBE JSON Queue format used to read and mutate the queue. 
Extracted from `mxcubeweb `QueueSerializer`/`QueueBuilder` in 
`mxcubeweb/mxcubeweb/core/components/queue.py` into (`mxcubecore.queuelib`). So 
the format can be expressed in a more well defined way. 

For the underlying queue architecture this format sits on top of (`QueueManager`,
`QueueModel`, `QueueEntry`, `TaskNode`, dynamic queue entries) see
`docs/source/dev/queue.md`.

Status: this describes the format **as it/is exists/used today**, version 0.0.1. 

## 1. The queue tree

The whole queue is a dict keyed by sample ID:

```json
{
  "SID1": { "...": "a SampleNode, see below" },
  "SID2": { "...": "a SampleNode, see below" },
  "sample_order": ["SID1", "SID2"],
  "format_version": "1.0.0"
}
```

- `sample_order` is a list of sample IDs in queue order 
- `format_version` identifies the version of this document/schema the
  response conforms to `mxcubecore.queuelib.QUEUE_FORMAT_VERSION`.
  `queuelib/json_schema.py`/`queuelib/queue.schema.json` for the generated,
  published JSON Schema this version identifies.

## 2. `SampleNode`

```json
{
  "type": "Sample",
  "queueID": 12,
  "checked": true,
  "state": 4,
  "sampleID": "1:05",
  "code": null,
  "location": "1:05",
  "cell_no": 0,
  "puck_no": 1,
  "sampleName": "sample-1",
  "proteinAcronym": "LYS",
  "defaultPrefix": "LYS-sample-1",
  "defaultSubDir": "LYS/LYS-sample-1",
  "tasks": [ "... TaskNode objects, see below ..." ]
}
```

- `location`: the sample-changer location string (`"cell:puck"` or similar), or
  the literal string `"Manual"` for a manually-added ("free pin") sample - not a
  separate boolean field.
- `defaultPrefix` / `defaultSubDir`: computed from `HWR.beamline.session`, not
  client-supplied.
- `state`: see the bit-flag encoding in section 5.

## 3. `TaskNode` base shape

Every task (`DataCollection`, `Characterisation`, `Workflow`, `GphlWorkflow`,
`xrf_spectrum`, `energy_scan`, `Interleaved`) shares these fields, then adds a
`parameters` object specific to its `type`:

```json
{
  "type": "DataCollection",
  "queueID": 34,
  "checked": true,
  "state": 0,
  "label": "OSCILLATION (foo_1_####.h5)",
  "sampleID": "1:05",
  "sampleQueueID": 12,
  "taskIndex": 0,
  "diffractionPlan": null,
  "diffractionPlanID": null,
  "name": null,
  "parameters": { "...": "type-specific, see below" }
}
```

- `queueID`: the node's `_node_id`. 
- `queueID: -1` is the "not yet queued" 
- `taskIndex`: position within the flattened per-sample task list 

### Type-specific `parameters`

| `type` | `parameters` schema | Notes |
|---|---|---|
| `DataCollection` | `DataCollectionParameters` | Also used, unmodified, for `Interleaved` wedges. |
| `Characterisation` | `CharacterisationParameters` (extends `DataCollectionParameters`) | |
| `xrf_spectrum` | `XRFParameters` | |
| `energy_scan` | `EnergyScanParameters` | |
| `Workflow` / `GphlWorkflow` | `WorkflowParameters` | |
| `Interleaved` | `DataCollectionParameters` + `wedges: [DataCollectionNodeModel, ...]` + `swNumImages: int` | Its own top-level fields (`wedges`, `swNumImages`) live inside `parameters`, not beside it. |

`shape` (present on every parameter set) is either `-1` (no associated shape),
a 2D-plane reference (`"2DP"` + optional digits), or a point/line/grid reference
matching `[a-zA-Z][0-9]+` (e.g. `"P3"`, `"L1"`, `"G2"`) - it identifies a shape
previously created via the sample-view/shape API, not part of this document.

## 4. Adding items - `queue_add_item`

Input is a **list** of items, each either a `SampleNode`-shaped object (to add a
sample, with its own nested `tasks`) or a `TaskNode`-shaped object (to add a task
to an already-queued sample, addressed by `parent_node_id` server-side / by
nesting under a `SampleNode`'s `tasks` client-side):

```json
[
  {
    "type": "Sample",
    "sampleID": "1:05",
    "location": "1:05",
    "sampleName": "sample-1",
    "tasks": [
      { "type": "DataCollection", "parameters": { "...": "..." }, "checked": true }
    ]
  }
]
```

- `type` drives dispatch: `"Sample"` -> add a sample, `"DataCollection"` ->
  add a data collection, `"Characterisation"` -> characterisation,
  `"Workflow"` / `"GphlWorkflow"` -> workflow, `"Interleaved"` -> interleaved
  collection, `"xrf_spectrum"` -> XRF scan, `"energy_scan"` -> energy scan.
  Anything else falls through to the **dynamic queue entry** path (see
  `docs/source/dev/queue.md`): the class looked up is
  `<type>.title().replace("_", "") + "QueueEntry"` (e.g. `type:
  "test_collection"` -> `TestCollectionQueueEntry`), and the **entire flat
  `parameters` dict is passed as-is to all five** of the entry's `DATA_MODEL`
  sub-models (`path_parameters`, `common_parameters`, `collection_parameters`,
  `user_collection_parameters`, `legacy_parameters`)
- For `"Workflow"` / `"GphlWorkflow"`: **`type` is not what selects a GPhL
  workflow** - both values are routed to the same handler, which instead
  branches on `parameters.wfpath == "Gphl"`. `type` only affects the value
  reported back on read (see the table in section 3). A client submitting
  `type: "GphlWorkflow"` without also setting `parameters.wfpath: "Gphl"` will
  get an ordinary `Workflow`, not a GPhL one.
- Response: `{"sampleOrder": [...], "sampleList": {...}}` (via the
  `/queue/` POST route) - not the same shape as `queue_to_dict()`'s own output;
  see mxcubeweb's `routes/queue.py` for how this is currently assembled.

## 5. State encoding

`state` is a bit-flag integer, matching the reference frontend's `constants.js`:

| Value | Meaning |
|---|---|
| `0x0` | Uncollected |
| `0x1` | Running |
| `0x2` | Failed |
| `0x4` | Collected |

Two more values are defined at the module level in mxcubeweb:
`WARNING = 0x10` and `SAMPLE_MOUNTED = 0x8`. `WARNING` **is** used, but not
through this JSON tree - it's only ever set on `collect_ended` (a collection
that finished unsuccessfully) and pushed as the `state` field of a separate
websocket `task` event, not through `queue_to_dict`/`get_node_state`. So a
`SampleNode`/`TaskNode`'s own `state` field in this JSON format never carries
`0x10` today, even though the *value* is real and reaches clients through a
different channel. `SAMPLE_MOUNTED` was not found used anywhere in the
repository - it looks genuinely dead.

`state` is derived from `QueueManager.get_entry_status(node_id)` (mxcubecore-
native `QUEUE_ENTRY_STATUS`/`is_executed`/currently-running checks), mapped to
these bit values by the client layer - the bit encoding itself is a
client/frontend convention, not an mxcubecore concept.

## 6. Task discovery - `get_available_tasks` / `get_default_task_parameters`

```json
{
  "acq_parameters": { "...": "defaults, merged with mxcubecore's own acquisition defaults" },
  "limits": { "...": "HWR.beamline.config.acquisition_limit_values" },
  "requires": ["..."],
  "name": "Data collection",
  "queue_entry": "data_collection",
  "schema": {
    "path_parameters": { "...": "JSON Schema" },
    "common_parameters": { "...": "JSON Schema" },
    "collection_parameters": { "...": "JSON Schema" },
    "user_collection_parameters": { "...": "JSON Schema" },
    "legacy_parameters": { "...": "JSON Schema" }
  },
  "ui_schema": "{...}"
}

