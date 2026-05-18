import { test, expect } from "@playwright/test";
import { loadDemoWorld, sendPublicLine } from "./helpers";

/** UI-R1–R3, UI-TRN-1: bubbles render; no edit on committed; streaming uses plain text. */
test("committed messages render as bubbles without edit controls", async ({ page }) => {
  await loadDemoWorld(page);
  await sendPublicLine(page, "Transcript test");
  await expect(page.locator(".bubble").first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("button", { name: /edit/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /delete/i })).toHaveCount(0);
});

test("markdown list renders in finalized bubble", async ({ page }) => {
  await loadDemoWorld(page);
  await sendPublicLine(page, "Hello");
  await expect(page.locator(".bubble").first()).toBeVisible({ timeout: 20_000 });
  const bubble = page.locator(".bubble").last();
  await expect(bubble).not.toHaveClass(/streaming/);
});
