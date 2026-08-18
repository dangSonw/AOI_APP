# Convex hull node

## Purpose and quick use

`convex-hull` performs **Convex hull** in an AOI pipeline. Computes the convex hull of every input contour. Configure it in Node inspector and connect outputs to ports with matching data types.

**Use when:** you need a repeatable convex hull step stored in a recipe and inspectable on its own.

**Quick flow:** `find-contours` → `convex-hull` → `draw-contours`

## Node structure

```text
contours
    │
    ▼
[convex-hull]
    │
    └── hulls
```

Inputs are `contours`:contours. The node applies OpenCV convexHull. Outputs are `hulls`:contours. Each key in the diagram is the exact port name used when connecting edges.

## How the algorithm works

- Validate input presence, data types, and shapes against `convex-hull`.
- The node has no parameters; behavior is determined by its input and runtime contract.
- Apply **OpenCV convexHull**: Computes the convex hull of every input contour.
- Normalize/package results with declared data types so graph compatibility is checked before execution.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `convex-hull` |
| Category | OpenCV tools |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `opencv`, `contour-analysis` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| `contours` | input | `contours` | yes | no | Contours |
| `hulls` | output | `contours` | yes | no | Convex hulls |

### Provide inputs

1. Connect a `contours` output to `contours`. Provide `contours` matching Contours; do not substitute image data.

### Read outputs

- `hulls` (`contours`): Convex hulls as `contours`; preview it or connect a compatible downstream node.

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | Node has no configurable parameters. |

## Copy-ready usage example

**Goal:** Run convex hull with correctly typed input (`contours`:contours) and inspect its output.

**Workflow:** `find-contours` → `convex-hull` → `draw-contours`

- Drag **Convex hull** onto the canvas.
- Connect ports as shown in the workflow.
- Open Node inspector and enter the JSON config below.
- Run, inspect output, then tune one parameter at a time.

**Paste into the config panel:**

```json
{}
```

**Example input:** Data for `contours`:contours; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types.

**Expected output:** Produce hulls with the declared type and no error.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Ports cannot connect | Data types differ. | Insert a node producing the exact type in the ports table. |
| Invalid parameter | Outside Min/Max or malformed JSON. | Copy the example config and change one value at a time. |
| Empty/noisy output | Input or settings violate assumptions. | Preview input, restore defaults, and tune incrementally. |

## Limitations and production checks

- This node is DEBUG and not production-approved.
- Results depend on input and assumptions of OpenCV convexHull.
- Measure latency/memory on target hardware.

### Production checklist

- Lock camera, illumination, resolution, and channel order.
- Evaluate representative OK/NG data and false-call/escape rates.
- Set parameter limits, timeouts, and fail-closed checks.
