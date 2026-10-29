"""Selection only sees public poses/current-model opacity and validation calibration."""

import hashlib
import json
from pathlib import Path
from typing import Literal, Self

import numpy as np
from pydantic import Field, model_validator
from scipy.optimize import nnls
from scipy.stats import spearmanr

from simready.data.dataset import sha256_file
from simready.data.schema import Contract, Digest, Identifier


def json_digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


class CandidateFeature(Contract):
    frame_id: Identifier
    distance_m: float = Field(ge=0)
    rotation_deg: float = Field(ge=0, le=180.001)
    alpha_hole_fraction: float = Field(ge=0, le=1)


class Acquisition(Contract):
    key: Identifier
    method: Literal["risk", "random", "farthest"]
    seed: int = Field(ge=0)
    selected_ids: tuple[Identifier, ...]
    base_artifact_sha256: Digest
    details_sha256: Digest


class SelectionSeal(Contract):
    schema_version: Literal["1.0"]
    curation_sha256: Digest
    protocol_sha256: Digest
    candidate_ids: tuple[Identifier, ...]
    seeds: tuple[int, ...]
    k: int = Field(gt=0)
    acquisitions: tuple[Acquisition, ...]

    @model_validator(mode="after")
    def complete_matrix(self) -> Self:
        expected = {
            (method, seed) for method in ("risk", "random", "farthest") for seed in self.seeds
        }
        actual = {(row.method, row.seed) for row in self.acquisitions}
        if (
            actual != expected
            or len(actual) != len(self.acquisitions)
            or len(set(self.seeds)) != len(self.seeds)
            or len(set(row.key for row in self.acquisitions)) != len(actual)
            or not self.seeds
            or len(set(self.candidate_ids)) != len(self.candidate_ids)
        ):
            raise ValueError("selection seal must contain exactly the complete method/seed matrix")
        for row in self.acquisitions:
            if (
                len(row.selected_ids) != self.k
                or len(set(row.selected_ids)) != self.k
                or not set(row.selected_ids).issubset(self.candidate_ids)
            ):
                raise ValueError(
                    "each sealed acquisition must select exactly K distinct candidates"
                )
        return self


def validate_seal(study: Path) -> SelectionSeal:
    path = study / "selections-sealed.json"
    if not path.is_file() or not (study / "selections-sealed.sha256").is_file():
        raise ValueError("all acquisitions must be sealed before observation release")
    if sha256_file(path) != (study / "selections-sealed.sha256").read_text().strip():
        raise ValueError("selection seal content changed")
    seal = SelectionSeal.model_validate_json(path.read_text())
    if seal.curation_sha256 != sha256_file(study / "curation.json"):
        raise ValueError("curation differs from selection seal")
    protocol = json.loads((study / "protocol.json").read_text())
    if seal.protocol_sha256 != json_digest(protocol):
        raise ValueError("protocol differs from selection seal")
    curation = json.loads((study / "curation.json").read_text())
    declared = protocol["study"]
    if (
        tuple(declared["seeds"]) != seal.seeds
        or declared["additional_observations"] != seal.k
        or curation["protocol_sha256"] != seal.protocol_sha256
    ):
        raise ValueError("seal matrix differs from the frozen protocol")
    if set(seal.candidate_ids) != set(curation["partitions"]["candidate"]):
        raise ValueError("seal candidate pool differs from frozen curation")
    for row in seal.acquisitions:
        details_path = study / "selection" / (row.key + ".json")
        if sha256_file(details_path) != row.details_sha256:
            raise ValueError("sealed selection details changed")
        details = json.loads(details_path.read_text())
        if any(
            details.get(key) != value
            for key, value in row.model_dump(mode="json").items()
            if key != "details_sha256"
        ):
            raise ValueError("selection details disagree with sealed acquisition")
        if (
            sha256_file(study / "models" / f"base-s{row.seed}" / "artifact.json")
            != row.base_artifact_sha256
        ):
            raise ValueError("sealed base artifact changed")
    return seal


def features(values: list[CandidateFeature], distance_scale=0.5, rotation_scale=30.0) -> np.ndarray:
    return np.array(
        [
            [
                min(value.distance_m / distance_scale, 1),
                min(value.rotation_deg / rotation_scale, 1),
                value.alpha_hole_fraction,
            ]
            for value in values
        ],
        dtype=float,
    )


def correlation(left, right) -> dict:
    a, b = np.asarray(left, dtype=float), np.asarray(right, dtype=float)
    if len(a) < 3 or not np.isfinite(a).all() or not np.isfinite(b).all():
        return {"rho": None, "reason": "fewer than three finite paired observations"}
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return {"rho": None, "reason": "constant input; rank correlation undefined"}
    return {"rho": float(spearmanr(a, b).statistic), "reason": None}


def calibrate(
    validation: list[CandidateFeature], targets: list[float], fit_count=8, penalty=0.1
) -> dict:
    if len(validation) != len(targets) or len(validation) <= fit_count or fit_count < 4:
        raise ValueError("calibration needs separate fit/check pose blocks")
    x = features(validation)
    design = np.column_stack([np.ones(fit_count), x[:fit_count]])
    regularizer = np.diag([0, np.sqrt(penalty), np.sqrt(penalty), np.sqrt(penalty)])
    coefficients, _ = nnls(
        np.vstack([design, regularizer]), np.r_[targets[:fit_count], np.zeros(4)]
    )
    predictions = np.column_stack([np.ones(len(validation)), x]) @ coefficients
    check = np.asarray(targets[fit_count:])
    return {
        "coefficients": coefficients.tolist(),
        "fit_ids": [v.frame_id for v in validation[:fit_count]],
        "check_ids": [v.frame_id for v in validation[fit_count:]],
        "ridge_penalty": penalty,
        "check_mae": float(np.abs(check - predictions[fit_count:]).mean()),
        "check_spearman": correlation(check, predictions[fit_count:]),
        "check_targets": check.tolist(),
        "check_predictions": predictions[fit_count:].tolist(),
        "scope": "Validation-only calibration, not a certified uncertainty estimator.",
    }


def select_risk(
    candidates: list[CandidateFeature], calibration: dict, k: int
) -> tuple[list[str], list[dict]]:
    if not 0 < k <= len(candidates):
        raise ValueError("invalid acquisition K")
    scores = np.column_stack([np.ones(len(candidates)), features(candidates)]) @ np.asarray(
        calibration["coefficients"]
    )
    ranked = sorted(
        [
            {
                "frame_id": row.frame_id,
                "score": float(score),
                "features": row.model_dump(mode="json"),
            }
            for row, score in zip(candidates, scores, strict=True)
        ],
        key=lambda row: (-row["score"], row["frame_id"]),
    )
    return [row["frame_id"] for row in ranked[:k]], ranked


def select_random(ids: list[str], k: int, seed: int) -> list[str]:
    return np.random.default_rng(1000 + seed).choice(ids, k, replace=False).tolist()


def select_farthest(
    train_centers: np.ndarray, ids: list[str], candidate_centers: np.ndarray, k: int
) -> list[str]:
    centers = list(np.asarray(train_centers))
    selected = []
    for _ in range(k):
        distances = np.linalg.norm(
            candidate_centers[:, None, :] - np.asarray(centers)[None, :, :], axis=-1
        ).min(axis=1)
        choices = sorted(
            ((-float(distances[i]), name, i) for i, name in enumerate(ids) if name not in selected)
        )
        _, name, index = choices[0]
        selected.append(name)
        centers.append(candidate_centers[index])
    return selected
