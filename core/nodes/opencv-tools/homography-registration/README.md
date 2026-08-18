# Homography registration node

## Purpose and quick use

`homography-registration` performs **Homography registration** in an AOI pipeline. Registers an image with a homography. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable homography registration step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `homography-registration` → `image-output`

## Node structure

```text
image, reference
    │
    ▼
[homography-registration]
    │
    └── registered-image, transform
```

Inputs are `image`:image, `reference`:image. The node applies Homography registration. Outputs are `registered-image`:image, `transform`:transform. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `homography-registration`.
- Parameters `method` control processing; change one value at a time to trace its effect.
- Apply **Homography registration**: Registers an image with a homography.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `homography-registration` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | None declared |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `reference` | input | `image` | yes | no | Reference |
| `registered-image` | output | `image` | yes | no | Registered image |
| `transform` | output | `transform` | yes | no | Transform |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.
2. Connect a `image` output to `reference`. Provide `image` image data; verify shape, dtype, and channel order.

### Read outputs

- `registered-image` (`image`): Registered image as `image`; preview it or connect a compatible downstream node.
- `transform` (`transform`): Transform as `transform`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `method` | `select` | `ransac` | — | — | `ransac`, `lmeds`, `direct` | Enter `select` within Min/Max; try the default first. |

## Copy-ready usage example

**Goal:** Run homography registration with correctly typed input (`image`:image, `reference`:image) and inspect its output.

**Workflow:** `image-input` → `homography-registration` → `image-output`

- Drag **Homography registration** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "method": "ransac"
}
```

**Example input:** Data for `image`:image, `reference`:image; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce registered-image, transform with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Homography registration.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
