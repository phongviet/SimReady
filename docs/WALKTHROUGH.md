# Recorded real-scene walkthrough

[Play the50.8-second recording](media/tum-walkthrough.webm) ·
[chapters](evidence/m6-walkthrough-chapters.json) ·
[hashes and acceptance evidence](evidence/m6-walkthrough.json)

Recorded2026-10-30 from clean source `3907377`, at1440×1000 in headless Chromium
with software WebGL. This is actual product UI acting on the genuine saved TUM
fr1 desk Gaussian model and its18-view measured report. It does not show live
training; the saved input/reconstruction comparison appears before editing.
No responses, renders or navigation outcomes were mocked.

| Approximate time | Action / suggested narration |
|---|---|
|0:00|“This is the saved real TUM reconstruction, not an analytic fixture.”|
|0:03|“The aligned real image, learned render and residual expose blur and missed predictions.”|
|0:05|“Orbit inspection uses Spark; scientific measurements use frozen gsplat views.”|
|0:09|“Insert and save a metric rigid box. Its mesh and collider share this transform.”|
|0:11|“Base-render evaluation stays frozen; inserted-object perception is unverified.”|
|0:22|“The observed coarse-map simulator reaches its goal over1.15m, with unknown cells blocked.”|
|0:35|“The Builder submits this limited regression and acknowledges measured failures.”|
|0:46|“A distinct automated local Reviewer records a scoped decision and builds the verified export.”|

The robot/route replay is simulated. Approval is an automated local-role fixture
for this known-map regression and listed reference cameras; it is not independent
human endorsement, detection accuracy or safety certification. The visible QA
retains48 reference predictions, zero rendered predictions and incomplete geometry.

The final50.8s WebM (10,120,465bytes) played to completion in Chromium. Decoded
comparison, navigation and review frames were visually inspected. There were
zero page errors. The route was1.150m with zero replay collisions. Its exported
ZIP contains213 individually hash-verified payloads, source revision3 and
approved revision5. SHA-256 for the published clip:
`ee09273afc9afe8b36505e2d600d137f615e1eaa2d055b6c8f1302cb318897ce`.
Earlier recordings/registries are retained ignored locally; only final attempt4
is published. Framing checks exposed and prompted a real overlay-order fix.

## Repeat the recording

First prepare the real model, independent TSDF, test renders and report using the
README and GPU/evaluation protocols. The preparation script expects these exact
local paths (all generated; never overwrite prior outputs):

- `data/scenes/tum-fr1-desk`
- `artifacts/scenes/tum-fr1-desk/baseline-1`
- `artifacts/geometry/tum-fr1-desk/tsdf-1`
- `artifacts/renders/tum-fr1-desk-test-1`
- `artifacts/evaluations/tum-fr1-desk-test-1`

Build/install the frontend and Chromium (`make browser-setup` if needed). Then:

```bash
make storage
npm --prefix frontend run build
uv run --frozen python scripts/prepare_walkthrough.py --root artifacts/walkthrough-new
uv run --frozen simready api serve --root artifacts/walkthrough-new --port 8002
```

In a second terminal:

```bash
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/playwright" node frontend/scripts/record_walkthrough.mjs \
  --root artifacts/walkthrough-new --out artifacts/walkthrough-recording-new \
  --url http://127.0.0.1:8002
make storage
```

Use a new registry and output directory each time. The script saves raw WebM,
chapter timestamps and screenshots; it fails if expected actual UI states do not
appear. Stop the API with Ctrl-C when finished. Tokens remain private and are
switched via browser storage, never displayed in the clip. GPU inference is not
needed to replay these saved assets. The recording server was stopped after this run.

Reference/derived TUM imagery: **TUM RGB-D benchmark, freiburg1_desk**, Sturm et al.,
IROS2012, [CC BY4.0](https://creativecommons.org/licenses/by/4.0/),
[source and attribution](https://cvg.cit.tum.de/data/datasets/rgbd-dataset).
The video includes derived renders/overlays and product UI; the full raw dataset
and third-party weights are not bundled. See DATASET_PROTOCOL.md for source hashes.
