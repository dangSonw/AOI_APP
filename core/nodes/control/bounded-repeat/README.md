# Bounded repeat node

## Purpose and quick use

`bounded-repeat` performs **Bounded repeat** in an AOI pipeline. Expands one image into a bounded image set without introducing a graph cycle. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable bounded repeat step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `bounded-repeat`

## Node structure

```text
image
    │
    ▼
[bounded-repeat]
    │
    └── images
```

Inputs are `image`:image. The node applies Bounded repeat. Outputs are `images`:image-set. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `bounded-repeat`.
- Parameters `iterations` control processing; change one value at a time to trace its effect.
- Apply **Bounded repeat**: Expands one image into a bounded image set without introducing a graph cycle.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `bounded-repeat` |
| Category | Control |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `bounded-repeat` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `images` | output | `image-set` | yes | no | Repeated images |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.

### Read outputs

- `images` (`image-set`): Repeated images as `image-set`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `iterations` | `integer` | `1` | `1` | `100` | — | Number of references added to the output image set. |

## Copy-ready usage example

**Goal:** Run bounded repeat with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `bounded-repeat`

- Drag **Bounded repeat** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "iterations": 1
}
```

**Example input:** Data for `image`:image; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce images with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Bounded repeat.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
