# Decision fusion node

## Purpose

Combines one or more scores into a review decision.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `decision-fusion` |
| Category | Decision |
| Status | `debug` |
| Package version | `1.0.0` |
| Execution target | `local-cpu` |
| Inspector | `generic` |
| Capabilities | None declared |

Executable `debug` runtime for development, simulation, and research. This node is not approved for production.

## Ports

| Key | Direction | Data type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `scores` | input | `score` | yes | yes | Scores |
| `decision` | output | `decision` | yes | no | Decision |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| `reviewThreshold` | `number` | `0.5` | `0.0` | `1.0` | — | Review threshold |
| `failThreshold` | `number` | `0.8` | `0.0` | `1.0` | — | Fail threshold |

## Workflow use

1. Add **Decision fusion** from **Decision** in Workflow editor.
2. Connect typed inputs: `scores`.
3. Configure parameters within listed limits.
4. Connect outputs: `decision`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `debug` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
