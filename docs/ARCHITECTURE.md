# Implemented reconstruction and editing architecture

```text
Analytic fixture generator     Pinned Open3D sample acquisition
            |                             |
            |                    Redwood format importer
            +---------------+-------------+
                            |
                 Atomic staging and validation
                            |
      manifest.json + frames.jsonl + immutable splits.json
                     RGB / uint16 depth / calib
                            |
                    CPU validation CLI
```

Pydantic defines versioned metadata and scene-package contracts. NumPy implements
explicit camera/pose math; Pillow decodes image files. SHA-256 binds content,
records and splits. Storage accounting is standard-library-only, so it runs
before dependency installation. pytest covers CPU correctness, failures and CLI
behavior, with one separately obtainable official real-data integration test.

M2 connects a React/TypeScript/Spark scene editor to the local FastAPI service.
SQLite stores authoritative current and immutable historical scene revisions;
filesystem packages hold independent Gaussian/TSDF assets, source/camera metadata
and saved scientific views. Inserted rigid proxies have shared mesh/collider
transforms, independent visibility/collision flags and optimistic version checks.
Assets are served only through registered scene keys and verified content hashes.

M1 adds CPU preparation of training-only RGB-D inputs and a separate Python3.10
GPU worker. JSON requests and safe NPZ arrays cross that boundary; the worker
uses upstream gsplat rasterization and DefaultStrategy, writes learned Gaussian
parameters and a documented Graphdeco PLY, and renders selected frozen camera
poses. Artifacts bind dataset/split/config/source provenance to their content.
There is no torch import in the CPU package. The bundled analytic trained model
and saved views provide CPU-only validation without pretending to render live.

Optional Open3D CPU TSDF fusion uses frozen training RGB-D and matching metric
camera transforms. Browser inspection and overlay-only inserted meshes are kept
separate from scientific gsplat RGB/depth renders. Saved-camera mode remains
available for CPU smoke and WebGL failures. Evaluation, simulation, review and
research boxes in PLAN.md remain future work.
