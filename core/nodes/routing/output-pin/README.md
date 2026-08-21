# Output Pin node

## Purpose and quick use

`output-pin` continues a named virtual data channel. Set its display name to the exact Input Pin name, then connect its generic output to a typed consumer.

**Use when:** a value from a distant Input Pin must continue into one or more consumers without a long visible wire.

**Quick flow:** `output-pin` → `gaussian-blur`

## Node structure

```text
(no input)
    │
    ▼
[output-pin]
    │
    └── value
```

Output `value` exposes the unchanged value captured by the single matching Input Pin. The trimmed display name is case-sensitive and the concrete type is inferred from all channel endpoints.

## How the algorithm works

- Resolve the single Input Pin with the same normalized display name.
- Wait for that Input Pin to capture its incoming value.
- Expose the same value object through generic output `value`.
- Validate every connected consumer against the one inferred channel type.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `output-pin` |
| Category | Workflow routing |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `named-virtual-data-routing`, `generic-type-inference` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `value` | output | `generic` | yes | no | Value |

### Provide inputs

This node has no input.

### Read outputs

- `value` (`generic`): Connect to a typed consumer. The displayed inferred type must match every other endpoint on the same channel.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | Node has no configurable parameters. |

## Copy-ready usage example

**Goal:** Continue the named `Camera` image channel into an image-processing node.

**Workflow:** `output-pin` → `gaussian-blur`

- Drag **Output Pin** near the destination node.
- Set Display name to exactly `Camera`.
- Connect `value` to the destination image input.
- Verify that the port shows `image · inferred`.

**Paste into the config panel:**

```json
{}
```

**Example input:** The value captured by the matching Input Pin during the same workflow execution.

**Expected output:** The downstream node receives the unchanged value with the inferred channel type.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| No matching Input Pin | The names differ by case or no Input Pin exists. | Create exactly one Input Pin with the same case-sensitive display name. |
| Generic type conflict | This consumer expects a different type from another channel endpoint. | Use consumers that agree on one concrete data type. |
| Cycle validation error | The virtual dependency routes data back to an upstream node. | Rearrange the graph so the Input Pin always precedes every matching Output Pin. |

## Limitations and production checks

- An Output Pin cannot execute before its matching Input Pin.
- Names are case-sensitive after outer whitespace is trimmed.
- All Output Pins sharing a name expose one common value and type.

### Production checklist

- Confirm the matching Input Pin is unique.
- Confirm the inferred type matches the destination port.
- Validate and Auto order the workflow before saving.
