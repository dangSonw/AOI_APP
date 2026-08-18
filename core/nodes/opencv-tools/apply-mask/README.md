# Apply mask node

## Purpose and quick use

`apply-mask` performs **Apply mask** in an AOI pipeline. Keeps image pixels selected by a same-size binary mask and clears all others. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable apply mask step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `apply-mask` → `image-output`

## Node structure

```text
image, mask
    │
    ▼
[apply-mask]
    │
    └── processed-image
```

Inputs are `image`:image, `mask`:mask. The node applies OpenCV bitwise_and. Outputs are `processed-image`:image. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `apply-mask`.
- The node has no parameters; behavior is determined by its input and runtime contract.
- Apply **OpenCV bitwise_and**: Keeps image pixels selected by a same-size binary mask and clears all others.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `apply-mask` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `mask-application` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `mask` | input | `mask` | yes | no | Mask |
| `processed-image` | output | `image` | yes | no | Masked image |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.
2. Connect a `mask` output to `mask`. Provide `mask` image data; verify shape, dtype, and channel order.

### Read outputs

- `processed-image` (`image`): Masked image as `image`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | Node has no configurable parameters. |

## Copy-ready usage example

**Goal:** Run apply mask with correctly typed input (`image`:image, `mask`:mask) and inspect its output.

**Workflow:** `image-input` → `apply-mask` → `image-output`

- Drag **Apply mask** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{}
```

**Example input:** Data for `image`:image, `mask`:mask; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce processed-image with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV bitwise_and.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
