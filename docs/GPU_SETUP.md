# Local GPU worker setup

Run from `/home/phong/simready`. This environment is separate from the Python
3.12 CPU package. It uses Python 3.10 because the official precompiled gsplat
1.5.3 / PyTorch 2.4 / CUDA 12.4 Linux wheel is published for CPython 3.10.
No global CUDA toolkit is installed and no CUDA compilation is required.

```bash
uv run --frozen python scripts/setup_gpu.py
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv-gpu/bin/python workers/gsplat_worker.py witness
make storage
```

Installation performs conservative storage preflights, uses project-local caches,
and records exact installed packages. A successful import is insufficient: the
witness must execute a seeded CUDA matrix operation and Gaussian rasterization
forward/backward, returning finite nonempty output. Environment status remains
unverified until this runs and a fresh agent follows the invocation verbatim.

The declarative spec is `configs/compute-gpu.json`; provider-specific state is
`.aris/compute/local.md`. The worker consumes local JSON and NumPy artifacts;
it does not load untrusted pickle checkpoints. This pinned runtime is for local
reconstruction, not an exposed service or general-purpose model loading.
