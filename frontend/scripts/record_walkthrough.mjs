// Record actual product actions against a fresh real-TUM registry; no mocked responses.
import { chromium, expect } from "@playwright/test";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { parseArgs } from "node:util";
const { values } = parseArgs({
  options: {
    root: { type: "string" },
    out: { type: "string" },
    url: { type: "string", default: "http://127.0.0.1:8002" },
  },
});
if (!values.root || !values.out) throw Error("--root and --out are required");
const out = resolve(values.out);
await mkdir(out, { recursive: false });
const credentials = JSON.parse(
  await readFile(resolve(values.root, "local-credentials.json"), "utf8"),
);
const browser = await chromium.launch({
  args: [
    "--enable-unsafe-swiftshader",
    "--use-angle=swiftshader",
    "--disable-dev-shm-usage",
  ],
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  recordVideo: { dir: out, size: { width: 1440, height: 1000 } },
});
await context.addInitScript((token) => {
  if (!sessionStorage.getItem("simready-token"))
    sessionStorage.setItem("simready-token", token);
}, credentials.builder.token);
const page = await context.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const started = Date.now(),
  chapters = [];
let completed = false;
async function chapter(name) {
  chapters.push({ name, seconds: (Date.now() - started) / 1000 });
  await page.waitForTimeout(2200);
}
try {
  await page.goto(values.url);
  await expect(
    page.getByRole("heading", { name: "TUM fr1 desk · recorded real scene" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Saved camera", exact: true }).click();
  await expect(
    page.getByRole("img", { name: /Saved Gaussian render/ }),
  ).toBeVisible();
  await chapter(
    "Saved genuine reconstruction: TUM fr1 desk; source run, not live training",
  );
  await page.getByRole("button", { name: "Evaluation", exact: true }).click();
  const evaluation = page.getByRole("region", { name: "Evaluation explorer" });
  await expect(
    evaluation.getByText("18 frozen test views", { exact: false }),
  ).toBeVisible();
  await chapter("Real input and learned render: measured held-out comparison");
  await page.screenshot({
    path: resolve(out, "real-comparison.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "3D scene", exact: true }).click();
  await expect(
    page.getByText("Gaussian scene loaded", { exact: true }),
  ).toBeVisible({ timeout: 45000 });
  await chapter(
    "Interactive learned Gaussian scene; overlays are not depth-composited",
  );
  await page.getByRole("button", { name: "＋ Box", exact: true }).click();
  await page
    .getByLabel("Object name", { exact: true })
    .fill("Recorded floor route box");
  for (const [axis, v] of [
    ["X", "-1"],
    ["Y", "0.15"],
    ["Z", "-1.8"],
  ])
    await page.getByLabel(`Position (m) ${axis}`, { exact: true }).fill(v);
  for (const [axis, v] of [
    ["X", "0.15"],
    ["Y", "0.3"],
    ["Z", "0.15"],
  ])
    await page.getByLabel(`Size (m) ${axis}`, { exact: true }).fill(v);
  await page.getByLabel("Collision proxy", { exact: true }).check();
  await page
    .getByRole("button", { name: "Save revision", exact: true })
    .click();
  await expect(page.getByText(/Saved revision/)).toBeVisible();
  await chapter(
    "Insert metric rigid box, persist its shared mesh/collider transform",
  );
  await page.getByRole("button", { name: "Evaluation", exact: true }).click();
  await chapter(
    "Base-render QA remains frozen; edited-scene perception is unverified",
  );
  await page.getByRole("button", { name: "Navigation", exact: true }).click();
  const nav = page.getByRole("region", { name: "Navigation simulator" });
  await nav
    .getByRole("button", { name: "Run navigation", exact: true })
    .click();
  await expect(nav.getByText("Goal reached", { exact: true })).toBeVisible({
    timeout: 30000,
  });
  const slider = nav.getByRole("slider", { name: "Replay position" });
  await slider.focus();
  await slider.press("End");
  await chapter(
    "Observed coarse-map simulated route replay; unknown space remains blocked",
  );
  await page.screenshot({
    path: resolve(out, "real-navigation.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Readiness / review", exact: true })
    .click();
  const panel = page.getByRole("region", {
    name: "Readiness and scoped review",
  });
  await panel
    .getByLabel("Named experiment")
    .fill("Recorded local known-map box-route regression");
  await panel.getByLabel("Acknowledge measured limits").check();
  await panel
    .getByRole("button", { name: "Submit for independent review" })
    .click();
  await expect(page.locator(".draft-badge")).toContainText("submitted");
  await chapter(
    "Builder submits a limited regression with measured failures acknowledged",
  );
  // Switch fixture roles without recording a credential on screen.
  await page.evaluate(
    (token) => sessionStorage.setItem("simready-token", token),
    credentials.reviewer.token,
  );
  await page.reload();
  await expect(page.locator(".account-bar")).toContainText("Local Reviewer");
  await page
    .getByRole("button", { name: "Readiness / review", exact: true })
    .click();
  await panel
    .getByLabel("Reviewer justification")
    .fill(
      "Automated recorded local-role fixture: approve only this known-map route regression and listed measured reference cameras. Not human endorsement, detector accuracy or safety certification.",
    );
  await panel
    .getByRole("button", { name: "Approve scoped experiment" })
    .click();
  await expect(
    panel.getByText("usable for declared test", { exact: true }),
  ).toBeVisible();
  await panel.getByRole("button", { name: "Build reviewed export" }).click();
  await expect(
    panel.getByRole("link", { name: /Download reviewed ZIP/ }),
  ).toBeVisible({ timeout: 30000 });
  await chapter(
    "Distinct automated local Reviewer: scoped decision, audit and verified ZIP",
  );
  await page.screenshot({
    path: resolve(out, "real-review.png"),
    fullPage: true,
  });
  expect(errors).toEqual([]);
  completed = true;
} finally {
  await writeFile(
    resolve(out, "chapters.json"),
    JSON.stringify(
      {
        completed,
        scope:
          "Actual saved real-TUM model/report; automated local role fixture; no live retraining or human endorsement",
        chapters,
        page_errors: errors,
      },
      null,
      2,
    ) + "\n",
  );
  await context.close();
  const video = await page.video().path();
  await writeFile(resolve(out, "video-path.txt"), video + "\n");
  await browser.close();
}
