"""Warm synchronized gsplat render timing; excludes disk IO and model loading."""

import argparse
import importlib.metadata
import json
import platform
import time
from pathlib import Path

import numpy as np
import torch
from gsplat_worker import raster


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--renders", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    metadata = json.loads((args.artifact / "artifact.json").read_text())
    cameras = json.loads((args.renders / "renders.json").read_text())["cameras"]
    with np.load(args.artifact / "gaussians.npz", allow_pickle=False) as arrays:
        params = {key: torch.from_numpy(arrays[key].copy()).cuda() for key in arrays.files}
    prepared = [
        (
            torch.tensor(c["viewmat"], dtype=torch.float32, device="cuda"),
            torch.tensor(c["K"], dtype=torch.float32, device="cuda"),
            c["width"],
            c["height"],
        )
        for c in cameras
    ]
    durations = []
    with torch.no_grad():
        for i in range(10):
            pixels, alpha, _ = raster(
                params, *prepared[i % len(prepared)], metadata["config"]["sh_degree"]
            )
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        for i in range(180):
            camera = prepared[i % len(prepared)]
            torch.cuda.synchronize()
            start = time.perf_counter()
            pixels, alpha, _ = raster(params, *camera, metadata["config"]["sh_degree"])
            torch.cuda.synchronize()
            durations.append(time.perf_counter() - start)
        assert torch.isfinite(pixels).all() and torch.isfinite(alpha).all()
    result = {
        "schema_version": "1.0",
        "scope": (
            "warm sequential synchronized RGB+ED rasterization; excludes startup, "
            "checkpoint loading, transfers, image encoding, HTTP and browser"
        ),
        "warmup_frames": 10,
        "measured_frames": len(durations),
        "camera_count": len(cameras),
        "resolutions": sorted({f"{c['width']}x{c['height']}" for c in cameras}),
        "seconds_per_frame": durations,
        "frames_per_second": len(durations) / sum(durations),
        "p50_ms": float(np.percentile(durations, 50) * 1000),
        "p95_ms": float(np.percentile(durations, 95) * 1000),
        "gaussians": len(params["means"]),
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
        "gpu": torch.cuda.get_device_name(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "gsplat": importlib.metadata.version("gsplat"),
        "python": platform.python_version(),
        "finite_output_witness": True,
    }
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
