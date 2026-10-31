# Workstation shell review

2026-10-31. This is the first UI slice, not acceptance of the complete improvement
brief. The actual application was exercised with its learned analytic synthetic
scene. No screenshot is labeled as a real capture or a new research result.

## Visual inspection

Desktop1440×1000: sidebar workflow navigation, scene evidence and inspector frame
the main viewport. Removed decorative milestone/header claims; preserved scene
controls and role-based editing. Mobile390×844: icon navigation, collapsed scene
library, main viewport and stacked inspector fit without horizontal overflow.
Actual screenshots: media/workstation-desktop.png and workstation-mobile.png.

The first mobile screenshot was captured before the re-mounted WebGL viewport
had rendered visible pixels. The regression now waits for varied framebuffer
pixels before both screenshots; the second inspected mobile screenshot contains
the actual splats and proxy. This was a capture-readiness issue, not evidence of
successful rendering from a loading label alone.

The initial attempted baseline run overlapped a frontend rebuild:7 passed and the
research route returned404 while dist was replaced. It is not a valid clean
baseline. A stable-build rerun passed all9 tests, followed by a targeted visual
regression pass. Neither failure was deleted or counted as acceptance.

## Applied design instructions

Anthropic frontend-design: viewport-led subject-specific hierarchy, compact
Inter typography, graphite tokens, restrained blue states and explicit design
plan before JSX. Sidebar-07 informed collapsible navigation/inset structure;
existing React/Vite logic was retained. Radix Collapsible/Tooltip, Tailwind and
shadcn-style variant controls were added incrementally.

Vercel React practices: viewer remains lazy; evaluation, research, simulation and
review now have separate lazy chunks and a contextual Suspense status. The new
shell's primary bundle is511.75KB versus457.23KB before dependencies; no load-time
speedup is claimed. Radix client directives generate Vite/Rolldown warnings in
this client-only app; build succeeds. The separate Spark chunk remains large.

## Web interface guidelines audit

frontend/src/App.tsx - added skip link, focusable workspace target, named library
control and expanded state; existing async alerts/status and unsaved-edit guards
remain. Corrected stale empty-state milestone text.

frontend/src/WorkbenchNav.tsx - native buttons, labels for collapsed icons,
aria-current, decorative SVG hiding and Radix keyboard/focus tooltips.

frontend/src/SceneCard.tsx - supplied thumbnail dimensions to reduce layout shift.

frontend/src/style.css - dark native controls, visible focus, touch-sized mobile
navigation, reduced-motion override, overflow-free tested mobile layout and
consistent semantic surface tokens. Existing error/warning colors remain.

Open: workflow states are not yet URL-synchronized; destructive object deletion
still needs an undo/confirmation interaction; several legacy form inputs lack
names/autocomplete hints; full per-view visual audit remains. These are outstanding
findings, not a completed accessibility certification. Mobile screenshots currently
cover the workspace; validation/research/simulation-specific visual refinements
remain to be reviewed.

Sources read: https://github.com/anthropics/skills/tree/main/skills/frontend-design,
https://github.com/vercel-labs/agent-skills,
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md,
https://ui.shadcn.com/blocks (sidebar-07).
