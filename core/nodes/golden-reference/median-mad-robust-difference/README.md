# Median–MAD robust difference node

## Purpose and quick use

`median-mad-robust-difference` performs **Median–MAD robust difference** in an AOI pipeline. Uses median and MAD reference statistics for robust deviation scoring. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable median–mad robust difference step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `median-mad-robust-difference`

## Node structure

```text
image
    │
    ▼
[median-mad-robust-difference]
    │
    └── anomaly-map, score
```

Inputs are `image`:image. The node applies Median–MAD robust difference. Outputs are `anomaly-map`:anomaly-map, `score`:score. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `median-mad-robust-difference`.
- Parameters `epsilon` control processing; change one value at a time to trace its effect.
- Apply **Median–MAD robust difference**: Uses median and MAD reference statistics for robust deviation scoring.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `median-mad-robust-difference` |
| Category | Golden/reference |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | None declared |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `anomaly-map` | output | `anomaly-map` | yes | no | Anomaly map |
| `score` | output | `score` | yes | no | Score |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.

### Read outputs

- `anomaly-map` (`anomaly-map`): Anomaly map as `anomaly-map`; preview it or connect a compatible downstream node.
- `score` (`score`): Score as `score`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `epsilon` | `number` | `0.001` | `1e-07` | `1.0` | — | Enter `number` within Min/Max; try the default first. |

## Copy-ready usage example

**Goal:** Run median–mad robust difference with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `median-mad-robust-difference`

- Drag **Median–MAD robust difference** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "epsilon": 0.001
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

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Median–MAD robust difference.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
