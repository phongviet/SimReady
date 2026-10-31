/** Read-only presentation export. Never launches jobs or edits experiment inputs. */
import { readFile, mkdir, writeFile, rename } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve, join, basename } from "node:path";
import { fileURLToPath } from "node:url";

const sha = (bytes) => createHash("sha256").update(bytes).digest("hex");
const read = async (path) => JSON.parse(await readFile(path, "utf8"));
const maybe = async (path) => {
  try {
    return await read(path);
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw error;
  }
};

export async function snapshot(root) {
  const bytes = await readFile(join(root, "protocol.json"));
  const seal = await read(join(root, "seal.json"));
  if (sha(bytes) !== seal.protocol_sha256)
    throw new Error("Protocol seal mismatch");
  const protocol = JSON.parse(bytes);
  const runs = [];
  for (const study of protocol.study_order) {
    const child = protocol.studies[study];
    for (const [run, item] of Object.entries(child.runs)) {
      const train = await maybe(
        join(root, study, "ledger", `train-${run}.json`),
      );
      const steps = item.config.checkpoint_steps.length
        ? item.config.checkpoint_steps
        : [item.config.iterations];
      const evaluations = await Promise.all(
        steps.map(async (step) => ({
          step,
          status:
            (
              await maybe(
                join(root, study, "ledger", `evaluate-${run}-${step}.json`),
              )
            )?.status ?? "queued",
        })),
      );
      runs.push({
        study,
        run,
        split: child.evaluation_split,
        views: child.evaluation_frames.length,
        iterations: item.config.iterations,
        config_sha256: item.config_sha256,
        training: train?.status ?? "queued",
        evaluations,
      });
    }
  }
  const completedTrain = runs.filter((r) => r.training === "complete").length;
  const plannedEvaluations = runs.reduce((n, r) => n + r.evaluations.length, 0);
  const completedEval = runs
    .flatMap((r) => r.evaluations)
    .filter((e) => e.status === "complete").length;
  let results = null;
  // No test scores are exported until every frozen arm and the sealed analysis finish.
  if (completedTrain === runs.length && completedEval === plannedEvaluations) {
    const status = await maybe(join(root, "analysis", "status.json"));
    if (status?.complete) {
      const files = await read(join(root, "analysis", "files.json"));
      for (const name of [
        "status.json",
        "measurements.json",
        "aggregates.json",
      ]) {
        if (sha(await readFile(join(root, "analysis", name))) !== files[name])
          throw new Error(`Analysis hash mismatch: ${name}`);
      }
      const measurements = await read(
        join(root, "analysis", "measurements.json"),
      );
      if (
        measurements.length !== plannedEvaluations ||
        status.evaluations_measured !== plannedEvaluations
      )
        throw new Error("Incomplete analysis");
      results = {
        aggregates: await read(join(root, "analysis", "aggregates.json")),
        analysis_files_sha256: files,
        ground_truth_detection: status.ground_truth_detection,
      };
    }
  }
  return {
    study_id: protocol.study_id,
    exported_utc: new Date().toISOString(),
    source_commit: protocol.source_commit,
    protocol_sha256: seal.protocol_sha256,
    verification:
      "Ledger progress; final metrics require completed artifact-bound analysis with file hashes.",
    policy: protocol.policy,
    runs,
    completed_training: completedTrain,
    planned_training: runs.length,
    completed_evaluations: completedEval,
    planned_evaluations: plannedEvaluations,
    results,
  };
}

async function publish() {
  const project = resolve(fileURLToPath(new URL("../..", import.meta.url)));
  const value = await snapshot(
    join(project, "experiments/engineering-improvement-1"),
  );
  for (const destination of [
    "frontend/public/research",
    "frontend/dist/research",
  ]) {
    await mkdir(join(project, destination), { recursive: true });
    if (value.results) {
      const assets = join(project, destination, "engineering-improvement-1");
      await mkdir(assets, { recursive: true });
      let total = 0;
      for (const [name, expected] of Object.entries(
        value.results.analysis_files_sha256,
      )) {
        if (basename(name) !== name)
          throw new Error("Analysis asset must be a local filename");
        const bytes = await readFile(
          join(project, "experiments/engineering-improvement-1/analysis", name),
        );
        total += bytes.length;
        if (total > 100_000_000 || sha(bytes) !== expected)
          throw new Error("Analysis asset integrity/size failure");
        let identical = false;
        try {
          identical = sha(await readFile(join(assets, name))) === expected;
        } catch (error) {
          if (error.code !== "ENOENT") throw error;
        }
        if (!identical) {
          await writeFile(join(assets, name + ".tmp"), bytes);
          await rename(join(assets, name + ".tmp"), join(assets, name));
        }
      }
    }
    const target = join(project, destination, "reconstruction.json");
    await writeFile(target + ".tmp", JSON.stringify(value, null, 2) + "\n");
    await rename(target + ".tmp", target);
  }
  console.log(
    `${value.completed_training}/${value.planned_training} trained; ${value.completed_evaluations}/${value.planned_evaluations} evaluated; metrics ${value.results ? "published" : "withheld"}`,
  );
}
if (
  process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  await publish();
  if (process.argv.includes("--watch"))
    setInterval(
      () => publish().catch((error) => console.error(error.message)),
      5000,
    );
}
