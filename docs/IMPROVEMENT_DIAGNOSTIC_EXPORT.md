# Fixed post-run diagnostic export

Defined2026-10-31 while the primary matrix is still running, before inspecting
its new test scores. This supplements the sealed analyzer without changing its
source or any primary output. It cannot select a training policy or authorize
reruns. Export into a new directory with source/input/output SHA-256 manifests.

- Recompute aggregate means and sample SD from every measured row, compare with
  the primary aggregate JSON, and report numeric disagreement rather than repair
  the primary output. Recheck complete split/view IDs and paired frame identity.
- Publish quality/runtime and quality/allocated-memory SVG plots from final-budget
  seed means, with seed-level points and mean/sample-SD summaries. Separate each
  dataset and evaluation split. Runtime is ordered local optimizer timing.
- Export all paired per-view LPIPS, PSNR, SSIM, depth MAE and support deltas.
  Compare selected versus matched at3600 on each new capture, and refinement1800
  and3000 versus900 at each saved checkpoint on original desk validation.
- For each new capture at seed42, select the three largest signed selected-minus-
  matched LPIPS differences, tie by frame ID. Show the SAME pose's real image,
  matched L1 render, selected L1+SSIM render and selected residual. If all deltas
  are negative, describe these as least improvement, not regressions.
- For original desk validation seed42 at3600, select the three largest signed
  refine3000-minus-refine900 LPIPS differences. Show real and all three schedules
  at each selected identical pose. Include sign and exact values in the index.
- Extract convergence records from every final model's immutable training log:
  actual completed updates, training objectives, counts, optimizer time and
  allocator observations. Curves are training diagnostics, not held-out evidence.
- Retain every primary worst-LPIPS montage and identify dynamic objects, pose
  extrapolation, missing support or artifacts only as qualitative observations.
  Do not infer causality or quantified object accuracy from appearance.

Ground-truth perception remains pending explicit human approval. No new diagram,
plot, detector proxy or AI inspection can substitute for approved annotations.
