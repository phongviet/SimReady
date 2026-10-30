# M6 shipping gates — completion remains unproven

- [x] Finish M5 companion integrity review and report; retain real-study negative outcome.
- [ ] Audit every PLAN.md interface and deliverable against current implementation.
- [x] Queued authenticated import HTTP path and persistent job polling.
- [x] Queued reconstruction HTTP path, controlled artifact downloads and actual CUDA acceptance.
- [x] Supplied-camera render HTTP path; actual CUDA import/train/render/download acceptance.
- [x] Fresh installed CPU wheel smoke without torch/Open3D; saved model/report and API import.
- [x] Fresh-checkout frontend/API demo, including saved-camera and missing-GPU fallback.
      See FRESH_INSTALL.md; own installed dependencies/registry/build,7 browser tests.
- [ ] End-to-end current-source regression, browser visual inspection and failure handling.
- [x] Measured render throughput/resolution, evaluation throughput and API p50/p95.
      See BENCHMARK_RESULTS.md and raw samples; historical training timing is separately labeled.
- [ ] Current CLI/API/setup/data/license documentation and architecture diagram.
- [ ] Walkthrough script and short actual demo recording.
- [ ] docs/CV_EVIDENCE.md with only measured/implemented claims and traceable sources.
- [ ] Final storage/Git/history/credential/export review and requirement-by-requirement audit.

Local state at entry: no remote configured; hosted CI/public deployment have not
run. Existing local review approval is an automated acceptance fixture, not human
endorsement. M7 is explicitly optional and conditional on M6, per PLAN.md.

Current implemented HTTP areas: health, scenes/assets/revisions, proxy edits,
evaluation queue/jobs/reports, research reports, navigation, readiness, role-bound
submission/review/audit and reviewed exports. Import/reconstruction/render HTTP paths have dedicated subprocess/CUDA acceptance;
they do not yet automatically register a new editable scene and collider.
