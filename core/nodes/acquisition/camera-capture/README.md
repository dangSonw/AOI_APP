# Camera capture node

## Purpose and quick use

`camera-capture` performs **Camera capture** in an AOI pipeline. Describes a configured camera acquisition step. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable camera capture step stored in a recipe and inspectable on its own.

**Quick flow:** `camera-capture` → `image-output`

## Node structure

```text
(no input)
    │
    ▼
[camera-capture]
    │
    └── image
```

Inputs are none. The node applies Camera capture. Outputs are `image`:image. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `camera-capture`.
- Parameters `cameraId`, `exposureUs` control processing; change one value at a time to trace its effect.
- Apply **Camera capture**: Describes a configured camera acquisition step.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `camera-capture` |
| Category | Acquisition |
| Status | `debug` |
| Execution target | `adapter` |
| Capabilities | None declared |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | output | `image` | yes | no | Image |

### Provide inputs

This node has no input.

### Read outputs

- `image` (`image`): Image as `image`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `cameraId` | `text` | `top-camera` | — | — | — | Enter `text` within Min/Max; try the default first. |
| `exposureUs` | `integer` | `8000` | `1` | `1000000` | — | Enter `integer` within Min/Max; try the default first. |

## Copy-ready usage example

**Goal:** Run camera capture with correctly typed input (none) and inspect its output.

**Workflow:** `camera-capture` → `image-output`

- Drag **Camera capture** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "cameraId": "top-camera",
  "exposureUs": 8000
}
```

**Example input:** Data for none; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce image with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Camera capture.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
