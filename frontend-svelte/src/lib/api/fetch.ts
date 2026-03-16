import { authStore } from '$lib/stores/auth.svelte';

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

/**
 * Centralized fetch wrapper with auth header injection and 401 handling.
 * Replaces per-page apiFetch helpers and raw fetch() calls.
 */
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
	const headers = new Headers(init?.headers);
	const auth = authStore.getAuthHeader();
	if (auth) headers.set('Authorization', auth);
	if (!headers.has('Content-Type') && init?.body) {
		headers.set('Content-Type', 'application/json');
	}

	const response = await fetch(`${API_BASE}${path}`, { ...init, headers });

	if (response.status === 401) {
		authStore.logout();
	}

	return response;
}
