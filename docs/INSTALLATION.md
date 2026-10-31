# Installation

## Interactive demonstration

Use Python3.12, uv and Node.js20.19–20.x or22.12+. The repository locks Python and
frontend dependencies. From a checkout:

```bash
make setup
make demo
make studio
```

The API prints its local address and account-setup information. The demo contains
an actual trained analytic synthetic scene, saved camera views and measured sample
reports. It can be inspected without CUDA. A WebGL2-capable browser displays the
Gaussian representation; saved-camera views provide the fallback.

Local account tokens are created under the chosen registry directory; follow
[account setup](REVIEW_PROTOCOL.md). Tokens stay local and are not committed.

## Reconstruction and optional tools

New reconstruction/rendering/perception runs use the separate GPU environment in
[GPU_SETUP.md](GPU_SETUP.md). The documented worker was measured on Linux/WSL2
with a GTX1660Ti6GB, Python3.10, PyTorch2.4.1+cu124 and gsplat1.5.3. This records a
validated configuration, not a guarantee that arbitrary scenes fit that hardware.
Training budgets, image resolution and Gaussian limits are explicit configuration.

Optional CPU extras:

```bash
uv sync --frozen --extra geometry       # Open3D collision geometry
uv sync --frozen --extra research       # Scientific plots
uv sync --frozen --extra annotations    # pycocotools approved-reference AP50
```

These commands do not install GPU packages into the CPU environment. Include
multiple extras together if needed. Dataset and generated artifact sizes depend
on sequence length, sampled resolution and experiment count. Acquisition commands
perform configured resource preflight and bounded-download checks; keep their
source records when moving artifacts between machines. Raw datasets/models remain
outside Git. Developer-specific resource policy is described in AGENTS.md rather
than as an installation requirement.

## Development checks

```bash
make test
make browser-setup
make test-browser
make test-gpu  # Requires the separately validated GPU worker
```

GPU tests skip explicitly in the CPU-only suite. Browser checks require an installed
Playwright Chromium. See [CLI](CLI.md) for import, training and evaluation commands,
[dataset protocol](DATASET_PROTOCOL.md) for coordinate/split conventions, and
[annotation protocol](ANNOTATION_PROTOCOL.md) for actual human-review requirements.
The historical environment inventory in ENVIRONMENT.md records earlier development
measurements and is not a current installation-size specification.
