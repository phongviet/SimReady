"""Pinned GPU detector + LPIPS inference; runs only in isolated Python3.10 env."""

import hashlib
import importlib.metadata
import json
import os
import sys
from pathlib import Path

import lpips
import numpy as np
import torch
import torchvision
from PIL import Image
from torchvision.models.detection import (
    SSDLite320_MobileNet_V3_Large_Weights,
    ssdlite320_mobilenet_v3_large,
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def models(config):
    if (
        torch.__version__ != "2.4.1+cu124"
        or torchvision.__version__ != config["torchvision_version"]
    ):
        raise ValueError("perception environment differs from pinned torch/torchvision versions")
    if importlib.metadata.version("lpips") != config["lpips_version"]:
        raise ValueError("LPIPS package differs from protocol")
    torch.manual_seed(config["seed"])
    torch.cuda.manual_seed_all(config["seed"])
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    weights = SSDLite320_MobileNet_V3_Large_Weights.COCO_V1
    weight_root = Path(torch.hub.get_dir()) / "checkpoints"
    files = [
        weight_root / weights.url.split("/")[-1],
        weight_root / "squeezenet1_1-b8a52dc0.pth",
        Path(lpips.__file__).parent / "weights/v0.1/squeeze.pth",
    ]
    pinned = json.loads(
        (Path(__file__).resolve().parents[1] / "configs/perception-weights.json").read_text()
    )
    for path in files:
        if not path.is_file() and path.parent == weight_root:
            weight_root.mkdir(parents=True, exist_ok=True)
            url = "https://download.pytorch.org/models/" + path.name
            torch.hub.download_url_to_file(
                url, str(path), hash_prefix=pinned[path.name], progress=False
            )
    observed = {p.name: digest(p) for p in files}
    if observed != pinned:
        raise ValueError("perception weights differ from pinned SHA-256 digests")
    detector = (
        ssdlite320_mobilenet_v3_large(
            weights=weights,
            weights_backbone=None,
            progress=False,
            score_thresh=config["detector_score_threshold"],
            nms_thresh=config["detector_nms_threshold"],
            topk_candidates=config["detector_topk_candidates"],
            detections_per_img=config["detector_detections_per_img"],
        )
        .eval()
        .cuda()
    )
    perceptual = lpips.LPIPS(net="squeeze", version="0.1", verbose=False).eval().cuda()
    metadata = {
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "lpips": importlib.metadata.version("lpips"),
        "numpy": np.__version__,
        "device": torch.cuda.get_device_name(),
        "cuda": torch.version.cuda,
        "weights_sha256": observed,
        "categories": weights.meta["categories"],
        "detector_preprocessing": "RGB float32 [0,1]; model fixed 320x320 resize; mean=.5 std=.5",
        "lpips_preprocessing": "RGB float32 [-1,1]; evaluation resolution; spatial=False",
        "raw_predictions": (
            "Post model score floor/NMS/top-k; before evaluation confidence threshold"
        ),
    }
    return detector, perceptual, metadata


def tensor(path):
    with Image.open(path) as image:
        a = np.array(image.convert("RGB"), dtype=np.float32) / 255
    return torch.from_numpy(a).permute(2, 0, 1).contiguous().cuda()


def lpips_input(image):
    return image * 2 - 1


def predictions(output):
    return [
        {"box": box, "score": score, "label": int(label)}
        for box, score, label in zip(
            output["boxes"].cpu().tolist(),
            output["scores"].cpu().tolist(),
            output["labels"].cpu().tolist(),
            strict=True,
        )
    ]


def run(job_path):
    job = json.loads(job_path.read_text())
    detector, perceptual, metadata = models(job["config"])
    rows = []
    with torch.inference_mode():
        for camera in job["views"]:
            a, b = (
                tensor(job_path.parent / camera["real"]),
                tensor(job_path.parent / camera["rendered"]),
            )
            # Separate calls have identical batch shape and preprocessing for both domains.
            real, rendered = detector([a])[0], detector([b])[0]
            distance = perceptual(lpips_input(a[None]), lpips_input(b[None])).item()
            if not np.isfinite(distance):
                raise ValueError("non-finite LPIPS")
            rows.append(
                {
                    "frame_id": camera["frame_id"],
                    "real": predictions(real),
                    "rendered": predictions(rendered),
                    "lpips": distance,
                }
            )
            print(camera["frame_id"], "inferred", flush=True)
    result = {"environment": metadata, "views": rows}
    (job_path.parent / "predictions.json").write_text(json.dumps(result, indent=2, allow_nan=False))


def witness():
    config = {
        "torchvision_version": "0.19.1+cu124",
        "lpips_version": "0.1.4",
        "seed": 42,
        "detector_score_threshold": 0.001,
        "detector_nms_threshold": 0.55,
        "detector_topk_candidates": 300,
        "detector_detections_per_img": 300,
    }
    detector, perceptual, metadata = models(config)
    with torch.inference_mode():
        endpoints = lpips_input(torch.tensor([0.0, 0.5, 1.0], device="cuda"))
        assert endpoints.tolist() == [-1.0, 0.0, 1.0]
        image = torch.rand((3, 240, 320), device="cuda")
        out = detector([image])[0]
        scores = out["scores"]
        same = perceptual(lpips_input(image[None]), lpips_input(image[None])).item()
        other = perceptual(lpips_input(image[None]), torch.zeros_like(image[None])).item()
        keep = torchvision.ops.nms(
            torch.tensor([[0.0, 0, 10, 10], [1.0, 1, 9, 9]], device="cuda"),
            torch.tensor([0.9, 0.8], device="cuda"),
            0.5,
        )
        assert keep.tolist() == [0] and torch.isfinite(scores).all()
        assert same == 0 and other > 0 and np.isfinite(other)
    print("PERCEPTION_WITNESS", json.dumps(metadata), "lpips_identical", same, "lpips_other", other)


if __name__ == "__main__":
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    if sys.argv[1] == "witness":
        witness()
    else:
        run(Path(sys.argv[1]).resolve())
