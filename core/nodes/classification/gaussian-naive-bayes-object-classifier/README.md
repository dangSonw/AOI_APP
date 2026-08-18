# Gaussian Naive Bayes object classifier node

## Purpose and quick use

`gaussian-naive-bayes-object-classifier` performs **Gaussian Naive Bayes object classifier** in an AOI pipeline. Classifies detected objects from Gaussian color distributions learned per class. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable gaussian naive bayes object classifier step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `global-threshold` → `connected-components` → `gaussian-naive-bayes-object-classifier` → `draw-detections`

## Node structure

```text
image, detections
    │
    ▼
[gaussian-naive-bayes-object-classifier]
    │
    └── classified-detections
```

Inputs are `image`:image, `detections`:detections. The node applies scikit-learn GaussianNB. Outputs are `classified-detections`:detections. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `gaussian-naive-bayes-object-classifier`.
- Parameters `implementation`, `varianceSmoothing`, `trainingSamples` control processing; change one value at a time to trace its effect.
- Estimate per-class BGR mean, variance, and prior.
- Add varianceSmoothing to avoid zero variance.
- Evaluate Gaussian log posterior and normalize it into class probabilities.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `gaussian-naive-bayes-object-classifier` |
| Category | Classification |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `numpy`, `scikit-learn`, `classification`, `probabilistic-model` |

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
| `implementation` | `select` | `scikit-learn` | — | — | `scikit-learn`, `manual-python` | Choose scikit-learn or the manually implemented Gaussian log-posterior. |
| `varianceSmoothing` | `number` | `1e-09` | `1e-12` | `1.0` | — | Prevents division by zero when samples in a class have nearly identical colors. |
| `trainingSamples` | `json` | `[{"label": "dark", "color": [20, 20, 20]}, {"label": "dark", "color": [50, 50, 50]}, {"label": "bright", "color": [205, 205, 205]}, {"label": "bright", "color": [245, 245, 245]}]` | — | — | — | JSON list: each item is {"label": "class-name", "color": [B, G, R]}. |

## Copy-ready usage example

**Goal:** Run gaussian naive bayes object classifier with correctly typed input (`image`:image, `detections`:detections) and inspect its output.

**Workflow:** `image-input` → `global-threshold` → `connected-components` → `gaussian-naive-bayes-object-classifier` → `draw-detections`

- Drag **Gaussian Naive Bayes object classifier** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "implementation": "scikit-learn",
  "varianceSmoothing": 1e-09,
  "trainingSamples": [
    {
      "label": "dark",
      "color": [
        20,
        20,
        20
      ]
    },
    {
      "label": "dark",
      "color": [
        50,
        50,
        50
      ]
    },
    {
      "label": "bright",
      "color": [
        205,
        205,
        205
      ]
    },
    {
      "label": "bright",
      "color": [
        245,
        245,
        245
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
- Results depend on input and assumptions of scikit-learn GaussianNB.
- Measure latency/memory on target hardware.
- trainingSamples live in the recipe and are intended only for small, non-sensitive sample sets.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
