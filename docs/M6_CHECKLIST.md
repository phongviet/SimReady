# M6 local gates verified — publication pending

- [x] Finish M5 companion integrity review and report; retain real-study negative outcome.
- [x] Audit every PLAN.md interface and deliverable against current implementation; see REQUIREMENTS_AUDIT.md.
- [x] Queued authenticated import HTTP path and persistent job polling.
- [x] Queued reconstruction HTTP path, controlled artifact downloads and actual CUDA acceptance.
- [x] Supplied-camera render HTTP path; actual CUDA import/train/render/download acceptance.
- [x] Fresh installed CPU wheel smoke without torch/Open3D; saved model/report and API import.
- [x] Fresh-checkout frontend/API demo, including saved-camera and missing-GPU fallback.
      See FRESH_INSTALL.md; own installed dependencies/registry/build,7 browser tests.
- [x] End-to-end current-source regression, browser visual inspection and failure handling; see FINAL_VERIFICATION.md.
- [x] Measured render throughput/resolution, evaluation throughput and API p50/p95.
      See BENCHMARK_RESULTS.md and raw samples; historical training timing is separately labeled.
- [x] Current CLI/API/setup/data/license documentation and architecture diagram.
- [x] Walkthrough script and short actual demo recording;50.8s real-TUM clip, playback/export verified.
- [x] docs/CV_EVIDENCE.md with only measured/implemented claims and traceable sources.
- [x] Final local storage/Git/history/credential/export review and requirement-by-requirement audit.
- [ ] Publish to the user-specified public repository and inspect hosted CI; destination/account pending.

Local state at entry: no remote configured; hosted CI/public deployment have not
run. Existing local review approval is an automated acceptance fixture, not human
endorsement. M7 is explicitly optional and conditional on M6, per PLAN.md.

Current implemented HTTP areas: health, scenes/assets/revisions, proxy edits,
evaluation queue/jobs/reports, research reports, navigation, readiness, role-bound
submission/review/audit and reviewed exports. Import/reconstruction/render HTTP paths have dedicated subprocess/CUDA acceptance;
they do not yet automatically register a new editable scene and collider.
