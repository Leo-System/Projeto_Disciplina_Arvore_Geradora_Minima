import { defineConfig, devices } from '@playwright/test'

const PORT = 8123
const BASE_URL = `http://127.0.0.1:${PORT}`

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: '../.venv/bin/python ../run.py --no-browser --port 8123',
    url: `${BASE_URL}/health`,
    reuseExistingServer: true,
    timeout: 120_000,
  },
})
