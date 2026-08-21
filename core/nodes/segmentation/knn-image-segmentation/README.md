# KNN image segmentation node

## Purpose and quick use

`knn-image-segmentation` performs **KNN image segmentation** in an AOI pipeline. It classifies pixels from named representative BGR color features and extracts object contours. Configure the feature names and colors in Node inspector and connect outputs to ports with matching data types.

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
- Parameters `neighbors`, `distanceMetric`, `distanceWeighted`, `minimumConfidence`, `foregroundLabels`, `trainingSamples` control processing; change one value at a time to trace its effect.
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
| `neighbors` | `integer` | `3` | `1` | `1000` | — | Must not exceed the number of training samples. |
| `distanceMetric` | `select` | `euclidean` | — | — | `euclidean`, `manhattan` | Euclidean uses straight-line color distance; Manhattan sums channel differences. |
| `distanceWeighted` | `boolean` | `true` | — | — | — | Weight closer color samples more strongly. |
| `minimumConfidence` | `number` | `0.5` | `0.0` | `1.0` | — | Pixels below this winning-vote confidence become background. |
| `foregroundLabels` | feature selection | `object` | — | — | named features | Select feature names that form the output object mask. |
| `trainingSamples` | feature editor | four defaults | — | — | name, B, G, R | Add a meaningful feature name and its representative BGR color without editing JSON. |

## Copy-ready usage example

**Goal:** Run knn image segmentation with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `knn-image-segmentation` → `overlay-mask`

- Drag **KNN image segmentation** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector, name the visual features, and enter a BGR reference color for each one.
- Run, inspect output, then tune one parameter at a time.

**Inspector example:** keep two `background` samples near BGR `(0, 0, 0)` and `(32, 32, 32)`, add two `object` samples near `(224, 224, 224)` and `(255, 255, 255)`, then select **object** under Foreground features.

**Example input:** Data for `image`:image; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce mask, contours with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | A numeric value is outside its range or a feature name is empty. | Restore defaults and edit one field at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV DescriptorMatcher.knnMatch and findContours.
- Measure latency/memory on target hardware.
- trainingSamples live in the recipe and are intended only for small, non-sensitive sample sets.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
