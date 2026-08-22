# RELEASE Gate Evidence

## Scope

The smallest candidate vertical slice is the existing deterministic workflow:

```text
image input -> OpenCV preprocessing -> golden/reference or segmentation -> image output
```

The candidate is not RELEASE-ready because its current manifests use `DEBUG` and the runtime catalog has no `RELEASE` node.

## Inventory

- Node manifests: 102.
- DEBUG nodes: 82.
- TEST nodes: 20.
- RELEASE nodes: 0.
- Existing deterministic evidence: SSIM and Watershed focused tests.
- Existing real-data production evidence: not available in this workspace.

## Decision

`RELEASE` promotion is blocked. The validator must continue rejecting DEBUG/TEST nodes and incomplete evidence. No production claim is made from unit tests alone.
