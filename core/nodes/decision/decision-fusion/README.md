# Decision fusion node

## Purpose and quick use

`decision-fusion` performs **Decision fusion** in an AOI pipeline. Combines one or more scores into a review decision. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable decision fusion step stored in a recipe and inspectable on its own.

**Quick flow:** `mask-coverage-score` → `decision-fusion` → `decision-output`

## Node structure

```text
scores
    │
    ▼
[decision-fusion]
    │
    └── decision
```

Inputs are `scores`:score. The node applies Decision fusion. Outputs are `decision`:decision. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `decision-fusion`.
- Parameters `reviewThreshold`, `failThreshold` control processing; change one value at a time to trace its effect.
- Apply **Decision fusion**: Combines one or more scores into a review decision.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `decision-fusion` |
| Category | Decision |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | None declared |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `scores` | input | `score` | yes | yes | Scores |
| `decision` | output | `decision` | yes | no | Decision |

### Provide inputs

1. Connect a `score` output to `scores`. Provide `score` matching Scores; do not substitute image data.

### Read outputs

- `decision` (`decision`): Decision as `decision`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `reviewThreshold` | `number` | `0.5` | `0.0` | `1.0` | — | Enter `number` within Min/Max; try the default first. |
| `failThreshold` | `number` | `0.8` | `0.0` | `1.0` | — | Enter `number` within Min/Max; try the default first. |

## Copy-ready usage example

**Goal:** Run decision fusion with correctly typed input (`scores`:score) and inspect its output.

**Workflow:** `mask-coverage-score` → `decision-fusion` → `decision-output`

- Drag **Decision fusion** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "reviewThreshold": 0.5,
  "failThreshold": 0.8
}
```

**Example input:** Data for `scores`:score; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce decision with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Decision fusion.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
