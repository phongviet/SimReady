"""Scene/editor contracts. Only inserted unit-box proxies are editable."""

from typing import Annotated, Literal, Self

import numpy as np
from pydantic import Field, field_validator, model_validator

from simready.data.schema import Contract, Identifier

Coordinate = Annotated[float, Field(ge=-10000, le=10000)]
Scale = Annotated[float, Field(ge=0.01, le=100)]


class ProxyObject(Contract):
    object_id: Identifier
    name: str = Field(min_length=1, max_length=80)
    kind: Literal["box", "barrier"] = "box"
    position: tuple[Coordinate, Coordinate, Coordinate]
    quaternion_xyzw: tuple[float, float, float, float] = (0, 0, 0, 1)
    scale: tuple[Scale, Scale, Scale] = (0.5, 0.5, 0.5)
    visible: bool = True
    collidable: bool = True
    color: str = Field(default="#d2f08a", pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("quaternion_xyzw")
    @classmethod
    def unit_quaternion(cls, value):
        if not np.isclose(np.linalg.norm(value), 1.0, atol=1e-5, rtol=0):
            raise ValueError("object quaternion must be unit length")
        return value


class ObjectUpdate(Contract):
    expected_version: int = Field(ge=1, strict=True)
    objects: tuple[ProxyObject, ...] = Field(max_length=128)

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        ids = [obj.object_id for obj in self.objects]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate object IDs")
        return self


def object_matrix(obj: ProxyObject) -> np.ndarray:
    """Unit box -> world, same transform used by visual mesh and collider."""
    x, y, z, w = obj.quaternion_xyzw
    rotation = np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )
    result = np.eye(4)
    result[:3, :3] = rotation @ np.diag(obj.scale)
    result[:3, 3] = obj.position
    return result


def object_corners(obj: ProxyObject) -> np.ndarray:
    local = np.array([[x, y, z] for x in (-0.5, 0.5) for y in (-0.5, 0.5) for z in (-0.5, 0.5)])
    transform = object_matrix(obj)
    return local @ transform[:3, :3].T + transform[:3, 3]
