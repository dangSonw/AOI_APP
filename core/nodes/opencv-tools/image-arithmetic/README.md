# Image arithmetic node

## Purpose and quick use

`image-arithmetic` performs **Image arithmetic** in an AOI pipeline. Applies saturated add, subtract, or multiply to equal-shaped images. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable image arithmetic step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `image-arithmetic` → `image-output`

## Node structure

```text
image, operand
    │
    ▼
[image-arithmetic]
    │
    └── processed-image
```

Inputs are `image`:image, `operand`:image. The node applies OpenCV add, subtract and multiply. Outputs are `processed-image`:image. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `image-arithmetic`.
- Parameters `operation` control processing; change one value at a time to trace its effect.
- Apply **OpenCV add, subtract and multiply**: Applies saturated add, subtract, or multiply to equal-shaped images.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `image-arithmetic` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `image-arithmetic` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `operand` | input | `image` | yes | no | Operand |
| `processed-image` | output | `image` | yes | no | Result |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.
2. Connect a `image` output to `operand`. Provide `image` image data; verify shape, dtype, and channel order.

### Read outputs

- `processed-image` (`image`): Result as `image`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `operation` | `select` | `add` | — | — | `add`, `subtract`, `multiply` | Saturated image arithmetic operation. |

## Copy-ready usage example

**Goal:** Run image arithmetic with correctly typed input (`image`:image, `operand`:image) and inspect its output.

**Workflow:** `image-input` → `image-arithmetic` → `image-output`

- Drag **Image arithmetic** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "operation": "add"
}
```

**Example input:** Data for `image`:image, `operand`:image; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce processed-image with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV add, subtract and multiply.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
