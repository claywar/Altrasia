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

test("zone labels are on structure bands not left margin", async ({ page }) => {
  await loadDemoWorld(page);
  const zone = page.locator(".map-zone-label").first();
  await expect(zone).toBeVisible();
  const box = await zone.boundingBox();
  expect(box).not.toBeNull();
  if (box) {
    const panel = await page.locator(".spatial-panel .minimap svg").boundingBox();
    if (panel) {
      const relX = (box.x - panel.x) / panel.width;
      expect(relX).toBeGreaterThan(0.15);
    }
  }
});

test("edge step badges use compact numeric pills", async ({ page }) => {
  await loadDemoWorld(page);
  const badges = page.locator(".map-edge-badge text");
  expect(await badges.count()).toBeGreaterThanOrEqual(1);
  await expect(badges.first()).toHaveText("2");
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
  await expect(page.locator('.map-overlay[role="dialog"]')).toBeVisible();
});

test("world map overlay shows multiple structures", async ({ page }) => {
  await loadDemoWorld(page);
  await page.keyboard.press("m");
  await expect(page.locator(".map-canvas-structures li")).toHaveCount(3);
});
