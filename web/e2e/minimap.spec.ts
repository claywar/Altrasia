import { test, expect } from "@playwright/test";
import { loadDemoWorld } from "./helpers";

/** UI-MAP-ACC1–4: structured mini-map for demo spatial world. */
test("mini-map shows spatial graph with nodes and edges", async ({ page }) => {
  await loadDemoWorld(page);
  const svg = page.locator('.minimap svg[aria-label="Spatial mini-map"]');
  await expect(svg).toBeVisible();
  const lines = svg.locator("line");
  const shapes = svg.locator("rect, circle");
  await expect(lines).toHaveCount(await lines.count());
  expect(await shapes.count()).toBeGreaterThanOrEqual(2);
  expect(await lines.count()).toBeGreaterThanOrEqual(1);
});

test("active scene node is highlighted on mini-map", async ({ page }) => {
  await loadDemoWorld(page);
  const active = page.locator('.minimap svg circle[fill*="accent"], .minimap svg rect[fill*="accent"]');
  expect(await active.count()).toBeGreaterThanOrEqual(1);
});
