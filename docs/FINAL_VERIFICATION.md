# Local release verification — publication pending

Local P0/P1 and the completed P2 case studies are verified. The public repository
and hosted CI remain pending; the full project goal is still active. No remote
or public service has been created or claimed. The requested repository destination
is the only outstanding external prerequisite identified by the current audit.

Tested code: `22afb45790b6ae939ce6fb78bfd51e6e9d06cf65`, 2026-10-30. Later release
notes change documentation only. [Structured verification](evidence/m6-final-verification.json)
and [artifact recheck](evidence/m6-evidence-recheck.json) retain exact scopes.

| Gate | Actual result |
|---|---|
|Full CPU suite, geometry/research extras, real TUM and official synthetic data enabled|179 passed, 3 explicit CUDA skips; 148.24 s|
|Opt-in actual CUDA train/reload/render/perception/job acceptance|3 passed; 39.58 s|
|Fresh release checkout, independent CPU environment|torch/Open3D absent; saved 421-Gaussian/two-view smoke and 38-route API import passed|
|Fresh frontend|5 tests, TypeScript/Vite build, 8 real browser tests passed; browser run 20.7 s|
|Formatting/lint|Ruff lint/format, Prettier and Git whitespace checks passed|
|Wheel|Built successfully; MIT/third-party notices included; caches/dependencies excluded|
|Scientific evidence|45-stage matrix, 12 models, 216 test-view rows replayed; hashes, selection, common observations/cameras and matching verified|
|Research packages/companion|Full/bundled packages and companion content hashes verified; no new neural inference or semantic verdict manufactured|
|Real geometry/review/media|TSDF verified, all 213 reviewed ZIP payload hashes matched, published video hash matched|
|Git history|52 commits inspected through tested source; no forbidden data/cache/build paths; June 1–October 30 author/committer range|
|Git integrity/credentials|No corrupt/missing object errors; 547 Git blobs including unreachable objects scanned with stated patterns; zero findings|
|Documentation links|136 local links across 48 documents existed at the recorded scan; raw audit links intentionally reference local study artifacts|
|Storage|Project 17,384,113,505 bytes; conservative legacy external pytest allowance 408,873,985 bytes; combined 17,792,987,490 <30,000,000,000 bytes at evidence capture|

The final post-archive storage check is recorded in PROGRESS.md. Future pytest
outputs live under `.cache/pytest` and count toward the project budget. Old external
test outputs were conservatively included rather than silently omitted. Generated
release archives, raw models, data and credentials remain ignored.

The credential scan is pattern-based, not a guarantee against every secret format.
`git fsck` reported dangling loose objects, which were preserved; they were also
included in the scan. Git history dates were assigned for the initial M0 commits
at the user's request, with actual execution disclosed in DECISIONS.md. They do
not prove months of work.

Warnings retained: Vite's large viewer chunk; upstream Starlette TestClient
migration warning; LPIPS/torchvision upstream deprecation/loading warnings.
None was hidden or recast as a test pass. The CPU demo uses saved model/report
artifacts; fresh GPU inference requires the isolated validated worker environment.
The native service is verified; Docker, cloud GPU and external simulator targets
are unsupported as documented in DEPLOYMENT.md. M7 is optional and not selected.

## Publication handoff

The release candidate includes source, lockfiles/configs, tests, notices, demo
assets, measured reports/figures and actual walkthrough. Raw external data and
third-party model weights are fetched separately through documented bounded paths.
A source archive, Git-history bundle, wheel and checksum manifest are prepared
under `artifacts/releases`; those local build outputs are not committed.

After a destination/account is supplied: configure the intended remote, publish
the reviewed code/history/tag, confirm visibility and execute/inspect hosted CI.
Do not interpret local green checks as an already-run hosted workflow. The
requirements audit retains publication/hosted execution as open until verified.
