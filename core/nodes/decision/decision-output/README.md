# Decision output node

## Purpose

Publishes the configured inspection decision.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `decision-output` |
| Category | Decision |
| Status | `debug` |
| Package version | `1.0.0` |
| Execution target | `local-cpu` |
| Inspector | `none` |
| Capabilities | None declared |

Executable `debug` runtime for development, simulation, and research. This node is not approved for production.

## Ports

| Key | Direction | Data type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `decision` | input | `decision` | yes | no | Decision |
| `result-decision` | output | `decision` | yes | no | Result decision |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | No parameters |

## Workflow use

1. Add **Decision output** from **Decision** in Workflow editor.
2. Connect typed inputs: `decision`.
3. Configure parameters within listed limits.
4. Connect outputs: `result-decision`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `debug` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
