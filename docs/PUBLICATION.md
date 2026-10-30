# Public repository and hosted acceptance

Repository: [phongviet/SimReady](https://github.com/phongviet/SimReady), verified
public through GitHub's repository API. The user supplied its SSH destination;
it was empty before publication. Existing local history was pushed without force.

[Hosted acceptance run41002820745](https://github.com/phongviet/SimReady/actions/runs/41002820745)
completed successfully on source `f007390b6ec9e26d1ac1ddb03acbc9a97056472c`:

- CPU unit/integration tests and lint/format.
- Official synthetic RGB-D sample acquisition/import tests.
- Independent Open3D geometry acceptance.
- Frontend formatting/unit/build and eight actual browser tests.

[Structured API observation](evidence/m6-publication.json) records the actual job
URLs/conclusions. Earlier hosted runs41002058943 and41002399387 failed; they are
not counted as successful. Their diagnostics exposed a missing `.cache` parent
for pytest basetemp. A configure hook now creates that parent without weakening
assertions. A fresh cold-checkout test passed42checks in9.09s before the successful
hosted rerun. Ubuntu24.04 is pinned to match the tested local base; that runner
pin alone did not fix the missing-parent bug.

Current-source local checks supplement hosted coverage: three actual CUDA tests
passed in91.17s; real TUM validation passed in4.07s. CUDA training/perception and
the full real capture are local acceptance, not hosted GPU jobs. The separately
measured performance/scientific results retain their original source pins and
scopes; test runtimes here are not new performance benchmarks.

The final `v0.0.1` source tag includes the cold-checkout fix. Candidate tags and
frozen research history remain intact. Documentation-only publication updates
run through the same hosted workflow. Check the live
[workflow page](https://github.com/phongviet/SimReady/actions/workflows/ci.yml)
for the latest branch/tag result; recorded runs above identify their exact source.

This publishes source, tests, licenses, reproducibility entry points, measured
examples and walkthrough. The web application is launched locally using README;
no public hosted API/service, cloud GPU, Docker runtime or external simulator is
claimed. M7 remains optional and unselected. Local automated review fixtures are
not independent human endorsement or safety certification.
