import { expect, test, type Locator, type Page, type Response } from '@playwright/test';
import { randomUUID } from 'node:crypto';

// Invitation codes are temporary credentials; traces contain request bodies.
// Capture only explicit screenshots after hiding/consuming the code.
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

async function enterPrivateValue(input: Locator, value: string): Promise<void> {
  // Playwright fill() includes its supplied argument in timeout diagnostics.
  await expect(input).toBeVisible();
  await expect(input).toBeEditable();
  await input.evaluate((element, privateValue) => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
    if (!setter) throw new Error('Input value setter unavailable');
    setter.call(element, privateValue);
    element.dispatchEvent(new Event('input', { bubbles: true }));
  }, value);
}

async function registerAndLogin(page: Page, name: string) {
  const identifier = randomUUID();
  const password = `Qa-${identifier}!`;
  await page.goto('/household');
  await page.getByRole('button', { name: 'Załóż konto', exact: true }).click();
  await page.getByLabel('E-mail', { exact: true }).fill(`qa-invite-${identifier}@example.invalid`);
  await enterPrivateValue(page.getByLabel('Hasło', { exact: true }), password);
  await page.getByLabel('Twoje imię', { exact: true }).fill(name);
  await confirmed(page, 'POST', '/auth/register', () => page.getByRole('button', { name: 'Utwórz konto', exact: true }).click(), 201);
  await expect(page.getByText('Konto utworzone. Zaloguj się.', { exact: true })).toBeVisible();
  await enterPrivateValue(page.getByLabel('Hasło', { exact: true }), password);
  const login = await confirmed(page, 'POST', '/auth/login', () => page.getByRole('button', { name: 'Zaloguj się', exact: true }).click(), 200);
  return (await login.json()).user;
}

