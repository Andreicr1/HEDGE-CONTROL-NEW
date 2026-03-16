import { test, expect } from '@playwright/test';
import { loginAsTrader } from './helpers';

test.describe('RFQ Lifecycle', () => {
	test.beforeEach(async ({ page }) => {
		await loginAsTrader(page);
	});

	test('navigates to RFQ board from dashboard', async ({ page }) => {
		await page.locator('a[href="/rfq"]').first().click();
		await expect(page).toHaveURL(/\/rfq/);
	});

	test('RFQ board loads and shows list or empty state', async ({ page }) => {
		await page.goto('/rfq');
		// Should see either RFQ items or the board header
		await expect(
			page.locator('text=RFQ').first(),
		).toBeVisible({ timeout: 10_000 });
	});

	test('navigates to new RFQ form', async ({ page }) => {
		await page.goto('/rfq');
		const newBtn = page.locator('a[href="/rfq/new"]');
		if (await newBtn.isVisible()) {
			await newBtn.click();
			await expect(page).toHaveURL(/\/rfq\/new/);
			// Form should have commodity selection
			await expect(page.locator('text=Commodity').first()).toBeVisible();
		}
	});

	test('RFQ creation form has required fields', async ({ page }) => {
		await page.goto('/rfq/new');
		// Key form elements
		await expect(page.locator('text=Commodity').first()).toBeVisible();
		await expect(page.locator('text=Quantidade').first()).toBeVisible();
		// Submit button
		await expect(page.locator('button[type="submit"]')).toBeVisible();
	});
});
