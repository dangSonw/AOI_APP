# Template matching node

## Purpose and quick use

`template-matching` performs **Template matching** in an AOI pipeline. Matches configured templates against an image. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable template matching step stored in a recipe and inspectable on its own.

**Quick flow:** `image-input` → `template-matching` → `draw-detections`

## Node structure

```text
image
    │
    ▼
[template-matching]
    │
    └── detections, score
```

Inputs are `image`:image. The node applies Template matching. Outputs are `detections`:detections, `score`:score. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `template-matching`.
- Parameters `method` control processing; change one value at a time to trace its effect.
- Apply **Template matching**: Matches configured templates against an image.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `template-matching` |
| Category | Golden/reference |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | None declared |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `image` | input | `image` | yes | no | Image |
| `detections` | output | `detections` | yes | no | Matches |
| `score` | output | `score` | yes | no | Score |

### Provide inputs

1. Connect a `image` output to `image`. Provide `image` image data; verify shape, dtype, and channel order.

### Read outputs

- `detections` (`detections`): Matches as `detections`; preview it or connect a compatible downstream node.
- `score` (`score`): Score as `score`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `method` | `select` | `ccoeff-normed` | — | — | `sqdiff`, `sqdiff-normed`, `ccorr-normed`, `ccoeff-normed` | Enter `select` within Min/Max; try the default first. |

## Copy-ready usage example

**Goal:** Run template matching with correctly typed input (`image`:image) and inspect its output.

**Workflow:** `image-input` → `template-matching` → `draw-detections`

- Drag **Template matching** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{
  "method": "ccoeff-normed"
}
```

**Example input:** Data for `image`:image; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce detections, score with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of Template matching.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
