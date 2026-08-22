# Node Benchmark Inventory

## Deterministic benchmark contract

Each benchmark fixture must record node ID, package version, image shape, dtype, input checksum, elapsed-time metric, and resource limit. Benchmarks are acceptance evidence only when executed in the target deployment environment.

## Current inventory

| Family | Packages | Runtime status | Evidence |
|---|---:|---|---|
| Golden/reference | 10 | DEBUG | focused deterministic, cancellation, oversized-input tests |
| OpenCV tools | 52 | DEBUG except camera-undistortion | focused Watershed/runtime tests |
| Visualization | 5 | DEBUG | contract/documentation inventory |
| Pipeline/evidence | 9 | DEBUG/TEST | manifest and registry contract tests |
| Other algorithm families | 26 | TEST/DEBUG | no RELEASE acceptance evidence |

## Decision

Phase 9 remains incomplete. The repository has package-level manifests and shared image contracts, but not every prioritized family has an independently recorded target-environment benchmark and RELEASE acceptance evidence.
