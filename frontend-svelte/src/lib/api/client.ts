import createClient from 'openapi-fetch';
import type { paths } from './schema';
import { authStore } from '$lib/stores/auth.svelte';

export const client = createClient<paths>({
	baseUrl: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
});

client.use({
	async onRequest({ request }) {
		const header = authStore.getAuthHeader();
		if (header) request.headers.set('Authorization', header);
		return request;
	},
	async onResponse({ response }) {
		if (response.status === 401) {
			authStore.logout();
		}
		return response;
	},
});
