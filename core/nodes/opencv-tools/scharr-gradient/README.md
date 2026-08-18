# Scharr gradient node

## Purpose and quick use

`scharr-gradient` performs **Scharr gradient** in an AOI pipeline. Computes a Scharr gradient. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable scharr gradient step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `scharr-gradient` → `image-output`

## Node structure

```text
image
    │
    ▼
[scharr-gradient]
    │
    └── processed-image
```

Inputs are `image`:image. The node applies Scharr gradient. Outputs are `processed-image`:image. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `scharr-gradient`.
- Parameters `axis` control processing; change one value at a time to trace its effect.
- Apply **Scharr gradient**: Computes a Scharr gradient.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `scharr-gradient` |
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
| `axis` | `select` | `x` | — | — | `x`, `y` | Enter `select` within Min/Max; try the default first. |

## Copy-ready usage example

**Goal:** Run scharr gradient with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `scharr-gradient` → `image-output`

- Drag **Scharr gradient** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "axis": "x"
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
- Results depend on input and assumptions of Scharr gradient.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
