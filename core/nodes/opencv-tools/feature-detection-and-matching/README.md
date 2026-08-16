# Feature detection and matching node

## Purpose

Runs feature extraction and correspondence matching.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `feature-detection-and-matching` |
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
| `image` | input | `image` | yes | no | Image |
| `reference` | input | `image` | yes | no | Reference |
| `keypoints` | output | `keypoints` | yes | no | Matches |
| `transform` | output | `transform` | yes | no | Transform |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| `detector` | `select` | `orb` | — | — | `orb`, `sift`, `akaze` | Detector |

## Workflow use

1. Add **Feature detection and matching** from **OpenCV tools** in Workflow editor.
2. Connect typed inputs: `image`, `reference`.
3. Configure parameters within listed limits.
4. Connect outputs: `keypoints`, `transform`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `debug` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
