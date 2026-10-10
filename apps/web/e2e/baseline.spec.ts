import { expect, test } from '@playwright/test';

const apiURL = process.env.PLAYWRIGHT_API_URL ?? 'http://127.0.0.1:8000';
const destinations = [
  { label: 'Dzisiaj', path: '/' },
  { label: 'Plan', path: '/plan' },
  { label: 'Przepisy', path: '/recipes' },
  { label: 'Kuchnia', path: '/kitchen' },
  { label: 'Zakupy', path: '/shopping' },
];

test('Polish shell has usable navigation and fits the viewport', async ({ page }, testInfo) => {
  const pageErrors: string[] = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('lang', 'pl');
  await expect(page.getByRole('main')).toBeVisible();
  for (const destination of destinations) {
    const link = page.getByRole('link', { name: destination.label, exact: true }).filter({ visible: true });
    await expect(link).toHaveCount(1);
    await link.click();
    await expect(page).toHaveURL(new URL(destination.path, testInfo.project.use.baseURL).href);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect.poll(() => page.evaluate(() => (
      document.documentElement.scrollWidth <= window.innerWidth
    ))).toBe(true);
    if (testInfo.project.name.includes('mobile')) {
      const box = await link.boundingBox();
      expect(box?.height, `${destination.label} needs a usable touch target`).toBeGreaterThanOrEqual(44);
    }
  }
  await page.screenshot({ path: testInfo.outputPath('shell.png'), fullPage: true });
  expect(pageErrors).toEqual([]);
});

test('status reports the real healthy API and migrated PostgreSQL', async ({ page, request }, testInfo) => {
  const health = await request.get(`${apiURL}/health`);
  expect(health.status()).toBe(200);
  expect(await health.json()).toEqual({ status: 'ok' });
  const ready = await request.get(`${apiURL}/ready`);
  expect(ready.status()).toBe(200);
  expect(await ready.json()).toEqual({ status: 'ready' });

  await page.goto('/status');
  await expect(page.getByTestId('api-health')).toContainText('ok');
  await expect(page.getByTestId('api-ready')).toContainText('ready');
  await page.screenshot({ path: testInfo.outputPath('status.png'), fullPage: true });
});

test('transport outage never reports healthy and retry recovers from live API', async ({ page }) => {
  await page.route('**/api/{health,ready}', (route) => route.abort('failed'));
  await page.goto('/status');
  await expect(page.getByTestId('api-health')).not.toContainText(/\bok\b/);
  await expect(page.getByTestId('api-ready')).not.toContainText(/\bready\b/);
  await expect(page.getByTestId('api-health')).toContainText(/niedostępn|połączeni|błąd/i);
  await expect(page.getByTestId('api-ready')).toContainText(/niedostępn|połączeni|błąd/i);
  await page.unroute('**/api/{health,ready}');
  await page.getByRole('button', { name: 'Sprawdź ponownie' }).click();
  await expect(page.getByTestId('api-health')).toContainText('ok');
  await expect(page.getByTestId('api-ready')).toContainText('ready');
});

test('manifest provides actual PNG icons and standalone app configuration', async ({ page, request }) => {
  await page.goto('/');
  const href = await page.locator('link[rel="manifest"]').getAttribute('href');
  expect(href).toBeTruthy();
  const response = await request.get(href!);
  expect(response.status()).toBe(200);
  const manifest = await response.json();
  expect(manifest.name).toContain('MealForge');
  expect(manifest.display).toBe('standalone');
  expect(manifest.lang).toBe('pl');
  expect(manifest.scope ?? '/').toBe('/');
  expect(manifest.start_url).toBe('/');
  for (const dimension of [192, 512]) {
    const icon = manifest.icons.find((item: { sizes: string }) => item.sizes === `${dimension}x${dimension}`);
    expect(icon).toBeDefined();
    const image = await request.get(icon.src);
    expect(image.status()).toBe(200);
    expect(image.headers()['content-type']).toContain('image/png');
    const bytes = await image.body();
    expect(bytes.subarray(0, 8)).toEqual(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));
    expect(bytes.readUInt32BE(16)).toBe(dimension);
    expect(bytes.readUInt32BE(20)).toBe(dimension);
  }
});

test('worker caches an offline fallback without persisting API or personal pages', async ({ page, context }) => {
  await page.goto('/');
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller) {
      await new Promise<void>((resolve) => {
        navigator.serviceWorker.addEventListener('controllerchange', () => resolve(), { once: true });
      });
    }
  });
  const registration = await page.evaluate(async () => {
    const worker = await navigator.serviceWorker.ready;
    return { scope: worker.scope, script: worker.active?.scriptURL };
  });
  expect(new URL(registration.scope).pathname).toBe('/');
  expect(new URL(registration.script!).pathname).toBe('/sw.js');
  await page.goto('/status');
  await expect(page.getByTestId('api-ready')).toContainText('ready');
  await page.goto('/plan');
  const cachedPaths = await page.evaluate(async () => {
    const paths: string[] = [];
    for (const name of await caches.keys()) {
      for (const entry of await (await caches.open(name)).keys()) {
        paths.push(new URL(entry.url).pathname);
      }
    }
    return paths;
  });
  expect(cachedPaths).toContain('/offline.html');
  expect(cachedPaths.some((path) => path.startsWith('/api/'))).toBe(false);
  expect(cachedPaths).not.toContain('/status');
  expect(cachedPaths).not.toContain('/plan');
  await context.setOffline(true);
  await page.goto('/plan');
  await expect(page.locator('body')).toContainText(/brak połączenia|offline|bez internetu/i);
  await context.setOffline(false);
});
