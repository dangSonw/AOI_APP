# Research and Models Dashboard-First Redesign

## Goal

Make the Research and Models workspaces understandable to a first-time AOI Studio operator while preserving every existing API, data contract, and lifecycle operation.

## Shared information architecture

Both pages use the same visual hierarchy:

1. A page introduction explains the job performed in the workspace.
2. A compact three-step guide explains the normal workflow.
3. Summary cards expose the current state at a glance.
4. The primary workspace contains clearly grouped controls and records.
5. Raw JSON, hashes, manifests, and lifecycle evidence remain available as progressively disclosed details.

The cross-page workflow is explicit: run training in Workflow, evaluate the result in Research, register a verified artifact in Models, promote it to candidate, and promote an accepted candidate to champion.

## Research workspace

The page introduction describes Research as the place to find, inspect, reproduce, and compare training runs. The guide teaches users to search, review metrics and diagnostics, then select at least two runs for comparison.

The search is a single labelled form so Enter submits naturally. Summary cards distinguish total, completed, and failed runs. The compare action reports the current selection count and remains disabled until two runs are selected.

Each run card prioritizes:

- a readable status badge with text and color;
- run identity, creation time, execution target, revision, and seed;
- metrics in a scannable grid;
- failure diagnostics when applicable.

Parameters/environment, artifacts, and reproducibility details remain secondary. Raw JSON is collapsed by default and bounded when expanded. Long IDs and hashes wrap without forcing horizontal page scrolling.

## Models workspace

The page introduction describes Models as the governed registry of immutable artifacts and deployment aliases. The guide teaches users to register a verified artifact, validate/promote it to candidate, then promote an accepted version to champion. Candidate, champion, and rollback are explained in plain language.

Registration remains one form but is visually divided into three numbered stages:

1. Choose a new or existing destination model.
2. Select a completed source run.
3. Select a verified artifact and register the immutable version.

The registry summary remains visible above the model list. Each model card prioritizes its description, current candidate/champion aliases, version count, and latest version. Version details expose compatibility and validation evidence in a responsive grid. Source-run navigation and lifecycle history are secondary actions. Candidate/champion promotion is visually distinct from rollback, and all existing reason/confirmation behavior is retained.

## Visual system

Use existing CSS variables and native HTML controls. Add no dependency. White panels, subtle shadows, stronger typography, blue informational accents, green success accents, amber running/candidate accents, and red failure/destructive accents provide hierarchy while remaining consistent with AOI Studio.

Cards use comfortable spacing and a bounded content width. At narrow widths, guides, summaries, forms, and action rows become single-column. Status meaning is always communicated in text, not color alone.

## Accessibility

- Keep one `h1` per workspace and use ordered heading levels.
- Use native forms, labels, fieldsets, buttons, details, and lists.
- Preserve keyboard operation and visible focus styles.
- Use `role="status"` and `role="alert"` for asynchronous feedback.
- Keep disabled-action explanations visible in nearby text.
- Meet usable touch-target sizing and avoid horizontal page overflow.

## Compatibility and testing

No service call, request payload, response type, reducer behavior, or parent callback changes. Existing tests continue to verify all current capabilities. New server-rendered component tests assert the introductory guidance, three-step workflow, status semantics, progressive disclosure, and lifecycle terminology. Validation includes focused tests, the full frontend suite, TypeScript checking, production build, diff checking, browser inspection at desktop and narrow widths, and an accessibility audit when the browser connector is available.

## Out of scope

- Backend filtering, pagination, or new analytics
- A multi-route wizard
- New dependencies or a design-system migration
- Translating the complete application UI
- Changing model governance policy or research contracts

## Approved full-width and Help extension

Research and Models remove their redundant page eyebrow, `h1`, and subtitle so their operational controls begin immediately below the studio toolbar. Both pages fill the available workspace width instead of using the previous 1480 px content cap. The three-step guides remain because they provide concise task guidance without displacing the primary content significantly.

The brand header removes the `Inspection workspace` context label. A new Help destination appears in the System explorer group before Settings. Help is a full-width, dashboard-style workspace with Vietnamese as its default language and an immediate Vietnamese/English toggle persisted under the browser-local `aoi-help-language` key.

Help content is maintained as structured bilingual data separate from its renderer. It covers Dashboard, Hardware, Camera rig, Workflow, Dataset, Database, Research, Models, and Settings, with an extended Workflow → Research → Models operating guide, lifecycle terminology, checklists, and troubleshooting. Each major section links directly to its corresponding workspace. Responsive inline HTML/CSS/SVG illustrations explain the application journey, workflow graph, research evidence, and model aliases without introducing image hosting or a new dependency. Illustrations have accessible names or captions, and never rely on color alone.