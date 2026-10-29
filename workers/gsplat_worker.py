"""Isolated CPython 3.10 GPU process. JSON/NPZ protocol, no pickle model loading.

Algorithms: gsplat 1.5.3 rasterization and DefaultStrategy (Apache-2.0).
This file provides canonical RGB-D initialization, optimization and artifact IO;
it does not reimplement the CUDA rasterizer or densification algorithm.
"""

import argparse
import importlib.metadata
import json
import math
import platform
import time
from pathlib import Path

import numpy as np
import torch
from gsplat import rasterization
from gsplat.strategy import DefaultStrategy
from PIL import Image

SH_C0 = 0.28209479177387814


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def raster(params, view, k, width, height, degree):
    return rasterization(
        means=params["means"],
        quats=params["quats"],
        scales=torch.exp(params["scales"]),
        opacities=torch.sigmoid(params["opacities"]),
        colors=torch.cat([params["sh0"], params["shN"]], dim=1),
        viewmats=view[None],
        Ks=k[None],
        width=width,
        height=height,
        sh_degree=degree,
        packed=True,
        render_mode="RGB+ED",
        near_plane=0.05,
        far_plane=20.0,
    )


def witness():
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; do not claim reconstruction succeeded")
    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)
    x = torch.randn(8, 8, device="cuda")
    assert torch.isfinite(x @ x.T).all()
    means = torch.tensor([[0.0, 0.0, 2.0]], device="cuda", requires_grad=True)
    image, alpha, _ = rasterization(
        means=means,
        quats=torch.tensor([[1.0, 0.0, 0.0, 0.0]], device="cuda"),
        scales=torch.full((1, 3), 0.1, device="cuda"),
        opacities=torch.tensor([0.8], device="cuda"),
        colors=torch.tensor([[1.0, 0.2, 0.1]], device="cuda"),
        viewmats=torch.eye(4, device="cuda")[None],
        Ks=torch.tensor([[[30.0, 0.0, 15.5], [0.0, 30.0, 15.5], [0.0, 0.0, 1.0]]], device="cuda"),
        width=32,
        height=32,
        packed=True,
        render_mode="RGB+ED",
    )
    image[..., :3].sum().backward()
    torch.cuda.synchronize()
    assert image.shape == (1, 32, 32, 4)
    assert torch.isfinite(image).all() and torch.isfinite(means.grad).all()
    assert alpha.max().item() > 0.1
    print(
        "WITNESS "
        + json.dumps(
            {
                "device": torch.cuda.get_device_name(),
                "torch": torch.__version__,
                "cuda": torch.version.cuda,
                "gsplat": importlib.metadata.version("gsplat"),
                "shape": list(image.shape),
                "alpha_max": alpha.max().item(),
                "backward_finite": True,
            }
        ),
        flush=True,
    )


def save_ply(params, path):
    """Graphdeco SH PLY: raw log scales, opacity logits, normalized wxyz quaternions."""
    values = {k: v.detach().cpu().numpy() for k, v in params.items()}
    count = len(values["means"])
    quats = values["quats"]
    quats = quats / np.linalg.norm(quats, axis=1, keepdims=True).clip(1e-12)
    # Graphdeco stores SH coefficients channel-major (all R, then G, then B).
    rest = values["shN"].transpose(0, 2, 1).reshape(count, -1)
    columns = [
        values["means"],
        np.zeros((count, 3)),
        values["sh0"][:, 0],
        rest,
        values["opacities"][:, None],
        values["scales"],
        quats,
    ]
    names = ["x", "y", "z", "nx", "ny", "nz"] + [f"f_dc_{i}" for i in range(3)]
    names += [f"f_rest_{i}" for i in range(rest.shape[1])]
    names += ["opacity"] + [f"scale_{i}" for i in range(3)] + [f"rot_{i}" for i in range(4)]
    data = np.column_stack(columns).astype("<f4")
    header = "ply\nformat binary_little_endian 1.0\n" + f"element vertex {count}\n"
    header += "".join(f"property float {name}\n" for name in names) + "end_header\n"
    with path.open("wb") as out:
        out.write(header.encode("ascii"))
        out.write(data.tobytes())


