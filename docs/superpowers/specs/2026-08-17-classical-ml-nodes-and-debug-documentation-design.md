# Classical ML Nodes and DEBUG Documentation Design

**Date:** 2026-08-17  
**Status:** Approved design, pending implementation plan  
**Scope:** Five executable classical machine-learning node packages and detailed bilingual documentation for every executable `DEBUG` node

## 1. Objective

Extend AOI Studio with five classical machine-learning algorithms that can execute in either of two explicitly selected modes:

1. a maintained library implementation using scikit-learn;
2. an educational, auditable implementation written with Python and NumPy.

At the same time, replace the current short generic documentation for all `DEBUG` nodes with detailed English and Vietnamese guides. Each guide must explain the algorithm, runtime contract, data expectations, parameters, outputs, workflow composition, a concrete example, troubleshooting, limitations, and production-readiness concerns.

The implementation must preserve the current manifest-driven plugin architecture. The node registry must continue discovering packages automatically from `core/nodes/*/*/{manifest.json,node.py}`. The frontend generic inspector must render all new configuration fields from manifest metadata without hard-coded node-specific UI.

## 2. Confirmed Constraints

- Existing working-tree KNN work remains in scope and must not be discarded.
- Python runtime dependencies currently include NumPy and OpenCV but no general-purpose ML package.
- Add a pinned scikit-learn dependency to `backend/requirements.txt` for library mode.
- Manual mode may use Python standard-library functionality and NumPy, but must not call scikit-learn internally.
- Training data is stored as bounded JSON node parameters in the workflow recipe.
- This design targets small AOI demonstrations, educational use, and bounded research recipes. It does not target large training sets or confidential production datasets embedded in workflow JSON.
- Every new runtime is `DEBUG`, executes on `local-cpu`, and remains rejected by production deployment validation.
- There is no silent fallback between implementations. If the selected implementation is unavailable or invalid, execution fails with a clear error.
- Existing exact port-type matching and DAG validation rules remain unchanged.

## 3. Approaches Considered

### 3.1 Hand-written README files only

This allows maximum node-specific prose but creates 156 documents after adding five nodes, duplicates manifest contracts, is difficult to audit, and can be overwritten by the existing documentation generator.

### 3.2 One expanded generic template

This keeps documentation synchronized but cannot explain substantially different algorithms such as SSIM, watershed, logic gates, PCA, and image registration with useful examples.

### 3.3 Manifest plus node-specific documentation metadata

This is the selected approach. Manifest files remain authoritative for identity, ports, parameters, status, execution target, and capabilities. A node-specific documentation metadata file supplies algorithm explanations and examples. The generator validates and combines both sources into bilingual README files.

## 4. New Node Catalog

The catalog receives five packages after the existing KNN packages. Final catalog-order values are assigned consecutively and all tests that assert catalog cardinality are updated from 93 to 98.

| Node ID | Name | Category | Inputs | Outputs |
|---|---|---|---|---|
| `kmeans-image-segmentation` | K-means image segmentation | Segmentation | `image` | `mask`, `contours` |
| `nearest-centroid-object-classifier` | Nearest-centroid object classifier | Classification | `image`, `detections` | `classified-detections` |
| `gaussian-naive-bayes-object-classifier` | Gaussian Naive Bayes object classifier | Classification | `image`, `detections` | `classified-detections` |
| `pca-anomaly-detector` | PCA anomaly detector | Classical ML anomaly detection | `image` | `anomaly-map`, `score` |
| `logistic-object-classifier` | Logistic object classifier | Classification | `image`, `detections` | `classified-detections` |

All packages contain:

- `__init__.py`;
- `node.py` with the standard runtime constants and `execute` entry point;
- `manifest.json` version 1;
- `documentation.json` with bilingual detailed guidance;
- generated `README.md` and `README.md.vn`.

## 5. Shared Feature Contract

### 5.1 Object feature extraction

The four object classifiers, including the existing KNN classifier, use the same bounded feature extractor so their results are comparable. For each detection bounding box, the extractor calculates:

