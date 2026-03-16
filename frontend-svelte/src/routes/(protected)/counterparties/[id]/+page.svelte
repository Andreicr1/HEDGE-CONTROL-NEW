<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';

	const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
	const cpId = $derived(page.params.id ?? '');
	let cp = $state<any>(null);
	let isLoading = $state(true);

	async function loadCounterparty() {
		isLoading = true;
		try {
			const headers: Record<string, string> = {};
			const auth = authStore.getAuthHeader();
			if (auth) headers['Authorization'] = auth;
			const res = await fetch(`${API_BASE}/counterparties/${cpId}`, { headers });
			if (res.ok) cp = await res.json();
			else if (res.status === 404) goto('/counterparties');
		} catch {
			notifications.error('Erro ao carregar contraparte');
		} finally {
			isLoading = false;
		}
	}

	onMount(() => loadCounterparty());
</script>

<div class="p-6">
	<a href="/counterparties" class="text-sm text-surface-500 hover:text-surface-300">← Contrapartes</a>

	{#if isLoading}
		<div class="mt-4 text-surface-500">Carregando...</div>
	{:else if cp}
		<h1 class="mt-4 text-lg font-semibold text-surface-200">{cp.name}</h1>

		<div class="mt-4 grid grid-cols-2 gap-4">
			<div class="rounded border border-surface-800 bg-surface-900 p-4 space-y-2">
				<h2 class="text-xs font-semibold uppercase text-surface-500">Informações</h2>
				<div class="text-sm"><span class="text-surface-500">Nome:</span> <span class="text-surface-200">{cp.name}</span></div>
				<div class="text-sm"><span class="text-surface-500">Abreviação:</span> <span class="text-surface-200">{cp.short_name ?? '—'}</span></div>
				<div class="text-sm"><span class="text-surface-500">Tipo:</span> <span class="text-surface-200">{cp.type ?? '—'}</span></div>
				<div class="text-sm"><span class="text-surface-500">WhatsApp:</span> <span class="text-surface-200 font-mono">{cp.whatsapp_phone ?? '—'}</span></div>
			</div>
			<div class="rounded border border-surface-800 bg-surface-900 p-4 space-y-2">
				<h2 class="text-xs font-semibold uppercase text-surface-500">Compliance</h2>
				<div class="text-sm"><span class="text-surface-500">KYC:</span>
					<span class="rounded px-1.5 py-0.5 text-xs {cp.kyc_status === 'approved' ? 'bg-success/20 text-success' : 'bg-warning/20 text-warning'}">
						{cp.kyc_status ?? '—'}
					</span>
				</div>
				<div class="text-sm"><span class="text-surface-500">Sanções:</span>
					<span class="text-surface-200">{cp.sanctions_status ?? '—'}</span>
				</div>
			</div>
		</div>
	{/if}
</div>
