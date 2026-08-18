# Counter / limit node

## Purpose and quick use

`counter-limit` performs **Counter / limit** in an AOI pipeline. Routes run-scoped activations below or at a configured limit. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable counter / limit step stored in a recipe and inspectable on its own.

**Quick flow:** `counter-limit`

## Node structure

```text
(no input)
    │
    ▼
[counter-limit]
    │
    └── count
```

Inputs are none. The node applies Counter / limit. Outputs are `count`:generic. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `counter-limit`.
- Parameters `limit` control processing; change one value at a time to trace its effect.
- Apply **Counter / limit**: Routes run-scoped activations below or at a configured limit.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `counter-limit` |
| Category | Control |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `bounded-control` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `count` | output | `generic` | yes | no | Count |

### Provide inputs

This node has no input.

### Read outputs

- `count` (`generic`): Count as `generic`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `limit` | `integer` | `1` | `1` | `10000` | — | Activation count selecting limit-reached. |

## Copy-ready usage example

**Goal:** Run counter / limit with correctly typed input (none) and inspect its output.

**Workflow:** `counter-limit`

- Drag **Counter / limit** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "limit": 1
}
```

**Example input:** Data for none; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce count with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Counter / limit.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
