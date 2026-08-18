# Distance transform node

## Purpose and quick use

`distance-transform` performs **Distance transform** in an AOI pipeline. Computes distance to the nearest zero pixel in a mask. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable distance transform step stored in a recipe and inspectable on its own.

**Quick flow:** `global-threshold` → `distance-transform`

## Node structure

```text
mask
    │
    ▼
[distance-transform]
    │
    └── distance-map
```

Inputs are `mask`:mask. The node applies OpenCV distanceTransform. Outputs are `distance-map`:anomaly-map. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `distance-transform`.
- Parameters `metric`, `maskSize` control processing; change one value at a time to trace its effect.
- Apply **OpenCV distanceTransform**: Computes distance to the nearest zero pixel in a mask.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `distance-transform` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `distance-transform` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `mask` | input | `mask` | yes | no | Mask |
| `distance-map` | output | `anomaly-map` | yes | no | Distance map |

### Provide inputs

1. Connect a `mask` output to `mask`. Provide `mask` image data; verify shape, dtype, and channel order.

### Read outputs

- `distance-map` (`anomaly-map`): Distance map as `anomaly-map`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `metric` | `select` | `l2` | — | — | `l1`, `l2`, `chessboard` | Distance metric. |
| `maskSize` | `select` | `3` | — | — | `3`, `5` | Distance approximation mask size. |

## Copy-ready usage example

**Goal:** Run distance transform with correctly typed input (`mask`:mask) and inspect its output.

**Workflow:** `global-threshold` → `distance-transform`

- Drag **Distance transform** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "metric": "l2",
  "maskSize": 3
}
```

**Example input:** Data for `mask`:mask; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce distance-map with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV distanceTransform.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
