# Erode node

## Purpose

Erodes a spatial mask.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `erode` |
| Category | OpenCV tools |
| Status | `debug` |
| Package version | `1.0.0` |
| Execution target | `local-cpu` |
| Inspector | `generic` |
| Capabilities | None declared |

Executable `debug` runtime for development, simulation, and research. This node is not approved for production.

## Ports

| Key | Direction | Data type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `mask` | input | `mask` | yes | no | Mask |
| `processed-mask` | output | `mask` | yes | no | Processed mask |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| `iterations` | `integer` | `1` | `1` | `100` | — | Iterations |

## Workflow use

1. Add **Erode** from **OpenCV tools** in Workflow editor.
2. Connect typed inputs: `mask`.
3. Configure parameters within listed limits.
4. Connect outputs: `processed-mask`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `debug` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
