# Draw contours node

## Purpose

Draws all contours or one selected contour on a copy of an image.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `draw-contours` |
| Category | Visualization |
| Status | `debug` |
| Package version | `1.0.0` |
| Execution target | `local-cpu` |
| Inspector | `generic` |
| Capabilities | `opencv`, `image-annotation`, `contour-rendering` |

Executable `debug` runtime for development, simulation, and research. This node is not approved for production.

## Ports

| Key | Direction | Data type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `contours` | input | `contours` | yes | no | Contours |
| `annotated-image` | output | `image` | yes | no | Annotated image |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| `color` | `json` | `[0, 255, 0]` | — | — | — | Three integer BGR channels from 0 to 255. |
| `thickness` | `integer` | `2` | `-1` | `32` | — | Stroke width; minus one fills contours. |
| `drawAll` | `boolean` | `true` | — | — | — | Draw every contour instead of one index. |
| `contourIndex` | `integer` | `0` | `0` | `1000000` | — | Zero-based index used when Draw all is disabled. |

## Workflow use

1. Add **Draw contours** from **Visualization** in Workflow editor.
2. Connect typed inputs: `image`, `contours`.
3. Configure parameters within listed limits.
4. Connect outputs: `annotated-image`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `debug` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
