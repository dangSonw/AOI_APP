# K-means image segmentation node

## Purpose and quick use

`kmeans-image-segmentation` performs **K-means image segmentation** in an AOI pipeline. Clusters pixel colors, selects configured clusters as foreground, and returns a binary mask with contours. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable k-means image segmentation step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `kmeans-image-segmentation` → `overlay-mask`

## Node structure

```text
image
    │
    ▼
[kmeans-image-segmentation]
    │
    └── mask, contours
```

Inputs are `image`:image. The node applies scikit-learn KMeans and Lloyd's algorithm. Outputs are `mask`:mask, `contours`:contours. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `kmeans-image-segmentation`.
- Parameters `clusters`, `colorSpace`, `foregroundClusters`, `maximumTrainingPixels`, `maximumIterations`, `tolerance`, `randomSeed` control processing; change one value at a time to trace its effect.
- Represent pixels in BGR, Lab, or HSV color space.
- Repeatedly assign pixels to the nearest centroid and update centroid means.
- Sort learned centroids from darkest ID 0 to brightest ID K-1, then turn foregroundClusters white in the mask.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `kmeans-image-segmentation` |
| Category | Segmentation |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `numpy`, `scikit-learn`, `clustering`, `segmentation`, `contours` |

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
| `clusters` | `integer` | `2` | `2` | `32` | — | Number of color groups K. |
| `colorSpace` | `select` | `bgr` | — | — | `bgr`, `lab`, `hsv` | Lab is often more stable for separating brightness from color. |
| `foregroundClusters` | `json` | `[1]` | — | — | — | JSON cluster IDs to turn white. IDs are ordered from darkest (0) to brightest (K-1); with K=2, [1] selects bright objects. |
| `maximumTrainingPixels` | `integer` | `10000` | `100` | `1000000` | — | Limits fitting cost; all pixels are still classified. |
| `maximumIterations` | `integer` | `100` | `1` | `1000` | — | Upper bound for centroid updates. |
| `tolerance` | `number` | `0.0001` | `1e-09` | `1.0` | — | Stop when centroid movement is below this value. |
| `randomSeed` | `integer` | `42` | `0` | `2147483647` | — | Keeps sampling and initialization repeatable. |

## Copy-ready usage example

**Goal:** Run k-means image segmentation with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `kmeans-image-segmentation` → `overlay-mask`

- Drag **K-means image segmentation** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and configure the fields shown below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "clusters": 2,
  "colorSpace": "bgr",
  "foregroundClusters": [
    1
  ],
  "maximumTrainingPixels": 10000,
  "maximumIterations": 100,
  "tolerance": 0.0001,
  "randomSeed": 42
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
- Results depend on input and assumptions of scikit-learn KMeans and Lloyd's algorithm.
- Measure latency/memory on target hardware.
- trainingSamples live in the recipe and are intended only for small, non-sensitive sample sets.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
