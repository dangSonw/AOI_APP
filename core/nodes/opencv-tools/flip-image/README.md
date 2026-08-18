# Flip image node

## Purpose and quick use

`flip-image` performs **Flip image** in an AOI pipeline. Flips an image across its horizontal axis, vertical axis, or both axes. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable flip image step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `flip-image` → `image-output`

## Node structure

```text
image
    │
    ▼
[flip-image]
    │
    └── processed-image
```

Inputs are `image`:image. The node applies OpenCV flip. Outputs are `processed-image`:image. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `flip-image`.
- Parameters `axis` control processing; change one value at a time to trace its effect.
- Apply **OpenCV flip**: Flips an image across its horizontal axis, vertical axis, or both axes.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `flip-image` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `geometric-transform` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `processed-image` | output | `image` | yes | no | Flipped image |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.

### Read outputs

- `processed-image` (`image`): Flipped image as `image`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `axis` | `select` | `horizontal` | — | — | `horizontal`, `vertical`, `both` | Axis operation applied to image coordinates. |

## Copy-ready usage example

**Goal:** Run flip image with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `flip-image` → `image-output`

- Drag **Flip image** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "axis": "horizontal"
}
```

**Example input:** Data for `image`:image; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce processed-image with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV flip.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
