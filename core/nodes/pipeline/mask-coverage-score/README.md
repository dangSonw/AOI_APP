# Mask coverage score node

## Purpose and quick use

`mask-coverage-score` performs **Mask coverage score** in an AOI pipeline. Calculates foreground pixel coverage as a normalized score from zero to one. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable mask coverage score step stored in a recipe and inspectable on its own.

**Quick flow:** `global-threshold` → `mask-coverage-score` → `decision-fusion`

## Node structure

```text
mask
    │
    ▼
[mask-coverage-score]
    │
    └── score
```

Inputs are `mask`:mask. The node applies Mask coverage score. Outputs are `score`:score. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `mask-coverage-score`.
- The node has no parameters; behavior is determined by its input and runtime contract.
- Apply **Mask coverage score**: Calculates foreground pixel coverage as a normalized score from zero to one.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `mask-coverage-score` |
| Category | Pipeline |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `mask-analysis` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `mask` | input | `mask` | yes | no | Mask |
| `score` | output | `score` | yes | no | Coverage score |

### Provide inputs

1. Connect a `mask` output to `mask`. Provide `mask` image data; verify shape, dtype, and channel order.

### Read outputs

- `score` (`score`): Coverage score as `score`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | Node has no configurable parameters. |

## Copy-ready usage example

**Goal:** Run mask coverage score with correctly typed input (`mask`:mask) and inspect its output.

**Workflow:** `global-threshold` → `mask-coverage-score` → `decision-fusion`

- Drag **Mask coverage score** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{}
```

**Example input:** Data for `mask`:mask; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce score with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Mask coverage score.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
