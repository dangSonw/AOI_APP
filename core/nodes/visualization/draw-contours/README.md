# Draw contours node

## Purpose and quick use

`draw-contours` performs **Draw contours** in an AOI pipeline. Draws all contours or one selected contour on a copy of an image. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable draw contours step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `draw-contours` → `image-output`

## Node structure

```text
image, contours
    │
    ▼
[draw-contours]
    │
    └── annotated-image
```

Inputs are `image`:image, `contours`:contours. The node applies OpenCV drawContours. Outputs are `annotated-image`:image. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `draw-contours`.
- Parameters `color`, `thickness`, `drawAll`, `contourIndex` control processing; change one value at a time to trace its effect.
- Apply **OpenCV drawContours**: Draws all contours or one selected contour on a copy of an image.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `draw-contours` |
| Category | Visualization |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `image-annotation`, `contour-rendering` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `contours` | input | `contours` | yes | no | Contours |
| `annotated-image` | output | `image` | yes | no | Annotated image |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.
2. Connect a `contours` output to `contours`. Provide `contours` matching Contours; do not substitute image data.

### Read outputs

- `annotated-image` (`image`): Annotated image as `image`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `color` | `json` | `[0, 255, 0]` | — | — | — | Three integer BGR channels from 0 to 255. |
| `thickness` | `integer` | `2` | `-1` | `32` | — | Stroke width; minus one fills contours. |
| `drawAll` | `boolean` | `true` | — | — | — | Draw every contour instead of one index. |
| `contourIndex` | `integer` | `0` | `0` | `1000000` | — | Zero-based index used when Draw all is disabled. |

## Copy-ready usage example

**Goal:** Run draw contours with correctly typed input (`image`:image, `contours`:contours) and inspect its output.

**Workflow:** `image-input` → `draw-contours` → `image-output`

- Drag **Draw contours** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "color": [
    0,
    255,
    0
  ],
  "thickness": 2,
  "drawAll": true,
  "contourIndex": 0
}
```

**Example input:** Data for `image`:image, `contours`:contours; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce annotated-image with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV drawContours.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
