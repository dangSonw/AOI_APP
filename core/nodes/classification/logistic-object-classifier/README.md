# Logistic object classifier node

## Purpose and quick use

`logistic-object-classifier` performs **Logistic object classifier** in an AOI pipeline. Fits a linear softmax classifier to labeled object-color samples and returns class probabilities. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable logistic object classifier step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `global-threshold` → `connected-components` → `logistic-object-classifier` → `draw-detections`

## Node structure

```text
image, detections
    │
    ▼
[logistic-object-classifier]
    │
    └── classified-detections
```

Inputs are `image`:image, `detections`:detections. The node applies scikit-learn LogisticRegression and softmax regression. Outputs are `classified-detections`:detections. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `logistic-object-classifier`.
- Parameters `implementation`, `regularizationStrength`, `learningRate`, `maximumIterations`, `tolerance`, `randomSeed`, `trainingSamples` control processing; change one value at a time to trace its effect.
- Standardize object mean-BGR features.
- Fit linear class weights by scikit-learn or manual softmax gradient descent.
- Apply softmax to produce classScores; confidence is the winning probability.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `logistic-object-classifier` |
| Category | Classification |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `numpy`, `scikit-learn`, `classification`, `linear-model` |

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
| `regularizationStrength` | `number` | `0.01` | `0.0` | `1000.0` | — | Higher values reduce large coefficients and may improve generalization. |
| `learningRate` | `number` | `0.1` | `1e-06` | `10.0` | — | Step size used only by manual-python. |
| `maximumIterations` | `integer` | `500` | `1` | `10000` | — | Maximum optimization updates. |
| `tolerance` | `number` | `1e-06` | `1e-09` | `1.0` | — | Stops when coefficient changes are sufficiently small. |
| `randomSeed` | `integer` | `42` | `0` | `2147483647` | — | Keeps the library solver repeatable. |
| `trainingSamples` | `json` | `[{"label": "dark", "color": [20, 20, 20]}, {"label": "dark", "color": [50, 50, 50]}, {"label": "bright", "color": [205, 205, 205]}, {"label": "bright", "color": [245, 245, 245]}]` | — | — | — | JSON list: each item is {"label": "class-name", "color": [B, G, R]}. |

## Copy-ready usage example

**Goal:** Run logistic object classifier with correctly typed input (`image`:image, `detections`:detections) and inspect its output.

**Workflow:** `image-input` → `global-threshold` → `connected-components` → `logistic-object-classifier` → `draw-detections`

- Drag **Logistic object classifier** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "implementation": "scikit-learn",
  "regularizationStrength": 0.01,
  "learningRate": 0.1,
  "maximumIterations": 500,
  "tolerance": 1e-06,
  "randomSeed": 42,
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
- Results depend on input and assumptions of scikit-learn LogisticRegression and softmax regression.
- Measure latency/memory on target hardware.
- trainingSamples live in the recipe and are intended only for small, non-sensitive sample sets.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
