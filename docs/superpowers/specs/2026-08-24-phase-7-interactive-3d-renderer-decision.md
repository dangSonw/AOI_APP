# Phase 7 interactive 3D renderer decision record

Date: 2026-08-24  
Status: **Task 7.2 automated implementation complete; browser/hardware acceptance pending**  
Scope: bounded heightmap renderer only; point-cloud and mesh remain excluded.

## 1. Decision

Use **Three.js directly, loaded through a dedicated lazy frontend chunk**, for the bounded interactive heightmap renderer proposed for Task 7.2. Keep the authenticated PNG/SVG artifact path as the always-available fallback and provide a semantic data summary outside the canvas.

Do not select raw WebGL, Plotly.js, or React Three Fiber (R3F) for the initial renderer:

- raw WebGL has the smallest framework cost but the largest implementation, reliability, interaction, and testing burden;
- Plotly.js has the strongest ready-made scientific chart features but is disproportionately large for the current bundle and gives less control over the narrow AOI contract;
- R3F adds a second React renderer and multiple runtime dependencies without removing the need to understand, bound, and test Three.js. The React 18 application would also have to pin R3F 8 rather than use current R3F 9.

This is a dependency gate, not installation approval. `three` must not be added until the user explicitly approves Task 7.2. Point-cloud and mesh contracts remain future work and do not enter runtime scope merely because the selected renderer can support them.

## 2. Current-system inventory

| Area | Observed baseline |
|---|---|
| Frontend runtime | React 18.3.1, React DOM 18.3.1, Vite 8.2.0, TypeScript strict, ES2020 and DOM targets |
| Existing graphics dependencies | None for 3D; XYFlow and Dagre are used for workflow editing |
| Production assets | Main JavaScript 574,135 bytes minified and 169,441 bytes gzip; CSS 100,000 bytes |
| Existing warning | Main JavaScript already exceeds Vite's 500 kB chunk warning threshold |
| Viewer contracts | Confusion matrix, table, and 2D plot only; `heightmap` is a descriptor kind but has no typed payload or renderer |
| Existing 3D output | Legacy/configuration-only `heightmap-output`, manifest v1, `3d-preview` capability, image-compatible artifact contract |
| Future outputs | Point-cloud and mesh are explicitly post-approval capabilities; no production contracts exist |
| Existing fallback | Authenticated, checksum-verified PNG/SVG artifact display with safe loading/error states |
| Existing client bound | Structured artifact reads are limited to 2 MiB |
| Browser target | No explicit Browserslist; ES2020 output and modern browsers are implied, but WebGL still depends on device/GPU support |

GitNexus found no existing 3D execution flow. The nearest indexed contracts are `ViewerDescriptor`, `parseVisualizationPayload`, and `StructuredVisualization`; therefore Task 7.2 would introduce a new capability rather than replace a working 3D path.

## 3. Required workloads

The renderer decision is evaluated against these separate payload families:

1. **Heightmap:** regular finite `z[row][column]` grid with physical x/y spacing and x/y/z units; invalid or missing samples are represented explicitly, never inferred from arbitrary objects.
2. **Point cloud (future):** finite packed x/y/z positions with optional scalar intensity or bounded color data.
3. **Triangle mesh (future):** finite packed vertex positions and validated integer triangle indices, with optional normals/scalar intensity.

All payloads must be platform-defined, versioned, authenticated, checksum-verified, and bounded before allocating browser or GPU resources. The renderer must never consume Python figure objects, arbitrary shader source, arbitrary URLs, or browser-supplied filesystem paths.

## 4. Options

### 4.1 Existing SVG/Canvas plus raw WebGL

**Fit:** technically supports all three workloads and has no third-party license or package cost. Existing React/SVG code can continue to provide static and semantic views.

**Costs and risks:** WebGL is intentionally low-level. The application would own shader programs, matrices, geometry buffers, camera and controls, picking, color scales, text/axes overlay, context loss/restoration, GPU resource disposal, resizing, and device-capability handling. This maximizes bespoke code and makes correctness across GPUs hardest to establish.

