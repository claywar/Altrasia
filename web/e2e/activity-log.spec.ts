import { test, expect } from "@playwright/test";
import { loadDemoWorld } from "./helpers";

/** UI-AMB-1/2: idle_timer lines hidden from chronicle; shown in activity log. */
test("idle_timer message hidden from chronicle and shown in activity log", async ({ page }) => {
  await loadDemoWorld(page);
  await page.route("**/api/v1/worlds/*/scenes/*/messages", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    const seeded = [
      ...body,
      {
        messageId: "msg-idle-e2e",
        role: "assistant",
        characterId: "char-alice",
        outputText: "Quiet ambient thought.",
        streamStatus: "final",
        metaJson: JSON.stringify({ communication: { scope: "public" } }),
        generationJobId: "job-idle-e2e",
        generationTrigger: "idle_timer",
        idleSource: "tab_visible",
        createdAt: new Date().toISOString(),
        perceivedByPersona: true,
      },
    ];
    await route.fulfill({ response, json: seeded });
  });
  await page.reload();
  await expect(page.getByPlaceholder(/speak as persona/i)).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Quiet ambient thought.")).toBeVisible();
  await expect(page.getByTestId("chronicle-entry")).toHaveCount(0);
  await expect(page.getByTestId("world-activity-log")).toBeVisible();
  await expect(page.getByTestId("world-activity-log")).toContainText(/alice/i);
  await expect(page.getByTestId("world-activity-log")).toContainText(/idle \(tab\)/i);
});

test("show ambient in transcript restores idle lines in chronicle", async ({ page }) => {
  await loadDemoWorld(page);
  await page.evaluate(() => {
    sessionStorage.setItem("altrasia.showAmbientInTranscript", "1");
  });
  await page.route("**/api/v1/worlds/*/scenes/*/messages", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    await route.fulfill({
      response,
      json: [
        ...body,
        {
          messageId: "msg-idle-e2e-2",
          role: "assistant",
          characterId: "char-alice",
          outputText: "Visible ambient line.",
          streamStatus: "final",
          metaJson: JSON.stringify({ communication: { scope: "public" } }),
          generationTrigger: "idle_timer",
          idleSource: "server_heartbeat",
          createdAt: new Date().toISOString(),
          perceivedByPersona: true,
        },
      ],
    });
  });
  await page.reload();
  await expect(page.getByPlaceholder(/speak as persona/i)).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("chronicle-entry")).toContainText("Visible ambient line.");
});

test("settings toggle controls ambient transcript preference", async ({ page }) => {
  await loadDemoWorld(page);
  await page.getByRole("button", { name: /^settings$/i }).click();
  const toggle = page.getByLabel(/show ambient lines in transcript/i);
  await expect(toggle).not.toBeChecked();
  await toggle.check();
  await expect(toggle).toBeChecked();
  await page.getByRole("button", { name: /close/i }).click();
});
