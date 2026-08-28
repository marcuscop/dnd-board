import { defineConfig, devices } from "@playwright/test";

const isCi = Boolean(process.env.CI);
const backendPort = 18_000;
const frontendPort = 15_173;
const backendUrl = `http://127.0.0.1:${backendPort}`;
const frontendUrl = `http://127.0.0.1:${frontendPort}`;

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: {
    timeout: 10_000
  },
  fullyParallel: false,
  reporter: isCi ? "github" : "list",
  use: {
    baseURL: frontendUrl,
    trace: "on-first-retry"
  },
  webServer: [
    {
      command: `poetry run uvicorn dnd_board.server:app --host 127.0.0.1 --port ${backendPort}`,
      reuseExistingServer: false,
      timeout: 120_000,
      url: `${backendUrl}/api/rooms/test-campaign/sheet?playerKey=dm`
    },
    {
      command: `VITE_BACKEND_URL=${backendUrl} VITE_WS_URL=ws://127.0.0.1:${backendPort}/ws VITE_PORT=${frontendPort} npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      reuseExistingServer: false,
      timeout: 120_000,
      url: `${frontendUrl}/test-campaign/player=dm`
    }
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