```text
[meanB, meanG, meanR, stdB, stdG, stdR, normalizedWidth, normalizedHeight, normalizedArea]
```

Color values are normalized to `[0, 1]`. Width, height, and area are normalized by image dimensions. A manifest parameter named `featureSet` selects:

- `mean-color`: first three values only, preserving compatibility with the initial KNN behavior;
- `color-statistics`: means and standard deviations;
- `color-and-geometry`: all nine values.

The initial default remains `mean-color`. Training samples must have a feature vector whose length exactly matches the selected feature set. For operator convenience, samples may instead provide `color: [B, G, R]` when `featureSet` is `mean-color`.

Detections must contain integer-convertible `x`, `y`, `width`, and `height` values. Boxes must have positive size and lie completely within the image. Runtimes copy detection mappings and never mutate input detections.

### 5.2 Supervised training sample schema

Classifier samples use one of these forms:

```json
{"label": "resistor", "color": [42, 88, 156]}
```

or:

```json
{"label": "resistor", "features": [0.16, 0.35, 0.61, 0.02, 0.03, 0.04]}
```

Requirements:

- `label` is a non-empty string;
- all features are finite numbers;
- at least two classes are required except for nearest-centroid validation tests that explicitly verify rejection;
- each class must contain enough samples for the selected algorithm;
- total JSON size remains subject to the existing bounded parameter-value validator.

### 5.3 Classified detection schema

Every object classifier returns a copied detection with:

```json
{
  "label": "resistor",
  "confidence": 0.93,
  "classScores": {"capacitor": 0.07, "resistor": 0.93}
}
```

`confidence` is always finite and clamped to `[0, 1]`. `classScores` uses normalized probabilities when the algorithm naturally provides them. For nearest-centroid, inverse-distance values are normalized. Existing KNN output keeps `neighbors` and additionally provides `classScores` for consistency.

## 6. Implementation Selection

Every new ML manifest exposes:

```json
{
  "key": "implementation",
  "kind": "select",
  "default_value": "scikit-learn",
  "options": ["scikit-learn", "manual-python"]
}
```

Rules:

- `scikit-learn` invokes the named estimator directly.
- `manual-python` invokes only project-owned NumPy/Python code.
- Both modes receive the same parsed and validated arrays.
- Randomized algorithms receive an explicit `randomSeed` parameter.
- Iterative algorithms receive bounded `maximumIterations` and `tolerance` parameters.
- No implementation may silently switch mode or adjust invalid parameters.

## 7. Algorithm Designs

### 7.1 K-means image segmentation

**Library mode:** `sklearn.cluster.KMeans`.

**Manual mode:** Lloyd's algorithm:

1. convert pixels to the selected color space;
2. optionally downsample bounded training pixels with a seeded random generator;
3. initialize centroids using seeded k-means++;
4. assign each sample to its nearest centroid;
5. recompute means;
6. stop on centroid-shift tolerance or maximum iteration count;
7. classify every pixel in bounded batches.

Parameters:

- `implementation`;
- `clusters`, integer `2..32`;
- `colorSpace`: `bgr`, `lab`, or `hsv`;
- `foregroundClusters`: JSON list of integer cluster IDs;
- `maximumTrainingPixels`, integer `100..1000000`;
- `maximumIterations`, integer `1..1000`;
- `tolerance`, positive number;
- `randomSeed`, bounded integer.

Outputs:

- `mask`: uint8 binary mask, foreground `255`;
- `contours`: external contours extracted from the mask.

Cluster IDs are deterministic for identical inputs, parameters, dependency versions, and seed, but users must not assume semantic meaning without checking centroid colors. README examples explain how to inspect cluster selection.

### 7.2 Nearest-centroid object classifier

**Library mode:** `sklearn.neighbors.NearestCentroid`.

**Manual mode:** calculate the arithmetic feature centroid of each class and choose the class with minimum distance.

Parameters:

