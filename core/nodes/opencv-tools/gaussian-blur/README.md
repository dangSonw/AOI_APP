# Gaussian blur node

## Purpose and quick use

`gaussian-blur` performs **Gaussian blur** in an AOI pipeline. Applies a configured Gaussian smoothing kernel. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable gaussian blur step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `gaussian-blur` → `image-output`

## Node structure

```text
image
    │
    ▼
[gaussian-blur]
    │
    └── processed-image
```

Inputs are `image`:image. The node applies Gaussian blur. Outputs are `processed-image`:image. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `gaussian-blur`.
- Parameters `kernelSize`, `sigma` control processing; change one value at a time to trace its effect.
- Apply **Gaussian blur**: Applies a configured Gaussian smoothing kernel.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `gaussian-blur` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | None declared |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `processed-image` | output | `image` | yes | no | Processed image |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.

### Read outputs

- `processed-image` (`image`): Processed image as `image`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `kernelSize` | `integer` | `5` | `1` | `255` | — | Enter `integer` within Min/Max; try the default first. |
| `sigma` | `number` | `1.0` | `0.0` | `1000.0` | — | Enter `number` within Min/Max; try the default first. |

## Copy-ready usage example

**Goal:** Run gaussian blur with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `gaussian-blur` → `image-output`

- Drag **Gaussian blur** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "kernelSize": 5,
  "sigma": 1.0
}
```

**Example input:** Data for `image`:image; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce processed-image with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Gaussian blur.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
