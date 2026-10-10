import { expect, test, type Locator, type Page, type Response } from '@playwright/test';
import { randomUUID } from 'node:crypto';

test.use({ trace: 'off', screenshot: 'off', actionTimeout: 10_000 });

async function confirmed(page: Page, method: string, suffix: string, action: () => Promise<void>, status: number): Promise<Response> {
  const pending = page.waitForResponse((response) => response.request().method() === method
    && new URL(response.url()).pathname.endsWith(suffix), { timeout: 10_000 });
  await action();
  const response = await pending;
  expect(response.status(), `${method} ${suffix}`).toBe(status);
  expect(response.headers()['cache-control']).toContain('no-store');
  return response;
}

async function privateEntry(input: Locator, value: string) {
  await expect(input).toBeVisible();
  await expect(input).toBeEditable();
  await input.evaluate((element, privateValue) => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
    if (!setter) throw new Error('Input value setter unavailable');
    setter.call(element, privateValue);
    element.dispatchEvent(new Event('input', { bubbles: true }));
  }, value);
}

async function account(page: Page, name: string) {
  const identifier = randomUUID();
  const password = `QA-${identifier}!`;
  await page.goto('/household');
  await page.getByRole('button', { name: 'Załóż konto', exact: true }).click();
  await page.getByLabel('E-mail', { exact: true }).fill(`qa-recipes-${identifier}@example.invalid`);
  await privateEntry(page.getByLabel('Hasło', { exact: true }), password);
  await page.getByLabel('Twoje imię', { exact: true }).fill(name);
  await confirmed(page, 'POST', '/auth/register', () => page.getByRole('button', { name: 'Utwórz konto', exact: true }).click(), 201);
  await expect(page.getByText('Konto utworzone. Zaloguj się.', { exact: true })).toBeVisible();
  await privateEntry(page.getByLabel('Hasło', { exact: true }), password);
  await confirmed(page, 'POST', '/auth/login', () => page.getByRole('button', { name: 'Zaloguj się', exact: true }).click(), 200);
}

async function mutationHeaders(page: Page, baseURL: string) {
  const response = await page.request.get('/api/v1/auth/session');
  expect(response.status()).toBe(200);
  return { Origin: new URL(baseURL).origin, 'X-CSRF-Token': (await response.json()).csrf_token,
    'Idempotency-Key': randomUUID() };
}

async function capture(page: Page, path: string) {
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    window.scrollTo(0, 0);
  });
  await page.screenshot({ path, fullPage: true, animations: 'disabled' });
}

async function unknowns(page: Page) {
  const detail = page.getByTestId('recipe-detail');
  for (const nutrient of ['kcal', 'protein', 'carbs', 'fat', 'allergens', 'yield']) {
    await expect(detail.getByTestId(`recipe-${nutrient}`)).toContainText(/Nieznan/i);
  }
}

