"""Seed a local editable scene from genuinely generated analytic artifacts."""

from pathlib import Path

from simready.data.synthetic import make_synthetic
from simready.scene.store import SceneStore


def seed_demo(store: SceneStore) -> dict:
    try:
        return store.get("analytic-demo")
    except KeyError:
        pass
    fixture = Path(__file__).resolve().parents[1] / "demo/analytic-plane"
    dataset = store.root / "demo-dataset"
    if not dataset.exists():
        make_synthetic(dataset)
    return store.register(
        "analytic-demo",
        "Analytic plane · CPU demo",
        fixture / "reconstruction",
        fixture / "geometry",
        fixture / "renders",
        dataset,
    )
