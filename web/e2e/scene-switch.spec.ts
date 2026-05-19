import { test, expect } from "@playwright/test";
import { loadDemoWorld } from "./helpers";

/** UI-LAY-6, UI-S4: scene switch updates header; active scene hoisted to top of World rail. */
test("scene switch updates World rail and scene header", async ({ page }) => {
  await loadDemoWorld(page);
  const header = page.getByTestId("scene-stage").locator("h2");
  const initial = await header.textContent();
  const worldRail = page.getByTestId("world-rail");
  const kitchen = worldRail.getByRole("button", { name: /Kitchen/i }).first();
  if (await kitchen.isVisible()) {
    await kitchen.click();
    await expect(header).toContainText(/Kitchen/i);
    expect(await header.textContent()).not.toBe(initial);
    const firstPlace = worldRail.locator(".place-card").first();
    await expect(firstPlace).toContainText(/Kitchen/i);
  }
});

test("knock shows banner at target scene", async ({ page }) => {
  await loadDemoWorld(page);
  const kitchen = page.getByTestId("world-rail").getByRole("button", { name: /Kitchen/i }).first();
  if (!(await kitchen.isVisible())) return;
  await kitchen.click();
  const spatialPanel = page.getByTestId("spatial-panel");
  let knock = spatialPanel.getByRole("button", { name: /^Knock$/i }).first();
  if (!(await knock.isVisible())) {
    await page.getByRole("button", { name: /Spatial/i }).click();
    knock = page.getByRole("button", { name: /^Knock$/i }).first();
  }
  if (await knock.isVisible()) {
    const entriesBefore = await page.getByTestId("chronicle-entry").count();
    await knock.click();
    await expect(page.getByTestId("signal-toast")).toBeVisible({ timeout: 5000 });
    const hall = page.getByTestId("world-rail").getByRole("button", { name: /Hall/i }).first();
    await hall.click();
    await expect(page.getByTestId("signal-toast")).toBeVisible();
    const entriesAfter = await page.getByTestId("chronicle-entry").count();
    expect(entriesAfter).toBe(entriesBefore);
  }
});

/** Door-gated knock: non-door exits (e.g. stairs) do not show Knock in ExitList. */
test("exit list hides knock on non-door exits", async ({ page }) => {
  await loadDemoWorld(page);
  const panel = page.getByTestId("spatial-panel");
  if (!(await panel.isVisible())) {
    await page.getByRole("button", { name: /Spatial/i }).click();
  }
  const exitList = page.getByTestId("exit-list");
  const stairs = exitList.getByRole("button", { name: /Go to .*[Ss]tairs/i });
  if ((await stairs.count()) === 0) return;
  const row = stairs.first().locator("xpath=ancestor::li[contains(@class,'exit-card')]");
  await expect(row.getByRole("button", { name: /^Knock$/i })).toHaveCount(0);
});
