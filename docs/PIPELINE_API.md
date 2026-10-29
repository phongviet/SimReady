# Queued scene preparation

The Builder-only `POST /api/v1/scenes/import` creates a persistent import job.
`GET /api/v1/jobs/{job_id}` returns queued/running/succeeded/failed, timestamps,
source digest, validation result and bounded log tail. Dataset output is private
under the registry's `import-jobs/{job_id}/dataset`; import does not yet create a
reconstructed editable scene. Reconstruction/render HTTP paths remain pending.

Example request with an existing local Builder bearer token:

```json
{"scene_id":"example-import","format":"synthetic"}
```

Other formats: `tum_rgbd` or `open3d_redwood_sample`, with `source_key` naming an
operator-provisioned entry directly under `artifacts/studio/inbox` (or the chosen
registry root). The key is an identifier, not a filesystem path. TUM input is an
archive; Open3D input is the extracted sample directory. TUM `max_frames` defaults
to100 and accepts8–256. Synthetic has eight fixed analytic frames and no source key.

Sources are capped at500MB/2000files, contained in the inbox and cannot include
symlinks. Digests bind the source before enqueue and are rechecked before and
after import. Original importers still enforce archive/path/pose/calibration/
split validation. Atomic output directories never overwrite existing imports.
Use a new scene ID for a new attempt; failed job history is retained.

Jobs use a serialized subprocess queue; startup under its worker lock marks
interrupted running jobs failed. This is a single-machine durable job state,
not distributed scheduling or production IAM. No GPU is required for import.

Acceptance: actual subprocess HTTP import and polling, strict anonymous denial,
duplicate IDs, malformed traversal/missing keys and inbox content/link checks.
Actual network-dataset formats have separate CLI/importer integration tests;
the HTTP acceptance fixture is explicitly analytic synthetic data.
