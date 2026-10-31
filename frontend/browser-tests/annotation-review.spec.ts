// Synthetic UI fixture only. This test never approves production annotations.
import { test, expect } from "./helpers";
import { spawn, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { resolve } from "node:path";
import { createHash } from "node:crypto";

test("annotation review keeps drafts separate and resets review on changes", async ({
  page,
}) => {
  const root = mkdtempSync(resolve("../.cache/annotation-ui-test-"));
  const python = resolve("../.venv/bin/python");
  const result = spawnSync(
    python,
    [
      "-c",
      `from pathlib import Path
from simready.data.synthetic import make_synthetic
from simready.annotations.package import export
root=Path(${JSON.stringify(root)})
make_synthetic(root/'fixture')
export(root/'fixture',root/'review')`,
    ],
    { encoding: "utf8" },
  );
  expect(result.status, result.stderr).toBe(0);
  const server = spawn(
    "python3",
    [
      "-m",
      "http.server",
      "8094",
      "--bind",
      "127.0.0.1",
      "--directory",
      root + "/review",
    ],
    { stdio: "ignore" },
  );
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  try {
    await expect
      .poll(async () => {
        try {
          return (await page.request.get("http://127.0.0.1:8094")).status();
        } catch {
          return 0;
        }
      })
      .toBe(200);
    await page.goto("http://127.0.0.1:8094");
    await expect(
      page.getByRole("button", { name: "Approve reviewed annotations" }),
    ).toBeDisabled();
    await expect(
      page.getByText("0 / 2 frames reviewed", { exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Add box using coordinates" })
      .click();
    await expect(page.getByLabel("Width", { exact: true })).toHaveValue("50");
    const reviewed = page.getByLabel(/I reviewed all visible/);
    await reviewed.check();
    await expect(
      page.getByText("1 / 2 frames reviewed", { exact: true }),
    ).toBeVisible();
    await page.getByLabel("Width", { exact: true }).fill("40");
    await page.getByLabel("Height", { exact: true }).focus();
    await expect(reviewed).not.toBeChecked();
    const pending = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download COCO draft" }).click();
    const download = await pending;
    const path = root + "/download.coco.json";
    await download.saveAs(path);
    const data = readFileSync(path);
    const coco = JSON.parse(data.toString());
    expect(coco.info.status).toBe("draft_not_ground_truth");
    expect(coco.annotations).toHaveLength(1);
    expect(createHash("sha256").update(data).digest("hex")).toHaveLength(64);
    await reviewed.check();
    await page.getByLabel("Import draft COCO").setInputFiles(path);
    await expect(
      page.getByText("0 / 2 frames reviewed", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Approve reviewed annotations" }),
    ).toBeDisabled();
    expect(errors).toEqual([]);
  } finally {
    server.kill();
    rmSync(root, { recursive: true, force: true });
  }
});
