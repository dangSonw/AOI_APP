# Plot 2D output node

## Purpose and quick use
`plot-2d-output` is the explicit workflow gate for structured plot-series and confusion-matrix viewers.

## Node structure
```text
structured payload -> [plot-2d-output] -> validated payload
```

## How to enter parameters
This node has no parameters. Connect a validated `aoi.plot-series.v1` or `aoi.confusion-matrix.v1` payload.

## Copy-ready usage example
```json
{"schema":"aoi.confusion-matrix.v1","labels":["OK","NG"],"matrix":[[9,1],[0,8]]}
```

## Troubleshooting
- Add the explicit node when no viewer appears.
- Keep matrix dimensions aligned with labels.
- Emit only finite bounded plot values.