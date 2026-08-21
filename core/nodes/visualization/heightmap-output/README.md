# 3D measurement output node

## Purpose and quick use

`heightmap-output` marks a heightmap as an explicit workflow 3D measurement output.

**Use when:** use when the Project tab should show a 3D measurement window.

**Quick flow:** `heightmap-output`

## Node structure

```text
heightmap
    │
    ▼
[heightmap-output]
    │
    └── measurement-heightmap
```

Input is `heightmap`:image. Output is `measurement-heightmap`:image.

## How the algorithm works

- Validate the heightmap input.
- Preserve the heightmap without changing its values.
- Publish the explicit 3D measurement output.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `heightmap-output` |
| Category | Visualization |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `3d-preview` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `heightmap` | input | `image` | yes | no | Heightmap |
| `measurement-heightmap` | output | `image` | yes | no | Measurement heightmap |

### Provide inputs

1. Connect a `image` output to `heightmap`. Provide a heightmap image produced by the configured measurement pipeline.

### Read outputs

- `measurement-heightmap` (`image`): The unchanged heightmap used by the Project 3D measurement viewer.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | Node has no configurable parameters. |

## Copy-ready usage example

**Goal:** Expose one 3D measurement output.

**Workflow:** `heightmap-output`

- Add the node.
- Connect a heightmap.
- Run the workflow.

**Paste into the config panel:**

```json
{}
```

**Example input:** Heightmap image.

**Expected output:** The 3D measurement viewer is enabled.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| No 3D viewer | The node is not in the saved workflow. | Add and save 3D measurement output. |
| Missing input | No heightmap is connected. | Connect a heightmap output. |
| Invalid connection | The source is not an image. | Use an image-compatible heightmap source. |

## Limitations and production checks

- This node marks the output; it does not calculate a heightmap.

### Production checklist

- Validate calibration and height units.
- Check representative boards.
- Confirm the output artifact is available.
