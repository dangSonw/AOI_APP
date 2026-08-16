# Polarity and orientation inspection node

## Purpose

Checks configured component polarity and orientation evidence.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `polarity-and-orientation-inspection` |
| Category | Component/logical |
| Status | `test` |
| Package version | `1.0.0` |
| Execution target | `local-cpu` |
| Inspector | `generic` |
| Capabilities | None declared |

Contract-only `test` runtime. Execution raises `NodeNotImplementedError`; do not use it in a workflow expected to complete.

## Ports

| Key | Direction | Data type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `components` | input | `detections` | no | no | Components |
| `detections` | output | `detections` | yes | no | Findings |
| `score` | output | `score` | yes | no | Score |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| `angleTolerance` | `number` | `5.0` | `0.0` | `180.0` | — | Angle tolerance |

## Workflow use

1. Add **Polarity and orientation inspection** from **Component/logical** in Workflow editor.
2. Connect typed inputs: `image`, `components`.
3. Configure parameters within listed limits.
4. Connect outputs: `detections`, `score`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `test` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
