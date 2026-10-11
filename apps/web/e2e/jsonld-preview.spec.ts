import { expect, test, type Locator, type Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';

test.use({ trace: 'off', screenshot: 'off' });
async function privateEntry(input: Locator, value: string) {
  await expect(input).toBeVisible();
  await expect(input).toBeEditable();
  await input.evaluate((element, privateValue) => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
    if (!setter) throw new Error('Input setter unavailable');
    setter.call(element, privateValue);
    element.dispatchEvent(new Event('input', { bubbles: true }));
  }, value);
}
async function account(page: Page) {
  const id = randomUUID();
  const password = `QA-${id}!`;
  await page.goto('/household');
  await page.getByRole('button', { name: 'Załóż konto', exact: true }).click();
  await page.getByRole('textbox', { name: 'E-mail', exact: true }).fill(`qa-jsonld-${id}@example.invalid`);
  await privateEntry(page.getByLabel('Hasło', { exact: true }), password);
  await page.getByRole('textbox', { name: 'Twoje imię', exact: true }).fill('Autor JSON-LD QA');
  const registered = page.waitForResponse((r) => new URL(r.url()).pathname.endsWith('/auth/register'));
  await page.getByRole('button', { name: 'Utwórz konto', exact: true }).click();
  expect((await registered).status()).toBe(201);
  await expect(page.getByText('Konto utworzone. Zaloguj się.', { exact: true })).toBeVisible();
  await privateEntry(page.getByLabel('Hasło', { exact: true }), password);
  const login = page.waitForResponse((r) => new URL(r.url()).pathname.endsWith('/auth/login'));
  await page.getByRole('button', { name: 'Zaloguj się', exact: true }).click();
  expect((await login).status()).toBe(200);
}

test('own JSON-LD preview remains literal, ephemeral and scoped to the selected household', async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  const errors: string[] = [];
  const outbound: string[] = [];
  const baseURL = testInfo.project.use.baseURL!;
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('request', (request) => { if (new URL(request.url()).origin !== new URL(baseURL).origin) outbound.push('external'); });
  await account(page);
  const session = await (await page.request.get('/api/v1/auth/session')).json();
  const headers = () => ({ Origin: new URL(baseURL).origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': randomUUID() });
  const houses = [];
  for (const name of ['Dokument A QA', 'Dokument B QA']) {
    const response = await page.request.post('/api/v1/households', { headers: headers(), data: { name } });
    expect(response.status()).toBe(201); houses.push(await response.json());
  }
  const [first, second] = houses;
  const base = `/api/v1/households/${first.id}`;
  const before = await (await page.request.get(`${base}/members`)).json();
  await page.goto('/recipes');
  await page.getByRole('combobox', { name: 'Gospodarstwo', exact: true }).selectOption(first.id);
  await page.getByRole('button', { name: 'Otwórz podgląd JSON-LD', exact: true }).click();
  const form = page.getByTestId('jsonld-preview-form');
  const input = form.getByRole('textbox', { name: 'Własny dokument JSON-LD', exact: true });
  const raw = JSON.stringify({ '@context': 'https://127.0.0.1/context', '@graph': [{
    '@type': 'Recipe', name: 'Moja własna receptura JSON-LD QA',
    recipeIngredient: ['3 łyżki mąki', 'woda według potrzeby'], recipeYield: '3 kg 700 g',
    recipeInstructions: [{ '@type': 'HowToSection', name: 'Moje przygotowanie', itemListElement: [
      { '@type': 'HowToStep', text: '<img src=x onerror="document.documentElement.dataset.jsonldXss=1"> pasteryzowane' },
    ] }], nutrition: { calories: '0 kcal' }, image: 'http://169.254.169.254/private', license: 'CC0',
  }] });
  await input.fill(raw);
  await form.getByLabel('Potwierdzam autorstwo całej przekazywanej receptury', { exact: true }).check();
  const refreshed = page.waitForResponse((r) => new URL(r.url()).pathname === '/api/v1/households');
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  expect((await refreshed).status()).toBe(200);
  await expect(input).toHaveValue(raw);
  const previewed = page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname.endsWith('/recipe-imports/preview'));
  await form.getByRole('button', { name: 'Pokaż podgląd', exact: true }).click();
  const response = await previewed;
  expect(response.status()).toBe(200);
  expect(response.headers()['cache-control']).toContain('no-store');
  const value = await response.json();
  expect(value.persisted).toBe(false); expect(value.planner_eligible).toBe(false); expect(value.license).toBeNull();
  expect(value.recipe_yield_raw).toEqual(['3 kg 700 g']);
  const result = page.getByTestId('jsonld-preview-result');
  await expect(result).toContainText('To niezapisany podgląd.');
  await expect(result).toContainText('Wartości odżywcze i alergeny są nieznane.');
  await expect(result).toContainText('3 kg 700 g');
  await expect(result).toContainText('<img src=x onerror=');
  await expect(result.locator('img, a')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.dataset.jsonldXss)).toBeUndefined();
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    window.scrollTo(0, 0);
  });
  await page.screenshot({ path: testInfo.outputPath('own-jsonld-preview.png'), fullPage: true, animations: 'disabled' });
  await input.fill('{"name":"duplicate","name":"other"}');
  const bad = page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname.endsWith('/recipe-imports/preview'));
  await form.getByRole('button', { name: 'Pokaż podgląd', exact: true }).click();
  expect((await bad).status()).toBe(422);
  await expect(input).toHaveValue('{"name":"duplicate","name":"other"}');
  await expect(form.getByRole('alert')).toBeVisible();
  await expect(result).toHaveCount(0);
  expect(await (await page.request.get(`${base}/members`)).json()).toEqual(before);
  expect((await (await page.request.get(`${base}/recipes`)).json()).recipes).toEqual([]);
  const cached = await page.evaluate(async () => {
    const paths: string[] = [];
    for (const name of await caches.keys()) for (const request of await (await caches.open(name)).keys()) paths.push(new URL(request.url).pathname);
    return paths;
  });
  expect(cached.some((path) => path.startsWith('/api/v1/') || path === '/recipes')).toBe(false);

  // A computed but delayed response must never appear under household B.
  await input.fill(raw);
  let release: () => void = () => undefined;
  const delayed = new Promise<void>((resolve) => { release = resolve; });
  let computed: (status: number) => void = () => undefined;
  const ready = new Promise<number>((resolve) => { computed = resolve; });
  await page.route(`**${base}/recipe-imports/preview`, async (route) => {
    const response = await route.fetch(); computed(response.status());
    await delayed; await route.fulfill({ response });
  });
  try {
    await form.getByRole('button', { name: 'Pokaż podgląd', exact: true }).click();
    expect(await ready).toBe(200);
    await page.getByRole('combobox', { name: 'Gospodarstwo', exact: true }).selectOption(second.id);
    const delivery = page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname.endsWith('/recipe-imports/preview'));
    release(); await (await delivery).finished(); await page.waitForLoadState('networkidle');
    await expect(page.getByRole('combobox', { name: 'Gospodarstwo', exact: true })).toHaveValue(second.id);
    await expect(result).toHaveCount(0); await expect(form).toHaveCount(0);
  } finally { release(); await page.unroute(`**${base}/recipe-imports/preview`); }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]); expect(outbound).toEqual([]);
});
