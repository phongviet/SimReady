/** Fixed diagnostic presentation supplement. Never edits primary outputs or selects a model. */
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { createHash } from "node:crypto";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const project = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const root = join(project, "experiments/engineering-improvement-1");
const out = join(project, "experiments/engineering-improvement-diagnostics-1");
const sha = (bytes) => createHash("sha256").update(bytes).digest("hex");
const read = async (path) => JSON.parse(await readFile(path, "utf8"));
const inputs = {};
async function bound(path) {
  const bytes = await readFile(path);
  inputs[path.slice(project.length + 1)] = sha(bytes);
  return bytes;
}
const json = async (name, value) =>
  writeFile(join(out, name), JSON.stringify(value, null, 2) + "\n");
const esc = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
const mean = (values) => values.reduce((a, b) => a + b, 0) / values.length;
const sd = (values) =>
  values.length > 1
    ? Math.sqrt(
        values.reduce((a, b) => a + (b - mean(values)) ** 2, 0) /
          (values.length - 1),
      )
    : null;
const metrics = [
  "lpips",
  "psnr_db",
  "ssim",
  "depth_mae_m",
  "depth_completeness",
];
const colors = ["#1769aa", "#bc4f00", "#15733d"];
const status = JSON.parse(await bound(join(root, "analysis/status.json")));
if (!status.complete || status.evaluations_measured !== 45)
  throw new Error(
    "Complete primary analysis required; no partial test-score inspection",
  );
