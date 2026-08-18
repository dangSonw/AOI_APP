# Overlay mask node

## Purpose and quick use

`overlay-mask` performs **Overlay mask** in an AOI pipeline. Blends a configurable BGR color over pixels selected by a binary mask. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable overlay mask step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `overlay-mask` → `image-output`

## Node structure

```text
image, mask
    │
    ▼
[overlay-mask]
    │
    └── annotated-image
```

Inputs are `image`:image, `mask`:mask. The node applies OpenCV addWeighted. Outputs are `annotated-image`:image. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `overlay-mask`.
- Parameters `color`, `opacity` control processing; change one value at a time to trace its effect.
- Apply **OpenCV addWeighted**: Blends a configurable BGR color over pixels selected by a binary mask.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `overlay-mask` |
| Category | Visualization |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `image-annotation`, `mask-overlay` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `mask` | input | `mask` | yes | no | Mask |
| `annotated-image` | output | `image` | yes | no | Annotated image |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.
2. Connect a `mask` output to `mask`. Provide `mask` image data; verify shape, dtype, and channel order.

### Read outputs

- `annotated-image` (`image`): Annotated image as `image`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `color` | `json` | `[0, 0, 255]` | — | — | — | Three integer BGR channels from 0 to 255. |
| `opacity` | `number` | `0.45` | `0.0` | `1.0` | — | Overlay opacity from zero to one. |

## Copy-ready usage example

**Goal:** Run overlay mask with correctly typed input (`image`:image, `mask`:mask) and inspect its output.

**Workflow:** `image-input` → `overlay-mask` → `image-output`

- Drag **Overlay mask** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "color": [
    0,
    0,
    255
  ],
  "opacity": 0.45
}
```

**Example input:** Data for `image`:image, `mask`:mask; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce annotated-image with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV addWeighted.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
