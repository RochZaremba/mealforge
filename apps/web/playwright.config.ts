import { defineConfig, devices } from '@playwright/test';

const webURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3000';
const apiURL = process.env.PLAYWRIGHT_API_URL ?? 'http://127.0.0.1:8000';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: webURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'desktop-chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'mobile-chromium',
      use: {
        ...devices['Pixel 7'],
        viewport: { width: 390, height: 844 },
        deviceScaleFactor: 1,
      },
    },
  ],
  webServer: process.env.PLAYWRIGHT_NO_SERVER
    ? undefined
    : [
        {
          command: 'uv run --project ../api uvicorn mealforge.main:app --host 127.0.0.1 --port 8000',
          url: `${apiURL}/ready`,
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
        {
          command: 'pnpm dev --hostname 127.0.0.1 --port 3000',
          url: webURL,
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
      ],
});
