import { defineConfig } from "@playwright/test";

const BACKEND_PORT = 8787;
const WEB_PORT = 5173;

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "pip install -e . -q && altrasia serve --port 8787",
      cwd: "../backend",
      url: `http://127.0.0.1:${BACKEND_PORT}/api/v1/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
    },
    {
      command: "npm run dev",
      url: `http://127.0.0.1:${WEB_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
