# SVM image classifier node

## Purpose and quick use

`svm-image-classifier` trains a bounded HOG plus scikit-learn SVC pipeline from immutable labeled image datasets. It preserves the `128 × 128`, RBF, `C=10`, and `gamma=scale` intent of the reference script without hard-coded paths or class names.

## Node structure

```text
immutable training/test datasets
              │
              ▼
    [svm-image-classifier]
              │
              ├── model and metrics
              ├── aoi.table.v1 classification report
              └── aoi.confusion-matrix.v1 / failed images
```

## How to enter parameters

Use the custom inspector sections for Dataset, Feature extraction, Model, Training, and Results. HOG block dimensions must divide into cells, stride must align to cells, and the window must match the resized image.

Connect `report` to an explicit `table-output` node and `confusion-matrix` to an explicit `plot-2d-output` node to enable Dashboard viewers. Generic output pins do not create viewers.

## Copy-ready usage example

```json
{"imageWidth":128,"imageHeight":128,"hogBlockWidth":16,"hogBlockStrideX":8,"hogCellWidth":8,"hogBins":9,"useScaler":true,"kernel":"rbf","c":10,"gamma":"scale","randomSeed":42}
```

## Troubleshooting

- Restore `128/16/8/8/9` when HOG geometry validation fails.
- Provide at least two classes for SVC fitting.
- Inspect failed-image logical IDs; storage paths are never exposed.

## Limitations and production checks

The node is CPU-only. Training behavior is introduced after the manifest contract and must remain inside this package. Verify dataset versions, metrics, and artifact checksums before model promotion.