"""Measure the real TUM local pipeline and loopback read API; preserve raw samples."""

import argparse
import fcntl
import json
import os
import platform
import subprocess
import threading
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import uvicorn

from simready.api.app import create_app
from simready.data.dataset import atomic_dataset, sha256_file, write_json
from simready.evaluation.config import EvaluationConfig
from simready.evaluation.runner import evaluate, verify_evaluation_binding, verify_inputs
from simready.scene.demo import seed_demo
from simready.scene.store import SceneStore
from simready.storage import PROJECT_ROOT, check_budget


def api_samples(root):
    store = SceneStore(root)
    seed_demo(store)
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(root), host="127.0.0.1", port=0, log_level="warning", access_log=False
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 20
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("benchmark API did not start")
            time.sleep(0.02)
        port = server.servers[0].sockets[0].getsockname()[1]
        measurements = {}
        for endpoint in ("/api/v1/health", "/api/v1/scenes", "/api/v1/scenes/analytic-demo"):
            samples = []
            for i in range(105):
                start = time.perf_counter()
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}{endpoint}", timeout=10
                ) as response:
                    body = response.read()
                    assert response.status == 200
                    json.loads(body)
                elapsed = time.perf_counter() - start
                if i >= 5:
                    samples.append(elapsed)
            measurements[endpoint] = {
                "seconds": samples,
                "p50_ms": float(np.percentile(samples, 50) * 1000),
                "p95_ms": float(np.percentile(samples, 95) * 1000),
                "samples": len(samples),
                "warmup_requests": 5,
            }
        return {
            "scope": (
                "single-client sequential loopback TCP reads using urllib (new "
                "connection/request), JSON parse included; analytic demo registry; no "
                "TLS/auth/mutations or network load"
            ),
            "endpoints": measurements,
        }
    finally:
        server.should_exit = True
        thread.join(timeout=20)
        if thread.is_alive():
            raise RuntimeError("benchmark server did not terminate")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=Path, default=PROJECT_ROOT / "data/scenes/tum-fr1-desk")
    parser.add_argument(
        "--artifact", type=Path, default=PROJECT_ROOT / "artifacts/scenes/tum-fr1-desk/baseline-1"
    )
    parser.add_argument(
        "--renders", type=Path, default=PROJECT_ROOT / "artifacts/renders/tum-fr1-desk-test-1"
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    check_budget(500_000_000)
    args.scene, args.artifact, args.renders = (
        p.resolve() for p in (args.scene, args.artifact, args.renders)
    )
    verify_inputs(args.scene, args.artifact, args.renders)
    pins = {
        str(p.relative_to(PROJECT_ROOT)): sha256_file(p)
        for p in (
            args.scene / "manifest.json",
            args.artifact / "artifact.json",
            args.renders / "renders.json",
            PROJECT_ROOT / "configs/compute-gpu.json",
            PROJECT_ROOT / "configs/perception-weights.json",
            PROJECT_ROOT / "scripts/run_benchmark.py",
            PROJECT_ROOT / "workers/render_benchmark.py",
        )
    }
    git = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    with atomic_dataset(args.out, 500_000_000) as stage:
        write_json(
            stage / "frozen-inputs.json",
            {
                "created_at": datetime.now(UTC).isoformat(),
                "sha256": pins,
                "git_commit": git,
                "git_dirty": dirty,
            },
        )
        lock_path = PROJECT_ROOT / "artifacts/studio/evaluation-worker.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            with (stage / "render-worker.log").open("w") as log:
                subprocess.run(
                    [
                        str(PROJECT_ROOT / ".venv-gpu/bin/python"),
                        str(PROJECT_ROOT / "workers/render_benchmark.py"),
                        "--artifact",
                        str(args.artifact.resolve()),
                        "--renders",
                        str(args.renders.resolve()),
                        "--out",
                        str(stage / "render.json"),
                    ],
                    env={**os.environ, "OMP_NUM_THREADS": "4"},
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                )
            start = time.perf_counter()
            evaluate(args.scene, args.artifact, args.renders, stage / "evaluation")
            elapsed = time.perf_counter() - start
            verify_evaluation_binding(
                stage / "evaluation", args.scene, args.artifact, args.renders, EvaluationConfig()
            )
        views = len(json.loads((stage / "evaluation/views.json").read_text()))
        # views.json is a list of paired observations; throughput counts pairs, not images.
        write_json(stage / "api.json", api_samples(stage / "api-registry"))
        for name, digest in pins.items():
            if sha256_file(PROJECT_ROOT / name) != digest:
                raise ValueError("benchmark input changed")
        write_json(
            stage / "summary.json",
            {
                "schema_version": "1.0",
                "git_commit": git,
                "git_dirty": dirty,
                "python": platform.python_version(),
                "platform": platform.platform(),
                "cpu": platform.processor(),
                "render": json.loads((stage / "render.json").read_text()),
                "evaluation": {
                    "scope": (
                        "single end-to-end fresh evaluation of saved real TUM test renders; "
                        "includes worker startup/model loading/staging/inference/metrics/report "
                        "writes, excludes reconstruction/render generation; no repeats or "
                        "confidence interval"
                    ),
                    "view_pairs": views,
                    "wall_seconds": elapsed,
                    "view_pairs_per_second": views / elapsed,
                },
                "api": json.loads((stage / "api.json").read_text()),
                "source_model_training": json.loads(
                    (args.artifact / "worker-result.json").read_text()
                ),
                "inputs_sha256": pins,
            },
        )
    print(args.out / "summary.json")
    check_budget()


if __name__ == "__main__":
    main()
