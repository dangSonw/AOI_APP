# Table output node

## Purpose and quick use
`table-output` is the explicit workflow gate for bounded typed HTML-table viewers.

## Node structure
```text
table payload -> [table-output] -> validated payload
```

## How to enter parameters
This node has no parameters. Connect an `aoi.table.v1` payload.

## Copy-ready usage example
```json
{"schema":"aoi.table.v1","columns":[{"key":"label","label":"Label","type":"string"}],"rows":[{"label":"OK"}]}
```

## Troubleshooting
- Add this explicit node when no table appears.
- Match every row key to the declared columns.
- Match each value to its declared type.