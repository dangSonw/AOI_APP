# PCA anomaly detector node

## Purpose and quick use

`pca-anomaly-detector` performs **PCA anomaly detector** in an AOI pipeline. Learns a normal BGR subspace and scores each pixel by PCA reconstruction error. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable pca anomaly detector step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `pca-anomaly-detector`

## Node structure

```text
image
    │
    ▼
[pca-anomaly-detector]
    │
    └── anomaly-map, score
```

Inputs are `image`:image. The node applies scikit-learn PCA and reconstruction-error anomaly detection. Outputs are `anomaly-map`:anomaly-map, `score`:score. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `pca-anomaly-detector`.
- Parameters `implementation`, `components`, `scorePercentile`, `trainingSamples` control processing; change one value at a time to trace its effect.
- Fit a low-dimensional subspace from known-normal BGR samples.
- Project each pixel into the subspace and reconstruct it.
- Use normalized reconstruction error as anomaly-map and its configured percentile as score.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `pca-anomaly-detector` |
| Category | Classical ML anomaly detection |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `numpy`, `scikit-learn`, `pca`, `anomaly-detection` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `anomaly-map` | output | `anomaly-map` | yes | no | Anomaly map |
| `score` | output | `score` | yes | no | Anomaly score |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.

### Read outputs

- `anomaly-map` (`anomaly-map`): Anomaly map as `anomaly-map`; preview it or connect a compatible downstream node.
- `score` (`score`): Anomaly score as `score`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `components` | `integer` | `2` | `1` | `3` | — | Number of normal color directions retained; fewer components make the detector more selective. |
| `scorePercentile` | `number` | `99.0` | `0.0` | `100.0` | — | Image score is this percentile of the normalized anomaly map. |
| `trainingSamples` | `json` | `[{"features": [20, 20, 20]}, {"features": [40, 40, 40]}, {"features": [60, 60, 60]}, {"features": [80, 80, 80]}]` | — | — | — | JSON list of known-normal colors: each item is {"features": [B, G, R]}. |

## Copy-ready usage example

**Goal:** Run pca anomaly detector with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `pca-anomaly-detector`

- Drag **PCA anomaly detector** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "implementation": "scikit-learn",
  "components": 2,
  "scorePercentile": 99.0,
  "trainingSamples": [
    {
      "features": [
        20,
        20,
        20
      ]
    },
    {
      "features": [
        40,
        40,
        40
      ]
    },
    {
      "features": [
        60,
        60,
        60
      ]
    },
    {
      "features": [
        80,
        80,
        80
      ]
    }
  ]
}
```

**Example input:** Data for `image`:image; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce anomaly-map, score with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |
| Implementations give slightly different confidence | Solvers and stopping criteria differ. | Compare labels/metrics with tolerance; do not require bit-identical floats. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of scikit-learn PCA and reconstruction-error anomaly detection.
- Measure latency/memory on target hardware.
- trainingSamples live in the recipe and are intended only for small, non-sensitive sample sets.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
