import { expect, test, type Locator, type Page } from '@playwright/test';
import { createHash, randomUUID } from 'node:crypto';

test.use({ trace: 'off', screenshot: 'off', actionTimeout: 10_000 });

async function privateEntry(input: Locator, value: string) {
  await expect(input).toBeVisible();
  await expect(input).toBeEditable();
  await input.evaluate((element, privateValue) => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
    if (!setter) throw new Error('Private input setter unavailable');
    setter.call(element, privateValue);
    element.dispatchEvent(new Event('input', { bubbles: true }));
  }, value);
}

async function responseFor(page: Page, method: string, pathname: string, action: () => Promise<unknown>, expectedStatus: number) {
  const pending = page.waitForResponse((response) => response.request().method() === method && new URL(response.url()).pathname === pathname, { timeout: 15_000 });
  const [response] = await Promise.all([pending, action()]);
  expect(response.status()).toBe(expectedStatus);
  expect(response.headers()['cache-control']).toContain('no-store');
  return response;
}

async function account(page: Page) {
  const id = randomUUID();
  const password = `QA-${id}!`;
  await page.goto('/household');
  await page.getByRole('button', { name: 'Załóż konto', exact: true }).click();
  await page.getByRole('textbox', { name: 'E-mail', exact: true }).fill(`qa-jsonld-save-${id}@example.invalid`);
  await privateEntry(page.getByLabel('Hasło', { exact: true }), password);
  await page.getByRole('textbox', { name: 'Twoje imię', exact: true }).fill('Autor zapisu QA');
  await responseFor(page, 'POST', '/api/v1/auth/register', () => page.getByRole('button', { name: 'Utwórz konto', exact: true }).click(), 201);
  await expect(page.getByText('Konto utworzone. Zaloguj się.', { exact: true })).toBeVisible();
  await privateEntry(page.getByLabel('Hasło', { exact: true }), password);
  await responseFor(page, 'POST', '/api/v1/auth/login', () => page.getByRole('button', { name: 'Zaloguj się', exact: true }).click(), 200);
}

async function setup(page: Page, baseURL: string, names: string[]) {
  await account(page);
  const session = await (await page.request.get('/api/v1/auth/session')).json();
  const headers = () => ({ Origin: new URL(baseURL).origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': randomUUID() });
  const houses: { id: string; name: string }[] = [];
  for (const name of names) {
    const response = await page.request.post('/api/v1/households', { headers: headers(), data: { name } });
    expect(response.status()).toBe(201);
    houses.push(await response.json());
  }
  await page.goto('/recipes');
  if (houses.length > 1) await page.getByRole('combobox', { name: 'Gospodarstwo', exact: true }).selectOption(houses[0].id);
  return { houses, headers };
}

function rawDocument(changes: Record<string, unknown> = {}) {
  return JSON.stringify({ '@context': 'https://127.0.0.1/private-context', '@graph': [{
    '@type': 'Recipe', name: 'Własny import zapisany QA',
    recipeIngredient: ['3 łyżki mąki', 'woda według potrzeby'], recipeYield: ['3 kg 700 g', '4 porcje'],
    recipeInstructions: [{ '@type': 'HowToSection', name: 'Przygotowanie własne QA', itemListElement: [
      { '@type': 'HowToStep', text: '<img src=x onerror="document.documentElement.dataset.savedJsonldXss=1"> Połącz.' },
    ] }], nutrition: { calories: '0 kcal' }, image: 'http://169.254.169.254/private',
    author: 'Niezweryfikowany autor źródłowy', license: 'CC0', storageMethod: 'shelf-stable', ...changes,
  }] });
}

async function preview(page: Page, hid: string, raw: string) {
  const form = page.getByTestId('jsonld-preview-form');
  if (await form.count() === 0) await page.getByRole('button', { name: 'Otwórz podgląd JSON-LD', exact: true }).click();
  const input = form.getByRole('textbox', { name: 'Własny dokument JSON-LD', exact: true });
  await input.fill(raw); // Synthetic own fixture; never an authentication secret.
  await form.getByRole('checkbox', { name: 'Potwierdzam autorstwo całej przekazywanej receptury', exact: true }).check();
  await responseFor(page, 'POST', `/api/v1/households/${hid}/recipe-imports/preview`, () => form.getByRole('button', { name: 'Pokaż podgląd', exact: true }).click(), 200);
  await expect(page.getByTestId('jsonld-preview-result')).toBeVisible();
  await expect(page.getByTestId('jsonld-save')).toBeEnabled();
  return { form, input };
}

async function unknownDetail(detail: Locator) {
  for (const nutrient of ['kcal', 'protein', 'carbs', 'fat']) await expect(detail.getByTestId(`recipe-${nutrient}`)).toContainText('Nieznane');
  await expect(detail.getByTestId('recipe-allergens')).toContainText('Nieznane');
  await expect(detail.getByTestId('recipe-yield')).toContainText('Nieznana');
  await expect(detail.locator('img')).toHaveCount(0);
}

async function privacyChecks(page: Page, errors: string[], outbound: string[]) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.dataset.savedJsonldXss)).toBeUndefined();
  const cached = await page.evaluate(async () => {
    const paths: string[] = [];
    for (const name of await caches.keys()) for (const request of await (await caches.open(name)).keys()) paths.push(new URL(request.url).pathname);
    return paths;
  });
  expect(cached.some((path) => path.startsWith('/api/v1/') || path === '/recipes')).toBe(false);
  expect(errors).toEqual([]);
  expect(outbound).toEqual([]);
}

