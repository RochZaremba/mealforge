import { expect, test, type Page, type Response } from '@playwright/test';
import { randomUUID } from 'node:crypto';

async function confirmed(
  page: Page,
  method: string,
  suffix: string,
  action: () => Promise<void>,
  status: number,
): Promise<Response> {
  const pending = page.waitForResponse((response) => (
    response.request().method() === method
    && new URL(response.url()).pathname.endsWith(suffix)
  ));
  await action();
  const response = await pending;
  expect(response.status(), await response.text()).toBe(status);
  expect(response.headers()['cache-control']).toContain('no-store');
  return response;
}

test('private household persists two separate nullable targets, history and editable meal slots', async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  const identifier = randomUUID();
  const email = `qa-e2e-${identifier}@example.invalid`;
  const password = `Qa-${identifier}!`;
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));

  await page.goto('/household');
  await page.getByRole('button', { name: 'Załóż konto', exact: true }).click();
  await page.getByLabel('E-mail', { exact: true }).fill(email);
  await page.getByLabel('Hasło', { exact: true }).fill(password);
  await page.getByLabel('Twoje imię', { exact: true }).fill('Osoba A QA');
  await confirmed(page, 'POST', '/auth/register', () => (
    page.getByRole('button', { name: 'Utwórz konto', exact: true }).click()
  ), 201);
  await expect(page.getByText('Konto utworzone. Zaloguj się.', { exact: true })).toBeVisible();
  await page.getByLabel('Hasło', { exact: true }).fill(password);
  await confirmed(page, 'POST', '/auth/login', () => (
    page.getByRole('button', { name: 'Zaloguj się', exact: true }).filter({ visible: true }).last().click()
  ), 200);
  await page.getByLabel('Nazwa gospodarstwa', { exact: true }).fill(`Dom QA ${identifier}`);
  const created = await confirmed(page, 'POST', '/api/v1/households', () => (
    page.getByRole('button', { name: 'Utwórz gospodarstwo', exact: true }).click()
  ), 201);
  const household = await created.json();
  await expect(page.getByTestId('member-card')).toHaveCount(1);
  const firstCard = page.getByTestId('member-card').filter({ hasText: 'Osoba A QA' });
  await expect(firstCard).toBeVisible();
  const firstId = await firstCard.getAttribute('data-member-id');
  expect(firstId).toBeTruthy();
  const membersPath = `/api/v1/households/${household.id}/members`;
  let members = await page.request.get(membersPath);
  expect(members.status()).toBe(200);
  expect((await members.json()).members[0].nutrition_target).toBeNull();

  await page.getByLabel('Imię domownika', { exact: true }).fill('Osoba B QA');
  const added = await confirmed(page, 'POST', '/members', () => (
    page.getByRole('button', { name: 'Dodaj domownika', exact: true }).click()
  ), 201);
  const secondMember = await added.json();
  expect(secondMember.user_id).toBeNull();
  expect(secondMember.nutrition_target).toBeNull();
  await expect(page.getByTestId('member-card')).toHaveCount(2);
  const secondCard = page.getByTestId('member-card').filter({ hasText: 'Osoba B QA' });

  await firstCard.getByRole('button', { name: 'Edytuj cele Osoba A QA', exact: true }).click();
  await firstCard.getByLabel('Kalorie (kcal)', { exact: true }).fill('2700.125');
  await firstCard.getByLabel('Białko (g)', { exact: true }).fill('170.25');
  await firstCard.getByLabel('Węglowodany (g)', { exact: true }).fill('');
  await firstCard.getByLabel('Tłuszcze (g)', { exact: true }).fill('0');
  const firstSaved = await confirmed(page, 'PUT', `/members/${firstId}/nutrition-target`, () => (
    firstCard.getByRole('button', { name: 'Zapisz cele', exact: true }).click()
  ), 200);
  const target = await firstSaved.json();
  expect(target.kcal_target).toBe('2700.125');
  expect(target.protein_target_g).toBe('170.25');
  expect(target.carbs_target_g).toBeNull();
  expect(target.fat_target_g).toBe('0');
  await expect(firstCard.getByTestId('target-carbs')).toHaveText('Nieznane');
  await expect(firstCard.getByTestId('target-fat')).toHaveText(/^0(?:\s*g)?$/);

  await secondCard.getByRole('button', { name: 'Edytuj cele Osoba B QA', exact: true }).click();
  await secondCard.getByLabel('Kalorie (kcal)', { exact: true }).fill('1600');
  for (const label of ['Białko (g)', 'Węglowodany (g)', 'Tłuszcze (g)']) {
    await secondCard.getByLabel(label, { exact: true }).fill('');
  }
  const secondSaved = await confirmed(page, 'PUT', `/members/${secondMember.id}/nutrition-target`, () => (
    secondCard.getByRole('button', { name: 'Zapisz cele', exact: true }).click()
  ), 200);
  const secondTarget = await secondSaved.json();
  expect(secondTarget.kcal_target).toBe('1600');
  expect(secondTarget.protein_target_g).toBeNull();
  expect(secondTarget.carbs_target_g).toBeNull();
  expect(secondTarget.fat_target_g).toBeNull();
  await expect(secondCard.getByTestId('target-fat')).toHaveText('Nieznane');

  await firstCard.getByRole('button', { name: 'Edytuj cele Osoba A QA', exact: true }).click();
  await firstCard.getByLabel('Kalorie (kcal)', { exact: true }).fill('2750.25');
  const revised = await confirmed(page, 'PUT', `/members/${firstId}/nutrition-target`, () => (
    firstCard.getByRole('button', { name: 'Zapisz cele', exact: true }).click()
  ), 200);
  expect((await revised.json()).version).toBe(2);
  const historyRead = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && new URL(response.url()).pathname.endsWith(`/members/${firstId}/nutrition-target/history`)
  ));
  await firstCard.getByRole('button', { name: 'Historia celów Osoba A QA', exact: true }).click();
  const history = await historyRead;
  expect(history.status()).toBe(200);
  const versions = (await history.json()).history;
  expect(versions.map((item: { version: number }) => item.version)).toEqual([2, 1]);
  expect(versions[1]).toEqual(target);
  await expect(firstCard.getByTestId('target-history')).toContainText(/2700[,.]125/);
  await expect(firstCard.getByTestId('target-history')).toContainText(/2750[,.]25/);

  const slotForm = page.getByTestId('meal-slots');
  await expect(slotForm.getByLabel(/^Nazwa posiłku\s*\d+$/)).toHaveCount(5);
  const breakfastRepeat = slotForm.getByLabel('Powtarzaj co tydzień: Śniadanie', { exact: true });
  await expect(breakfastRepeat).toBeChecked();
  await breakfastRepeat.uncheck();
  await slotForm.getByLabel('Nazwa posiłku 1', { exact: true }).fill('Śniadanie QA');
  await slotForm.getByLabel('Godzina posiłku 1', { exact: true }).fill('07:45');
  await slotForm.getByLabel('Udział energii posiłku 1', { exact: true }).fill('0.2');
  const savedSlots = await confirmed(page, 'PUT', '/meal-slot-presets', () => (
    slotForm.getByRole('button', { name: 'Zapisz posiłki', exact: true }).click()
  ), 200);
  const slots = await savedSlots.json();
  expect(slots.slots).toHaveLength(5);
  expect(slots.slots[0]).toMatchObject({
    name: 'Śniadanie QA', repeat_weekly: false, default_time: '07:45:00', default_share: '0.2',
  });
  await page.reload();
  await expect(page.getByTestId('member-card')).toHaveCount(2);
  await expect(firstCard.getByTestId('target-carbs')).toHaveText('Nieznane');
  await expect(firstCard.getByTestId('target-fat')).toHaveText(/^0(?:\s*g)?$/);
  await expect(secondCard.getByTestId('target-kcal')).toHaveText(/^1600(?:\s*kcal)?$/);
  await expect(slotForm.getByLabel('Nazwa posiłku 1', { exact: true })).toHaveValue('Śniadanie QA');
  await expect(slotForm.getByLabel('Powtarzaj co tydzień: Śniadanie QA', { exact: true })).not.toBeChecked();
  members = await page.request.get(membersPath);
  const persisted = (await members.json()).members;
  expect(persisted.find((item: { id: string }) => item.id === firstId).nutrition_target.kcal_target).toBe('2750.25');
  expect(persisted.find((item: { id: string }) => item.id === secondMember.id).nutrition_target.kcal_target).toBe('1600');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('private-household.png'), fullPage: true });

  const cachedPaths = await page.evaluate(async () => {
    const paths: string[] = [];
    for (const cacheName of await caches.keys()) {
      for (const entry of await (await caches.open(cacheName)).keys()) {
        paths.push(new URL(entry.url).pathname);
      }
    }
    return paths;
  });
  expect(cachedPaths.some((path) => path.startsWith('/api/v1/') || path === '/household')).toBe(false);
  await confirmed(page, 'POST', '/auth/logout', () => (
    page.getByRole('button', { name: 'Wyloguj się', exact: true }).click()
  ), 204);
  await expect(page.getByTestId('member-card')).toHaveCount(0);
  expect((await page.request.get(membersPath)).status()).toBe(401);
  await page.reload();
  await expect(page.getByLabel('E-mail', { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});
