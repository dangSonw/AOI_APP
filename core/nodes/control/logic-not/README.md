# Logic NOT node

## Purpose and quick use

`logic-not` performs **Logic NOT** in an AOI pipeline. Inverts one boolean input and routes true or false. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable logic not step stored in a recipe and inspectable on its own.

**Quick flow:** `logic-not` → `logic-or`

## Node structure

```text
value
    │
    ▼
[logic-not]
    │
    └── result
```

Inputs are `value`:boolean. The node applies Logic NOT. Outputs are `result`:boolean. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `logic-not`.
- The node has no parameters; behavior is determined by its input and runtime contract.
- Apply **Logic NOT**: Inverts one boolean input and routes true or false.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `logic-not` |
| Category | Control |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `boolean-logic`, `control-routing` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `value` | input | `boolean` | yes | no | Value |
| `result` | output | `boolean` | yes | no | Result |

### Provide inputs

1. Connect a `boolean` output to `value`. Provide `boolean` matching Value; do not substitute image data.

### Read outputs

- `result` (`boolean`): Result as `boolean`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | Node has no configurable parameters. |

## Copy-ready usage example

**Goal:** Run logic not with correctly typed input (`value`:boolean) and inspect its output.

**Workflow:** `logic-not` → `logic-or`

- Drag **Logic NOT** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{}
```

**Example input:** Data for `value`:boolean; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce result with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Logic NOT.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