test('explicit separate demo and private recipe versions preserve real goals and shared selection', async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await account(page, 'Autor przepisów QA');
  await page.getByLabel('Nazwa gospodarstwa', { exact: true }).fill(`Realny dom ${randomUUID()}`);
  const response = await confirmed(page, 'POST', '/api/v1/households', () => page.getByRole('button', { name: 'Utwórz gospodarstwo', exact: true }).click(), 201);
  const realHome = await response.json();
  const card = page.getByTestId('member-card');
  await expect(card).toHaveCount(1);
  const memberId = await card.getAttribute('data-member-id');
  await card.getByRole('button', { name: 'Edytuj cele Autor przepisów QA', exact: true }).click();
  await card.getByLabel('Kalorie (kcal)', { exact: true }).fill('2950.125');
  await card.getByLabel('Białko (g)', { exact: true }).fill('0');
  await card.getByLabel('Węglowodany (g)', { exact: true }).fill('');
  await card.getByLabel('Tłuszcze (g)', { exact: true }).fill('1.234');
  await confirmed(page, 'PUT', `/members/${memberId}/nutrition-target`, () => card.getByRole('button', { name: 'Zapisz cele', exact: true }).click(), 200);
  const historyPath = `/api/v1/households/${realHome.id}/members/${memberId}/nutrition-target/history`;
  const realHistory = (await (await page.request.get(historyPath)).json()).history;
  await page.getByRole('link', { name: 'Przepisy', exact: true }).click();
  await expect(page.getByTestId('recipe-card')).toHaveCount(0);
  const demoForm = page.getByTestId('demo-create');
  await expect(demoForm.getByRole('button', { name: 'Utwórz osobne demo', exact: true })).toBeDisabled();
  await demoForm.getByLabel('Rozumiem, że powstanie osobne gospodarstwo demo', { exact: true }).check();
  const seeded = await confirmed(page, 'POST', '/households/demo', () => demoForm.getByRole('button', { name: 'Utwórz osobne demo', exact: true }).click(), 201);
  const demonstration = (await seeded.json()).household;
  expect(demonstration.id).not.toBe(realHome.id);
  expect(demonstration.source).toBe('demo_seed');
  await expect(page.getByTestId('demo-household-warning')).toBeVisible();
  const members = (await (await page.request.get(`/api/v1/households/${demonstration.id}/members`)).json()).members;
  expect(members.map((member: { nutrition_target: { kcal_target: string } }) => member.nutrition_target.kcal_target).sort()).toEqual(['1600', '2700']);
  for (const member of members) {
    expect(member.nutrition_target.source).toBe('demo_seed');
    expect(member.nutrition_target.protein_target_g).toBeNull();
    expect(member.nutrition_target.carbs_target_g).toBeNull();
    expect(member.nutrition_target.fat_target_g).toBeNull();
  }
  await page.getByRole('link', { name: 'Gospodarstwo', exact: true }).click();
  await expect(page.getByTestId('member-card')).toHaveCount(2);
  await expect(page.getByTestId('meal-slots').getByLabel(/^Nazwa posiłku\s*\d+$/)).toHaveCount(5);
  expect((await (await page.request.get(historyPath)).json()).history).toEqual(realHistory);

  await page.getByRole('link', { name: 'Przepisy', exact: true }).click();
  await expect(page.getByRole('combobox', { name: 'Gospodarstwo', exact: true })).toHaveValue(demonstration.id);
  await expect(page.getByTestId('recipe-card')).toHaveCount(3);
  await page.getByRole('button', { name: 'Otwórz Kasza jaglana z jabłkiem i cynamonem', exact: true }).click();
  await unknowns(page);
  const ownTitle = `Własny przepis ${randomUUID()}`;
  await page.getByRole('button', { name: 'Dodaj własny przepis', exact: true }).click();
  const form = page.getByTestId('recipe-form');
  await form.getByLabel('Nazwa przepisu', { exact: true }).fill(ownTitle);
  await form.getByLabel('Składnik 1', { exact: true }).fill('Warzywo QA');
  await form.getByLabel('Ilość składnika 1', { exact: true }).fill('125.001');
  await form.getByRole('combobox', { name: 'Jednostka składnika 1', exact: true }).selectOption('g');
  await form.getByRole('combobox', { name: 'Stan składnika 1', exact: true }).selectOption('raw');
  await form.getByRole('textbox', { name: 'Krok 1', exact: true }).fill('Odważ składnik.');
  await form.getByLabel('Potwierdzam autorstwo własnego wkładu', { exact: true }).check();
  await page.evaluate(() => window.dispatchEvent(new Event('blur')));
  await confirmed(page, 'GET', '/api/v1/households', async () => {
    await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  }, 200);
  await expect(form.getByLabel('Nazwa przepisu', { exact: true })).toHaveValue(ownTitle);
  await expect(form.getByLabel('Ilość składnika 1', { exact: true })).toHaveValue('125.001');
  await expect(form.getByRole('textbox', { name: 'Krok 1', exact: true })).toHaveValue('Odważ składnik.');
  await expect(form.getByLabel('Potwierdzam autorstwo własnego wkładu', { exact: true })).toBeChecked();
  const created = await confirmed(page, 'POST', `/${demonstration.id}/recipes`, () => form.getByRole('button', { name: 'Zapisz przepis', exact: true }).click(), 201);
  const recipe = await created.json();
  expect(recipe.ingredients[0].amount).toBe('125.001');
  expect(recipe.provenance.license).toBeNull();
  await unknowns(page);
  await page.getByTestId('recipe-detail').getByRole('button', { name: 'Edytuj przepis', exact: true }).click();
  await form.getByRole('textbox', { name: 'Krok 1', exact: true }).fill('Nowy własny opis przygotowania.');
  await form.getByLabel('Potwierdzam autorstwo własnego wkładu', { exact: true }).check();
  const saved = await confirmed(page, 'PUT', `/recipes/${recipe.id}`, () => form.getByRole('button', { name: 'Zapisz nową wersję', exact: true }).click(), 200);
  expect((await saved.json()).version).toBe(2);
  await confirmed(page, 'GET', `/recipes/${recipe.id}/history`, () => page.getByRole('button', { name: 'Historia przepisu', exact: true }).click(), 200);
  await expect(page.getByTestId('recipe-history')).toContainText('Odważ składnik.');
  await expect(page.getByTestId('recipe-history')).toContainText('Nowy własny opis przygotowania.');
  await page.reload();
  await page.getByRole('combobox', { name: 'Gospodarstwo', exact: true }).selectOption(demonstration.id);
  await page.getByRole('button', { name: `Otwórz ${ownTitle}`, exact: true }).click();
  await expect(page.getByTestId('recipe-detail')).toContainText('Nowy własny opis przygotowania.');
  await unknowns(page);
  await capture(page, testInfo.outputPath('private-recipe-history.png'));
  await page.getByRole('combobox', { name: 'Gospodarstwo', exact: true }).selectOption(realHome.id);
  await expect(page.getByTestId('recipe-card')).toHaveCount(0);
  await page.getByRole('link', { name: 'Gospodarstwo', exact: true }).click();
  await expect(page.getByRole('combobox', { name: 'Gospodarstwo', exact: true })).toHaveValue(realHome.id);
  await expect(page.getByTestId('member-card').getByTestId('target-kcal')).toHaveText('2950.125');
  expect((await (await page.request.get(historyPath)).json()).history).toEqual(realHistory);
  const cachedPaths = await page.evaluate(async () => {
    const paths: string[] = [];
    for (const name of await caches.keys()) for (const entry of await (await caches.open(name)).keys()) paths.push(new URL(entry.url).pathname);
    return paths;
  });
  expect(cachedPaths.some((path) => path.startsWith('/api/v1/') || path === '/recipes')).toBe(false);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

test('a separate recipient account sees private recipes read-only and loses access after revoke', async ({ page: owner, browser }, testInfo) => {
  test.setTimeout(90_000);
  const context = await browser.newContext({ baseURL: testInfo.project.use.baseURL,
    viewport: testInfo.project.use.viewport, isMobile: testInfo.project.use.isMobile,
    hasTouch: testInfo.project.use.hasTouch, deviceScaleFactor: testInfo.project.use.deviceScaleFactor });
  const recipient = await context.newPage();
  const baseURL = testInfo.project.use.baseURL!;
  let invitation: { id: string; version: number } | undefined;
  let householdId: string | undefined;
  try {
    await account(owner, 'Właściciel katalogu QA');
    const created = await owner.request.post('/api/v1/households', {
      headers: await mutationHeaders(owner, baseURL), data: { name: 'Prywatny katalog QA' },
    });
    expect(created.status()).toBe(201);
    householdId = (await created.json()).id;
    const base = `/api/v1/households/${householdId}`;
    const recipeResponse = await owner.request.post(`${base}/recipes`, {
      headers: await mutationHeaders(owner, baseURL), data: { title: 'Przepis współdzielony QA',
        ingredients: [{ name: 'Składnik bez danych', amount: null, unit: 'unknown', weight_state: 'unknown' }],
        instructions: ['Mój własny opis.'], rights_attestation: 'i_am_author' },
    });
    expect(recipeResponse.status()).toBe(201);
    const recipe = await recipeResponse.json();
    const invitationResponse = await owner.request.post(`${base}/invite`, {
      headers: await mutationHeaders(owner, baseURL), data: { role: 'viewer', member_id: null },
    });
    expect(invitationResponse.status()).toBe(201);
    const code = await invitationResponse.json();
    invitation = { id: code.id, version: code.version };
    await account(recipient, 'Czytelnik katalogu QA');
    const accepted = await recipient.request.post('/api/v1/household-invitations/accept', {
      headers: await mutationHeaders(recipient, baseURL), data: { token: code.token },
    });
    expect(accepted.status()).toBe(200);
    const membership = (await accepted.json()).member;
    await recipient.goto('/recipes');
    await expect(recipient.getByTestId('recipe-card')).toHaveCount(1);
    await recipient.getByRole('button', { name: 'Otwórz Przepis współdzielony QA', exact: true }).click();
    await unknowns(recipient);
    await expect(recipient.getByTestId('recipe-form')).toHaveCount(0);
    await expect(recipient.getByRole('button', { name: 'Edytuj przepis', exact: true })).toHaveCount(0);
    await recipient.getByRole('button', { name: 'Historia przepisu', exact: true }).click();
    await expect(recipient.getByTestId('recipe-history')).toContainText('Mój własny opis.');
    expect((await recipient.request.put(`${base}/recipes/${recipe.id}`, {
      headers: await mutationHeaders(recipient, baseURL), data: { expected_version: 1,
        title: recipe.title, instructions: ['Zmiana zabroniona.'],
        ingredients: [{ name: 'Składnik', amount: null, unit: 'unknown', weight_state: 'unknown' }],
        rights_attestation: 'i_am_author' },
    })).status()).toBe(403);
    await capture(recipient, testInfo.outputPath('viewer-private-recipes.png'));
    const promoted = await owner.request.put(`${base}/members/${membership.id}/access`, {
      headers: await mutationHeaders(owner, baseURL), data: { expected_version: membership.access_version,
        role: 'editor', access_enabled: true },
    });
    expect(promoted.status()).toBe(200);
    const editor = await promoted.json();
    await recipient.reload();
    await recipient.getByRole('button', { name: 'Otwórz Przepis współdzielony QA', exact: true }).click();
    await recipient.getByRole('button', { name: 'Edytuj przepis', exact: true }).click();
    await recipient.getByTestId('recipe-form').getByRole('textbox', { name: 'Krok 1', exact: true }).fill('Niezapisany własny wkład.');
    await recipient.getByTestId('recipe-form').getByLabel('Potwierdzam autorstwo własnego wkładu', { exact: true }).check();
    const downgraded = await owner.request.put(`${base}/members/${membership.id}/access`, {
      headers: await mutationHeaders(owner, baseURL), data: { expected_version: editor.access_version,
        role: 'viewer', access_enabled: true },
    });
    expect(downgraded.status()).toBe(200);
    const viewer = await downgraded.json();
    await confirmed(recipient, 'GET', '/api/v1/households', async () => {
      await recipient.evaluate(() => window.dispatchEvent(new Event('focus')));
    }, 200);
    await expect(recipient.getByTestId('recipe-form')).toHaveCount(0);
    await expect(recipient.getByTestId('recipe-detail')).toHaveCount(1);
    await expect(recipient.getByRole('button', { name: 'Edytuj przepis', exact: true })).toHaveCount(0);
    const promotedAgain = await owner.request.put(`${base}/members/${membership.id}/access`, {
      headers: await mutationHeaders(owner, baseURL), data: { expected_version: viewer.access_version,
        role: 'editor', access_enabled: true },
    });
    expect(promotedAgain.status()).toBe(200);
    const currentEditor = await promotedAgain.json();
    await recipient.reload();
    await recipient.getByRole('button', { name: 'Otwórz Przepis współdzielony QA', exact: true }).click();
    await recipient.getByRole('button', { name: 'Edytuj przepis', exact: true }).click();
    await recipient.getByTestId('recipe-form').getByRole('textbox', { name: 'Krok 1', exact: true }).fill('Niezapisany własny wkład.');
    await recipient.getByTestId('recipe-form').getByLabel('Potwierdzam autorstwo własnego wkładu', { exact: true }).check();
    const revoked = await owner.request.put(`${base}/members/${membership.id}/access`, {
      headers: await mutationHeaders(owner, baseURL), data: { expected_version: currentEditor.access_version,
        role: 'viewer', access_enabled: false },
    });
    expect(revoked.status()).toBe(200);
    expect((await recipient.request.get(`${base}/recipes/${recipe.id}`)).status()).toBe(404);
    await confirmed(recipient, 'PUT', `/recipes/${recipe.id}`, () => recipient.getByTestId('recipe-form').getByRole('button', {
      name: 'Zapisz nową wersję', exact: true,
    }).click(), 404);
    await expect(recipient.getByTestId('recipe-form')).toHaveCount(0);
    await expect(recipient.getByTestId('recipe-card')).toHaveCount(0);
    await expect(recipient.getByTestId('recipe-detail')).toHaveCount(0);
    expect((await (await owner.request.get(`${base}/recipes/${recipe.id}`)).json()).version).toBe(1);
    expect(await recipient.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  } finally {
    if (householdId && invitation) await owner.request.post(`/api/v1/households/${householdId}/invitations/${invitation.id}/revoke`, {
      headers: await mutationHeaders(owner, baseURL), data: { expected_version: invitation.version },
    }).catch(() => undefined);
    await context.close();
  }
});

test('a committed response from the prior household cannot add its member to the selected household', async ({ page }, testInfo) => {
  test.setTimeout(60_000);
  await account(page, 'Właściciel dwóch domów QA');
  const baseURL = testInfo.project.use.baseURL!;
  const households = [];
  for (const name of ['Dom A opóźniony', 'Dom B wybrany']) {
    const response = await page.request.post('/api/v1/households', {
      headers: await mutationHeaders(page, baseURL), data: { name },
    });
    expect(response.status()).toBe(201);
    households.push(await response.json());
  }
  const [first, second] = households;
  const secondMembers = (await (await page.request.get(`/api/v1/households/${second.id}/members`)).json()).members;
  await page.reload();
  await page.getByRole('combobox', { name: 'Gospodarstwo', exact: true }).selectOption(first.id);
  await expect(page.getByTestId('member-card')).toHaveCount(1);
  let release: () => void = () => undefined;
  const delayed = new Promise<void>((resolve) => { release = resolve; });
  let committed: (status: number) => void = () => undefined;
  const committedResponse = new Promise<number>((resolve) => { committed = resolve; });
  await page.route(`**/api/v1/households/${first.id}/members`, async (route) => {
    if (route.request().method() !== 'POST') return route.continue();
    const response = await route.fetch();
    committed(response.status());
    await delayed;
    await route.fulfill({ response });
  });
  try {
    await page.getByLabel('Imię domownika', { exact: true }).fill('Domownik wyłącznie A');
    await page.getByRole('button', { name: 'Dodaj domownika', exact: true }).click();
    expect(await committedResponse).toBe(201);
    await confirmed(page, 'GET', `/${second.id}/members`, async () => {
      await page.getByRole('combobox', { name: 'Gospodarstwo', exact: true }).selectOption(second.id);
    }, 200);
    const delivered = page.waitForResponse((response) => response.request().method() === 'POST'
      && new URL(response.url()).pathname.endsWith(`/${first.id}/members`), { timeout: 10_000 });
    release();
    await (await delivered).finished();
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('combobox', { name: 'Gospodarstwo', exact: true })).toHaveValue(second.id);
    await expect(page.getByTestId('member-card')).toHaveCount(1);
    const visibleIds = await page.getByTestId('member-card').evaluateAll((cards) => cards.map((card) => card.getAttribute('data-member-id')));
    expect(visibleIds).toEqual(secondMembers.map((member: { id: string }) => member.id));
    await expect(page.getByTestId('member-card').filter({ hasText: 'Domownik wyłącznie A' })).toHaveCount(0);
    const firstMembers = (await (await page.request.get(`/api/v1/households/${first.id}/members`)).json()).members;
    expect(firstMembers.filter((member: { display_name: string }) => member.display_name === 'Domownik wyłącznie A')).toHaveLength(1);
  } finally {
    release();
    await page.unroute(`**/api/v1/households/${first.id}/members`).catch(() => undefined);
  }
});


test('private recipe list and history pagination reaches every distinct page through the proxy', async ({ page }, testInfo) => {
  test.setTimeout(60_000);
  await account(page, 'Autor stronicowania QA');
  const baseURL = testInfo.project.use.baseURL!;
  const demo = await page.request.post('/api/v1/households/demo', {
    headers: await mutationHeaders(page, baseURL), data: { confirmation: 'create_separate_demo' },
  });
  expect(demo.status()).toBe(201);
  const household = (await demo.json()).household;
  const path = `/api/v1/households/${household.id}/recipes`;
  const originalPage = await page.request.get(`${path}?limit=20`);
  expect(originalPage.status()).toBe(200);
  const originals = (await originalPage.json()).recipes;
  const recipeResponse = await page.request.get(`${path}/${originals[0].id}`);
  expect(recipeResponse.status()).toBe(200);
  const recipe = await recipeResponse.json();
  for (let version = 1; version < 6; version++) {
    const updated = await page.request.put(`${path}/${recipe.id}`, {
      headers: await mutationHeaders(page, baseURL), data: {
        title: recipe.title, expected_version: version,
        ingredients: recipe.ingredients.map((item: { name: string; amount: string | null; unit: string; weight_state: string }) => ({
          name: item.name, amount: item.amount, unit: item.unit, weight_state: item.weight_state,
        })), instructions: [`Własny opis QA wersja ${version + 1}`], rights_attestation: 'i_am_author',
      },
    });
    expect(updated.status()).toBe(200);
  }
  await page.goto('/recipes');
  await page.getByRole('combobox', { name: 'Przepisy na stronie', exact: true }).selectOption('2');
  await expect(page.getByTestId('recipe-card')).toHaveCount(2);
  const firstIds = await page.getByTestId('recipe-card').evaluateAll((cards) => cards.map((card) => card.getAttribute('data-recipe-id')));
  await confirmed(page, 'GET', `/${household.id}/recipes`, () => page.getByTestId('recipe-list-next').click(), 200);
  await expect(page.getByTestId('recipe-card')).toHaveCount(1);
  const secondIds = await page.getByTestId('recipe-card').evaluateAll((cards) => cards.map((card) => card.getAttribute('data-recipe-id')));
  expect(new Set([...firstIds, ...secondIds]).size).toBe(3);
  expect([...firstIds, ...secondIds]).toEqual(originals.map((item: { id: string }) => item.id));
  await expect(page.getByTestId('recipe-list-next')).toBeDisabled();
  await page.getByRole('button', { name: 'Poprzednia strona', exact: true }).click();
  await expect(page.getByTestId('recipe-card')).toHaveCount(2);
  await page.getByRole('button', { name: `Otwórz ${recipe.title}`, exact: true }).click();
  await confirmed(page, 'GET', `/recipes/${recipe.id}/history`, () => page.getByRole('button', { name: 'Historia przepisu', exact: true }).click(), 200);
  const history = page.getByTestId('recipe-history');
  await expect(history.locator('details')).toHaveCount(2);
  const versions: number[] = [];
  for (let index = 0; index < 3; index++) {
    await expect(history.locator('details')).toHaveCount(2);
    const batch = await history.locator('details').evaluateAll((rows) => rows.map((row) => Number(row.getAttribute('data-version'))));
    expect(batch).toEqual([6 - index * 2, 5 - index * 2]);
    versions.push(...batch);
    if (index < 2) await confirmed(page, 'GET', `/recipes/${recipe.id}/history`, () => page.getByTestId('recipe-history-next').click(), 200);
  }
  expect(versions).toEqual([6, 5, 4, 3, 2, 1]);
  await expect(page.getByTestId('recipe-history-next')).toBeDisabled();
  for (const query of ['limit=21', 'limit=2&limit=3', 'after=127.0.0.1', 'source_url=https://example.invalid']) {
    expect((await page.request.get(`${path}?${query}`)).status()).toBe(400);
  }
  await capture(page, testInfo.outputPath('private-recipe-pagination.png'));
});