**Verdict:** reject for the initial slice. Retain Canvas/SVG only for fallback and semantic alternatives.

### 4.2 Plotly.js

**Fit:** first-class `surface`, `scatter3d`, and `mesh3d` traces directly match height grids, point clouds, and indexed/derived triangle meshes. It includes camera interaction, hover labels, color bars, modebar/download controls, static mode, and responsive resizing.

**License and footprint:** MIT. Registry metadata on 2026-08-24 reports `plotly.js-dist-min@3.7.0` at 4,854,193 unpacked bytes. The source package reports 98,161,486 unpacked bytes, 1,115 files, and a broad dependency graph. Unpacked package size is not identical to shipped gzip size, but it is sufficient to establish that a full distribution cannot enter the existing main chunk. A custom partial bundle could reduce cost, but adds a bespoke packaging and upgrade surface that must itself be benchmarked.

**Accessibility/testing:** built-in labels and controls are useful, but a WebGL chart still cannot be the sole accessible representation. Deterministic DOM/unit tests are possible around configuration, while visual/WebGL behavior still needs real-browser testing.

**Verdict:** reject for this narrow viewer because footprint and framework breadth outweigh the ready-made chart features. Revisit if the product later needs a broad scientific-chart platform.

### 4.3 Three.js directly

**Fit:** its renderer/scene/camera/geometry/material model covers regular surfaces, points, and indexed meshes while remaining lower-level than Plotly. `BufferGeometry`, typed attributes, `Points`, and `Mesh` allow platform bounds to map directly to GPU allocations. Controls can be imported separately as addons.

**License and footprint:** MIT, copyright Three.js authors. Registry metadata on 2026-08-24 reports `three@0.185.1` at 23,172,772 unpacked bytes across 1,195 files. This includes source, builds, examples, addons, and metadata and is not a shipped bundle measurement. ES module imports and a dedicated dynamic import allow Vite to emit a separate viewer chunk; only required addons may be imported.

**Accessibility/testing:** Three.js does not make canvas geometry semantic. AOI must own keyboard controls, visible instructions/status, a semantic min/max/dimensions/units summary, reduced-motion behavior, and the static image fallback. Pure payload-to-buffer/camera/color functions can be unit-tested without WebGL; context creation, interaction, rendering, and loss/restoration require real-browser tests.

**Operations:** direct ownership enables render-on-demand, capped device-pixel ratio, explicit disposal, bounded draw calls, and deterministic degradation. It also requires disciplined lifecycle code and actual target-hardware validation.

**Verdict:** recommend conditionally.

### 4.4 React Three Fiber

**Fit:** provides declarative React components over Three.js and supports the same primitives. Its `Canvas` supports fallback, DPR/performance options, frameloop configuration, resize handling, and unmounting. A separate test renderer and accessibility helper exist in the ecosystem.

**Compatibility and footprint:** MIT, copyright Poimandres. Current R3F 9 requires React 19; official guidance maps R3F 8 to React 18. The compatible `@react-three/fiber@8.18.0` registry package is 423,267 unpacked bytes, but it still requires Three.js and adds React reconciler, Zustand, scheduler, measurement, suspension, buffer/base64, and runtime helper dependencies.

**Trade-off:** declarative composition is valuable for a large 3D application. AOI currently needs one isolated, tightly bounded viewer, so an additional renderer/reconciler and version pin increase lifecycle and upgrade complexity without reducing the underlying Three.js/GPU responsibilities.

**Verdict:** reject for the initial slice. Revisit if multiple reusable 3D scenes make declarative composition materially valuable.

## 5. Comparative scorecard

Scores are relative for this AOI slice: 5 is best. Bundle score assumes lazy loading where feasible.

| Criterion | Weight | Raw WebGL | Plotly.js | Three.js | R3F |
|---|---:|---:|---:|---:|---:|
| Heightmap/point/mesh fit | 20 | 5 | 5 | 5 | 5 |
| Bounded performance control | 20 | 5 | 3 | 5 | 4 |
| Implementation/maintenance cost | 15 | 1 | 5 | 3 | 3 |
| Bundle/dependency discipline | 15 | 5 | 1 | 4 | 2 |
| React 18 integration | 10 | 3 | 3 | 4 | 2 |
| Testability | 10 | 2 | 3 | 4 | 4 |
| Accessibility/fallback control | 10 | 3 | 3 | 4 | 4 |
| **Weighted total / 5** | **100** | **3.65** | **3.35** | **4.30** | **3.55** |

