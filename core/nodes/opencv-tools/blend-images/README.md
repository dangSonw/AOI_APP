# Blend images node

## Purpose

Alpha blends two images with identical dimensions, channels, and dtype.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `blend-images` |
| Category | OpenCV tools |
| Status | `debug` |
| Package version | `1.0.0` |
| Execution target | `local-cpu` |
| Inspector | `generic` |
| Capabilities | `opencv`, `image-composition` |

Executable `debug` runtime for development, simulation, and research. This node is not approved for production.

## Ports

| Key | Direction | Data type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Base image |
| `overlay` | input | `image` | yes | no | Overlay image |
| `processed-image` | output | `image` | yes | no | Blended image |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| `alpha` | `number` | `0.5` | `0.0` | `1.0` | — | Overlay contribution from zero to one. |

## Workflow use

1. Add **Blend images** from **OpenCV tools** in Workflow editor.
2. Connect typed inputs: `image`, `overlay`.
3. Configure parameters within listed limits.
4. Connect outputs: `processed-image`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `debug` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
