# In-range mask node

## Purpose and quick use

`in-range-mask` performs **In-range mask** in an AOI pipeline. Creates a binary mask from inclusive channel bounds in BGR, HSV, Lab, or grayscale space. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable in-range mask step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `in-range-mask` → `overlay-mask`

## Node structure

```text
image
    │
    ▼
[in-range-mask]
    │
    └── mask
```

Inputs are `image`:image. The node applies OpenCV inRange. Outputs are `mask`:mask. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `in-range-mask`.
- Parameters `colorSpace`, `lowerBound`, `upperBound` control processing; change one value at a time to trace its effect.
- Apply **OpenCV inRange**: Creates a binary mask from inclusive channel bounds in BGR, HSV, Lab, or grayscale space.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `in-range-mask` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `color-segmentation` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `mask` | output | `mask` | yes | no | Mask |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.

### Read outputs

- `mask` (`mask`): Mask as `mask`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `colorSpace` | `select` | `hsv` | — | — | `bgr`, `hsv`, `lab`, `grayscale` | Color space used before range comparison. |
| `lowerBound` | `json` | `[0, 0, 0]` | — | — | — | Inclusive lower channel values; use one value for grayscale. |
| `upperBound` | `json` | `[179, 255, 255]` | — | — | — | Inclusive upper channel values; use one value for grayscale. |

## Copy-ready usage example

**Goal:** Run in-range mask with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `in-range-mask` → `overlay-mask`

- Drag **In-range mask** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "colorSpace": "hsv",
  "lowerBound": [
    0,
    0,
    0
  ],
  "upperBound": [
    179,
    255,
    255
  ]
}
```

**Example input:** Data for `image`:image; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce mask with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV inRange.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
