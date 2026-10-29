"""Versioned evaluation protocol; thresholds are heuristics, not certification."""

from typing import Literal

from pydantic import Field

from simready.data.schema import Contract


class EvaluationConfig(Contract):
    schema_version: Literal["1.0"] = "1.0"
    detector: Literal["ssdlite320_mobilenet_v3_large"] = "ssdlite320_mobilenet_v3_large"
    detector_weights: Literal["COCO_V1"] = "COCO_V1"
    torchvision_version: Literal["0.19.1+cu124"] = "0.19.1+cu124"
    lpips_version: Literal["0.1.4"] = "0.1.4"
    lpips_network: Literal["squeeze"] = "squeeze"
    lpips_calibration: Literal["0.1"] = "0.1"
    confidence_threshold: float = Field(default=0.5, gt=0, le=1)
    match_iou_threshold: float = Field(default=0.5, gt=0, le=1)
    detector_score_threshold: Literal[0.001] = 0.001
    detector_nms_threshold: Literal[0.55] = 0.55
    detector_topk_candidates: Literal[300] = 300
    detector_detections_per_img: Literal[300] = 300
    depth_alpha_threshold: float = Field(default=0.1, gt=0, le=1)
    ssim_window: Literal[7] = 7
    rgb_domain: Literal["sRGB uint8 / 255; whole image; no exposure correction"] = (
        "sRGB uint8 / 255; whole image; no exposure correction"
    )
    seed: Literal[42] = 42
