# Switch / case node

## Purpose and quick use

`switch-case` performs **Switch / case** in an AOI pipeline. Routes a generic value to the first matching named case or default. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable switch / case step stored in a recipe and inspectable on its own.

**Quick flow:** `switch-case`

## Node structure

```text
value
    │
    ▼
[switch-case]
    │
    └── (no output)
```

Inputs are `value`:generic. The node applies Switch / case. Outputs are none. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `switch-case`.
- Parameters `cases` control processing; change one value at a time to trace its effect.
- Apply **Switch / case**: Routes a generic value to the first matching named case or default.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `switch-case` |
| Category | Control |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `dynamic-control-routing` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `value` | input | `generic` | yes | no | Value |

### Provide inputs

1. Connect a `generic` output to `value`. Provide `generic` matching Value; do not substitute image data.

### Read outputs

- —

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `cases` | `json` | `[]` | — | — | — | Ordered objects containing branch and value. |

## Copy-ready usage example

**Goal:** Run switch / case with correctly typed input (`value`:generic) and inspect its output.

**Workflow:** `switch-case`

- Drag **Switch / case** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "cases": []
}
```

**Example input:** Data for `value`:generic; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce no output with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Switch / case.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
