import { expect, test, type Locator, type Page, type Response } from '@playwright/test';
import { randomUUID } from 'node:crypto';

test.use({ trace: 'off', screenshot: 'off', actionTimeout: 10_000 });

async function confirmed(page: Page, method: string, suffix: string, action: () => Promise<void>, status: number): Promise<Response> {
  const pending = page.waitForResponse((response) => response.request().method() === method
    && new URL(response.url()).pathname.endsWith(suffix), { timeout: 10_000 });
  const [response] = await Promise.all([pending, action()]);
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
  await page.getByRole('textbox', { name: 'E-mail', exact: true }).fill(`qa-links-${identifier}@example.invalid`);
  await privateEntry(page.getByLabel('Hasło', { exact: true }), password);
  await page.getByRole('textbox', { name: 'Twoje imię', exact: true }).fill(name);
  await confirmed(page, 'POST', '/auth/register', () => page.getByRole('button', { name: 'Utwórz konto', exact: true }).click(), 201);
  await expect(page.getByText('Konto utworzone. Zaloguj się.', { exact: true })).toBeVisible();
  await privateEntry(page.getByLabel('Hasło', { exact: true }), password);
  await confirmed(page, 'POST', '/auth/login', () => page.getByRole('button', { name: 'Zaloguj się', exact: true }).click(), 200);
}

async function headers(page: Page, baseURL: string) {
  const response = await page.request.get('/api/v1/auth/session');
  expect(response.status()).toBe(200);
  return { Origin: new URL(baseURL).origin, 'X-CSRF-Token': (await response.json()).csrf_token,
    'Idempotency-Key': randomUUID() };
}

async function screenshot(page: Page, path: string) {
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    window.scrollTo(0, 0);
  });
  await page.screenshot({ path, fullPage: true, animations: 'disabled' });
}

async function fillLink(page: Page, title: string, url: string, note: string) {
  const form = page.getByTestId('recipe-link-form');
  await form.getByRole('textbox', { name: 'Własny tytuł linku', exact: true }).fill(title);
  await form.getByRole('textbox', { name: 'Adres strony (HTTPS)', exact: true }).fill(url);
  await form.getByRole('textbox', { name: 'Własna notatka (opcjonalnie)', exact: true }).fill(note);
  await form.getByLabel('Potwierdzam autorstwo własnego tytułu i notatki', { exact: true }).check();
}

