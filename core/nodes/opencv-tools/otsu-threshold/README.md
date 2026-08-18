# Otsu threshold node

## Purpose and quick use

`otsu-threshold` performs **Otsu threshold** in an AOI pipeline. Selects a global threshold using Otsu criteria. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable otsu threshold step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `otsu-threshold` → `overlay-mask`

## Node structure

```text
image
    │
    ▼
[otsu-threshold]
    │
    └── mask
```

Inputs are `image`:image. The node applies Otsu threshold. Outputs are `mask`:mask. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `otsu-threshold`.
- The node has no parameters; behavior is determined by its input and runtime contract.
- Apply **Otsu threshold**: Selects a global threshold using Otsu criteria.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `otsu-threshold` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | None declared |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `mask` | output | `mask` | yes | no | Mask |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.

### Read outputs

- `mask` (`mask`): Mask as `mask`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | Node has no configurable parameters. |

## Copy-ready usage example

**Goal:** Run otsu threshold with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `otsu-threshold` → `overlay-mask`

- Drag **Otsu threshold** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{}
```

**Example input:** Data for `image`:image; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce mask with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Otsu threshold.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
