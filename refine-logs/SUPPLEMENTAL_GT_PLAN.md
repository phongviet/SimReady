# M5 labeled-object companion — protocol before measurement

This is a new, controlled synthetic E1 companion, planned after inspecting the
completed real TUM study. It does not tune or replace that study or its negative
recapture outcome. No result is assumed.

Generate one bench-shaped rigid object from explicitly authored box primitives,
plus a floor/backdrop, using analytic ray intersections. Ground-truth object
masks, boxes, RGB, metric depth and camera poses come from this geometry alone;
no detector or reconstruction output defines the labels. All visible bench
parts belong to one object instance. Verify the bench category against the
already pinned detector category table. This is procedural-domain truth,
not human annotations or evidence about real object detection accuracy.

Freeze28camera poses spanning a70degree arc, looking at the bench center.
Use128x96pinhole images and canonical meters/Y-up/OpenCV camera axes.
Contiguous14train/4validation/4candidate/6test blocks; every view must contain
a valid visible object mask. Failure to satisfy this is an input error, not a
reason to silently drop views. Save label/mask/geometry hashes before training.

Train one genuine gsplat model from only14training RGB-D observations, seed42,
1200fresh steps, width128, initial<=5000/max12000Gaussians, SH1 and depth loss.05.
Reuse the ready local GPU runtime; no model/detector fitting on test. Render and
evaluate the exact6test poses using the existing fixed SSDLite/LPIPS protocol.
Keep raw real/rendered predictions, checkpoint, source/environment/input hashes
and complete per-view outputs. Preserve negative/empty prediction results.

Compute bench-class precision/recall at confidence.5 and class-gated IoU.5.
Compute single-class101-recall-point interpolated AP50 from all saved post-floor
bench predictions; label it a custom synthetic AP50, never official COCO mAP.
Other predicted categories remain in raw outputs, separate from this class-only
metric. Report FP/FN and matched counts for each domain and view.

E1 comparison: show image metrics and real/render prediction disagreement beside
true per-domain detection errors and their rendered-minus-reference changes.
Use Spearman only with at least3finite, nonconstant pairs; otherwise null with
the exact reason. Show cases where agreement coexists with shared errors if
observed. Six correlated poses of one authored object support a mechanism /
integration demonstration, not population significance or detector generalization.

Acceptance: numeric ray/depth/mask/box tests, no GT dependence on model outputs,
actual learned reconstruction and fixed-view inference, preserved labels and raw
predictions, reproducible metric definitions, report/figure and honest failure
discussion. Reserve300MB and check the whole project remains below30GB.
