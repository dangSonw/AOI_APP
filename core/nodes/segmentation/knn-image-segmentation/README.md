# KNN image segmentation node

## Purpose and quick use

`knn-image-segmentation` performs **KNN image segmentation** in an AOI pipeline. Segments pixels by representative BGR colors and extracts object contours using OpenCV KNN matching or a manual Python KNN implementation. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable knn image segmentation step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `knn-image-segmentation` → `overlay-mask`

## Node structure

```text
image
    │
    ▼
[knn-image-segmentation]
    │
    └── mask, contours
```

Inputs are `image`:image. The node applies OpenCV DescriptorMatcher.knnMatch and findContours. Outputs are `mask`:mask, `contours`:contours. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `knn-image-segmentation`.
- Parameters `implementation`, `neighbors`, `distanceMetric`, `distanceWeighted`, `minimumConfidence`, `foregroundLabels`, `trainingSamples` control processing; change one value at a time to trace its effect.
- Convert every pixel to a normalized BGR query.
- Find K nearest labeled colors in bounded batches.
- Set pixels whose winning label is in foregroundLabels to 255, then extract external contours.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `knn-image-segmentation` |
| Category | Segmentation |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `numpy`, `knn`, `segmentation`, `contours` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `mask` | output | `mask` | yes | no | Object mask |
| `contours` | output | `contours` | yes | no | Object contours |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.

### Read outputs

- `mask` (`mask`): Object mask as `mask`; preview it or connect a compatible downstream node.
- `contours` (`contours`): Object contours as `contours`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `implementation` | `select` | `opencv` | — | — | `opencv`, `manual-python` | Use OpenCV BFMatcher KNN matching or the KNN algorithm implemented with Python/NumPy. |
| `neighbors` | `integer` | `3` | `1` | `1000` | — | Must not exceed the number of training samples. |
| `distanceMetric` | `select` | `euclidean` | — | — | `euclidean`, `manhattan` | OpenCV supports Euclidean; manual Python supports Euclidean and Manhattan. |
| `distanceWeighted` | `boolean` | `true` | — | — | — | Weight closer color samples more strongly. |
| `minimumConfidence` | `number` | `0.5` | `0.0` | `1.0` | — | Pixels below this winning-vote confidence become background. |
| `foregroundLabels` | `json` | `["object"]` | — | — | — | Labels that form the output object mask. |
| `trainingSamples` | `json` | `[{"label": "background", "color": [0, 0, 0]}, {"label": "background", "color": [32, 32, 32]}, {"label": "object", "color": [224, 224, 224]}, {"label": "object", "color": [255, 255, 255]}]` | — | — | — | JSON samples with a label and representative BGR color. |

## Copy-ready usage example

**Goal:** Run knn image segmentation with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `knn-image-segmentation` → `overlay-mask`

- Drag **KNN image segmentation** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "implementation": "opencv",
  "neighbors": 3,
  "distanceMetric": "euclidean",
  "distanceWeighted": true,
  "minimumConfidence": 0.5,
  "foregroundLabels": [
    "object"
  ],
  "trainingSamples": [
    {
      "label": "background",
      "color": [
        0,
        0,
        0
      ]
    },
    {
      "label": "background",
      "color": [
        32,
        32,
        32
      ]
    },
    {
      "label": "object",
      "color": [
        224,
        224,
        224
      ]
    },
    {
      "label": "object",
      "color": [
        255,
        255,
        255
      ]
    }
  ]
}
```

**Example input:** Data for `image`:image; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce mask, contours with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |
| Implementations give slightly different confidence | Solvers and stopping criteria differ. | Compare labels/metrics with tolerance; do not require bit-identical floats. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV DescriptorMatcher.knnMatch and findContours.
- Measure latency/memory on target hardware.
- trainingSamples live in the recipe and are intended only for small, non-sensitive sample sets.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