const files = JSON.parse(await bound(join(root, "analysis/files.json")));
for (const [name, expected] of Object.entries(files)) {
  if (name.includes("/") || name.includes("\\"))
    throw new Error("Unexpected analysis filename");
  if (sha(await bound(join(root, "analysis", name))) !== expected)
    throw new Error(`Altered primary export: ${name}`);
}
const protocol = JSON.parse(await bound(join(root, "protocol.json")));
const rows = await read(join(root, "analysis/measurements.json"));
const aggregates = await read(join(root, "analysis/aggregates.json"));
if (rows.length !== 45) throw new Error("Expected 45 measurements");
const views = new Map();
let comparisons = 0;
for (const row of rows) {
  const values = JSON.parse(await bound(join(root, row.report, "views.json")));
  const expected = protocol.studies[row.study].evaluation_frames;
  if (
    values.length !== expected.length ||
    new Set(values.map((v) => v.frame_id)).size !== expected.length ||
    values.some((v) => !expected.includes(v.frame_id))
  )
    throw new Error("Incomplete/duplicate split");
  views.set(`${row.study}/${row.run}/${row.step}`, values);
  for (const metric of metrics) {
    const numbers = values
      .map((v) => v.metrics[metric])
      .filter((v) => v != null);
    const actual = numbers.length ? mean(numbers) : null;
    if (
      actual == null
        ? row[metric] != null
        : Math.abs(actual - row[metric]) > 1e-9
    )
      throw new Error(`Per-view replay mismatch ${metric}`);
    comparisons++;
  }
}
for (const aggregate of aggregates) {
  const group = rows.filter(
    (r) =>
      r.study === aggregate.study &&
      r.policy === aggregate.policy &&
      r.step === aggregate.step,
  );
  for (const [metric, expected] of Object.entries(aggregate.statistics)) {
    const values = group.map((r) => r[metric]).filter((v) => v != null);
    for (const [kind, actual] of Object.entries({
      mean: values.length ? mean(values) : null,
      sample_sd: sd(values),
    })) {
      if (
        actual == null
          ? expected[kind] != null
          : Math.abs(actual - expected[kind]) >
            1e-9 * Math.max(1, Math.abs(actual))
      )
        throw new Error(`Aggregate replay mismatch: ${metric}/${kind}`);
      comparisons++;
    }
  }
}
// Only create a new supplement after validating all primary numeric inputs.
await mkdir(out);
const outputNames = [];
async function save(name, bytes) {
  await writeFile(join(out, name), bytes);
  outputNames.push(name);
}
function csv(rows) {
  const keys = Object.keys(rows[0] ?? {});
  const field = (v) => '"' + String(v ?? "").replaceAll('"', '""') + '"';
  return (
    [
      keys.map(field).join(","),
      ...rows.map((r) => keys.map((k) => field(r[k])).join(",")),
    ].join("\n") + "\n"
  );
}
const paired = [];
for (const row of rows) {
  const reference = row.study.startsWith("densification")
    ? "refine900"
    : "matched";
  if (row.policy === reference || row.policy === "original") continue;
  const control = rows.find(
    (r) =>
      r.study === row.study &&
      r.policy === reference &&
      r.seed === row.seed &&
      r.step === row.step,
  );
  if (!control) throw new Error("Missing paired control");
  const controlViews = new Map(
    views
      .get(`${control.study}/${control.run}/${control.step}`)
      .map((v) => [v.frame_id, v]),
  );
  for (const value of views.get(`${row.study}/${row.run}/${row.step}`)) {
    const other = controlViews.get(value.frame_id);
    if (JSON.stringify(value.camera) !== JSON.stringify(other.camera))
      throw new Error("Camera mismatch");
    paired.push({
      study: row.study,
      run: row.run,
      reference: control.run,
      seed: row.seed,
      step: row.step,
      split: row.split,
      frame_id: value.frame_id,
      ...Object.fromEntries(
        metrics.map((k) => [
          k + "_delta",
          value.metrics[k] == null || other.metrics[k] == null
            ? null
            : value.metrics[k] - other.metrics[k],
        ]),
      ),
    });
  }
}
await save("paired-views.csv", csv(paired));
const cases = [];
for (const study of protocol.study_order) {
  const policy = study.startsWith("densification") ? "refine3000" : "selected";
  const policies = study.startsWith("densification")
    ? ["refine900", "refine1800", "refine3000"]
    : ["matched", "selected"];
  const selected = paired
    .filter(
      (p) =>
        p.study === study &&
        p.seed === 42 &&
        p.step === 3600 &&
        p.run.startsWith(policy + "-"),
    )
    .sort(
      (a, b) =>
        b.lpips_delta - a.lpips_delta || a.frame_id.localeCompare(b.frame_id),
    )
    .slice(0, 3);
  const svg = [
    '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="866" viewBox="0 0 1280 866"><rect width="100%" height="100%" fill="#fff"/>',
  ];
  svg.push(
    `<text x="10" y="22" font-family="sans-serif" font-size="16">${esc(study)} · seed42 · largest signed LPIPS delta · same poses</text>`,
  );
  for (let i = 0; i < selected.length; i++) {
    const item = selected[i];
    const pics = [];
    const treatment = rows.find(
      (r) =>
        r.study === study &&
        r.policy === policy &&
        r.seed === 42 &&
        r.step === 3600,
    );
    const view = views
      .get(`${study}/${treatment.run}/3600`)
      .find((v) => v.frame_id === item.frame_id);
    pics.push([
      join(root, treatment.report, view.assets.real),
      "Real reference",
    ]);
    for (const arm of policies) {
      const row = rows.find(
        (r) =>
          r.study === study &&
          r.policy === arm &&
          r.seed === 42 &&
          r.step === 3600,
      );
      const v = views
        .get(`${study}/${row.run}/3600`)
        .find((v) => v.frame_id === item.frame_id);
      pics.push([join(root, row.report, v.assets.rendered), arm]);
    }
    if (pics.length === 3)
      pics.push([
        join(root, treatment.report, view.assets.residual),
        "Selected RGB residual",
      ]);
    const y = 40 + i * 274;
    svg.push(
      `<text x="10" y="${y + 14}" font-family="sans-serif" font-size="13">${esc(item.frame_id)} · signed ΔLPIPS ${item.lpips_delta.toFixed(6)} · ${item.lpips_delta > 0 ? "degradation" : "least improvement"}</text>`,
    );
    for (let j = 0; j < pics.length; j++) {
      const [path, label] = pics[j];
      const bytes = await bound(path);
      svg.push(
        `<text x="${j * 320 + 8}" y="${y + 30}" font-family="sans-serif" font-size="12">${esc(label)}</text><image x="${j * 320}" y="${y + 34}" width="320" height="240" href="data:image/png;base64,${bytes.toString("base64")}"/>`,
      );
    }
    cases.push({
      ...item,
      rule: "top three largest signed LPIPS deltas, seed42/final3600; tie frame ID",
      figure: `${study}-paired.svg`,
    });
  }
  svg.push("</svg>");
  await save(`${study}-paired.svg`, svg.join("\n"));
}
const convergence = [];
for (const study of protocol.study_order)
  for (const run of Object.keys(protocol.studies[study].runs)) {
    const model = join(root, study, run, "model");
    const artifact = JSON.parse(await bound(join(model, "artifact.json")));
    const bytes = await bound(join(model, "training-log.jsonl"));
    if (sha(bytes) !== artifact.files_sha256["training-log.jsonl"])
      throw new Error("Training log binding changed");
    for (const line of bytes.toString("utf8").trim().split("\n")) {
      const r = JSON.parse(line);
      convergence.push({
        study,
        run,
        completed_steps: r.completed_steps,
        optimization_seconds: r.optimization_seconds,
        rgb_l1: r.rgb_l1,
        total_loss: r.total_loss,
        gaussians: r.gaussians,
        peak_vram_allocated_bytes: r.peak_vram_allocated_bytes,
      });
    }
  }
