# Workstation design and interface review

2026-10-31. The redesign preserves React/Vite, real scene persistence, Gaussian
rendering, saved cameras, validation, navigation, scoped review and recapture
research. Scientific extension acceptance is separate from this interface review.

## Instructions and visual direction

Read and applied Anthropic frontend-design, Vercel web-design-guidelines and
react-best-practices. Source copies/URLs/SHA hashes are retained in the local
.cache/improvement-skills intake. Sidebar-07 informed the collapsible navigation
and inset workspace structure; this is not a Next.js migration or a claim to
have installed the complete shadcn SidebarProvider. Radix Collapsible/Tooltip,
Tailwind utilities and shadcn-style variant buttons adapt that structure to the
existing app. No writing-guidelines skill was available.

The specification preceded JSX in IMPROVEMENT_PLAN.md: local Inter, graphite
surfaces, restrained blue states, consistent borders, contextual inspector,
compact engineering controls and a dominant viewport. The measured metric
summary is now a flat instrument strip, rather than six oversized cards.

## Actual visual inspection and iteration

Inspected desktop1440/1600×1000 and mobile390×844 screenshots. The initial
synthetic analytic screenshots establish functional WebGL rendering only;
framebuffer-readiness assertions wait for varied pixels rather than trusting a
loading label. Current real-TUM screenshots use a separate fresh registry with
the saved baseline-1 model and its existing18-view report. No image was generated
as a fake screenshot. Existing blur, missed detector predictions and geometry
limitations remain visible.

Reviewed saved camera, validation, experiments, navigation and scoped review at
both sizes. Based on those images: increased explanatory scope text; reduced
metric-card decoration; filtered the27-job ledger by study; expanded cramped
mobile scenario fields to two columns; stacked mobile review inputs; supplied
image aspect dimensions; and added a review-evidence loading state. Mobile
screenshots collapse the scene library through its actual control. Their
no-horizontal-overflow assertions pass, including tables with internal scroll.

Published examples: media/workstation-tum-desktop.png,
media/workstation-validation-desktop.png and media/workstation-review-mobile.png.
The screenshot capture tool records dataset, capture time and actual browser
errors under .cache/workstation-review-1/capture.json. Screenshots of a scoped
review interface do not constitute actual human approval of a scene or labels.

## Web interface guidelines audit

- frontend/src/App.tsx:74 — synchronizes view URLs/history; unsaved-edit guards
  and server conflicts remain. A skip link targets the focusable workspace.
  Deletion offers an explicit undo until save/reload.
- frontend/src/WorkbenchNav.tsx:65 — native keyboard-operable buttons, collapsed
  accessible names, aria-current, decorative SVG hiding and Radix tooltips.
- frontend/src/ReviewPanel.tsx:48 — asynchronous evidence now has a loading state;
  distinct server roles and disabled approval controls remain enforced. Added
  names/autocomplete hints to editable text fields.
- frontend/src/ReconstructionStudy.tsx:40 — abortable reads and cleanup, explicit
  loading/error/pending states, visible snapshot age, semantic table captions,
  scoped headers and a functioning study selector. No fake cancel/queue controls.
- frontend/src/EvaluationExplorer.tsx:280 and SavedView.tsx:34 — explicit aspect
  dimensions prevent image layout shifts while preserving actual source pixels.
- frontend/src/style.css:1154 — skip-link focus treatment, visible focus states,
  dark native controls, mobile touch targets and reduced-motion handling. New
  long scope notes use12px text and normal tracking. Graphite/blue semantics are
  consistent across workflow panels; error colors remain distinct.

These are targeted source and browser checks, not an accessibility certification
or screen-reader compatibility claim. External assistive-technology testing and
profiling on other GPUs/mobile devices have not been performed.

## React and performance checks

Viewer and heavier workflow panels use separate lazy/Suspense boundaries. The
current primary bundle is500.53KB versus457.23KB before the redesign dependencies;
no load-time speedup is claimed. The separate viewer/Spark chunk is3,063.04KB.
Vite/Rolldown reports large chunks and Radix client-directive warnings; build
succeeds. Six frontend unit tests pass. Presentation-export regression rejects
incomplete matrices and altered seals/analysis. Stable browser runs passed all11
existing/extended tests, including reviewer permissions, editing, navigation,
exports, URL history, undo and the synthetic annotation-review gate.

The first baseline attempt overlapped a frontend rebuild:7 passed/one404, an
invalid clean baseline. A later invocation omitted PLAYWRIGHT_BROWSERS_PATH and
failed before browser launch. Both logs remain local; neither was counted as
successful execution. The final stable-build verification is recorded in
PROGRESS.md and its evidence directory.

Sources: https://github.com/anthropics/skills/tree/main/skills/frontend-design,
https://github.com/vercel-labs/agent-skills,
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md,
https://ui.shadcn.com/blocks (sidebar-07).
