"""Frozen supported local study protocol; no implicit knobs after test exposure."""

from typing import Literal, Self

from pydantic import Field, model_validator

from simready.data.schema import Contract


class StudyConfig(Contract):
    schema_version: Literal["1.0"]
    seeds: tuple[int, ...] = Field(min_length=3, max_length=3)
    methods: tuple[Literal["base", "risk", "random", "farthest"], ...]
    additional_observations: Literal[4]
    blind_test_frames: Literal[18]
    base_training_frames: Literal[50]
    validation_fit_frames: Literal[8]
    validation_check_frames: Literal[8]
    candidate_frames: Literal[16]
    ridge_penalty: Literal[0.1]
    feature_distance_scale_m: Literal[0.5]
    feature_rotation_scale_deg: Literal[30.0]
    hole_alpha_threshold: Literal[0.1]
    distance_bin_edges_m: tuple[float, ...]
    rotation_bin_edges_deg: tuple[float, ...]
    pose_blocks: Literal[3]
    reconstruction_config: str
    evaluation_config: str
    source_dataset: str
    source_archive: str

    @model_validator(mode="after")
    def fixed_matrix(self) -> Self:
        if len(set(self.seeds)) != 3 or any(not 0 <= seed < 2**32 for seed in self.seeds):
            raise ValueError("study requires three distinct valid optimization seeds")
        if set(self.methods) != {"base", "risk", "random", "farthest"} or len(self.methods) != 4:
            raise ValueError("all four declared study arms are required")
        for edges in (self.distance_bin_edges_m, self.rotation_bin_edges_deg):
            if len(edges) < 3 or any(b <= a for a, b in zip(edges[:-1], edges[1:], strict=True)):
                raise ValueError("novelty bin edges must increase")
        return self