def train(job_path):
    job = json.loads(job_path.read_text())
    output = job_path.parent
    config = job["config"]
    torch.manual_seed(config["seed"])
    torch.cuda.manual_seed_all(config["seed"])
    rng = np.random.default_rng(config["seed"])
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    with np.load(output / "training.npz", allow_pickle=False) as data:
        initial = {key: data[key].copy() for key in ("means", "scales", "colors")}
        images = torch.from_numpy(data["images"].copy()).to("cuda")
        depths = torch.from_numpy(data["depths"].copy()).to("cuda")
        views = torch.from_numpy(data["viewmats"].copy()).to("cuda")
        intrinsics = torch.from_numpy(data["Ks"].copy()).to("cuda")
    count = len(initial["means"])
    degree = config["sh_degree"]
    quats = torch.zeros((count, 4), device="cuda")
    quats[:, 0] = 1
    params = torch.nn.ParameterDict(
        {
            "means": torch.nn.Parameter(torch.tensor(initial["means"], device="cuda")),
            "scales": torch.nn.Parameter(torch.tensor(np.log(initial["scales"]), device="cuda")),
            "quats": torch.nn.Parameter(quats),
            "opacities": torch.nn.Parameter(torch.full((count,), -0.5, device="cuda")),
            "sh0": torch.nn.Parameter(
                torch.tensor((initial["colors"] - 0.5) / SH_C0, device="cuda")[:, None, :]
            ),
            "shN": torch.nn.Parameter(
                torch.zeros((count, (degree + 1) ** 2 - 1, 3), device="cuda")
            ),
        }
    )
    rates = {
        "means": 0.00016,
        "scales": 0.005,
        "quats": 0.001,
        "opacities": 0.05,
        "sh0": 0.0025,
        "shN": 0.000125,
    }
    optimizers = {
        key: torch.optim.Adam([value], lr=rates[key], eps=1e-15) for key, value in params.items()
    }
    strategy = DefaultStrategy(
        refine_start_iter=config["refine_start"],
        refine_stop_iter=config["refine_stop"],
        refine_every=config["refine_every"],
        reset_every=10000,
        grow_grad2d=0.0008,
        prune_scale3d=0.5,
    )
    strategy.check_sanity(params, optimizers)
    state = strategy.initialize_state(scene_scale=2.0)
    height, width = images.shape[1:3]
    with (output / "training-log.jsonl").open("w") as log:
        for step in range(config["iterations"]):
            index = int(rng.integers(len(images)))
            rendered, alpha, info = raster(
                params, views[index], intrinsics[index], width, height, degree
            )
            strategy.step_pre_backward(params, optimizers, state, step, info)
            rgb_loss = torch.abs(rendered[0, ..., :3] - images[index]).mean()
            valid = (depths[index] > 0) & (alpha[0, ..., 0] > 0.01)
            depth_loss = (
                torch.abs(rendered[0, ..., 3][valid] - depths[index][valid]).mean()
                if valid.any()
                else rgb_loss * 0
            )
            loss = rgb_loss + config["depth_loss_weight"] * depth_loss
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite training loss at iteration {step}")
            loss.backward()
            for optimizer in optimizers.values():
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
            # Strategy can at most double count; stop growth before exceeding budget.
            if len(params["means"]) * 2 > config["max_gaussians"]:
                strategy.grow_grad2d = math.inf
            strategy.step_post_backward(params, optimizers, state, step, info, packed=True)
            if not 0 < len(params["means"]) <= config["max_gaussians"]:
                raise RuntimeError("Gaussian count violates configured budget")
            if step % 10 == 0 or step == config["iterations"] - 1:
                row = {
                    "step": step,
                    "rgb_l1": float(rgb_loss.detach()),
                    "depth_l1_m": float(depth_loss.detach()),
                    "gaussians": len(params["means"]),
                }
                log.write(json.dumps(row) + "\n")
                log.flush()
                print(json.dumps(row), flush=True)
    torch.cuda.synchronize()
    if not all(torch.isfinite(value).all() for value in params.values()):
        raise RuntimeError("non-finite learned parameters")
    np.savez_compressed(
        output / "gaussians.npz",
        **{key: value.detach().cpu().numpy() for key, value in params.items()},
    )
    save_ply(params, output / "gaussian.ply")
    write_json(
        output / "worker-result.json",
        {
            "backend": "gsplat",
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "gsplat": importlib.metadata.version("gsplat"),
            "python": platform.python_version(),
            "gpu": torch.cuda.get_device_name(),
            "peak_vram_allocated_bytes": torch.cuda.max_memory_allocated(),
            "peak_vram_reserved_bytes": torch.cuda.max_memory_reserved(),
            "training_seconds": time.perf_counter() - started,
            "iterations": config["iterations"],
            "initial_gaussians": count,
            "final_gaussians": len(params["means"]),
            "sh_degree": degree,
            "loss": "RGB L1 + configured weight * valid axial-depth L1 (meters)",
            "determinism": "Seeded; CUDA floating-point kernels may not be bitwise deterministic.",
        },
    )


def render(job_path):
    job = json.loads(job_path.read_text())
    output = job_path.parent
    with np.load(job["checkpoint"], allow_pickle=False) as arrays:
        params = {key: torch.from_numpy(arrays[key].copy()).to("cuda") for key in arrays.files}
    with torch.no_grad():
        for camera in job["cameras"]:
            view = torch.tensor(camera["viewmat"], device="cuda", dtype=torch.float32)
            k = torch.tensor(camera["K"], device="cuda", dtype=torch.float32)
            pixels, alpha, _ = raster(
                params, view, k, camera["width"], camera["height"], job["sh_degree"]
            )
            pixels = pixels[0].cpu().numpy()
            rgb = (pixels[..., :3].clip(0, 1) * 255).round().astype(np.uint8)
            name = camera["frame_id"]
            Image.fromarray(rgb).save(output / f"{name}.png")
            np.save(output / f"{name}-depth.npy", pixels[..., 3], allow_pickle=False)
            np.save(
                output / f"{name}-alpha.npy", alpha[0, ..., 0].cpu().numpy(), allow_pickle=False
            )
    print(json.dumps({"rendered_views": len(job["cameras"])}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["witness", "train", "render"])
    parser.add_argument("job", nargs="?", type=Path)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for gsplat; use saved renders for CPU smoke mode")
    {"witness": witness, "train": lambda: train(args.job), "render": lambda: render(args.job)}[
        args.action
    ]()
