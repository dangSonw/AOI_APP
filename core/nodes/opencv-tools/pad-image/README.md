# Pad image node

## Purpose and quick use

`pad-image` performs **Pad image** in an AOI pipeline. Adds independently sized borders around an image. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable pad image step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `pad-image` → `image-output`

## Node structure

```text
image
    │
    ▼
[pad-image]
    │
    └── processed-image
```

Inputs are `image`:image. The node applies OpenCV copyMakeBorder. Outputs are `processed-image`:image. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `pad-image`.
- Parameters `top`, `right`, `bottom`, `left`, `borderMode`, `borderValue` control processing; change one value at a time to trace its effect.
- Apply **OpenCV copyMakeBorder**: Adds independently sized borders around an image.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `pad-image` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `geometric-transform` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `processed-image` | output | `image` | yes | no | Padded image |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.

### Read outputs

- `processed-image` (`image`): Padded image as `image`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `top` | `integer` | `0` | `0` | `100000` | — | Top padding in pixels. |
| `right` | `integer` | `0` | `0` | `100000` | — | Right padding in pixels. |
| `bottom` | `integer` | `0` | `0` | `100000` | — | Bottom padding in pixels. |
| `left` | `integer` | `0` | `0` | `100000` | — | Left padding in pixels. |
| `borderMode` | `select` | `constant` | — | — | `constant`, `replicate`, `reflect`, `wrap` | Border pixel policy. |
| `borderValue` | `json` | `[0, 0, 0]` | — | — | — | Three BGR channels used by constant borders. |

## Copy-ready usage example

**Goal:** Run pad image with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `pad-image` → `image-output`

- Drag **Pad image** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "top": 0,
  "right": 0,
  "bottom": 0,
  "left": 0,
  "borderMode": "constant",
  "borderValue": [
    0,
    0,
    0
  ]
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
- Results depend on input and assumptions of OpenCV copyMakeBorder.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
