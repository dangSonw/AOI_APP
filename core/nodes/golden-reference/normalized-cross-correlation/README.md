# Normalized cross-correlation node

## Purpose and quick use

`normalized-cross-correlation` performs **Normalized cross-correlation** in an AOI pipeline. Scores normalized correlation with a configured reference. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable normalized cross-correlation step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `normalized-cross-correlation`

## Node structure

```text
image
    │
    ▼
[normalized-cross-correlation]
    │
    └── anomaly-map, score
```

Inputs are `image`:image. The node applies Normalized cross-correlation. Outputs are `anomaly-map`:anomaly-map, `score`:score. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `normalized-cross-correlation`.
- The node has no parameters; behavior is determined by its input and runtime contract.
- Apply **Normalized cross-correlation**: Scores normalized correlation with a configured reference.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `normalized-cross-correlation` |
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
| — | — | — | — | — | — | Node has no configurable parameters. |

## Copy-ready usage example

**Goal:** Run normalized cross-correlation with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `normalized-cross-correlation`

- Drag **Normalized cross-correlation** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{}
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
- Results depend on input and assumptions of Normalized cross-correlation.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
