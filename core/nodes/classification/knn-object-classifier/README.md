# KNN object classifier node

## Purpose and quick use

`knn-object-classifier` performs **KNN object classifier** in an AOI pipeline. Classifies detected objects from their mean BGR color using OpenCV KNN matching or a manual Python KNN implementation. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable knn object classifier step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `global-threshold` → `connected-components` → `knn-object-classifier` → `draw-detections`

## Node structure

```text
image, detections
    │
    ▼
[knn-object-classifier]
    │
    └── classified-detections
```

Inputs are `image`:image, `detections`:detections. The node applies OpenCV DescriptorMatcher.knnMatch. Outputs are `classified-detections`:detections. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `knn-object-classifier`.
- Parameters `implementation`, `neighbors`, `distanceMetric`, `distanceWeighted`, `trainingSamples` control processing; change one value at a time to trace its effect.
- Compute the mean BGR vector inside every detection box.
- Find K closest configured color samples; vote by count or inverse distance.
- Return the winning label, confidence, and neighbor distances without changing input detections.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `knn-object-classifier` |
| Category | Classification |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `numpy`, `knn`, `object-classification` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `detections` | input | `detections` | yes | no | Detected objects |
| `classified-detections` | output | `detections` | yes | no | Classified objects |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.
2. Connect a `detections` output to `detections`. Provide `detections` matching Detected objects; do not substitute image data.

### Read outputs

- `classified-detections` (`detections`): Classified objects as `detections`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `implementation` | `select` | `opencv` | — | — | `opencv`, `manual-python` | Use OpenCV BFMatcher KNN matching or the KNN algorithm implemented with Python/NumPy. |
| `neighbors` | `integer` | `3` | `1` | `1000` | — | Must not exceed the number of training samples. |
| `distanceMetric` | `select` | `euclidean` | — | — | `euclidean`, `manhattan` | OpenCV supports Euclidean; manual Python supports Euclidean and Manhattan. |
| `distanceWeighted` | `boolean` | `true` | — | — | — | Weight closer neighbors more strongly. |
| `trainingSamples` | `json` | `[{"label": "dark", "color": [32, 32, 32]}, {"label": "dark", "color": [64, 64, 64]}, {"label": "bright", "color": [192, 192, 192]}, {"label": "bright", "color": [224, 224, 224]}]` | — | — | — | JSON samples with a label and representative BGR color. |

## Copy-ready usage example

**Goal:** Run knn object classifier with correctly typed input (`image`:image, `detections`:detections) and inspect its output.

**Workflow:** `image-input` → `global-threshold` → `connected-components` → `knn-object-classifier` → `draw-detections`

- Drag **KNN object classifier** onto the canvas.
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
  "trainingSamples": [
    {
      "label": "dark",
      "color": [
        32,
        32,
        32
      ]
    },
    {
      "label": "dark",
      "color": [
        64,
        64,
        64
      ]
    },
    {
      "label": "bright",
      "color": [
        192,
        192,
        192
      ]
    },
    {
      "label": "bright",
      "color": [
        224,
        224,
        224
      ]
    }
  ]
}
```

**Example input:** Data for `image`:image, `detections`:detections; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce classified-detections with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |
| Implementations give slightly different confidence | Solvers and stopping criteria differ. | Compare labels/metrics with tolerance; do not require bit-identical floats. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV DescriptorMatcher.knnMatch.
- Measure latency/memory on target hardware.
- trainingSamples live in the recipe and are intended only for small, non-sensitive sample sets.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
