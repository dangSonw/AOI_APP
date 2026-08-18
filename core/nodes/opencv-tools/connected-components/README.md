# Connected components node

## Purpose and quick use

`connected-components` performs **Connected components** in an AOI pipeline. Labels connected mask components. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable connected components step stored in a recipe and inspectable on its own.

**Quick flow:** `global-threshold` → `connected-components` → `draw-detections`

## Node structure

```text
mask
    │
    ▼
[connected-components]
    │
    └── detections
```

Inputs are `mask`:mask. The node applies Connected components. Outputs are `detections`:detections. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `connected-components`.
- The node has no parameters; behavior is determined by its input and runtime contract.
- Apply **Connected components**: Labels connected mask components.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `connected-components` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | None declared |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `mask` | input | `mask` | yes | no | Mask |
| `detections` | output | `detections` | yes | no | Components |

### Provide inputs

1. Connect a `mask` output to `mask`. Provide `mask` image data; verify shape, dtype, and channel order.

### Read outputs

- `detections` (`detections`): Components as `detections`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | Node has no configurable parameters. |

## Copy-ready usage example

**Goal:** Run connected components with correctly typed input (`mask`:mask) and inspect its output.

**Workflow:** `global-threshold` → `connected-components` → `draw-detections`

- Drag **Connected components** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{}
```

**Example input:** Data for `mask`:mask; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce detections with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Connected components.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
