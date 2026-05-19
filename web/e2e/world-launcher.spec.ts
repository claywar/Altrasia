import { test, expect } from "@playwright/test";
import { loadDemoWorld } from "./helpers";

/** UI-WLD-1: load demo; single active world shell. */
test("load demo world from launcher", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Altrasia" })).toBeVisible();
  await loadDemoWorld(page);
  await expect(page.getByText(/Altrasia —/)).toBeVisible();
  await expect(page.locator(".scene-header h2")).toContainText(/Lobby|Vertex|Demo/i);
  await expect(page.getByPlaceholder(/speak as persona/i)).toBeVisible();
});
