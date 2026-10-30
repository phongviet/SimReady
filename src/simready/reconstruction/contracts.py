"""CPU-visible reconstruction contracts; importing this never imports torch."""

from pathlib import Path
from typing import Literal, Protocol, Self

from pydantic import Field, StrictInt, model_validator

from simready.data.schema import Contract, Identifier, Intrinsics, Matrix4, rigid_matrix


class RenderCamera(Contract):
    frame_id: Identifier
    intrinsics: Intrinsics
    T_world_camera: Matrix4

    @model_validator(mode="after")
    def verified(self) -> Self:
        rigid_matrix(self.T_world_camera)
        if max(self.intrinsics.width, self.intrinsics.height) > 640:
            raise ValueError("local render dimensions must be <=640 pixels")
        return self


class ReconstructionConfig(Contract):
    schema_version: Literal["1.0"]
    preset: Literal["smoke", "local_6gb"]
    iterations: int = Field(ge=1, le=30000, strict=True)
    width: int = Field(ge=32, le=640, strict=True)
    initial_stride: int = Field(ge=1, le=32, strict=True)
    max_initial_gaussians: int = Field(ge=8, le=100000, strict=True)
    max_gaussians: int = Field(ge=8, le=200000, strict=True)
    seed: int = Field(ge=0, le=2**32 - 1, strict=True)
    sh_degree: int = Field(ge=0, le=3, strict=True)
    refine_start: int = Field(ge=0, strict=True)
    refine_stop: int = Field(ge=0, strict=True)
    refine_every: int = Field(gt=0, strict=True)
    depth_loss_weight: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def sensible_limits(self) -> Self:
        if self.max_initial_gaussians > self.max_gaussians:
            raise ValueError("initial Gaussian limit exceeds final budget")
        if not self.refine_start <= self.refine_stop <= self.iterations:
            raise ValueError("refinement interval must fit inside training")
        return self


class ReconstructionBackend(Protocol):
    def train(self, scene: Path, config: ReconstructionConfig, output: Path) -> Path: ...

    def render(self, artifact: Path, scene: Path, split: str, output: Path) -> Path: ...

    def render_cameras(self, artifact: Path, cameras: list[RenderCamera], output: Path) -> Path: ...


class QualityTrainingConfig(ReconstructionConfig):
    """Opt-in study controls; legacy configuration serialization stays unchanged."""

    photometric_loss: Literal["l1", "mse", "l1_ssim"] = "l1"
    ssim_weight: float = Field(default=0.2, ge=0, le=1)
    depth_supervision: Literal["none", "l1", "relative_l1"] = "l1"
    depth_mask: Literal["alpha", "gt_valid"] = "alpha"
    checkpoint_steps: list[StrictInt] = Field(default_factory=list)
    log_every: int = Field(default=10, ge=1, le=100)
    memory_limit_bytes: int = Field(default=4_500_000_000, ge=100_000_000, le=4_500_000_000)

    @model_validator(mode="after")
    def quality_limits(self) -> Self:
        if self.checkpoint_steps != sorted(set(self.checkpoint_steps)) or any(
            type(n) is not int or not 1 <= n <= self.iterations for n in self.checkpoint_steps
        ):
            raise ValueError("checkpoints must be unique increasing steps inside the budget")
        if self.depth_supervision == "none" and self.depth_loss_weight != 0:
            raise ValueError("disabled depth supervision requires zero weight")
        return self
