# Merge node

## Purpose and quick use

`merge` performs **Merge** in an AOI pipeline. Merges any or all incoming control branches deterministically. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable merge step stored in a recipe and inspectable on its own.

**Quick flow:** `merge`

## Node structure

```text
(no input)
    │
    ▼
[merge]
    │
    └── (no output)
```

Inputs are none. The node applies Merge. Outputs are none. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `merge`.
- Parameters `policy` control processing; change one value at a time to trace its effect.
- Apply **Merge**: Merges any or all incoming control branches deterministically.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `merge` |
| Category | Control |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `control-merge` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| — | — | — | — | — | No ports |

### Provide inputs

This node has no input.

### Read outputs

- —

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `policy` | `select` | `any` | — | — | `any`, `all` | Run on any arrival or after all incoming edges arrive. |

## Copy-ready usage example

**Goal:** Run merge with correctly typed input (none) and inspect its output.

**Workflow:** `merge`

- Drag **Merge** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "policy": "any"
}
```

**Example input:** Data for none; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce no output with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Merge.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
