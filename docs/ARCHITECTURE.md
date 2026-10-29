# Implemented M0 architecture

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

The React/TypeScript frontend is a standalone scope shell with no API connection.
The `ScenePackage` type accepts draft metadata with optional null assets; it
does not create any reconstruction, collision geometry, editable scene or review.

All other boxes in PLAN.md's system diagram are future work.
