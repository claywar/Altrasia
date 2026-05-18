import { test, expect } from "@playwright/test";
import { loadDemoWorld } from "./helpers";

/** UI-LAY-6, UI-S4: scene switch updates header; knock banner without auto NPC line. */
test("scene switch updates Places and scene header", async ({ page }) => {
  await loadDemoWorld(page);
  const header = page.locator(".scene-header h2");
  const initial = await header.textContent();
  const kitchen = page.locator("aside.panel.right .rail-list li", { hasText: /Kitchen/i }).first();
  if (await kitchen.isVisible()) {
    await kitchen.click();
    await expect(header).toContainText(/Kitchen/i);
    expect(await header.textContent()).not.toBe(initial);
  }
});

test("knock shows banner at target scene", async ({ page }) => {
  await loadDemoWorld(page);
  const kitchenLi = page.locator("aside.panel.right .rail-list li", { hasText: /Kitchen/i }).first();
  if (!(await kitchenLi.isVisible())) return;
  await kitchenLi.click();
  const knockBtn = page.getByRole("button", { name: /^Knock$/i }).first();
  if (await knockBtn.isVisible()) {
    const bubblesBefore = await page.locator(".bubble").count();
    await knockBtn.click();
    await expect(page.locator(".signal-banner")).toBeVisible({ timeout: 5000 });
    const hall = page.locator("aside.panel.right .rail-list li", { hasText: /Hall/i }).first();
    await hall.click();
    await expect(page.locator(".signal-banner")).toBeVisible();
    const bubblesAfter = await page.locator(".bubble").count();
    expect(bubblesAfter).toBe(bubblesBefore);
  }
});
