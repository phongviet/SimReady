// Capture the actual saved real-TUM application, without changing scene state.
import { chromium, expect } from "@playwright/test";
import { readFile, mkdir, writeFile } from "node:fs/promises";
const credentials = JSON.parse(
  await readFile(
    "artifacts/workstation-review-1/local-credentials.json",
    "utf8",
  ),
);
const output = ".cache/workstation-review-1";
await mkdir(output, { recursive: true });
const browser = await chromium.launch({
  args: [
    "--enable-unsafe-swiftshader",
    "--use-angle=swiftshader",
    "--disable-dev-shm-usage",
  ],
});
const context = await browser.newContext({
  viewport: { width: 1600, height: 1000 },
});
await context.addInitScript(
  (token) => sessionStorage.setItem("simready-token", token),
  credentials.builder.token,
);
const page = await context.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const views = [
  ["saved", "Saved camera", /Saved Gaussian render/],
  ["evaluation", "Evaluation"],
  ["research", "Research"],
  ["navigation", "Navigation"],
  ["review", "Readiness / review"],
];
await page.goto("http://127.0.0.1:8002");
await expect(
  page.getByRole("heading", { name: "TUM fr1 desk · recorded real scene" }),
).toBeVisible();
for (const [id, name, image] of views) {
  await page.getByRole("button", { name, exact: true }).click();
  if (image)
    await expect
      .poll(() =>
        page
          .getByRole("img", { name: image })
          .evaluate((img) => img.complete && img.naturalWidth > 0),
      )
      .toBe(true);
  if (id === "evaluation")
    await expect(
      page.getByText("18 frozen test views", { exact: false }),
    ).toBeVisible();
  if (id === "research")
    await expect(
      page.getByRole("region", { name: "Reconstruction study" }),
    ).toBeVisible();
  if (id === "review")
    await expect(page.getByText("Loading recorded evidence…")).toHaveCount(0);
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all(
      Array.from(document.images, (img) => img.decode().catch(() => {})),
    );
  });
  await page.screenshot({
    path: `${output}/${id}-desktop.png`,
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  const toggle = page.getByRole("button", { name: "Toggle scene library" });
  if ((await toggle.getAttribute("aria-expanded")) === "true")
    await toggle.click();
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
  await page.screenshot({ path: `${output}/${id}-mobile.png`, fullPage: true });
  await page.setViewportSize({ width: 1600, height: 1000 });
  if ((await toggle.getAttribute("aria-expanded")) === "false")
    await toggle.click();
}
await writeFile(
  `${output}/capture.json`,
  JSON.stringify(
    {
      dataset: "TUM fr1 desk",
      source: "saved baseline-1; existing report",
      actual_human_review: false,
      page_errors: errors,
      captured_utc: new Date().toISOString(),
    },
    null,
    2,
  ),
);
await browser.close();
if (errors.length) throw new Error(errors.join("\n"));