Licensing does not distinguish the three third-party options: Plotly.js, Three.js, and R3F are MIT. All require preservation of their license notice in distributions that include substantial portions.

## 6. Benchmark datasets fixed before implementation

The Task 7.2 benchmark must generate deterministic fixtures from formulas and fixed seeds so no proprietary manufacturing data is needed:

| Dataset | Shape | Purpose |
|---|---:|---|
| H-S | 128 × 128 = 16,384 samples | low-end/smoke heightmap |
| H-M | 256 × 256 = 65,536 samples | default acceptance heightmap |
| H-L | 512 × 512 = 262,144 samples | maximum accepted heightmap |
| P-M (future) | 100,000 points | nominal point-cloud interaction |
| P-L (future) | 250,000 points | maximum accepted point cloud |
| M-M (future) | 100,000 vertices, 200,000 triangles | nominal mesh |
| M-L (future) | 250,000 vertices, 500,000 triangles | maximum accepted mesh |

Heightmaps use a deterministic plane plus Gaussian bump, sinusoidal texture, and a bounded missing-sample mask. Point data uses a fixed-seed stratified surface sample. Mesh data uses deterministic indexed grids with known bounds and normals. Each fixture records schema version, dimensions/counts, byte length, SHA-256, min/max, units, and seed/formula revision.

Task 7.2 may initially implement only H-S/H-M/H-L. P-* and M-* remain predeclared future benchmarks, not approval to add their runtime contracts.

## 7. Acceptance budgets fixed before implementation

Measurements use a production build, a cold navigation to the lazy viewer, browser performance marks, and at least five runs after one warm-up. Report median and worst run, browser/version, OS, CPU, GPU, devicePixelRatio, viewport, power mode, and whether hardware acceleration is active. Automated CI may validate contracts and fallback, but cannot substitute for the hardware matrix.

### 7.1 Size and loading

- `three` and 3D viewer code must be absent from the initial application chunk and requested only when an accepted 3D descriptor is opened.
- Main entry gzip growth: **≤ 10 KiB** from the pre-Task-7 baseline.
- Dedicated 3D viewer chunk: **≤ 180 KiB gzip**; all newly loaded 3D JavaScript for first open: **≤ 220 KiB gzip**.
- No CDN runtime dependency; package and lockfile must pin an approved version.
- Lazy-load or renderer failure must leave the authenticated fallback usable.

### 7.2 Heightmap performance

- H-M first interactive frame: **≤ 1.5 s median, ≤ 2.5 s worst** on reference desktop; **≤ 3.0 s worst** on minimum hardware.
- H-L first interactive frame: **≤ 3.0 s worst** on reference desktop; otherwise reject safely or render an explicitly disclosed deterministic downsample.
- During a five-second orbit of H-M: **≥ 45 FPS median desktop, ≥ 30 FPS median minimum hardware**, with no long task over 200 ms caused by viewer interaction.
- Idle viewer uses render-on-demand and must not sustain a continuous animation loop.
- Resize response settles within **250 ms** without recreating duplicate contexts.

### 7.3 Resource and reliability

- Payload limits: H-L maximum; future P-L/M-L maximum. Reject counts/dimensions, non-finite values, malformed indices, byte lengths, or allocation estimates over their bound before GPU allocation.
- Device pixel ratio is capped at **2** and may degrade to 1 on minimum hardware.
- Estimated viewer-owned CPU plus GPU data for H-L must be **≤ 64 MiB** excluding the browser/runtime; measured JS heap must return to within **10 MiB** of pre-open baseline after five open/close cycles and forced test GC where supported.
- Exactly one active WebGL context per visible viewer. Geometry, material, texture, controls, listeners, animation frames, and renderer are disposed on replacement/unmount.
- Simulated `webglcontextlost` shows a text status and the static fallback without reload; restoration may recreate from already validated data. Context creation failure follows the same fallback path.
- No uncaught console error and no WebGL error during the acceptance journey.