- common `implementation`, `featureSet`, and `trainingSamples`;
- `distanceMetric`: `euclidean` or `manhattan`;
- `shrinkThreshold`, optional non-negative number. Manual mode implements centroid shrinkage or explicitly rejects unsupported combinations; it never ignores the parameter.

Confidence is the normalized inverse distance to all class centroids. Exact zero distance receives dominant finite weight using a documented epsilon.

### 7.3 Gaussian Naive Bayes object classifier

**Library mode:** `sklearn.naive_bayes.GaussianNB`.

**Manual mode:** for every class and feature, estimate mean, variance, and prior, then calculate log posterior:

```text
log P(class) - 0.5 * sum(log(2π variance) + (x - mean)^2 / variance)
```

Log-sum-exp converts posterior values to stable probabilities.

Parameters:

- common classifier parameters;
- `varianceSmoothing`, positive number;
- `classPriors`, optional JSON mapping from label to probability.

Priors must cover exactly the configured labels, be finite and positive, and sum to one within tolerance.

### 7.4 PCA anomaly detector

PCA operates on image patches rather than whole-image scalar color. The image is padded only when required by the documented border policy, divided into patches, and each patch is flattened after normalization.

Training samples are JSON vectors representing known-normal patches:

```json
{"features": [0.12, 0.13, 0.11, 0.15]}
```

**Library mode:** `sklearn.decomposition.PCA`.

**Manual mode:** center training data and apply `numpy.linalg.svd`. Keep the selected components and reconstruct each query patch.

The per-patch reconstruction mean-squared error is expanded to the patch area to produce `anomaly-map`. Overlapping values are averaged. `score` is the configured percentile of the finite anomaly map, normalized by a training reconstruction-error scale with epsilon protection.

Parameters:

- `implementation`;
- `trainingSamples`;
- `components`, integer or explained-variance number represented through separate, unambiguous parameters;
- `patchSize`, odd integer with documented upper bound;
- `patchStride`, positive integer;
- `scorePercentile`, `0..100`;
- `normalization`: `zero-one` or `standardize`;
- `maximumBatchPatches`, bounded integer.

Training and query feature dimensions must match exactly. Component count must not exceed `min(sampleCount, featureCount)`.

### 7.5 Logistic object classifier

The node performs multiclass softmax logistic regression. Binary classification uses the same multiclass contract with two labels.

**Library mode:** `sklearn.linear_model.LogisticRegression` with explicit solver, regularization, tolerance, iteration limit, and random seed.

**Manual mode:** standardized features, softmax probabilities, cross-entropy loss, L2 regularization, and bounded batch gradient descent. It uses stable softmax by subtracting each row maximum.

Parameters:

- common classifier parameters;
- `regularizationStrength`, non-negative number;
- `learningRate`, positive bounded number for manual mode;
- `maximumIterations`;
- `tolerance`;
- `fitIntercept`;
- `randomSeed`.

The README states that the two implementations optimize equivalent objectives but may not produce bit-identical coefficients or probabilities.

## 8. Runtime Module Structure

Avoid one monolithic ML runtime. Use focused modules:

```text
core/nodes/ml/
  __init__.py
  validation.py
  features.py
  voting.py
  kmeans.py
  nearest_centroid.py
  gaussian_naive_bayes.py
  pca.py
  logistic_regression.py
```

Existing KNN helpers move into or call these shared modules where doing so preserves behavior. Public plugin entry points remain small and delegate to one algorithm runtime. Shared validation owns finite-number checks, sample schemas, feature dimensions, image and detection validation, implementation selection, and confidence normalization.

This refactor must preserve existing KNN node IDs, ports, default behavior, and tests. Parameter migrations are required only if a persisted parameter key or default changes; the preferred design avoids such changes.

## 9. Documentation Metadata Design

Every `DEBUG` package must contain `documentation.json`. It is versioned independently from the runtime manifest:

