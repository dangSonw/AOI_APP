# Warp affine node

## Purpose and quick use

`warp-affine` performs **Warp affine** in an AOI pipeline. Applies a connected 2 by 3 affine transform to an image. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable warp affine step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `warp-affine` → `image-output`

## Node structure

```text
image, transform
    │
    ▼
[warp-affine]
    │
    └── processed-image
```

Inputs are `image`:image, `transform`:transform. The node applies OpenCV warpAffine. Outputs are `processed-image`:image. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `warp-affine`.
- Parameters `width`, `height`, `interpolation`, `borderMode`, `borderValue` control processing; change one value at a time to trace its effect.
- Apply **OpenCV warpAffine**: Applies a connected 2 by 3 affine transform to an image.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `warp-affine` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `geometric-transform` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `transform` | input | `transform` | yes | no | Transform |
| `processed-image` | output | `image` | yes | no | Warped image |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.
2. Connect a `transform` output to `transform`. Provide `transform` matching Transform; do not substitute image data.

### Read outputs

- `processed-image` (`image`): Warped image as `image`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `width` | `integer` | `640` | `1` | `100000` | — | Output width. |
| `height` | `integer` | `480` | `1` | `100000` | — | Output height. |
| `interpolation` | `select` | `linear` | — | — | `nearest`, `linear`, `cubic` | Pixel resampling method. |
| `borderMode` | `select` | `constant` | — | — | `constant`, `replicate`, `reflect`, `wrap` | Out-of-bounds pixel policy. |
| `borderValue` | `json` | `[0, 0, 0]` | — | — | — | Constant border BGR channels. |

## Copy-ready usage example

**Goal:** Run warp affine with correctly typed input (`image`:image, `transform`:transform) and inspect its output.

**Workflow:** `image-input` → `warp-affine` → `image-output`

- Drag **Warp affine** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "width": 640,
  "height": 480,
  "interpolation": "linear",
  "borderMode": "constant",
  "borderValue": [
    0,
    0,
    0
  ]
}
```

**Example input:** Data for `image`:image, `transform`:transform; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce processed-image with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV warpAffine.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
