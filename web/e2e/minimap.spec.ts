import { test, expect } from "@playwright/test";
import { loadDemoWorld } from "./helpers";

/** UI-MAP-ACC1–4: spatial panel and 3D minimap for demo world. */
test("spatial panel shows 3D minimap", async ({ page }) => {
  await loadDemoWorld(page);
  await expect(page.getByTestId("minimap-3d")).toBeVisible();
});

test("spatial panel header shows structure context", async ({ page }) => {
  await loadDemoWorld(page);
  await expect(page.locator(".map-panel-header")).toContainText("Manor");
});

async function openDiagramMap(page: import("@playwright/test").Page) {
  await page.keyboard.press("m");
  await page.getByRole("button", { name: /diagram/i }).click();
}

test("structure envelope visible in diagram map", async ({ page }) => {
  await loadDemoWorld(page);
  await openDiagramMap(page);
  await expect(page.locator(".map-envelope")).toHaveCount(3);
  await expect(page.locator(".map-structure-label").filter({ hasText: "Round Keep" })).toBeVisible();
});

test("zone badges appear in diagram site view", async ({ page }) => {
  await loadDemoWorld(page);
  await openDiagramMap(page);
  const badge = page.locator(".map-zone-badge").first();
  await expect(badge).toBeVisible();
});

test("outdoor paths render as smooth curves in diagram view", async ({ page }) => {
  await loadDemoWorld(page);
  await openDiagramMap(page);
  const paths = page.locator(".map-edge path");
  expect(await paths.count()).toBeGreaterThanOrEqual(1);
  const d = await paths.first().getAttribute("d");
  expect(d).toMatch(/^M .+/);
});

test("exit hover highlights edge in diagram view", async ({ page }) => {
  await loadDemoWorld(page);
  await openDiagramMap(page);
  const exitRow = page.getByRole("button", { name: /Door to kitchen/i }).first();
  if ((await exitRow.count()) > 0) {
    await exitRow.hover();
    await expect(page.locator(".map-edge--hi path").first()).toBeVisible();
  }
});

test("Map keyboard shortcut opens 3D overlay", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await expect(page.getByTestId("map-explorer-3d")).toBeVisible();
});

test("diagram view shows structure list", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await page.getByRole("button", { name: /diagram/i }).click();
  await expect(page.locator(".map-console-structures li")).toHaveCount(3);
});

test("site view shows structure placement footprints", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await page.getByRole("button", { name: /diagram/i }).click();
  await expect(page.locator(".map-site-placement-footprint")).toHaveCount(3);
});

test("map console has zoom controls and layers", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await page.getByRole("button", { name: /diagram/i }).click();
  await expect(page.locator(".map-console-zoom-label")).toBeVisible();
  await expect(page.locator('.map-console-layers input[type="checkbox"]').first()).toBeVisible();
});

test("map console shows Go somewhere destinations", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await page.getByRole("button", { name: /diagram/i }).click();
  await expect(page.getByText("Go somewhere")).toBeVisible();
  await expect(page.locator(".map-console-destination__main").first()).toBeVisible();
});

test("level stack view shows plates and vertical connectors", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await page.getByRole("button", { name: /diagram/i }).click();
  const stackTab = page.getByRole("button", { name: /stack/i });
  if ((await stackTab.count()) === 0) {
    test.skip();
    return;
  }
  await stackTab.click();
  await expect(page.locator(".level-stack-panel")).toBeVisible();
  await expect(page.locator(".level-stack-selector__btn")).toHaveCount(3);
  await expect(page.locator(".level-stack__svg")).toBeVisible();
  await expect(page.locator(".level-stack-connector")).toHaveCount(2);
  await expect(page.locator(".iso-room").first()).toBeVisible();
  await expect(page.locator(".level-stack-annotation--active")).toBeVisible();
});

test("map guide dismisses with Got it in diagram view", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await page.getByRole("button", { name: /diagram/i }).click();
  const dismiss = page.getByTestId("map-guide-dismiss");
  if (await dismiss.isVisible()) {
    await dismiss.click();
    await expect(dismiss).not.toBeVisible();
  }
});
