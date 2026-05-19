import { test, expect } from "@playwright/test";
import { loadDemoWorld } from "./helpers";

/** MAP-ACC: 3D map explorer and navigation. */
test("M opens 3D world map explorer", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await expect(page.getByTestId("map-explorer-3d")).toBeVisible();
  await expect(page.getByTestId("map3d-inspector")).toBeVisible();
  await expect(page.getByText("You are here")).toBeVisible();
});

test("3D map inspector lists nearby exits", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await expect(page.getByText("Nearby exits")).toBeVisible();
});

test("Diagram toggle returns to SVG map console", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await page.getByRole("button", { name: /diagram/i }).click();
  await expect(page.getByTestId("map-console")).toBeVisible();
  await page.getByRole("button", { name: /3d view/i }).click();
  await expect(page.getByTestId("map-explorer-3d")).toBeVisible();
});

test("sidebar 3D minimap is visible", async ({ page }) => {
  await loadDemoWorld(page);
  await expect(page.getByTestId("minimap-3d")).toBeVisible();
});

test("scene header shows exit compass when available", async ({ page }) => {
  await loadDemoWorld(page);
  const compass = page.locator(".scene-stage__compass");
  if ((await compass.count()) > 0) {
    await expect(compass).toBeVisible();
  }
});