### 7.4 Accessibility and interaction

- Canvas is never the only representation. Title, dimensions, axes, units, min/max, missing-sample count, and fallback image/table or summary are available in semantic DOM.
- All actions have visible labels and keyboard operation. Required minimum: focus viewer, arrow-key orbit, `+`/`-` zoom, `0` reset camera, and Escape/blur exit without a keyboard trap.
- Pointer gestures have documented keyboard equivalents; focus indication and status updates are visible and screen-reader-addressable.
- Honor `prefers-reduced-motion`; no automatic rotation. Color scale is not the sole carrier of state and is accompanied by numeric values/legend.
- Static fallback remains available when JavaScript, dynamic import, WebGL, GPU acceleration, or interaction is unavailable.

### 7.5 Browser and hardware matrix

- Latest stable Chrome and Edge on Windows/Linux with hardware acceleration.
- Latest stable Firefox on Windows/Linux.
- Latest stable Safari on macOS where hardware is available.
- Minimum profile: integrated GPU, 4 logical CPU cores, 8 GiB RAM, 1920 × 1080 viewport at DPR 1.
- Reference profile: integrated or entry discrete GPU, 8 logical CPU cores, 16 GiB RAM.
- At least one software-rendered/disabled-WebGL run must prove fallback behavior; it is not expected to meet interactive FPS targets.

## 8. Proposed Task 7.2 boundary after approval

1. Add a pinned `three` dependency only after license/security review and explicit approval.
2. Add a strict, versioned, bounded heightmap schema in core and frontend; do not overload the 2D plot schema.
3. Preserve authenticated artifact verification and 2 MiB transport bound unless an independently reviewed bound change is required.
4. Implement a dynamically imported Three.js heightmap adapter with render-on-demand, explicit disposal, context failure/loss handling, and no arbitrary shaders or URLs.
5. Add semantic summary, static fallback, keyboard controls, reduced-motion behavior, and responsive sizing.
6. Validate H-S/H-M/H-L and the browser/hardware matrix against this record. Record raw measurements and build chunk sizes as acceptance evidence.
7. Do not add point-cloud/mesh output nodes or schemas in Task 7.2 without a separate scope decision.

## 9. Rejected shortcuts

- Do not place a 3D library in the eager main bundle.
- Do not use a CDN script or unpinned dependency.
- Do not render unvalidated JSON or accept user shaders/material code.
- Do not claim accessibility from canvas labels alone.
- Do not silently truncate, sample, or downscale; any deterministic degradation must be declared in status and evidence.
- Do not infer production GPU/hardware support from headless CI.

## 10. Sources consulted

Accessed 2026-08-24:

- MDN, **WebGL: 2D and 3D graphics for the web**: WebGL is a hardware-accelerated canvas API available in modern browsers, subject to device support; context creation/loss/restoration are explicit lifecycle concerns. https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API
- MDN, **WebGL best practices**: eliminate errors, query limits/extensions, eagerly delete resources, avoid blocking calls, budget per-pixel VRAM, batch draws, consider smaller back buffers, cap high-DPI cost, and handle context lifecycle. https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/WebGL_best_practices
- Plotly.js 3D charts and figure references for `surface`, `scatter3d`, and `mesh3d`. https://plotly.com/javascript/3d-charts/ ; https://plotly.com/javascript/reference/surface/ ; https://plotly.com/javascript/reference/scatter3d/ ; https://plotly.com/javascript/reference/mesh3d/
- Plotly.js configuration/responsive guidance. https://plotly.com/javascript/configuration-options/ ; https://plotly.com/javascript/responsive-fluid-layout/
- Plotly.js MIT license. https://github.com/plotly/plotly.js/blob/master/LICENSE
- Three.js fundamentals and installation: renderer, scene graph, camera, geometry/material responsibilities, npm/build-tool recommendation, ES modules, and separately imported addons. https://threejs.org/manual/en/fundamentals.html ; https://threejs.org/manual/en/installation.html
- Three.js MIT license. https://github.com/mrdoob/three.js/blob/dev/LICENSE
- R3F official introduction/installation: React renderer over Three.js; R3F 8 pairs with React 18 and R3F 9 with React 19; ecosystem testing/a11y packages are separate. https://github.com/pmndrs/react-three-fiber/blob/master/docs/getting-started/introduction.mdx ; https://github.com/pmndrs/react-three-fiber/blob/master/docs/getting-started/installation.mdx
- R3F MIT license and repository security page (no SECURITY.md detected at evaluation time). https://github.com/pmndrs/react-three-fiber/blob/master/LICENSE ; https://github.com/pmndrs/react-three-fiber/security
- npm registry metadata queried without installation for `three@0.185.1`, `plotly.js@3.7.0`, `plotly.js-dist-min@3.7.0`, and `@react-three/fiber@8.18.0`.