```json
{
  "documentationVersion": 1,
  "en": {
    "overview": "...",
    "algorithm": ["..."],
    "inputRequirements": ["..."],
    "parameterGuidance": {"parameterKey": "..."},
    "outputInterpretation": ["..."],
    "example": {
      "goal": "...",
      "workflow": ["image-input", "node-id", "image-output"],
      "parameters": {},
      "input": "...",
      "expectedOutput": "..."
    },
    "troubleshooting": [{"symptom": "...", "cause": "...", "resolution": "..."}],
    "limitations": ["..."],
    "productionChecklist": ["..."]
  },
  "vi": {
    "overview": "...",
    "algorithm": ["..."],
    "inputRequirements": ["..."],
    "parameterGuidance": {"parameterKey": "..."},
    "outputInterpretation": ["..."],
    "example": {
      "goal": "...",
      "workflow": ["image-input", "node-id", "image-output"],
      "parameters": {},
      "input": "...",
      "expectedOutput": "..."
    },
    "troubleshooting": [{"symptom": "...", "cause": "...", "resolution": "..."}],
    "limitations": ["..."],
    "productionChecklist": ["..."]
  }
}
```

Metadata text must be genuinely node-specific. Repeating the manifest description or a generic sentence does not satisfy validation.

## 10. Generated README Structure

The generator produces these sections for each `DEBUG` node:

1. Purpose / Mục đích
2. When to use it in AOI / Khi nào nên dùng trong AOI
3. Algorithm explanation / Giải thích thuật toán
4. Runtime contract / Contract runtime
5. Ports
6. Input requirements, shape, dtype, and semantics
7. Parameters with manifest bounds plus node-specific guidance
8. Output interpretation
9. Detailed example
   - inspection goal;
   - complete node chain;
   - parameter JSON;
   - concrete input;
   - expected output;
   - how to verify it visually or numerically;
10. Troubleshooting table
11. Performance and limitations
12. Production checklist and `DEBUG` warning

For non-`DEBUG` nodes, the generator preserves current behavior unless they later receive documentation metadata. Running the generator twice must produce byte-identical files.

## 11. Coverage of Existing DEBUG Nodes

Before this extension the repository contains 73 `DEBUG` nodes:

- Acquisition: 2
- Classification: 1
- Control: 9
- Decision: 2
- Golden/reference: 10
- OpenCV tools: 43
- Pipeline: 1
- Segmentation: 1
- Visualization: 4

After adding five nodes, all 78 `DEBUG` packages receive valid bilingual documentation metadata and regenerated README files. Documentation work is grouped by category but delivered in the same implementation series so repository-wide documentation tests never remain permanently broken.

## 12. Frontend Behavior

No new custom inspector is required. Generic inspector behavior already supports:

- `select` for implementation and algorithm choices;
- `integer` and `number` bounds;
- `boolean` toggles;
- `json` text areas for samples, priors, labels, and cluster lists.

The generated parameter descriptions must explain mode-specific fields. A parameter remains visible in both modes because the current inspector has no conditional schema. Runtime validation rejects combinations that are invalid for the selected implementation. README examples show valid combinations for both modes.

## 13. Dependency and Packaging

Add a pinned scikit-learn version compatible with the pinned Python, NumPy, and deployment image. Dependency validation includes:

- clean installation from `backend/requirements.txt`;
- importing all selected estimators;
- executing one smoke prediction for each estimator;
- documenting that model objects are trained in-memory per node invocation for this bounded `DEBUG` milestone;
- no pickle or untrusted model deserialization.

The exact version is selected during implementation after checking the target Python version and package compatibility. It must be pinned exactly before the implementation is considered complete.

## 14. Validation and Error Handling

All new runtimes fail closed on:

- missing or empty images;
- unsupported image channels;
- NaN or infinite image/features/parameters;
- malformed training JSON;
- feature-dimension mismatch;
- fewer than two classes for classifiers;
- invalid detection boxes;
- unsupported implementation/parameter combinations;
- impossible cluster/component counts;
- non-convergence when the algorithm cannot provide a valid bounded result;
- unavailable scikit-learn in library mode.

