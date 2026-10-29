"""Build the isolated worker from a declarative spec with storage preflights."""

import hashlib
import json
import os
import subprocess

from simready.storage import PROJECT_ROOT, check_budget


def main() -> None:
    root = PROJECT_ROOT
    spec = json.loads((root / "configs/compute-gpu.json").read_text())
    spec_hash = hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode())
    key = spec_hash.hexdigest()[:8]
    ledger = root / ".aris/compute/local.md"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    check_budget(14_000_000_000)
    env = (
        os.environ
        | spec["env"]
        | {
            "UV_CACHE_DIR": str(root / ".cache/gpu"),
            "UV_PYTHON_INSTALL_DIR": str(root / ".cache/python"),
        }
    )
    python = root / ".venv-gpu/bin/python"
    with ledger.open("a") as out:
        out.write(
            f"\n### env: simready-gpu@{key}\nstatus: building; not validated\n"
            f"how: local uv venv {python.parent.parent}\n"
            "tier: 4 CPU threads, 11 GiB host RAM, GTX 1660 Ti 6144 MiB\n"
            "weights: none\n"
        )
    if not python.exists():
        subprocess.run(
            ["uv", "venv", "--python", "3.10", ".venv-gpu"], cwd=root, env=env, check=True
        )
    for phase in spec["pip_phases"]:
        check_budget(8_000_000_000)
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python), *phase], cwd=root, env=env, check=True
        )
    check_budget()
    frozen = subprocess.check_output(
        ["uv", "pip", "freeze", "--python", str(python)], cwd=root, env=env, text=True
    )
    (root / "configs/gpu-requirements-lock.txt").write_text(frozen)
    with ledger.open("a") as out:
        out.write("status: installed; kernel and agent-follows-doc validation still required\n")
    print(f"Installed spec {key}; run the documented kernel witness before using this environment.")


if __name__ == "__main__":
    main()
