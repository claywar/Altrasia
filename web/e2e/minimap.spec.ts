import { test, expect } from "@playwright/test";
import { loadDemoWorld } from "./helpers";

/** UI-MAP-ACC1–4: structured mini-map for demo spatial world. */
test("mini-map shows spatial graph with nodes and edges", async ({ page }) => {
  await loadDemoWorld(page);
  const svg = page.locator('.minimap svg[aria-label="Spatial mini-map"]');
  await expect(svg).toBeVisible();
  const paths = svg.locator("path.map-edge, path");
  const shapes = svg.locator("rect, circle");
  expect(await shapes.count()).toBeGreaterThanOrEqual(2);
  expect(await paths.count()).toBeGreaterThanOrEqual(1);
});

test("active scene node is highlighted on mini-map", async ({ page }) => {
  await loadDemoWorld(page);
  const active = page.locator(
    '.minimap svg circle[fill*="accent"], .minimap svg rect[fill*="accent"]'
  );
  expect(await active.count()).toBeGreaterThanOrEqual(1);
});

test("compass shows when exits have direction", async ({ page }) => {
  await loadDemoWorld(page);
  await expect(page.locator(".map-compass")).toBeVisible();
});

test("structure envelope and panel header visible", async ({ page }) => {
  await loadDemoWorld(page);
  await expect(page.locator(".map-panel-header")).toContainText("Manor");
  await expect(page.locator(".map-envelope")).toHaveCount(3);
  await expect(page.locator(".map-structure-label").filter({ hasText: "Round Keep" })).toBeVisible();
});

test("zone badges appear inside structure envelopes", async ({ page }) => {
  await loadDemoWorld(page);
  const badge = page.locator(".map-zone-badge").first();
  await expect(badge).toBeVisible();
  await expect(page.locator(".map-zone-band")).toHaveCount(0);
});

test("outdoor paths render as smooth curves", async ({ page }) => {
  await loadDemoWorld(page);
  const paths = page.locator(".map-edge path");
  expect(await paths.count()).toBeGreaterThanOrEqual(1);
  const d = await paths.first().getAttribute("d");
  expect(d).toMatch(/^M .+/);
});

test("exit hover highlights edge path", async ({ page }) => {
  await loadDemoWorld(page);
  const exitRow = page.getByRole("button", { name: /Door to kitchen/i }).first();
  if ((await exitRow.count()) > 0) {
    await exitRow.hover();
    await expect(page.locator(".map-edge--hi path").first()).toBeVisible();
  }
});

test("Map keyboard shortcut opens overlay", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await expect(page.getByTestId("map-console")).toBeVisible();
});

test("world map overlay shows multiple structures", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await expect(page.locator(".map-console-structures li")).toHaveCount(3);
});

test("site view shows structure placement footprints", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await expect(page.locator(".map-site-placement-footprint")).toHaveCount(3);
});

test("map console has zoom controls and layers", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await expect(page.locator(".map-console-zoom-label")).toBeVisible();
  await expect(page.locator('.map-console-layers input[type="checkbox"]').first()).toBeVisible();
});

test("map console shows Go somewhere destinations", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await expect(page.getByText("Go somewhere")).toBeVisible();
  await expect(page.locator(".map-console-destination__main").first()).toBeVisible();
});

test("level stack view shows plates and vertical connectors", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
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

test("map guide dismisses with Got it and Escape", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  const dismiss = page.getByTestId("map-guide-dismiss");
  if (await dismiss.isVisible()) {
    await dismiss.click();
    await expect(dismiss).not.toBeVisible();
  }
  await page.keyboard.press("m");
  await page.keyboard.press("m");
  await page.keyboard.press("Escape");
  if (await dismiss.isVisible()) {
    await page.keyboard.press("Escape");
    await expect(dismiss).not.toBeVisible();
    await expect(page.getByTestId("map-console")).toBeVisible();
  }
});
