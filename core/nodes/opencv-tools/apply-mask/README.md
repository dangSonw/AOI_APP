# Apply mask node

## Purpose

Keeps image pixels selected by a same-size binary mask and clears all others.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `apply-mask` |
| Category | OpenCV tools |
| Status | `debug` |
| Package version | `1.0.0` |
| Execution target | `local-cpu` |
| Inspector | `none` |
| Capabilities | `opencv`, `mask-application` |

Executable `debug` runtime for development, simulation, and research. This node is not approved for production.

## Ports

| Key | Direction | Data type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `mask` | input | `mask` | yes | no | Mask |
| `processed-image` | output | `image` | yes | no | Masked image |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | No parameters |

## Workflow use

1. Add **Apply mask** from **OpenCV tools** in Workflow editor.
2. Connect typed inputs: `image`, `mask`.
3. Configure parameters within listed limits.
4. Connect outputs: `processed-image`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `debug` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
