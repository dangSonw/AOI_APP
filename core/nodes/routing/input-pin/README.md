# Input Pin node

## Purpose and quick use

`input-pin` starts a named virtual data channel. Connect one typed source to its generic input, set the node display name, and reuse that exact name on one or more Output Pin nodes.

**Use when:** a long data wire would make the workflow canvas hard to read.

**Quick flow:** `image-input` → `input-pin`

## Node structure

```text
value
    │
    ▼
[input-pin]
    │
    └── (no output)
```

Input `value` accepts any declared workflow data type. The trimmed, case-sensitive display name identifies the virtual channel. The value is forwarded to every matching `output-pin` node without conversion.

## How the algorithm works

- Read the value connected to the generic `value` input.
- Normalize the channel name by trimming outer whitespace while preserving letter case.
- Infer one concrete channel type from the connected Input Pin and Output Pin endpoints.
- Publish the same value object to all matching Output Pin nodes during workflow execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `input-pin` |
| Category | Workflow routing |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `named-virtual-data-routing`, `generic-type-inference` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `value` | input | `generic` | yes | no | Value |

### Provide inputs

1. Connect a `generic` output to `value`. Connect exactly one source. Its concrete type becomes part of the channel type inference.

### Read outputs

- —

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | Node has no configurable parameters. |

## Copy-ready usage example

**Goal:** Route one camera image to a distant workflow section without drawing a long wire.

**Workflow:** `image-input` → `input-pin`

- Drag **Input Pin** onto the canvas.
- Connect an image output to its `value` input.
- Set Display name to `Camera`.
- Add one or more Output Pin nodes named exactly `Camera`.

**Paste into the config panel:**

```json
{}
```

**Example input:** A typed value such as an image, mask, score, decision, or detection collection.

**Expected output:** Matching Output Pin nodes receive the same value and show the inferred concrete type.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| No matching Output Pin | The names differ by case or the matching node is missing. | Use the exact same case-sensitive display name on at least one Output Pin. |
| Duplicate Input Pin error | More than one Input Pin uses the same trimmed name. | Keep exactly one Input Pin for each virtual channel name. |
| Generic type conflict | The connected endpoints declare different concrete data types. | Connect only one consistent concrete type across the named channel. |

## Limitations and production checks

- Names are case-sensitive after outer whitespace is trimmed.
- Each channel requires exactly one Input Pin and at least one Output Pin.
- The virtual dependency must remain acyclic.

### Production checklist

- Use descriptive channel names that are unique within the workflow.
- Confirm the inferred type shown on every paired pin.
- Run workflow validation and Auto order before saving.
