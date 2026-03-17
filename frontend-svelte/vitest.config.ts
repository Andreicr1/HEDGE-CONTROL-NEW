import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
	plugins: [svelte({ hot: false })],
	resolve: {
		conditions: ['browser'],
	},
	test: {
		include: ['src/**/*.test.ts'],
		environment: 'jsdom',
		setupFiles: ['src/tests/setup.ts'],
		globals: true,
		alias: {
			'$lib': new URL('./src/lib', import.meta.url).pathname,
			'$app/navigation': new URL('./src/tests/mocks/app-navigation.ts', import.meta.url).pathname,
			'$app/environment': new URL('./src/tests/mocks/app-environment.ts', import.meta.url).pathname,
		},
		coverage: {
			provider: 'v8',
			include: ['src/lib/**/*.ts', 'src/lib/**/*.svelte.ts'],
			exclude: ['src/lib/api/schema.d.ts', 'src/tests/**'],
			reporter: ['text', 'html'],
		},
	},
});
