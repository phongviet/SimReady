# Verified local deployment and unsupported targets

The supported deployment is a single-machine loopback service with filesystem
artifacts, SQLite and subprocess jobs. It is verified under Ubuntu24.04/WSL2;
CPU API/UI and optional isolated GPU worker environments are separate.

```bash
make setup
make demo
make studio
```

Open http://127.0.0.1:8000. `--demo` provisions private local credentials under
the selected registry. Use the Builder/Reviewer token in the UI; do not commit
or share that file. It is a local-role fixture, not production IAM. Read-only
assets are served from registered hash-verified locations. No arbitrary public
file upload, public network binding, TLS or multi-tenant deployment is provided.

`simready api serve --root ... --port ...` uses the same built frontend. CPU
viewing/editing/report inspection/navigation/review works without torch/Open3D.
Fresh training/render/evaluation requires the separately validated `.venv-gpu`;
missing workers produce persistent failed jobs without damaging saved reports.
See FRESH_INSTALL.md and GPU_SETUP.md for actual acceptance evidence and versions.

## Container and cloud boundary

PLAN.md prefers Docker Compose, but the current WSL Docker command reports:
“docker could not be found in this WSL2 distro”; Docker Desktop WSL integration
is unavailable. No container image, Compose runtime or GPU container witness has
run. The tested native deployment above is the explicit fallback. Unexecuted
container recipes are not supplied as if they were release evidence.

A container deployment would need an enabled engine, pinned build/runtime images,
project-local cache/asset storage accounting and separate GPU worker validation.
Do not infer compatibility from the native CUDA witness. Remote/cloud GPU,
public hosting and Isaac/CARLA integration are not configured. M7 is optional and
conditional on the core shipping gate; no external simulator claim is made.

## Repository and CI

GitHub Actions defines CPU, official-sample, optional geometry and frontend/browser
checks. Their local equivalents are verified; hosted execution has not occurred
because this checkout has no Git remote. A public repository/service URL is not
claimed. Final publication needs a destination/account and the completed local
release audit; local delivery and externally hosted publication are separate facts.
