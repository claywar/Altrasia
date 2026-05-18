import { test, expect } from "@playwright/test";
import { loadDemoWorld } from "./helpers";

/** UI-M4: memory inspector from People rail. */
test("open memory inspector from People", async ({ page }) => {
  await loadDemoWorld(page);
  const memoryBtn = page.getByRole("button", { name: /^Memory$/i }).first();
  await expect(memoryBtn).toBeVisible({ timeout: 10_000 });
  await memoryBtn.click();
  await expect(page.getByRole("dialog").filter({ hasText: /memory|loci|diary/i })).toBeVisible({
    timeout: 5000,
  });
});
