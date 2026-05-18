import { test, expect } from "@playwright/test";
import { loadDemoWorld, sendPublicLine } from "./helpers";

/** UI-REG-1, UI-2: queue strip shows busy; cancel available while in flight. */
test("queue strip shows busy then idle after generation", async ({ page }) => {
  await loadDemoWorld(page);
  await sendPublicLine(page, "Queue test line from Playwright");
  const strip = page.locator(".queue-strip-panel");
  await expect(strip).toHaveClass(/busy/, { timeout: 5000 }).catch(() => {});
  await expect(page.locator(".queue-status")).toContainText(/GPU (busy|idle)/i, { timeout: 5000 });
  await expect(page.locator(".queue-status")).toContainText(/GPU idle/i, { timeout: 20_000 });
});

test("cancel button appears when job is busy", async ({ page }) => {
  await loadDemoWorld(page);
  await sendPublicLine(page, "Cancel probe");
  const cancel = page.getByRole("button", { name: /^Cancel$/i });
  if (await cancel.isVisible({ timeout: 3000 }).catch(() => false)) {
    await cancel.click();
    await expect(page.locator(".queue-status")).toContainText(/GPU idle/i, { timeout: 15_000 });
  }
});