## 11. Approval gate

Task 7.1 is complete. The next action requires explicit user approval of:

- adding pinned `three` as the sole new 3D runtime dependency;
- implementing only the bounded heightmap slice first;
- enforcing the datasets and budgets in this record;
- retaining static/semantic fallback as acceptance-critical behavior.

Until that approval, no package file or application source should change for Task 7.2.

## 12. Task 7.2 implementation evidence

The user explicitly approved the pinned dependency, accepted the GitNexus HIGH/CRITICAL integration warnings, and approved production Dashboard integration. Task 7.2 added exact runtime `three@0.185.1` plus dev-only `@types/three@0.185.0`; both are MIT. The post-install production audit reports zero known vulnerabilities.

Implemented scope:

- strict `aoi.heightmap.v1` contracts in Python and TypeScript, limited to 2–512 rows/columns, positive finite spacing, a bounded unit, finite-or-null samples, and at least one valid sample;
- matching `heightmap` descriptor validation and capability-driven Dashboard routing while preserving the legacy static placeholder when no typed descriptor exists;
- a dedicated lazy Three.js chunk, render-on-demand only, DPR capped at 2, one indexed geometry, explicit listener/observer/geometry/material/renderer/context cleanup, responsive resize, context loss/restoration status, and safe context-creation failure;
- pointer, wheel, arrow-key, `+`/`-`, `0`, Home, and Escape controls without automatic motion;
- a semantic DOM summary that remains outside the canvas and reports grid, valid/missing samples, range, spacing, and units; authenticated PNG/SVG artifact handling remains unchanged.

Automated evidence on the available CI host:

- TDD RED was observed for missing heightmap contracts/model and GREEN ended at 19 focused tests passing.
- Full frontend: 48 files / 140 tests pass; TypeScript and production build pass.
- Deterministic H-S/H-M/H-L pure model construction passes; the three fixtures complete in 109 ms total on this host. H-L packed positions plus indices remain below 10 MiB; positions, indices, and computed normals with CPU/GPU copies are estimated around 24 MiB, below the 64 MiB viewer-owned budget.
- Production build: eager main JavaScript 579.26 kB / 172.99 kB gzip, approximately +5.13 kB / +3.55 kB gzip from baseline; lazy `HeightmapCanvas` 518.85 kB / 130.00 kB gzip. Both gzip growth budgets pass and Three.js remains absent from the eager chunk.
- Python production compile and direct heightmap valid/non-finite assertions pass. The configured `/usr/bin/python3` has no pytest module, so the Python pytest file could not be executed in this environment.
- `git diff --check` passes. Final GitNexus aggregate change detection remains CRITICAL at 41 indexed files, 224 symbols, and 294 flows because the uncommitted worktree combines Phases 1–7 and retains known broad false-positive edges.

Claim boundary: first-frame latency, interaction FPS, resize timing, browser WebGL/context-loss behavior, five-cycle heap recovery, and the Chrome/Edge/Firefox/Safari minimum/reference hardware matrix were not measured on real target browsers/hardware. Task 7.2 code and automated gates are complete, but interactive 3D must remain **conditionally accepted** until that manual matrix is recorded.