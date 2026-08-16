# Warp perspective node

## Purpose

Applies a connected 3 by 3 perspective transform to an image.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `warp-perspective` |
| Category | OpenCV tools |
| Status | `debug` |
| Package version | `1.0.0` |
| Execution target | `local-cpu` |
| Inspector | `generic` |
| Capabilities | `opencv`, `geometric-transform` |

Executable `debug` runtime for development, simulation, and research. This node is not approved for production.

## Ports

| Key | Direction | Data type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `transform` | input | `transform` | yes | no | Transform |
| `processed-image` | output | `image` | yes | no | Warped image |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| `width` | `integer` | `640` | `1` | `100000` | — | Output width in pixels. |
| `height` | `integer` | `480` | `1` | `100000` | — | Output height in pixels. |
| `interpolation` | `select` | `linear` | — | — | `nearest`, `linear`, `cubic`, `area` | Pixel resampling method. |
| `borderMode` | `select` | `constant` | — | — | `constant`, `replicate`, `reflect`, `wrap` | Out-of-bounds pixel policy. |
| `borderValue` | `json` | `[0, 0, 0]` | — | — | — | Three BGR channels used by constant borders. |

## Workflow use

1. Add **Warp perspective** from **OpenCV tools** in Workflow editor.
2. Connect typed inputs: `image`, `transform`.
3. Configure parameters within listed limits.
4. Connect outputs: `processed-image`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `debug` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
