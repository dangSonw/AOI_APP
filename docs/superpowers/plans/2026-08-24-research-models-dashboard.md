# Research and Models Dashboard-First Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the visually flat Research and Models pages with accessible dashboard-first workspaces that teach the existing workflow without changing its contracts.

**Architecture:** Keep state, service calls, and lifecycle handlers in the existing pages. Restructure only their semantic JSX and add a shared page-level CSS vocabulary in `global.css`; no component abstraction or dependency is needed for two pages.

**Tech Stack:** React 18, TypeScript 5.6, native HTML, CSS, Vitest server rendering.

## Global Constraints

- Preserve all endpoints, payloads, response types, reducer behavior, and parent callbacks.
- Add no dependency and no backend behavior.
- Keep one `h1`, ordered headings, labelled native controls, text status labels, visible focus, and responsive layouts.
- Keep raw JSON, hashes, manifests, and advanced evidence available but progressively disclosed.
- Do not commit because the existing worktree contains combined uncommitted Phase 1–7 work.

---

### Task 1: Research dashboard hierarchy

**Files:**
- Modify: `frontend/src/pages/ResearchPage.test.tsx`
- Modify: `frontend/src/pages/ResearchPage.tsx`

**Interfaces:**
- Consumes: `ResearchRun`, `searchResearchRuns`, `transitionResearchComparison` unchanged.
- Produces: semantic Research markup using `workspace-intro`, `workspace-guide`, `summary-card`, `status-badge`, and existing interaction handlers.

- [ ] **Step 1: Write the failing test**

Add assertions for `Find the right run`, `Review the evidence`, `Compare outcomes`, `2 selected`, `Status: Completed`, and the explanatory page subtitle.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- src/pages/ResearchPage.test.tsx`
Expected: FAIL because the new guidance and semantic status copy do not exist.

- [ ] **Step 3: Write minimal implementation**

Restructure the header/search into a native form, add the three-step ordered guide, turn counters into labelled cards, add explicit selection help, and make each run card's primary identity/metrics readable while retaining details, manifest, artifacts, and diagnostics.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- src/pages/ResearchPage.test.tsx`
Expected: all Research tests pass.

### Task 2: Models guided registry

**Files:**
- Modify: `frontend/src/pages/ModelsPage.test.tsx`
- Modify: `frontend/src/pages/ModelsPage.tsx`

**Interfaces:**
- Consumes: all existing registration, promotion, rollback, history, and source-run handlers unchanged.
- Produces: semantic Models markup using the same dashboard vocabulary plus numbered registration stages and lifecycle alias explanations.

- [ ] **Step 1: Write the failing test**

Add assertions for `Register an artifact`, `Promote a candidate`, `Choose a champion`, `Candidate is a version under review`, `1 model`, and the three registration stage headings.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- src/pages/ModelsPage.test.tsx`
Expected: FAIL because the guidance, terminology, and stage headings do not exist.

- [ ] **Step 3: Write minimal implementation**

Add the page introduction, guide and glossary; divide the existing form into three visual stages without changing fields; improve model/version card summaries, alias badges and action grouping while preserving confirmation behavior.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- src/pages/ModelsPage.test.tsx`
Expected: all Models tests pass.

### Task 3: Shared professional responsive visual system and verification

**Files:**
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Consumes: class names introduced by Tasks 1 and 2 and existing studio CSS variables.
- Produces: desktop and narrow-width layouts with no horizontal page overflow.

- [ ] **Step 1: Add the minimum shared CSS**

Replace the flat Research block with bounded page width, intro typography, step cards, summary cards, badges, elevated record cards, clear details rows, registration stages, grouped actions, and narrow-width rules. Reuse current variables and native focus handling.

- [ ] **Step 2: Run focused and full automated verification**

Run: `cd frontend && npm test -- src/pages/ResearchPage.test.tsx src/pages/ModelsPage.test.tsx && npm test && npm run typecheck && npm run build`
Expected: all tests pass, TypeScript exits 0, production build exits 0.

- [ ] **Step 3: Inspect the rendered application**

Use the authenticated running app to inspect Research and Models at desktop and narrow widths, then run an accessibility audit. If the browser connector is unavailable, report this exact limitation rather than claiming visual acceptance.

- [ ] **Step 4: Verify change scope**

Run: `git diff --check`, `node .gitnexus/run.cjs detect_changes`, and review `git diff --stat` plus the edited files.
Expected: no whitespace errors; changes are limited to the approved documentation, page tests, pages, CSS, and generated build output if tracked.

### Task 4: Full-width operational focus and studio brand cleanup

**Files:**
- Modify: `frontend/src/pages/ResearchPage.test.tsx`
- Modify: `frontend/src/pages/ResearchPage.tsx`
- Modify: `frontend/src/pages/ModelsPage.test.tsx`
- Modify: `frontend/src/pages/ModelsPage.tsx`
- Modify: `frontend/src/components/StudioChrome.test.tsx`
- Modify: `frontend/src/components/StudioChrome.tsx`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Consumes: existing Research/Models state, handlers, services, and shell props unchanged.
- Produces: full-width pages without redundant introductions and a brand containing only the AOI Studio mark/name.

- [ ] Write SSR assertions that the removed copy is absent.
- [ ] Run focused tests and confirm they fail against the old markup.
- [ ] Remove only the specified intro/context elements and the 1480 px width cap.
- [ ] Run focused tests and confirm they pass.

### Task 5: Bilingual illustrated Help workspace

**Files:**
- Create: `frontend/src/pages/help-content.ts`
- Create: `frontend/src/pages/HelpPage.tsx`
- Create: `frontend/src/pages/HelpPage.test.tsx`
- Modify: `frontend/src/types/workspace.ts`
- Modify: `frontend/src/components/ProjectExplorer.tsx`
- Modify: `frontend/src/components/ProjectExplorer.test.tsx`
- Modify: `frontend/src/pages/WorkspacePage.tsx`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Produces: `HelpPage({ onOpenWorkspace }: { onOpenWorkspace: (view: WorkspaceView) => void })` and structured `HELP_CONTENT` for `vi` and `en`.
- Persists: `aoi-help-language` with values `vi` or `en`; missing/unavailable storage falls back to `vi`.
- Consumes: `WorkspaceView` extended with `'help'` and existing `requestViewChange`.

- [ ] Write the failing Help SSR/navigation tests.
- [ ] Run focused tests and confirm Help is missing.
- [ ] Add bilingual structured content, search, locale toggle, inline illustrations, section navigation, and workspace actions.
- [ ] Wire Help into Project Explorer, page title, and WorkspacePage rendering.
- [ ] Add responsive CSS and verify focused tests, full suite, typecheck, build, browser layouts, diff check, and GitNexus change scope.