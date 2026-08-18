# ECC registration node

## Purpose and quick use

`ecc-registration` performs **ECC registration** in an AOI pipeline. Registers an image by enhanced correlation coefficient. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable ecc registration step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `ecc-registration` → `image-output`

## Node structure

```text
image, reference
    │
    ▼
[ecc-registration]
    │
    └── registered-image, transform
```

Inputs are `image`:image, `reference`:image. The node applies ECC registration. Outputs are `registered-image`:image, `transform`:transform. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `ecc-registration`.
- Parameters `motionModel`, `iterations` control processing; change one value at a time to trace its effect.
- Apply **ECC registration**: Registers an image by enhanced correlation coefficient.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `ecc-registration` |
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
| `motionModel` | `select` | `homography` | — | — | `translation`, `euclidean`, `affine`, `homography` | Enter `select` within Min/Max; try the default first. |
| `iterations` | `integer` | `100` | `1` | `10000` | — | Enter `integer` within Min/Max; try the default first. |

## Copy-ready usage example

**Goal:** Run ecc registration with correctly typed input (`image`:image, `reference`:image) and inspect its output.

**Workflow:** `image-input` → `ecc-registration` → `image-output`

- Drag **ECC registration** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "motionModel": "homography",
  "iterations": 100
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
- Results depend on input and assumptions of ECC registration.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
