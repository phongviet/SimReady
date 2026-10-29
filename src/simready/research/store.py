"""Controlled read-only study packages; snapshots explicitly omit raw predictions."""

import json
import shutil
from pathlib import Path

from pydantic import TypeAdapter

from simready.data.dataset import atomic_dataset, local_file, sha256_file, write_json
from simready.data.schema import Identifier
from simready.research.analysis import validate_analysis

RAW = {"predictions_real.jsonl", "predictions_rendered.jsonl"}
REQUIRED = {
    "metrics_summary.json",
    "per_view.csv",
    "runs.csv",
    "report.html",
    "report.md",
    "config.yaml",
    "environment.json",
    "dataset_and_split_hash.json",
    "study-figures.svg",
}


def validate_package(root: Path) -> dict:
    package = json.loads(local_file(root, "study.json").read_text())
    if package.get("schema_version") != "1.0" or package.get("type") != "measured_study_package":
        raise ValueError("unsupported study package")
    files = package["files_sha256"]
    if not REQUIRED.issubset(files) or (
        not package["summary_snapshot"] and not RAW.issubset(files)
    ):
        raise ValueError("incomplete study package")
    if package["summary_snapshot"] and RAW.intersection(files):
        raise ValueError("snapshot flag disagrees with raw prediction contents")
    for name, digest in files.items():
        if sha256_file(local_file(root, name)) != digest:
            raise ValueError("study package content changed: " + name)
    return package


def package_analysis(source: Path, output: Path, snapshot: bool = False) -> Path:
    metadata = validate_analysis(source)
    with atomic_dataset(output, 100_000_000) as stage:
        names = set(metadata["files_sha256"]) - (RAW if snapshot else set())
        for name in sorted(names):
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(local_file(source, name), destination)
            # Normalize presentation-only text in the portable package, while
            # retaining the original analysis manifest and its original hashes.
            if destination.suffix == ".csv":
                destination.write_bytes(destination.read_bytes().replace(b"\r\n", b"\n"))
            elif destination.suffix == ".svg":
                destination.write_text(
                    "\n".join(line.rstrip() for line in destination.read_text().splitlines()) + "\n"
                )
        shutil.copyfile(source / "analysis.json", stage / "source-analysis.json")
        write_json(
            stage / "study.json",
            {
                "schema_version": "1.0",
                "type": "measured_study_package",
                "summary_snapshot": snapshot,
                "source_analysis_sha256": sha256_file(source / "analysis.json"),
                "text_serialization": (
                    "Portable CSV uses LF and SVG omits trailing layout whitespace. "
                    "Values are unchanged; source-analysis.json retains original byte hashes."
                ),
                "scope": (
                    "Measured summary snapshot; raw predictions/checkpoints require reproducing "
                    "the recorded GPU study."
                    if snapshot
                    else "Measured benchmark reports and raw predictions; "
                    "checkpoints remain in the source study."
                ),
                "files_sha256": {
                    p.relative_to(stage).as_posix(): sha256_file(p)
                    for p in stage.rglob("*")
                    if p.is_file()
                },
            },
        )
        validate_package(stage)
    return output


class StudyStore:
    def __init__(self, root: Path):
        self.root = root.resolve() / "research"
        self.root.mkdir(parents=True, exist_ok=True)

    def directory(self, study_id: str) -> Path:
        TypeAdapter(Identifier).validate_python(study_id)
        directory = self.root / study_id
        if not directory.resolve().is_relative_to(self.root):
            raise ValueError("study path escapes registered root")
        return directory

    def register(self, study_id: str, analysis: Path) -> dict:
        package_analysis(analysis, self.directory(study_id))
        return self.get(study_id)

    def import_package(self, study_id: str, source: Path) -> dict:
        metadata = validate_package(source)
        with atomic_dataset(self.directory(study_id), 100_000_000) as stage:
            for name in (*metadata["files_sha256"], "study.json"):
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(local_file(source, name), target)
            validate_package(stage)
        return self.get(study_id)

    def get(self, study_id: str) -> dict:
        root = self.directory(study_id)
        if not root.is_dir():
            raise KeyError(study_id)
        metadata = validate_package(root)
        summary = json.loads((root / "metrics_summary.json").read_text())
        return {"study_id": study_id, "package": metadata, "summary": summary}

    def list(self) -> list[dict]:
        return [
            self.get(p.name)
            for p in sorted(self.root.iterdir())
            if p.is_dir() and not p.name.startswith(".") and (p / "study.json").is_file()
        ]

    def asset(self, study_id: str, name: str) -> Path:
        metadata = validate_package(self.directory(study_id))
        if name not in metadata["files_sha256"]:
            raise KeyError(name)
        return local_file(self.directory(study_id), name)
