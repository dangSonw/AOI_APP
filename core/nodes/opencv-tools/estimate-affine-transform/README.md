# Estimate affine transform node

## Purpose and quick use

`estimate-affine-transform` performs **Estimate affine transform** in an AOI pipeline. Estimates a robust 2 by 3 affine transform from corresponding points. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable estimate affine transform step stored in a recipe and inspectable on its own.

**Quick flow:** `estimate-affine-transform`

## Node structure

```text
source-points, destination-points
    │
    ▼
[estimate-affine-transform]
    │
    └── transform
```

Inputs are `source-points`:keypoints, `destination-points`:keypoints. The node applies OpenCV estimateAffine2D. Outputs are `transform`:transform. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `estimate-affine-transform`.
- Parameters `method`, `ransacThreshold` control processing; change one value at a time to trace its effect.
- Apply **OpenCV estimateAffine2D**: Estimates a robust 2 by 3 affine transform from corresponding points.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `estimate-affine-transform` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `transform-estimation` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `source-points` | input | `keypoints` | yes | no | Source points |
| `destination-points` | input | `keypoints` | yes | no | Destination points |
| `transform` | output | `transform` | yes | no | Affine transform |

### Provide inputs

1. Connect a `keypoints` output to `source-points`. Provide `keypoints` matching Source points; do not substitute image data.
2. Connect a `keypoints` output to `destination-points`. Provide `keypoints` matching Destination points; do not substitute image data.

### Read outputs

- `transform` (`transform`): Affine transform as `transform`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `method` | `select` | `ransac` | — | — | `ransac`, `lmeds` | Robust estimation method. |
| `ransacThreshold` | `number` | `3.0` | `0.01` | `1000.0` | — | Maximum reprojection error. |

## Copy-ready usage example

**Goal:** Run estimate affine transform with correctly typed input (`source-points`:keypoints, `destination-points`:keypoints) and inspect its output.

**Workflow:** `estimate-affine-transform`

- Drag **Estimate affine transform** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "method": "ransac",
  "ransacThreshold": 3.0
}
```

**Example input:** Data for `source-points`:keypoints, `destination-points`:keypoints; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce transform with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV estimateAffine2D.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
