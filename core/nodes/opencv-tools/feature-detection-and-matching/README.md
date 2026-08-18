# Feature detection and matching node

## Purpose and quick use

`feature-detection-and-matching` performs **Feature detection and matching** in an AOI pipeline. Runs feature extraction and correspondence matching. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable feature detection and matching step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `feature-detection-and-matching`

## Node structure

```text
image, reference
    │
    ▼
[feature-detection-and-matching]
    │
    └── keypoints, transform
```

Inputs are `image`:image, `reference`:image. The node applies Feature detection and matching. Outputs are `keypoints`:keypoints, `transform`:transform. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `feature-detection-and-matching`.
- Parameters `detector` control processing; change one value at a time to trace its effect.
- Apply **Feature detection and matching**: Runs feature extraction and correspondence matching.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `feature-detection-and-matching` |
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
| `keypoints` | output | `keypoints` | yes | no | Matches |
| `transform` | output | `transform` | yes | no | Transform |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.
2. Connect a `image` output to `reference`. Provide `image` image data; verify shape, dtype, and channel order.

### Read outputs

- `keypoints` (`keypoints`): Matches as `keypoints`; preview it or connect a compatible downstream node.
- `transform` (`transform`): Transform as `transform`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `detector` | `select` | `orb` | — | — | `orb`, `sift`, `akaze` | Enter `select` within Min/Max; try the default first. |

## Copy-ready usage example

**Goal:** Run feature detection and matching with correctly typed input (`image`:image, `reference`:image) and inspect its output.

**Workflow:** `image-input` → `feature-detection-and-matching`

- Drag **Feature detection and matching** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "detector": "orb"
}
```

**Example input:** Data for `image`:image, `reference`:image; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce keypoints, transform with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Feature detection and matching.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
