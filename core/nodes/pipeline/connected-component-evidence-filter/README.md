# Connected-component evidence filter node

## Purpose

Filters spatial evidence by component geometry.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `connected-component-evidence-filter` |
| Category | Pipeline |
| Status | `test` |
| Package version | `1.0.0` |
| Execution target | `local-cpu` |
| Inspector | `generic` |
| Capabilities | None declared |

Contract-only `test` runtime. Execution raises `NodeNotImplementedError`; do not use it in a workflow expected to complete.

## Ports

| Key | Direction | Data type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `anomaly-map` | input | `anomaly-map` | yes | no | Anomaly map |
| `detections` | output | `detections` | yes | no | Evidence |
| `score` | output | `score` | yes | no | Score |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| `minimumArea` | `integer` | `4` | `1` | `1000000` | — | Minimum area |

## Workflow use

1. Add **Connected-component evidence filter** from **Pipeline** in Workflow editor.
2. Connect typed inputs: `anomaly-map`.
3. Configure parameters within listed limits.
4. Connect outputs: `detections`, `score`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `test` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
