# Inspected development environment

Initial M0 observations, 2026-10-29; training/GPU work had not yet started at that point.

| Item | Observed value |
|---|---|
| OS | Ubuntu 24.04.4 LTS, x86_64 WSL2, kernel 6.18.33.2-microsoft-standard-WSL2 |
| CPU | Intel Core i7-10750H, 6 cores / 12 logical CPUs |
| WSL memory | 11 GiB RAM, 16 GiB swap (`free -h`) |
| GPU | NVIDIA GeForce GTX 1660 Ti, 6144 MiB VRAM |
| Driver | nvidia-smi 615.71.08, KMD 616.92 |
| Driver CUDA compatibility | UMD 13.4 reported by nvidia-smi; not a tested CUDA runtime |
| CUDA toolkit | `nvcc` unavailable; libcuda driver present, no libcudart listed by ldconfig |
| Python | 3.12.3 |
| uv | 0.12.2 |
| Node / npm | 20.20.2 / 10.8.2 |
| Git | 2.43.0; no configured user identity or preexisting repository |
| Filesystem | 1007 GiB total, 292 GiB used, 664 GiB available at inspection |
| Initial project size | 60 KiB (`du -sh .`) |

System Python had NumPy 1.26.4, Pillow 10.2.0, pytest 7.4.4. Project dependencies
use an isolated `.venv` and the exact checked-in uv lock. Docker was located
but its daemon was not tested or required. No global configuration was changed.

Tested project versions: NumPy 2.5.4, Pillow 12.3.0, Pydantic 2.14.1, pytest 9.2.0,
Ruff 0.17.3. Frontend: React/ReactDOM 19.3.1, TypeScript 7.0.2, Vite 8.3.5,
Vitest 4.1.12. Exact transitive versions are in the checked-in lockfiles.
The final project including caches/dependencies/data occupies about 0.30 GB;
`make storage` reports conservative accounting and is the authoritative live check.

## M3 tested additions (2026-10-29)

Core: SciPy1.18.1 and scikit-image0.26.0, exact versions in uv.lock.
GPU spec3db6217d adds torchvision0.19.1+cu124, LPIPS0.1.4, SciPy1.15.3 and
tqdm4.67.1 to the existing Python3.10.20/torch2.4.1+cu124/gsplat1.5.3+pt24cu124
environment. Official SSDLite320 COCO and SqueezeNet1.1 plus LPIPSv0.1 calibration
weights are SHA-256 pinned. Both actual CUDA witnesses and fresh-agent documented
invocations passed. Real18-view evaluation and actual queued analytic evaluation
ran successfully. No hosted CI or external simulator was run.
