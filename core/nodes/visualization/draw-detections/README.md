# Draw detections node

## Purpose and quick use

`draw-detections` performs **Draw detections** in an AOI pipeline. Draws detection boxes, circles, lines, and labels on a copy of the image. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable draw detections step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `global-threshold` → `connected-components` → `draw-detections` → `draw-detections`

## Node structure

```text
image, detections
    │
    ▼
[draw-detections]
    │
    └── annotated-image
```

Inputs are `image`:image, `detections`:detections. The node applies OpenCV drawing functions. Outputs are `annotated-image`:image. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `draw-detections`.
- Parameters `color`, `thickness`, `showLabels` control processing; change one value at a time to trace its effect.
- Apply **OpenCV drawing functions**: Draws detection boxes, circles, lines, and labels on a copy of the image.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `draw-detections` |
| Category | Visualization |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `image-annotation` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `detections` | input | `detections` | yes | no | Detections |
| `annotated-image` | output | `image` | yes | no | Annotated image |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.
2. Connect a `detections` output to `detections`. Provide `detections` matching Detections; do not substitute image data.

### Read outputs

- `annotated-image` (`image`): Annotated image as `image`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `color` | `json` | `[0, 255, 0]` | — | — | — | Three integer BGR channels from 0 to 255. |
| `thickness` | `integer` | `2` | `1` | `32` | — | Stroke thickness in pixels. |
| `showLabels` | `boolean` | `true` | — | — | — | Draw detection labels above boxes. |

## Copy-ready usage example

**Goal:** Run draw detections with correctly typed input (`image`:image, `detections`:detections) and inspect its output.

**Workflow:** `image-input` → `global-threshold` → `connected-components` → `draw-detections` → `draw-detections`

- Drag **Draw detections** onto the canvas.
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
  "showLabels": true
}
```

**Example input:** Data for `image`:image, `detections`:detections; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce annotated-image with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV drawing functions.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
