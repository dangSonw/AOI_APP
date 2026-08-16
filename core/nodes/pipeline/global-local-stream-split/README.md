# Global/local stream split node

## Purpose

Creates global and local image streams.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `global-local-stream-split` |
| Category | Pipeline |
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
| `global` | output | `image` | yes | no | Global image |
| `local` | output | `image-set` | yes | no | Local images |

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
| `tileSize` | `integer` | `256` | `16` | `4096` | — | Tile size |

## Workflow use

1. Add **Global/local stream split** from **Pipeline** in Workflow editor.
2. Connect typed inputs: `image`.
3. Configure parameters within listed limits.
4. Connect outputs: `global`, `local`.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `test` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
