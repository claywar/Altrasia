import { test, expect } from "@playwright/test";

test("load demo and see hall", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /load demo/i }).click();
  await expect(page.getByText(/Hall|Demo Spatial/i).first()).toBeVisible({ timeout: 15_000 });
});

test("compose public line", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /load demo/i }).click();
  await expect(page.getByPlaceholder(/speak as persona/i)).toBeVisible({ timeout: 15_000 });
  await page.getByPlaceholder(/speak as persona/i).fill("Hello from Playwright");
  await page.getByRole("button", { name: /send/i }).click();
  await expect(page.getByTestId("chronicle-entry").first()).toBeVisible();
});
