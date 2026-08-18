# Watershed node

## Purpose and quick use

`watershed` performs **Watershed** in an AOI pipeline. Segments an image from a connected foreground mask. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable watershed step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `watershed` → `overlay-mask`

## Node structure

```text
image, mask
    │
    ▼
[watershed]
    │
    └── segmented-mask
```

Inputs are `image`:image, `mask`:mask. The node applies OpenCV watershed. Outputs are `segmented-mask`:mask. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `watershed`.
- The node has no parameters; behavior is determined by its input and runtime contract.
- Apply **OpenCV watershed**: Segments an image from a connected foreground mask.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `watershed` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `segmentation` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `mask` | input | `mask` | yes | no | Foreground mask |
| `segmented-mask` | output | `mask` | yes | no | Segmented mask |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.
2. Connect a `mask` output to `mask`. Provide `mask` image data; verify shape, dtype, and channel order.

### Read outputs

- `segmented-mask` (`mask`): Segmented mask as `mask`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | Node has no configurable parameters. |

## Copy-ready usage example

**Goal:** Run watershed with correctly typed input (`image`:image, `mask`:mask) and inspect its output.

**Workflow:** `image-input` → `watershed` → `overlay-mask`

- Drag **Watershed** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{}
```

**Example input:** Data for `image`:image, `mask`:mask; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce segmented-mask with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV watershed.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
