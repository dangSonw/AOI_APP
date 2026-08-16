# In-range mask node

## Purpose

Creates a binary mask from inclusive channel bounds in BGR, HSV, Lab, or grayscale space.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `in-range-mask` |
| Category | OpenCV tools |
| Status | `debug` |
| Package version | `1.0.0` |
| Execution target | `local-cpu` |
| Inspector | `generic` |
| Capabilities | `opencv`, `color-segmentation` |

Executable `debug` runtime for development, simulation, and research. This node is not approved for production.

## Ports

| Key | Direction | Data type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `mask` | output | `mask` | yes | no | Mask |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| `colorSpace` | `select` | `hsv` | — | — | `bgr`, `hsv`, `lab`, `grayscale` | Color space used before range comparison. |
| `lowerBound` | `json` | `[0, 0, 0]` | — | — | — | Inclusive lower channel values; use one value for grayscale. |
| `upperBound` | `json` | `[179, 255, 255]` | — | — | — | Inclusive upper channel values; use one value for grayscale. |

## Workflow use

1. Add **In-range mask** from **OpenCV tools** in Workflow editor.
2. Connect typed inputs: `image`.
3. Configure parameters within listed limits.
4. Connect outputs: `mask`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `debug` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