test('saved links stay literal, private and link-only through pagination, viewer access and revocation', async ({ page: owner, browser }, testInfo) => {
  test.setTimeout(90_000);
  const baseURL = testInfo.project.use.baseURL!;
  const recipientContext = await browser.newContext({ baseURL, viewport: testInfo.project.use.viewport,
    isMobile: testInfo.project.use.isMobile, hasTouch: testInfo.project.use.hasTouch,
    deviceScaleFactor: testInfo.project.use.deviceScaleFactor });
  const viewer = await recipientContext.newPage();
  const externalRequests: string[] = [];
  const pageErrors: string[] = [];
  for (const page of [owner, viewer]) {
    page.on('request', (request) => { if (new URL(request.url()).origin !== new URL(baseURL).origin) externalRequests.push('external'); });
    page.on('pageerror', (error) => pageErrors.push(error.message));
  }
  let hid: string | undefined;
  try {
    await account(owner, 'Autor prywatnego linku QA');
    await owner.getByRole('textbox', { name: 'Nazwa gospodarstwa', exact: true }).fill('Dom linków QA');
    const created = await confirmed(owner, 'POST', '/api/v1/households', () => owner.getByRole('button', {
      name: 'Utwórz gospodarstwo', exact: true,
    }).click(), 201);
    hid = (await created.json()).id;
    const base = `/api/v1/households/${hid}`;
    const beforeMembers = (await (await owner.request.get(`${base}/members`)).json()).members;
    await owner.getByRole('link', { name: 'Przepisy', exact: true }).click();
    const links = owner.getByTestId('recipe-links');
    await links.getByRole('button', { name: 'Dodaj link', exact: true }).click();
    const title = 'Moja nazwa — szkic zewnętrznego linku';
    const url = 'https://aniagotuje.pl/przepis/pomysl-qa?b=2&a=1#moja-sekcja';
    const note = '<img src=x onerror="document.documentElement.dataset.linkXss=1"> 0 kcal; bez glutenu; pasteryzowane — moja literalna notatka.';
    await fillLink(owner, title, url, note);
    await owner.evaluate(() => window.dispatchEvent(new Event('blur')));
    await confirmed(owner, 'GET', '/api/v1/households', async () => {
      await owner.evaluate(() => window.dispatchEvent(new Event('focus')));
    }, 200);
    await expect(owner.getByTestId('recipe-link-form')).toBeVisible();
    await expect(owner.getByRole('textbox', { name: 'Własny tytuł linku', exact: true })).toHaveValue(title);
    await expect(owner.getByRole('textbox', { name: 'Własna notatka (opcjonalnie)', exact: true })).toHaveValue(note);
    await owner.getByRole('textbox', { name: 'Adres strony (HTTPS)', exact: true }).fill('https://127.0.0.1/private-qa');
    await confirmed(owner, 'POST', '/recipe-links', () => owner.getByRole('button', {
      name: 'Zapisz link', exact: true,
    }).click(), 422);
    await expect(owner.getByTestId('recipe-link-card')).toHaveCount(0);
    await expect(owner.getByRole('textbox', { name: 'Własna notatka (opcjonalnie)', exact: true })).toHaveValue(note);
    await owner.getByRole('textbox', { name: 'Adres strony (HTTPS)', exact: true }).fill(url);
    const saved = await confirmed(owner, 'POST', '/recipe-links', () => owner.getByRole('button', {
      name: 'Zapisz link', exact: true,
    }).click(), 201);
    const link = await saved.json();
    expect(link.status).toBe('link_only');
    expect(link.planner_eligible).toBe(false);
    expect(link.automatic_fetch_enabled).toBe(false);
    expect(link.license).toBeNull();
    expect(link.nutrition_status).toBe('unknown');
    expect(link.allergen_status).toBe('unknown');
    expect(link.source_url).toBe(url);
    expect(link.canonical_url).toBe(url.split('#')[0]);
    const firstTitle = title;
    for (let index = 1; index <= 2; index++) {
      const response = await owner.request.post(`${base}/recipe-links`, {
        headers: await headers(owner, baseURL), data: { user_title: `Kolejny link QA ${index}`,
          source_url: `https://kwestiasmaku.com/qa/${index}`, own_note: null,
          own_contribution_attestation: 'i_am_author_of_label_and_note' },
      });
      expect(response.status()).toBe(201);
    }
    await owner.reload();
    await expect(owner.getByTestId('recipe-link-card')).toHaveCount(3);
    await links.getByRole('combobox', { name: 'Linki na stronie', exact: true }).selectOption('2');
    await expect(owner.getByTestId('recipe-link-card')).toHaveCount(2);
    const firstIds = await owner.getByTestId('recipe-link-card').evaluateAll((cards) => cards.map((card) => card.getAttribute('data-link-id')));
    await confirmed(owner, 'GET', '/recipe-links', () => owner.getByTestId('recipe-link-next').click(), 200);
    await expect(owner.getByTestId('recipe-link-card')).toHaveCount(1);
    const secondIds = await owner.getByTestId('recipe-link-card').evaluateAll((cards) => cards.map((card) => card.getAttribute('data-link-id')));
    expect(new Set([...firstIds, ...secondIds]).size).toBe(3);
    await links.getByRole('combobox', { name: 'Linki na stronie', exact: true }).selectOption('10');
    await expect(owner.getByTestId('recipe-link-card')).toHaveCount(3);
    await owner.getByRole('button', { name: `Szczegóły linku ${firstTitle}`, exact: true }).click();
    const detail = owner.getByTestId('recipe-link-detail');
    await expect(detail.getByTestId('recipe-link-note')).toHaveText(note);
    await expect(detail.getByTestId('recipe-link-unknown')).toContainText('Wartości odżywcze i alergeny nieznane. Link nie jest dostępny dla planera.');
    await expect(detail.locator('img')).toHaveCount(0);
    expect(await owner.evaluate(() => document.documentElement.dataset.linkXss)).toBeUndefined();
    const external = detail.getByRole('link', { name: 'Otwórz stronę źródłową', exact: true });
    await expect(external).toHaveAttribute('href', url);
    await expect(external).toHaveAttribute('target', '_blank');
    expect((await external.getAttribute('rel'))?.split(' ')).toEqual(expect.arrayContaining(['noopener', 'noreferrer']));
    expect((await (await owner.request.get(`${base}/members`)).json()).members).toEqual(beforeMembers);
    expect((await (await owner.request.get(`${base}/recipes`)).json()).recipes).toEqual([]);
    await screenshot(owner, testInfo.outputPath('link-only-literal-note.png'));

    const invitationResponse = await owner.request.post(`${base}/invite`, {
      headers: await headers(owner, baseURL), data: { role: 'viewer', member_id: null },
    });
    expect(invitationResponse.status()).toBe(201);
    const invitation = await invitationResponse.json();
    await account(viewer, 'Czytelnik prywatnego linku QA');
    const accepted = await viewer.request.post('/api/v1/household-invitations/accept', {
      headers: await headers(viewer, baseURL), data: { token: invitation.token },
    });
    expect(accepted.status()).toBe(200);
    const membership = (await accepted.json()).member;
    await viewer.goto('/recipes');
    await expect(viewer.getByTestId('recipe-link-card')).toHaveCount(3);
    await expect(viewer.getByTestId('recipe-links').getByRole('button', { name: 'Dodaj link', exact: true })).toHaveCount(0);
    await expect(viewer.getByTestId('recipe-link-form')).toHaveCount(0);
    await viewer.getByRole('button', { name: `Szczegóły linku ${firstTitle}`, exact: true }).click();
    await expect(viewer.getByTestId('recipe-link-note')).toHaveText(note);
    const denied = await viewer.request.post(`${base}/recipe-links`, {
      headers: await headers(viewer, baseURL), data: { user_title: 'Zabroniony link',
        source_url: 'https://aniagotuje.pl/inny-qa', own_note: null,
        own_contribution_attestation: 'i_am_author_of_label_and_note' },
    });
    expect(denied.status()).toBe(403);
    const revoked = await owner.request.put(`${base}/members/${membership.id}/access`, {
      headers: await headers(owner, baseURL), data: { expected_version: membership.access_version,
        role: 'viewer', access_enabled: false },
    });
    expect(revoked.status()).toBe(200);
    await confirmed(viewer, 'GET', '/api/v1/households', async () => {
      await viewer.evaluate(() => window.dispatchEvent(new Event('focus')));
    }, 200);
    await expect(viewer.getByTestId('recipe-link-detail')).toHaveCount(0);
    await expect(viewer.getByTestId('recipe-link-card')).toHaveCount(0);
    expect((await viewer.request.get(`${base}/recipe-links/${link.id}`)).status()).toBe(404);
    expect((await (await owner.request.get(`${base}/recipe-links/${link.id}`)).json()).own_note).toBe(note);
    const cached = await owner.evaluate(async () => {
      const paths: string[] = [];
      for (const name of await caches.keys()) for (const request of await (await caches.open(name)).keys()) paths.push(new URL(request.url).pathname);
      return paths;
    });
    expect(cached.some((value) => value.startsWith('/api/v1/') || value === '/recipes')).toBe(false);
    expect(await owner.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(await viewer.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(externalRequests).toEqual([]);
    expect(pageErrors).toEqual([]);
  } finally {
    if (hid) {
      const pending = await owner.request.get(`/api/v1/households/${hid}/invitations`).catch(() => undefined);
      if (pending?.ok()) for (const invitation of (await pending.json()).invitations.filter((item: { status: string }) => item.status === 'pending')) {
        await owner.request.post(`/api/v1/households/${hid}/invitations/${invitation.id}/revoke`, {
          headers: await headers(owner, baseURL), data: { expected_version: invitation.version },
        }).catch(() => undefined);
      }
    }
    await recipientContext.close();
  }
});

test('a delayed committed link response cannot populate a newly selected household', async ({ page }, testInfo) => {
  test.setTimeout(60_000);
  const baseURL = testInfo.project.use.baseURL!;
  await account(page, 'Właściciel dwóch katalogów linków QA');
  const households = [];
  for (const name of ['Linki A', 'Linki B']) {
    const response = await page.request.post('/api/v1/households', {
      headers: await headers(page, baseURL), data: { name },
    });
    expect(response.status()).toBe(201);
    households.push(await response.json());
  }
  const [first, second] = households;
  await page.goto('/recipes');
  await page.getByRole('combobox', { name: 'Gospodarstwo', exact: true }).selectOption(first.id);
  await page.getByTestId('recipe-links').getByRole('button', { name: 'Dodaj link', exact: true }).click();
  await fillLink(page, 'Wyłącznie link gospodarstwa A', 'https://aniagotuje.pl/qa-dom-a', 'Notatka tylko dla domu A');
  let release: () => void = () => undefined;
  const delayed = new Promise<void>((resolve) => { release = resolve; });
  let committed: (status: number) => void = () => undefined;
  const committedResponse = new Promise<number>((resolve) => { committed = resolve; });
  await page.route(`**/api/v1/households/${first.id}/recipe-links`, async (route) => {
    if (route.request().method() !== 'POST') return route.continue();
    const response = await route.fetch();
    committed(response.status());
    await delayed;
    await route.fulfill({ response });
  });
  try {
    await page.getByRole('button', { name: 'Zapisz link', exact: true }).click();
    expect(await committedResponse).toBe(201);
    await confirmed(page, 'GET', `/${second.id}/recipe-links`, async () => {
      await page.getByRole('combobox', { name: 'Gospodarstwo', exact: true }).selectOption(second.id);
    }, 200);
    const delivery = page.waitForResponse((response) => response.request().method() === 'POST'
      && new URL(response.url()).pathname.endsWith(`/${first.id}/recipe-links`), { timeout: 10_000 });
    release();
    await (await delivery).finished();
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('combobox', { name: 'Gospodarstwo', exact: true })).toHaveValue(second.id);
    await expect(page.getByTestId('recipe-link-card')).toHaveCount(0);
    await expect(page.getByTestId('recipe-link-detail')).toHaveCount(0);
    await expect(page.getByTestId('recipe-link-form')).toHaveCount(0);
    const firstLinks = (await (await page.request.get(`/api/v1/households/${first.id}/recipe-links`)).json()).recipe_links;
    expect(firstLinks).toHaveLength(1);
    expect(firstLinks[0].user_title).toBe('Wyłącznie link gospodarstwa A');
  } finally {
    release();
    await page.unroute(`**/api/v1/households/${first.id}/recipe-links`).catch(() => undefined);
  }
});