test('viewer joins an existing profile once and loses access without losing nutrition history', async ({ page: owner, browser }, testInfo) => {
  test.setTimeout(120_000);
  const recipientContext = await browser.newContext({
    baseURL: testInfo.project.use.baseURL,
    viewport: testInfo.project.use.viewport,
    isMobile: testInfo.project.use.isMobile,
    hasTouch: testInfo.project.use.hasTouch,
    deviceScaleFactor: testInfo.project.use.deviceScaleFactor,
  });
  const recipient = await recipientContext.newPage();
  const pageErrors: string[] = [];
  owner.on('pageerror', (error) => pageErrors.push(error.message));
  recipient.on('pageerror', (error) => pageErrors.push(error.message));
  let householdId: string | undefined;
  try {
    await registerAndLogin(owner, 'Właściciel QA');
    await owner.getByLabel('Nazwa gospodarstwa', { exact: true }).fill(`Dom zaproszeń ${randomUUID()}`);
    const created = await confirmed(owner, 'POST', '/api/v1/households', () => owner.getByRole('button', { name: 'Utwórz gospodarstwo', exact: true }).click(), 201);
    householdId = (await created.json()).id;
    await expect(owner.getByTestId('member-card')).toHaveCount(1);
    await owner.getByLabel('Imię domownika', { exact: true }).fill('Zaproszona osoba');
    const added = await confirmed(owner, 'POST', '/members', () => owner.getByRole('button', { name: 'Dodaj domownika', exact: true }).click(), 201);
    const resident = await added.json();
    const card = owner.getByTestId('member-card').filter({ hasText: 'Zaproszona osoba' });
    const base = `/api/v1/households/${householdId}`;
    const historyPath = `${base}/members/${resident.id}/nutrition-target/history`;
    for (const energy of ['2700.001', '2750.001']) {
      await card.getByRole('button', { name: 'Edytuj cele Zaproszona osoba', exact: true }).click();
      await card.getByLabel('Kalorie (kcal)', { exact: true }).fill(energy);
      await card.getByLabel('Białko (g)', { exact: true }).fill('0');
      await card.getByLabel('Węglowodany (g)', { exact: true }).fill('');
      await card.getByLabel('Tłuszcze (g)', { exact: true }).fill('1.234');
      await confirmed(owner, 'PUT', `/members/${resident.id}/nutrition-target`, () => card.getByRole('button', { name: 'Zapisz cele', exact: true }).click(), 200);
    }
    const originalHistory = (await (await owner.request.get(historyPath)).json()).history;
    expect(originalHistory.map((item: { version: number }) => item.version)).toEqual([2, 1]);
    expect(originalHistory[0].protein_target_g).toBe('0');
    expect(originalHistory[0].carbs_target_g).toBeNull();

    const invitationForm = owner.getByTestId('invitation-create');
    await expect(invitationForm).toHaveCount(1);
    await expect(owner.locator('[id="invite-member"]')).toHaveCount(1);
    await expect(owner.locator('[id="invite-role"]')).toHaveCount(1);
    await invitationForm.getByRole('combobox', { name: 'Profil domownika', exact: true }).selectOption(resident.id);
    await invitationForm.getByRole('combobox', { name: 'Dostęp dla zaproszonej osoby', exact: true }).selectOption('viewer');
    await confirmed(owner, 'POST', '/invite', () => invitationForm.getByRole('button', { name: 'Utwórz zaproszenie', exact: true }).click(), 201);
    const token = await owner.getByTestId('invitation-code').textContent();
    await owner.getByRole('button', { name: 'Schowaj kod', exact: true }).click();
    await expect(owner.getByTestId('invitation-code')).toHaveCount(0);
    expect(Boolean(token && /^[0-9a-f]{64}$/.test(token))).toBe(true);

    const newUser = await registerAndLogin(recipient, 'Odbiorca QA');
    const accepting = recipient.getByTestId('invitation-accept');
    await enterPrivateValue(accepting.getByLabel('Kod zaproszenia', { exact: true }), token!);
    const accepted = await confirmed(recipient, 'POST', '/household-invitations/accept', () => accepting.getByRole('button', { name: 'Przyjmij zaproszenie', exact: true }).click(), 200);
    const joined = await accepted.json();
    expect(joined.member.id).toBe(resident.id);
    expect(joined.member.user_id).toBe(newUser.id);
    expect(joined.household.role).toBe('viewer');
    expect(joined.household.capabilities.can_edit).toBe(false);
    expect(joined.household.capabilities.can_manage_access).toBe(false);
    if (await accepting.getByLabel('Kod zaproszenia', { exact: true }).count()) {
      await accepting.getByLabel('Kod zaproszenia', { exact: true }).fill('');
    }
    await expect(recipient.getByTestId('member-card')).toHaveCount(2);
    const recipientCard = recipient.getByTestId('member-card').filter({ hasText: 'Zaproszona osoba' });
    await expect(recipientCard.getByTestId('target-protein')).toHaveText('0');
    await expect(recipientCard.getByTestId('target-carbs')).toHaveText('Nieznane');
    await expect(recipient.getByRole('button', { name: /^Edytuj cele / })).toHaveCount(0);
    await expect(recipient.getByTestId('member-access')).toHaveCount(0);
    await expect(recipient.getByTestId('invitation-create')).toHaveCount(0);
    await expect(recipient.getByTestId('meal-slots')).toContainText('Śniadanie');
    await expect(recipient.getByRole('button', { name: 'Zapisz posiłki', exact: true })).toHaveCount(0);
    await expect(recipient.getByRole('button', { name: 'Dodaj posiłek', exact: true })).toHaveCount(0);
    const people = (await (await recipient.request.get(`${base}/members`)).json()).members;
    expect(people).toHaveLength(2);
    expect(people.filter((item: { id: string }) => item.id === resident.id)).toHaveLength(1);
    expect((await (await recipient.request.get(historyPath)).json()).history).toEqual(originalHistory);
    const session = (await (await recipient.request.get('/api/v1/auth/session')).json());
    const origin = new URL(testInfo.project.use.baseURL!).origin;
    const denied = await recipient.request.put(`${base}/members/${resident.id}/nutrition-target`, {
      headers: { Origin: origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': randomUUID() },
      data: { expected_version: 2, kcal_target: '1800', protein_target_g: null,
        carbs_target_g: null, fat_target_g: null, goal_type: 'custom', valid_from: originalHistory[0].valid_from },
    });
    expect(denied.status()).toBe(403);
    expect((await (await owner.request.get(historyPath)).json()).history).toEqual(originalHistory);
    await recipient.screenshot({ path: testInfo.outputPath('viewer-profile.png'), fullPage: true });

    await confirmed(owner, 'GET', `/${householdId}/members`, () => owner.getByRole('button', { name: 'Odśwież gospodarstwo', exact: true }).click(), 200);
    const changed = await confirmed(owner, 'PUT', `/members/${resident.id}/access`, () => card.getByRole('button', { name: 'Odbierz dostęp Zaproszona osoba', exact: true }).click(), 200);
    expect((await changed.json()).access_enabled).toBe(false);
    expect((await recipient.request.get(base)).status()).toBe(404);
    expect((await recipient.request.get(historyPath)).status()).toBe(404);
    expect((await (await recipient.request.get('/api/v1/households')).json()).households).toEqual([]);
    await recipient.reload();
    await expect(recipient.getByTestId('member-card')).toHaveCount(0);
    await expect(recipient.getByRole('button', { name: 'Wyloguj się', exact: true })).toBeVisible();
    await expect(card).toBeVisible();
    await expect(card.getByTestId('target-protein')).toHaveText('0');
    expect((await (await owner.request.get(historyPath)).json()).history).toEqual(originalHistory);
    expect((await (await owner.request.get(`${base}/members`)).json()).members).toHaveLength(2);
    expect(await owner.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(await recipient.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await owner.screenshot({ path: testInfo.outputPath('owner-retained-profile.png'), fullPage: true });
    await recipient.screenshot({ path: testInfo.outputPath('revoked-access.png'), fullPage: true });
    expect(pageErrors).toEqual([]);
  } finally {
    // Clear browser memory before the runner generates a failure DOM snapshot.
    const hideCode = owner.getByRole('button', { name: 'Schowaj kod', exact: true });
    if (await hideCode.count().catch(() => 0)) await hideCode.click().catch(() => undefined);
    await owner.getByTestId('invitation-code').evaluateAll((outputs) => {
      for (const output of outputs) output.textContent = '';
    }).catch(() => undefined);
    await recipient.getByLabel('Kod zaproszenia', { exact: true }).evaluateAll((inputs) => {
      for (const input of inputs) {
        if (input instanceof HTMLInputElement) input.value = '';
      }
    }).catch(() => undefined);
    // Revoke any still-pending synthetic codes if the scenario exits early.
    // Metadata-only listing and boolean/status assertions do not disclose codes.
    if (householdId) {
      const listing = await owner.request.get(`/api/v1/households/${householdId}/invitations`).catch(() => undefined);
      if (listing?.ok()) {
        const entries = (await listing.json()).invitations;
        const current = await owner.request.get('/api/v1/auth/session');
        if (current.ok()) {
          const session = await current.json();
          for (const item of entries.filter((entry: { status: string }) => entry.status === 'pending')) {
            await owner.request.post(`/api/v1/households/${householdId}/invitations/${item.id}/revoke`, {
              headers: { Origin: new URL(testInfo.project.use.baseURL!).origin,
                'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': randomUUID() },
              data: { expected_version: item.version },
            });
          }
        }
      }
    }
    await owner.getByTestId('invitation-code').evaluateAll((outputs) => {
      for (const output of outputs) output.textContent = '';
    }).catch(() => undefined);
    await recipientContext.close();
  }
});
