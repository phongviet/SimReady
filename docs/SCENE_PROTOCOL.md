# M2 scene packages and editor protocol

The local studio registers immutable Gaussian/TSDF assets, camera records and
saved gsplat views. Inserted box/barrier proxies remain separate from those assets.
All use the canonical right-handed Y-up world frame and meters.

```text
artifacts/studio/
  studio.sqlite3                 # authoritative current versions + immutable revisions
  packages/<scene_id>/
    base.json                    # provenance, camera records, registered asset digests
    scene.json                   # atomic snapshot of the current editable state
    reconstruction/              # learned Gaussian PLY/NPZ and source metadata
    geometry/                    # independent coarse TSDF mesh and metadata
    views/                       # saved reference camera RGB / depth / alpha
```

SQLite transactions serialize writers. Each successful object update inserts a
new immutable revision and advances the current version. Requests carry an
`expected_version`; stale edits receive HTTP 409 with the current version. The
browser keeps local edits until the user explicitly reloads/discards them.
SQLite is authoritative if an external interruption leaves a snapshot out of sync;
API reads and history use the database, not a mutable filesystem pointer.

Object transforms use position in meters, unit quaternion in **xyzw** order, and
positive XYZ scale applied to a centered unit cube. Thus scale is the box's
metric size before rotation. Both the visible mesh and collider use that same
transform. This differs deliberately from the Gaussian PLY's wxyz convention.
No base-scene deletion, removal/inpainting, or editing of source splats is exposed.

Visibility affects only the visual mesh. Collider enablement is independent,
explicit in the inspector, and preserved across saves. Deletion removes the
inserted object from the new revision while historical revisions remain intact.

## Geometry scope

`geometry build` integrates **only frozen training RGB-D** using Open3D CPU TSDF,
the inverse supplied c2w, the declared depth scale, and no ICP/scene scaling.
Its frame/manifest hashes must match the reconstruction during registration.
The output is an observed coarse surface, potentially open and incomplete.
Surface/box intersection uses an oriented-box/triangle separating-axis test;
it does not infer solid occupancy behind unobserved/open surfaces. Ground-truth
geometry errors remain null; the analytic plane test checks metric consistency.

## Browser rendering scope

Spark/Three.js renders the Gaussian PLY for orbit inspection. The browser renderer
is separate from scientific gsplat rendering. Inserted assets and colliders are
drawn in an explicit **overlay pass**, without claiming splat-depth occlusion.
Saved-camera mode projects box corners using exactly the stored OpenCV calibration
and c2w/w2c conventions. A test compares the same known marker in Python and
Three.js pixel coordinates, including half-pixel image centers.

The initial look target is captured before constructing OrbitControls, because
its constructor updates camera orientation. Browser tests require nonempty actual
rendered pixels and changed pixels after an orbit drag, not only a load message.
WebGL2 failures fall back to saved views with numeric proxy editing still available.

## API scope

Implemented `/api/v1`: health, scene list/detail, object update, revision history,
individual historical revisions and registered assets. Asset requests use scene ID
and a registered asset key, with scene-relative paths, symlink containment and
content-hash verification. Arbitrary filesystem path requests are unsupported.
Errors carry request IDs. No review or role-spoofable approval endpoint exists.
The server binds to loopback; authenticated review and persistent compute jobs
remain later milestones. This is not production identity/access management.