Errors identify the parameter or sample index whenever possible and never include full image data or sensitive sample payloads.

## 15. Testing Strategy

### 15.1 Unit tests

For every algorithm:

- library mode predicts a deterministic synthetic example;
- manual mode predicts the same expected classes or segmentation structure;
- both modes expose the same output schema;
- probabilities/confidences are finite and bounded;
- input mappings are not mutated;
- invalid schemas, dimensions, bounds, and mode combinations fail with clear messages;
- seed-controlled output is repeatable;
- empty and degenerate inputs are covered.

Parity assertions compare semantic output and use numerical tolerances. They do not require bit-identical floating-point arrays.

### 15.2 Integration and registry tests

- Catalog, manifest, runtime, and documentation package counts become 98.
- All runtime ports match their manifests.
- API catalog exposes all five node IDs and implementation options.
- Workflow validation accepts valid graphs using the new typed ports.
- Production validation rejects every new `DEBUG` runtime.
- Existing KNN tests continue to pass.

### 15.3 Documentation tests

For every `DEBUG` package:

- `documentation.json`, `README.md`, and `README.md.vn` exist;
- metadata version and required keys are valid;
- both languages include non-empty node-specific content;
- every manifest parameter has guidance or an explicit no-guidance justification;
- example workflow contains the documented node ID and only known node IDs;
- example parameter keys exist in the manifest and values pass parameter validation;
- README contains all required sections and a fenced JSON example;
- generated README matches committed README byte-for-byte;
- no placeholder tokens such as `TBD`, `TODO`, or generic copied boilerplate remain.

### 15.4 Full verification

- Python compilation;
- complete core tests;
- relevant backend/API tests with backend dependencies installed;
- frontend tests, typecheck, and production build;
- `git diff --check`;
- GitNexus impact analysis before modifying existing symbols;
- GitNexus detect-changes after implementation.

## 16. Performance and Safety Boundaries

- Pixel algorithms operate in bounded batches.
- K-means samples at most `maximumTrainingPixels` pixels.
- PCA processes at most `maximumBatchPatches` query patches per batch.
- Iterative algorithms enforce iteration limits and tolerance.
- JSON training samples remain bounded by the existing parameter-value validator.
- README documentation clearly labels these nodes as educational/research `DEBUG` implementations.
- Production promotion requires measured target-hardware latency, memory, repeatability, class accuracy, false-call rate, escape rate, calibration stability, and dataset lineage.

## 17. Migration and Compatibility

- Existing workflow recipes remain valid.
- New nodes are opt-in and do not alter default workflows.
- Existing node IDs and port keys are not renamed.
- Existing KNN manifests retain compatible defaults and training-sample color syntax.
- Catalog cardinality assertions and documentation counts are updated atomically.
- The API response schema does not change; it receives additional catalog entries and richer documentation content only.

## 18. Acceptance Criteria

The feature is complete when:

1. all five node packages are discoverable and executable;
2. every node offers explicit `scikit-learn` and `manual-python` modes;
3. selected implementations do not silently fallback;
4. deterministic synthetic tests pass for both modes;
5. catalog and runtime registries contain 98 matching entries;
6. all 78 `DEBUG` nodes have validated bilingual metadata and detailed generated README files;
7. every generated README includes a concrete parameter and workflow example;
8. documentation regeneration is deterministic;
9. existing core/frontend behavior and KNN tests remain green;
10. dependency installation and scikit-learn smoke tests succeed in the supported backend environment;
11. GitNexus reports only expected affected symbols and flows;
12. no new node is marked production-ready.

## 19. Explicit Non-goals

- Large-dataset training pipelines.
- Persisted fitted model artifacts or model registry integration.
- GPU acceleration.
- Online/incremental learning.
- Automatic hyperparameter search.
- Conditional/custom inspector UI.
- Production promotion of any new node.
- Rewriting documentation for `TEST` contract-only nodes beyond preserving their current generated files.