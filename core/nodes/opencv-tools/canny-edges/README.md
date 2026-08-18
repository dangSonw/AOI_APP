# Canny edges node

## Purpose and quick use

`canny-edges` performs **Canny edges** in an AOI pipeline. Runs Canny edge extraction. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable canny edges step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `canny-edges` → `overlay-mask`

## Node structure

```text
image
    │
    ▼
[canny-edges]
    │
    └── mask
```

Inputs are `image`:image. The node applies Canny edges. Outputs are `mask`:mask. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `canny-edges`.
- Parameters `lowThreshold`, `highThreshold` control processing; change one value at a time to trace its effect.
- Apply **Canny edges**: Runs Canny edge extraction.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `canny-edges` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | None declared |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `mask` | output | `mask` | yes | no | Edges |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.

### Read outputs

- `mask` (`mask`): Edges as `mask`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `lowThreshold` | `number` | `50.0` | `0.0` | `65535.0` | — | Enter `number` within Min/Max; try the default first. |
| `highThreshold` | `number` | `150.0` | `0.0` | `65535.0` | — | Enter `number` within Min/Max; try the default first. |

## Copy-ready usage example

**Goal:** Run canny edges with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `canny-edges` → `overlay-mask`

- Drag **Canny edges** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "lowThreshold": 50.0,
  "highThreshold": 150.0
}
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
- Results depend on input and assumptions of Canny edges.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
