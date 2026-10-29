"""Seed a local editable scene from genuinely generated analytic artifacts."""

from pathlib import Path

from simready.data.synthetic import make_synthetic
from simready.evaluation.store import EvaluationStore
from simready.scene.store import SceneStore


def seed_demo(store: SceneStore) -> dict:
    fixture = Path(__file__).resolve().parents[1] / "demo/analytic-plane"
    try:
        state = store.get("analytic-demo")
    except KeyError:
        dataset = store.root / "demo-dataset"
        if not dataset.exists():
            make_synthetic(dataset)
        state = store.register(
            "analytic-demo",
            "Analytic plane · CPU demo",
            fixture / "reconstruction",
            fixture / "geometry",
            fixture / "renders",
            dataset,
        )
    evaluations = EvaluationStore(store)
    if not any(r["run_id"] == "bundled-test-1" for r in evaluations.reports("analytic-demo")):
        evaluations.register(
            "analytic-demo", "bundled-test-1", fixture / "evaluation", state["version"]
        )
    return store.get("analytic-demo")
