import { type Page, expect } from "@playwright/test";

/** T-112: shared demo world load for UI acceptance specs. */
export async function loadDemoWorld(page: Page): Promise<void> {
  await page.goto("/");
  await page.getByRole("button", { name: /load demo world/i }).click();
  await expect(page.getByPlaceholder(/speak as persona/i)).toBeVisible({ timeout: 20_000 });
  await expect(page.locator(".scene-header h2")).toBeVisible();
}

export async function sendPublicLine(page: Page, text: string): Promise<void> {
  await page.getByPlaceholder(/speak as persona/i).fill(text);
  await page.getByRole("button", { name: /^send$/i }).click();
}

export async function waitQueueIdle(page: Page, timeoutMs = 15_000): Promise<void> {
  await expect(page.locator(".queue-status")).toContainText(/GPU idle/i, { timeout: timeoutMs });
}