await save("convergence.csv", csv(convergence));
function plot(study, mode) {
  const final = rows.filter(
    (r) => r.study === study && (r.step === 3600 || r.policy === "original"),
  );
  const points =
    mode === "convergence"
      ? convergence
          .filter((r) => r.study === study)
          .map((r) => ({
            ...r,
            policy: r.run.split("-s")[0],
            x: r.completed_steps,
            y: r.rgb_l1,
          }))
      : final.map((r) => ({
          ...r,
          x:
            mode === "runtime"
              ? r.optimization_seconds
              : r.peak_allocated_bytes / 1e6,
          y: r.lpips,
        }));
  const policies = [...new Set(points.map((r) => r.policy))].sort();
  const minX = 0,
    maxX = Math.max(...points.map((r) => r.x)) * 1.12;
  const minY = Math.max(0, Math.min(...points.map((r) => r.y)) * 0.85),
    maxY = Math.max(...points.map((r) => r.y)) * 1.12;
  const px = (x) => 76 + (640 * (x - minX)) / (maxX - minX);
  const py = (y) => 360 - (280 * (y - minY)) / (maxY - minY);
  const svg = [
    '<svg xmlns="http://www.w3.org/2000/svg" width="820" height="490" viewBox="0 0 820 490"><rect width="100%" height="100%" fill="white"/>',
    `<text x="20" y="26" font-family="sans-serif" font-size="17">${esc(study)} · ${mode === "convergence" ? "training RGB L1 diagnostics" : "final-budget LPIPS / " + mode}</text>`,
    `<text x="20" y="48" font-family="sans-serif" font-size="12">${mode === "convergence" ? "Training samples; not held-out evidence." : "Individual seeds; crossbars show mean ± sample SD. Original uses1200; others3600."}</text>`,
  ];
  for (let t = 0; t <= 5; t++) {
    const x = (maxX * t) / 5,
      y = minY + ((maxY - minY) * t) / 5;
    svg.push(
      `<path d="M76 ${py(y)}H716" stroke="#d4d9df"/><text x="68" y="${py(y) + 4}" text-anchor="end" font-family="sans-serif" font-size="11">${y.toFixed(3)}</text><text x="${px(x)}" y="380" text-anchor="middle" font-family="sans-serif" font-size="11">${x.toFixed(0)}</text>`,
    );
  }
  for (let i = 0; i < policies.length; i++) {
    const policy = policies[i],
      group = points.filter((r) => r.policy === policy),
      color = colors[i % colors.length];
    svg.push(
      `<text x="${35 + i * 255}" y="451" fill="${color}" font-family="sans-serif" font-size="13">${esc(policy)}</text>`,
    );
    if (mode === "convergence")
      for (const run of [...new Set(group.map((r) => r.run))]) {
        const g = group.filter((r) => r.run === run);
        svg.push(
          `<polyline fill="none" stroke="${color}" stroke-width="1" opacity=".5" points="${g.map((r) => `${px(r.x)},${py(r.y)}`).join(" ")}"/>`,
        );
      }
    else {
      for (const p of group)
        svg.push(
          `<circle cx="${px(p.x)}" cy="${py(p.y)}" r="4" fill="${color}"/>`,
        );
      const x = mean(group.map((r) => r.x)),
        y = mean(group.map((r) => r.y)),
        sx = sd(group.map((r) => r.x)) ?? 0,
        sy = sd(group.map((r) => r.y)) ?? 0;
      svg.push(
        `<path d="M${px(x - sx)} ${py(y)}H${px(x + sx)}M${px(x)} ${py(y - sy)}V${py(y + sy)}" fill="none" stroke="${color}" stroke-width="2"/>`,
      );
    }
  }
  svg.push(
    `<text x="380" y="410" text-anchor="middle" font-family="sans-serif" font-size="13">${mode === "runtime" ? "Optimizer time (s), ordered local observations" : mode === "memory" ? "Peak PyTorch allocated memory (MB), not board usage" : "Completed optimizer updates"}</text><text x="20" y="476" font-family="sans-serif" font-size="11">${mode === "convergence" ? "Raw logs are hash-bound to final model artifacts." : "Separate datasets/splits; three seeds; no significance or unseen-site claim."}</text></svg>`,
  );
  return svg.join("\n");
}
for (const study of protocol.study_order)
  for (const mode of ["runtime", "memory", "convergence"])
    await save(`${study}-${mode}.svg`, plot(study, mode));
await json("cases.json", cases);
outputNames.push("cases.json");
await bound(fileURLToPath(import.meta.url));
await bound(join(project, "docs/IMPROVEMENT_DIAGNOSTIC_EXPORT.md"));
await json("replay.json", {
  numeric_comparisons: comparisons,
  measured_rows: rows.length,
  paired_views: paired.length,
  training_records: convergence.length,
  all_numeric_checks_passed: true,
  ground_truth_detection: "pending_human_review",
  source_commit: protocol.source_commit,
  diagnostic_source_sha256:
    inputs[fileURLToPath(import.meta.url).slice(project.length + 1)],
  input_sha256: inputs,
  generated_utc: new Date().toISOString(),
});
outputNames.push("replay.json");
await json(
  "files.json",
  Object.fromEntries(
    await Promise.all(
      outputNames.map(async (name) => [
        name,
        sha(await readFile(join(out, name))),
      ]),
    ),
  ),
);
console.log(
  JSON.stringify({
    out,
    numeric_comparisons: comparisons,
    paired_views: paired.length,
    training_records: convergence.length,
  }),
);
