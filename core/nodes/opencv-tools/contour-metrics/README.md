# Contour metrics node

## Purpose and quick use

`contour-metrics` performs **Contour metrics** in an AOI pipeline. Measures area, perimeter, centroid, and solidity for contours. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable contour metrics step stored in a recipe and inspectable on its own.

**Quick flow:** `find-contours` → `contour-metrics` → `draw-detections`

## Node structure

```text
contours
    │
    ▼
[contour-metrics]
    │
    └── metrics
```

Inputs are `contours`:contours. The node applies OpenCV contourArea, arcLength and moments. Outputs are `metrics`:detections. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `contour-metrics`.
- The node has no parameters; behavior is determined by its input and runtime contract.
- Apply **OpenCV contourArea, arcLength and moments**: Measures area, perimeter, centroid, and solidity for contours.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `contour-metrics` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `contour-analysis` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `contours` | input | `contours` | yes | no | Contours |
| `metrics` | output | `detections` | yes | no | Metrics |

### Provide inputs

1. Connect a `contours` output to `contours`. Provide `contours` matching Contours; do not substitute image data.

### Read outputs

- `metrics` (`detections`): Metrics as `detections`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | Node has no configurable parameters. |

## Copy-ready usage example

**Goal:** Run contour metrics with correctly typed input (`contours`:contours) and inspect its output.

**Workflow:** `find-contours` → `contour-metrics` → `draw-detections`

- Drag **Contour metrics** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{}
```

**Example input:** Data for `contours`:contours; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce metrics with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV contourArea, arcLength and moments.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
