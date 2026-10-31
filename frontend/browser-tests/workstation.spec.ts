import { test, expect } from "./helpers";

test("workstation navigation collapses without losing scene and supports mobile", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Analytic plane · CPU demo" }),
  ).toBeVisible();
  await expect(
    page.getByText("Gaussian scene loaded", { exact: true }),
  ).toBeVisible({ timeout: 45000 });
  const toggle = page.getByRole("button", { name: "Toggle scene library" });
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await expect
    .poll(
      () =>
        page.locator("canvas").evaluate((canvas: HTMLCanvasElement) => {
          const gl = canvas.getContext("webgl2")!;
          const pixels = new Uint8Array(canvas.width * canvas.height * 4);
          gl.readPixels(
            0,
            0,
            canvas.width,
            canvas.height,
            gl.RGBA,
            gl.UNSIGNED_BYTE,
            pixels,
          );
          const colors = new Set<string>();
          for (
            let i = 0;
            i < pixels.length;
            i += Math.max(4, Math.floor(pixels.length / 1024 / 4) * 4)
          )
            colors.add(`${pixels[i]},${pixels[i + 1]},${pixels[i + 2]}`);
          return colors.size;
        }),
      { timeout: 45000 },
    )
    .toBeGreaterThan(8);
  await page.screenshot({
    path: "../.cache/playwright-results/workstation-desktop.png",
    fullPage: true,
  });
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(
    page.getByRole("navigation", { name: "Workbench views" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Evaluation", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Evaluation", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await page.getByRole("button", { name: "3D scene", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
  await expect
    .poll(
      () =>
        page.locator("canvas").evaluate((canvas: HTMLCanvasElement) => {
          const gl = canvas.getContext("webgl2")!;
          const pixels = new Uint8Array(canvas.width * canvas.height * 4);
          gl.readPixels(
            0,
            0,
            canvas.width,
            canvas.height,
            gl.RGBA,
            gl.UNSIGNED_BYTE,
            pixels,
          );
          const colors = new Set<string>();
          for (
            let i = 0;
            i < pixels.length;
            i += Math.max(4, Math.floor(pixels.length / 1024 / 4) * 4)
          )
            colors.add(`${pixels[i]},${pixels[i + 1]},${pixels[i + 2]}`);
          return colors.size;
        }),
      { timeout: 45000 },
    )
    .toBeGreaterThan(8);
  await page.screenshot({
    path: "../.cache/playwright-results/workstation-mobile.png",
    fullPage: true,
  });
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await expect(page.locator("#scene-library-content")).toBeVisible();
});

test("view URLs restore history and object deletion can be undone", async ({
  page,
}) => {
  await page.goto("/?view=research");
  await expect(
    page.getByRole("region", { name: "Reconstruction study" }),
  ).toBeVisible();
  await expect(page.locator(".inspector")).toBeHidden();
  await page.getByRole("button", { name: "3D scene", exact: true }).click();
  await expect(page).toHaveURL(/view=3d/);
  await expect(page.locator(".inspector")).toBeVisible();
  await page.getByRole("button", { name: "＋ Box", exact: true }).click();
  const name = await page
    .getByLabel("Object name", { exact: true })
    .inputValue();
  await page
    .getByRole("button", { name: "Delete object", exact: true })
    .click();
  await page.getByRole("button", { name: "Undo removal", exact: true }).click();
  await expect(page.getByLabel("Object name", { exact: true })).toHaveValue(
    name,
  );
  await page
    .getByRole("button", { name: "Reload / discard", exact: true })
    .click();
  await page.getByRole("button", { name: "Evaluation", exact: true }).click();
  await expect(page).toHaveURL(/view=evaluation/);
  await expect(page.locator(".inspector")).toBeHidden();
  await page.goBack();
  await expect(page).toHaveURL(/view=3d/);
  await expect(page.locator(".inspector")).toBeVisible();
});
