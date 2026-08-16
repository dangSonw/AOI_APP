# Camera capture node

## Purpose

Describes a configured camera acquisition step.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `camera-capture` |
| Category | Acquisition |
| Status | `debug` |
| Package version | `1.0.0` |
| Execution target | `adapter` |
| Inspector | `custom` |
| Capabilities | None declared |

Executable `debug` runtime for development, simulation, and research. This node is not approved for production.

## Ports

| Key | Direction | Data type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | output | `image` | yes | no | Image |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| `cameraId` | `text` | `top-camera` | — | — | — | Camera ID |
| `exposureUs` | `integer` | `8000` | `1` | `1000000` | — | Exposure (μs) |

## Workflow use

1. Add **Camera capture** from **Acquisition** in Workflow editor.
2. Connect typed inputs: none.
3. Configure parameters within listed limits.
4. Connect outputs: `image`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `debug` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
