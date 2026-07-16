"""Strict, versioned contracts; no training or evaluation state is implied."""

from pathlib import PurePosixPath
from typing import Annotated, Literal, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Nonempty = Annotated[str, Field(min_length=1)]
Matrix4 = tuple[tuple[float, float, float, float], ...]


def relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value:
        raise ValueError("asset paths must be scene-relative POSIX paths without traversal")
    if path == PurePosixPath("."):
        raise ValueError("asset path must name a file")
    return value


def rigid_matrix(value: Matrix4 | np.ndarray) -> np.ndarray:
    matrix = np.asarray(value, dtype=np.float64)
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise ValueError("pose must be a finite 4x4 matrix")
    if not np.allclose(matrix[3], [0, 0, 0, 1], atol=1e-8, rtol=0):
        raise ValueError("pose must have homogeneous last row [0, 0, 0, 1]")
    rotation = matrix[:3, :3]
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-5, rtol=0):
        raise ValueError("pose rotation must be orthonormal")
    if not np.isclose(np.linalg.det(rotation), 1, atol=1e-5, rtol=0):
        raise ValueError("pose rotation must be proper (determinant +1)")
    return matrix


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Intrinsics(Contract):
    model: Literal["pinhole"] = "pinhole"
    width: int = Field(gt=0, strict=True)
    height: int = Field(gt=0, strict=True)
    fx: float = Field(gt=0)
    fy: float = Field(gt=0)
    cx: float = Field(ge=0)
    cy: float = Field(ge=0)

    @model_validator(mode="after")
    def principal_point(self) -> Self:
        if self.cx >= self.width or self.cy >= self.height:
            raise ValueError("principal point must be inside image bounds")
        return self


class DepthEncoding(Contract):
    meters_per_unit: float = Field(gt=0)
    invalid_value: int = Field(ge=0, le=65535, strict=True)
    representation: Literal["uint16_z"] = "uint16_z"


class Source(Contract):
    name: Nonempty
    url: Nonempty
    license: Nonempty
    attribution: Nonempty
    description: Nonempty
    archive_sha256: Digest | None = None


class DatasetManifest(Contract):
    schema_version: Literal["1.0"] = "1.0"
    scene_id: Identifier
    kind: Literal["real", "synthetic"]
    source: Source
    world_units: Literal["meters"] = "meters"
    world_frame: Literal["canonical_right_handed_y_up"] = "canonical_right_handed_y_up"
    camera_axes: Literal["opencv_x_right_y_down_z_forward"] = "opencv_x_right_y_down_z_forward"
    cameras: dict[Identifier, Intrinsics] = Field(min_length=1)
    depth: DepthEncoding
    pose_provenance: Nonempty
    timestamp_provenance: Nonempty
    association_tolerance: float = Field(ge=0)
    capture_conditions: Nonempty
    privacy: Nonempty
    limitations: tuple[Nonempty, ...] = Field(min_length=1)
    T_canonical_source_world: Matrix4
    frames_sha256: Digest
    split_sha256: Digest

    @field_validator("T_canonical_source_world")
    @classmethod
    def check_world_transform(cls, value: Matrix4) -> Matrix4:
        rigid_matrix(value)
        return value


class Frame(Contract):
    frame_id: Identifier
    timestamp: float = Field(ge=0)
    depth_timestamp: float | None = Field(default=None, ge=0)
    camera_id: Identifier
    sequence_id: Identifier
    rgb_path: str
    rgb_sha256: Digest
    depth_path: str | None = None
    depth_sha256: Digest | None = None
    T_world_camera: Matrix4

    @field_validator("rgb_path", "depth_path")
    @classmethod
    def check_path(cls, value: str | None) -> str | None:
        return relative_path(value) if value is not None else None

    @field_validator("T_world_camera")
    @classmethod
    def check_pose(cls, value: Matrix4) -> Matrix4:
        rigid_matrix(value)
        return value

    @model_validator(mode="after")
    def depth_metadata(self) -> Self:
        present = (self.depth_path, self.depth_sha256, self.depth_timestamp)
        if any(x is not None for x in present) and not all(x is not None for x in present):
            raise ValueError("depth path, hash and timestamp must be provided together")
        return self


class Splits(Contract):
    schema_version: Literal["1.0"] = "1.0"
    strategy: Literal["contiguous_blocks_v1"] = "contiguous_blocks_v1"
    frames_sha256: Digest
    train: tuple[Identifier, ...] = Field(min_length=1)
    validation: tuple[Identifier, ...] = Field(min_length=1)
    candidate: tuple[Identifier, ...] = Field(min_length=1)
    test: tuple[Identifier, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def disjoint(self) -> Self:
        ids = self.train + self.validation + self.candidate + self.test
        if len(set(ids)) != len(ids):
            raise ValueError("split overlap or duplicate frame IDs")
        return self


class ScenePackage(Contract):
    """Metadata contract only; no reconstruction/editor/review behavior in M0."""

    schema_version: Literal["1.0"] = "1.0"
    scene_id: Identifier
    version: int = Field(gt=0, strict=True)
    world_units: Literal["meters"] = "meters"
    world_frame: Literal["canonical_right_handed_y_up"] = "canonical_right_handed_y_up"
    dataset_manifest: str
    render_asset: str | None = None
    collision_asset: str | None = None
    status: Literal["draft"] = "draft"

    @field_validator("dataset_manifest", "render_asset", "collision_asset")
    @classmethod
    def check_asset(cls, value: str | None) -> str | None:
        return relative_path(value) if value is not None else None
