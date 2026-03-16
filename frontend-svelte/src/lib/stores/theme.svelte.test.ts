import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('ThemeStore', () => {
	let themeStore: typeof import('./theme.svelte').themeStore;

	beforeEach(async () => {
		vi.resetModules();
		// Setup minimal document.documentElement for classList
		document.documentElement.className = '';
		const mod = await import('./theme.svelte');
		themeStore = mod.themeStore;
	});

	it('defaults to dark mode', () => {
		expect(themeStore.isDark).toBe(true);
	});

	it('toggle switches to light and updates document class', () => {
		themeStore.toggle();
		expect(themeStore.isDark).toBe(false);

		themeStore.toggle();
		expect(themeStore.isDark).toBe(true);
	});

	it('toggle adds/removes dark class on documentElement', () => {
		themeStore.toggle(); // → light
		expect(document.documentElement.classList.contains('dark')).toBe(false);

		themeStore.toggle(); // → dark
		expect(document.documentElement.classList.contains('dark')).toBe(true);
	});
});
