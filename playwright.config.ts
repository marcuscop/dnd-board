import { defineConfig, devices } from "@playwright/test";

const isCi = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: {
    timeout: 10_000
  },
  fullyParallel: false,
  reporter: isCi ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry"
  },
  webServer: [
    {
      command: "poetry run uvicorn dnd_board.server:app --host 127.0.0.1 --port 8000",
      reuseExistingServer: !isCi,
      timeout: 120_000,
      url: "http://127.0.0.1:8000/api/rooms/test-campaign/sheet?playerKey=dm"
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      reuseExistingServer: !isCi,
      timeout: 120_000,
      url: "http://127.0.0.1:5173/test-campaign/player=dm"
    }
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
