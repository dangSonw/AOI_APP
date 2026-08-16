# ROI extraction node

## Purpose

Extracts configured regions from an image.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `roi-extraction` |
| Category | Pipeline |
| Status | `test` |
| Package version | `1.0.0` |
| Execution target | `local-cpu` |
| Inspector | `none` |
| Capabilities | None declared |

Contract-only `test` runtime. Execution raises `NodeNotImplementedError`; do not use it in a workflow expected to complete.

## Ports

| Key | Direction | Data type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `regions` | input | `roi-set` | yes | no | Regions |
| `images` | output | `image-set` | yes | no | ROI images |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | No parameters |

## Workflow use

1. Add **ROI extraction** from **Pipeline** in Workflow editor.
2. Connect typed inputs: `image`, `regions`.
3. Configure parameters within listed limits.
4. Connect outputs: `images`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `test` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
