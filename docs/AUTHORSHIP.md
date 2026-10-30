# GitHub attribution correction

Repository author and maintainer: [phongviet](https://github.com/phongviet).
Commit identity: `phongviet <162717702+phongviet@users.noreply.github.com>`.
The numeric ID was verified against GitHub's user API. Repository-local Git
configuration uses this identity for future commits; global Git settings are
unchanged.

The initial history used a placeholder identity, SimReady Development. At the
owner's request, all60 existing commits and annotated tags were rewritten to
attribute them to phongviet. Every original source tree, author/committer date,
message and parent topology was verified unchanged. Dependent commit/tag IDs
necessarily changed. The initial June–October date assignments and actual
execution disclosures remain intact.

A complete pre-correction history bundle is retained locally under ignored
`artifacts/attribution`. Published refs are updated with explicit leases against
the previously observed remote IDs; no unrelated remote updates are overwritten.

## Immutable experiment provenance

Frozen datasets, model/evaluation/analysis outputs and recorded CI observations
keep their original hashes and original source-commit IDs. They are not edited
to pretend the experiments ran under a new identity or source revision.
`configs/git-author-map.json` maps each original commit to the corrected commit
with exactly the same source tree. Research inspection resolves through this map
before checking source-file SHA-256 values. A fresh-clone check verifies resolution
without requiring the original commit objects.

For checking out older tags whose inspection code predates the resolver, load the
map from current main and install local Git replacement refs before replay:

```bash
git show origin/main:configs/git-author-map.json > .git/simready-author-map.json
python3 - <<'PY'
import json, subprocess
from pathlib import Path
for old, new in json.loads(Path('.git/simready-author-map.json').read_text())['commits'].items():
    subprocess.run(['git', 'update-ref', 'refs/replace/' + old, new], check=True)
PY
```

Current main resolves the map directly and does not need that extra step.
GitHub's contributor statistics may take time to refresh after a history rewrite;
individual commit-account attribution is verified separately through the API.
