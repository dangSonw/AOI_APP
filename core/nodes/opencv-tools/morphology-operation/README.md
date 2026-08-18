# Morphology operation node

## Purpose and quick use

`morphology-operation` performs **Morphology operation** in an AOI pipeline. Applies a selected morphology operation. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable morphology operation step stored in a recipe and inspectable on its own.

**Quick flow:** `global-threshold` → `morphology-operation` → `overlay-mask`

## Node structure

```text
mask
    │
    ▼
[morphology-operation]
    │
    └── processed-mask
```

Inputs are `mask`:mask. The node applies Morphology operation. Outputs are `processed-mask`:mask. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `morphology-operation`.
- Parameters `operation`, `kernelSize` control processing; change one value at a time to trace its effect.
- Apply **Morphology operation**: Applies a selected morphology operation.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `morphology-operation` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | None declared |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `mask` | input | `mask` | yes | no | Mask |
| `processed-mask` | output | `mask` | yes | no | Processed mask |

### Provide inputs

1. Connect a `mask` output to `mask`. Provide `mask` image data; verify shape, dtype, and channel order.

### Read outputs

- `processed-mask` (`mask`): Processed mask as `mask`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `operation` | `select` | `open` | — | — | `open`, `close`, `gradient`, `top-hat`, `black-hat` | Enter `select` within Min/Max; try the default first. |
| `kernelSize` | `integer` | `3` | `1` | `255` | — | Enter `integer` within Min/Max; try the default first. |

## Copy-ready usage example

**Goal:** Run morphology operation with correctly typed input (`mask`:mask) and inspect its output.

**Workflow:** `global-threshold` → `morphology-operation` → `overlay-mask`

- Drag **Morphology operation** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "operation": "open",
  "kernelSize": 3
}
```

**Example input:** Data for `mask`:mask; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce processed-mask with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Morphology operation.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