function watch(page: Page, baseURL: string) {
  const errors: string[] = [];
  const outbound: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('request', (request) => { if (new URL(request.url()).origin !== new URL(baseURL).origin) outbound.push('external'); });
  return { errors, outbound };
}

test('explicit JSON-LD save preserves draft failures, original unknowns and immutable edit history', async ({ page }, testInfo) => {
  test.setTimeout(120_000);
  const baseURL = testInfo.project.use.baseURL!;
  const { errors, outbound } = watch(page, baseURL);
  const { houses, headers } = await setup(page, baseURL, ['Własny JSON-LD QA']);
  const hid = houses[0].id;
  const base = `/api/v1/households/${hid}`;
  const members = (await (await page.request.get(`${base}/members`)).json()).members;
  const target = await page.request.put(`${base}/members/${members[0].id}/nutrition-target`, {
    headers: headers(), data: { expected_version: 0, kcal_target: '2700.125', protein_target_g: '0', carbs_target_g: null, fat_target_g: '1.234', goal_type: 'custom', valid_from: new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Warsaw', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()) },
  });
  expect(target.status()).toBe(200);
  const before = await (await page.request.get(`${base}/members`)).json();
  const longRaw = rawDocument({ recipeIngredient: ['x'.repeat(161)] });
  let { form, input } = await preview(page, hid, longRaw);
  expect((await (await page.request.get(`${base}/recipes`)).json()).recipes).toEqual([]);
  await responseFor(page, 'POST', `${base}/recipe-imports`, () => page.getByTestId('jsonld-save').click(), 422);
  await expect(form.getByRole('alert')).toBeVisible();
  await expect(input).toHaveValue(longRaw);
  await expect(page.getByTestId('jsonld-save-success')).toHaveCount(0);
  await expect(page.getByTestId('recipe-card')).toHaveCount(0);

  const oversizedRaw = rawDocument({ recipeIngredient: Array(40).fill('ą'.repeat(75)), recipeInstructions: Array(30).fill('ą'.repeat(85)) });
  expect(Buffer.byteLength(oversizedRaw, 'utf8')).toBeLessThanOrEqual(12288);
  ({ form, input } = await preview(page, hid, oversizedRaw));
  const oversizedResponse = await responseFor(page, 'POST', `${base}/recipe-imports`, () => page.getByTestId('jsonld-save').click(), 422);
  expect((await oversizedResponse.json()).error_code).toBe('RECIPE_SNAPSHOT_TOO_LARGE');
  await expect(input).toHaveValue(oversizedRaw);
  await expect(form.getByRole('alert')).toBeVisible();
  expect((await (await page.request.get(`${base}/recipes`)).json()).recipes).toEqual([]);

  // Use the same account to prove an earlier detail read cannot overwrite a
  // newer confirmed import selection. This creates a real unrelated recipe.
  const existingResponse = await page.request.post(`${base}/recipes`, {
    headers: headers(), data: { title: 'Starszy przepis odczytywany QA', instructions: ['Własny starszy krok.'], ingredients: [{ name: 'składnik', amount: null, unit: 'unknown', weight_state: 'unknown' }], rights_attestation: 'i_am_author' },
  });
  expect(existingResponse.status()).toBe(201);
  const existing = await existingResponse.json();
  await page.reload();
  await expect(page.getByRole('button', { name: `Otwórz ${existing.title}`, exact: true })).toBeVisible();
  const raw = rawDocument();
  ({ form, input } = await preview(page, hid, raw));
  const refreshed = page.waitForResponse((r) => r.request().method() === 'GET' && new URL(r.url()).pathname === '/api/v1/households');
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  expect((await refreshed).status()).toBe(200);
  await expect(input).toHaveValue(raw);
  await expect(page.getByTestId('jsonld-save')).toBeEnabled();
  let releaseOld: () => void = () => undefined;
  const oldGate = new Promise<void>((resolve) => { releaseOld = resolve; });
  let readOld: (status: number) => void = () => undefined;
  const oldReady = new Promise<number>((resolve) => { readOld = resolve; });
  const oldPath = `${base}/recipes/${existing.id}`;
  const oldMatcher = `**${oldPath}`;
  await page.route(oldMatcher, async (route) => {
    const response = await route.fetch(); readOld(response.status());
    await oldGate; await route.fulfill({ response });
  });
  const original = await (async () => {
    try {
      await page.getByRole('button', { name: `Otwórz ${existing.title}`, exact: true }).click();
      expect(await oldReady).toBe(200);
      const savedResponse = await responseFor(page, 'POST', `${base}/recipe-imports`, () => page.getByTestId('jsonld-save').click(), 201);
      const imported = await savedResponse.json();
      await expect(page.getByTestId('recipe-detail')).toHaveAttribute('data-recipe-id', imported.id);
      const deliveredOld = page.waitForResponse((r) => r.request().method() === 'GET' && new URL(r.url()).pathname === oldPath);
      releaseOld(); await (await deliveredOld).finished(); await page.waitForLoadState('networkidle');
      await expect(page.getByTestId('recipe-detail')).toHaveAttribute('data-recipe-id', imported.id);
      await expect(page.getByTestId('recipe-detail')).toContainText(imported.title);
      await expect(page.getByTestId('jsonld-save-success')).toContainText(imported.title);
      await expect(page.getByTestId('recipe-detail')).not.toContainText(existing.title);
      return imported;
    } finally { releaseOld(); await page.unroute(oldMatcher); }
  })();
  await expect(page.getByTestId('jsonld-save-success')).toBeVisible();
  await expect(input).toBeDisabled();
  await expect(page.getByTestId('jsonld-save')).toHaveCount(0);
  expect(original.version).toBe(1);
  expect(original.provenance.import_origin.source_sha256).toBe(createHash('sha256').update(raw).digest('hex'));
  expect(original.provenance.import_origin.recipe_yield_raw).toEqual(['3 kg 700 g', '4 porcje']);
  expect(original.provenance.license).toBeNull();
  expect(original.planner_eligible).toBe(false);
  const detail = page.getByTestId('recipe-detail');
  await expect(detail).toContainText(original.title);
  await unknownDetail(detail);
  await detail.getByTestId('jsonld-import-origin').locator('summary').click();
  await expect(detail.getByTestId('jsonld-import-origin')).toContainText('Przygotowanie własne QA');
  await expect(detail.getByTestId('jsonld-import-origin')).toContainText('3 kg 700 g');
  await expect(detail.getByTestId('jsonld-import-origin')).toContainText('<img src=x onerror=');
  await expect(detail.getByTestId('jsonld-source-sha256')).toContainText(original.provenance.import_origin.source_sha256);
  await page.evaluate(() => { if (document.activeElement instanceof HTMLElement) document.activeElement.blur(); window.scrollTo(0, 0); });
  await page.screenshot({ path: testInfo.outputPath('saved-own-jsonld-origin.png'), fullPage: true, animations: 'disabled' });

  await page.reload();
  await page.getByRole('button', { name: `Otwórz ${original.title}`, exact: true }).click();
  await unknownDetail(detail);
  await detail.getByRole('button', { name: 'Edytuj przepis', exact: true }).click();
  const edit = detail.getByTestId('recipe-form');
  await edit.getByRole('textbox', { name: 'Nazwa przepisu', exact: true }).fill('Ręcznie zmieniony import QA');
  await edit.getByRole('textbox', { name: 'Krok 1', exact: true }).fill('Ręcznie poprawiony krok QA.');
  await edit.getByRole('checkbox', { name: 'Potwierdzam autorstwo własnego wkładu', exact: true }).check();
  const changed = await responseFor(page, 'PUT', `${base}/recipes/${original.id}`, () => edit.getByRole('button', { name: 'Zapisz nową wersję', exact: true }).click(), 200);
  const updated = await changed.json();
  expect(updated.version).toBe(2);
  expect(updated.provenance.source_mode).toBe('user_authored');
  expect(updated.provenance.source_version_id).toBe(original.version_id);
  expect(updated.provenance.import_origin).toEqual(original.provenance.import_origin);
  await expect(detail.getByTestId('jsonld-current-source')).toContainText('ręczne zmiany');
  await detail.getByRole('button', { name: 'Historia przepisu', exact: true }).click();
  const history = detail.getByTestId('recipe-history');
  const old = history.locator('[data-version="1"]');
  await old.locator(':scope > summary').click();
  await expect(old).toContainText('Połącz.');
  await expect(old).not.toContainText('Ręcznie poprawiony krok QA.');
  await old.getByTestId('jsonld-import-origin').locator('summary').click();
  await expect(old.getByTestId('jsonld-import-origin')).toContainText('3 kg 700 g');
  await expect(old.getByTestId('jsonld-import-origin')).toContainText('3 łyżki mąki');
  expect(await (await page.request.get(`${base}/members`)).json()).toEqual(before);
  const reloaded = await (await page.request.get(`${base}/recipes/${original.id}`)).json();
  expect(reloaded.provenance.import_origin).toEqual(original.provenance.import_origin);
  await page.evaluate(() => { if (document.activeElement instanceof HTMLElement) document.activeElement.blur(); window.scrollTo(0, 0); });
  await page.screenshot({ path: testInfo.outputPath('saved-jsonld-immutable-history.png'), fullPage: true, animations: 'disabled' });
  await privacyChecks(page, errors, outbound);
});

test('late committed JSON-LD save stays in its original household after selection changes', async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  const baseURL = testInfo.project.use.baseURL!;
  const { errors, outbound } = watch(page, baseURL);
  const { houses } = await setup(page, baseURL, ['Zapis dokumentu A QA', 'Zapis dokumentu B QA']);
  const [first, second] = houses;
  const base = `/api/v1/households/${first.id}`;
  await preview(page, first.id, rawDocument({ name: 'Spóźniony zapis tylko A QA' }));
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let committed: (status: number) => void = () => undefined;
  const ready = new Promise<number>((resolve) => { committed = resolve; });
  const matcher = `**${base}/recipe-imports`;
  await page.route(matcher, async (route) => {
    const response = await route.fetch();
    committed(response.status());
    await gate;
    await route.fulfill({ response });
  });
  try {
    await page.getByTestId('jsonld-save').click();
    expect(await ready).toBe(201);
    const selected = page.waitForResponse((r) => r.request().method() === 'GET' && new URL(r.url()).pathname === `/api/v1/households/${second.id}/recipes`);
    await page.getByRole('combobox', { name: 'Gospodarstwo', exact: true }).selectOption(second.id);
    expect((await selected).status()).toBe(200);
    const delivery = page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname === `${base}/recipe-imports`);
    release(); await (await delivery).finished(); await page.waitForLoadState('networkidle');
    await expect(page.getByRole('combobox', { name: 'Gospodarstwo', exact: true })).toHaveValue(second.id);
    await expect(page.getByTestId('recipe-card')).toHaveCount(0);
    await expect(page.getByTestId('recipe-detail')).toHaveCount(0);
    await expect(page.getByTestId('jsonld-save-success')).toHaveCount(0);
    await expect(page.getByTestId('jsonld-preview-form')).toHaveCount(0);
    await expect(page.getByText('Spóźniony zapis tylko A QA', { exact: true })).toHaveCount(0);
    const firstRecipes = (await (await page.request.get(`${base}/recipes`)).json()).recipes;
    expect(firstRecipes).toHaveLength(1);
    expect(firstRecipes[0].title).toBe('Spóźniony zapis tylko A QA');
    expect((await (await page.request.get(`/api/v1/households/${second.id}/recipes`)).json()).recipes).toEqual([]);
    await page.getByRole('combobox', { name: 'Gospodarstwo', exact: true }).selectOption(first.id);
    await expect(page.getByTestId('recipe-card')).toHaveCount(1);
    await page.getByRole('button', { name: 'Otwórz Spóźniony zapis tylko A QA', exact: true }).click();
    await unknownDetail(page.getByTestId('recipe-detail'));
  } finally {
    release(); await page.unroute(matcher);
  }
  await privacyChecks(page, errors, outbound);
});
