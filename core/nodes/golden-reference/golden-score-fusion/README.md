# Golden score fusion node

## Purpose and quick use

`golden-score-fusion` performs **Golden score fusion** in an AOI pipeline. Fuses configured golden-reference scores. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable golden score fusion step stored in a recipe and inspectable on its own.

**Quick flow:** `mask-coverage-score` → `golden-score-fusion` → `decision-fusion`

## Node structure

```text
scores
    │
    ▼
[golden-score-fusion]
    │
    └── score
```

Inputs are `scores`:score. The node applies Golden score fusion. Outputs are `score`:score. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `golden-score-fusion`.
- Parameters `method` control processing; change one value at a time to trace its effect.
- Apply **Golden score fusion**: Fuses configured golden-reference scores.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `golden-score-fusion` |
| Category | Golden/reference |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | None declared |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `scores` | input | `score` | yes | yes | Scores |
| `score` | output | `score` | yes | no | Score |

### Provide inputs

1. Connect a `score` output to `scores`. Provide `score` matching Scores; do not substitute image data.

### Read outputs

- `score` (`score`): Score as `score`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `method` | `select` | `maximum` | — | — | `maximum`, `mean`, `weighted-mean` | Enter `select` within Min/Max; try the default first. |

## Copy-ready usage example

**Goal:** Run golden score fusion with correctly typed input (`scores`:score) and inspect its output.

**Workflow:** `mask-coverage-score` → `golden-score-fusion` → `decision-fusion`

- Drag **Golden score fusion** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "method": "maximum"
}
```

**Example input:** Data for `scores`:score; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce score with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Golden score fusion.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
