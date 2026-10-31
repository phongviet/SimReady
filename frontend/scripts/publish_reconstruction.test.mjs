import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile, mkdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createHash } from "node:crypto";
import { snapshot } from "./publish_reconstruction.mjs";
const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
test("presentation export withholds incomplete test results and rejects tampered analysis", async () => {
  const root = await mkdtemp(join(tmpdir(), "simready-export-"));
  const json = async (file, value) => {
    const bytes = JSON.stringify(value);
    await writeFile(join(root, file), bytes);
    return hash(bytes);
  };
  try {
    const seal = await json("protocol.json", {
      study_id: "UNIT-FIXTURE",
      source_commit: "fixture",
      study_order: ["scene"],
      studies: {
        scene: {
          evaluation_split: "test",
          evaluation_frames: ["f1"],
          runs: {
            "arm-s42": {
              config_sha256: "fixture",
              config: { checkpoint_steps: [], iterations: 10 },
            },
          },
        },
      },
    });
    await json("seal.json", { protocol_sha256: seal });
    await mkdir(join(root, "scene/ledger"), { recursive: true });
    await mkdir(join(root, "analysis"));
    const files = {};
    files["status.json"] = await json("analysis/status.json", {
      complete: true,
      evaluations_measured: 1,
    });
    files["measurements.json"] = await json("analysis/measurements.json", [
      { fixture: true },
    ]);
    files["aggregates.json"] = await json("analysis/aggregates.json", []);
    await json("analysis/files.json", files);
    assert.equal((await snapshot(root)).results, null);
    await json("scene/ledger/train-arm-s42.json", { status: "complete" });
    assert.equal((await snapshot(root)).results, null);
    await json("scene/ledger/evaluate-arm-s42-10.json", { status: "complete" });
    assert.ok((await snapshot(root)).results);
    await json("analysis/measurements.json", [{ tampered: true }]);
    await assert.rejects(snapshot(root), /Analysis hash mismatch/);
    await json("protocol.json", { tampered: true });
    await assert.rejects(snapshot(root), /Protocol seal mismatch/);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
