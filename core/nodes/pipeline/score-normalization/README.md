# Score normalization node

## Purpose

Normalizes a score to a configured range.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `score-normalization` |
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
| `score` | input | `score` | yes | no | Score |
| `normalized-score` | output | `score` | yes | no | Normalized score |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| `minimum` | `number` | `0.0` | `-1000000.0` | `1000000.0` | — | Minimum |
| `maximum` | `number` | `1.0` | `-1000000.0` | `1000000.0` | — | Maximum |

## Workflow use

1. Add **Score normalization** from **Pipeline** in Workflow editor.
2. Connect typed inputs: `score`.
3. Configure parameters within listed limits.
4. Connect outputs: `normalized-score`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `test` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
