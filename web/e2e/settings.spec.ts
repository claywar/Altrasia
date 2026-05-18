import { test, expect } from "@playwright/test";
import { loadDemoWorld } from "./helpers";

/** UI-SET-*, HB-4/5: settings panel and heartbeat toggle. */
test("settings opens and heartbeat toggle persists in session", async ({ page }) => {
  await loadDemoWorld(page);
  await page.getByRole("button", { name: /^Settings$/i }).click();
  await expect(page.getByRole("dialog", { name: /^Settings$/i })).toBeVisible();
  await page.getByRole("tab", { name: /^Server$/i }).click();
  const hb = page.getByLabel(/enable server heartbeat/i);
  await expect(hb).toBeVisible();
  const wasChecked = await hb.isChecked();
  await hb.setChecked(!wasChecked);
  await page.getByRole("button", { name: /Esc — Close/i }).click();
  await page.getByRole("button", { name: /^Settings$/i }).click();
  await page.getByRole("tab", { name: /^Server$/i }).click();
  await expect(page.getByLabel(/enable server heartbeat/i)).toBeChecked({ checked: !wasChecked });
  await page.getByLabel(/enable server heartbeat/i).setChecked(wasChecked);
});
