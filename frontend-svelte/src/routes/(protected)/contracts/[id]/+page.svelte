<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';
	import { formatDate, formatNumber } from '$lib/utils/format';

	const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
	const contractId = $derived(page.params.id ?? '');
	let contract = $state<any>(null);
	let isLoading = $state(true);

	async function loadContract() {
		isLoading = true;
		try {
			const headers: Record<string, string> = {};
			const auth = authStore.getAuthHeader();
			if (auth) headers['Authorization'] = auth;
			const res = await fetch(`${API_BASE}/contracts/${contractId}`, { headers });
			if (res.ok) contract = await res.json();
			else if (res.status === 404) goto('/contracts');
		} catch {
			notifications.error('Erro ao carregar contrato');
		} finally {
			isLoading = false;
		}
	}

	onMount(() => loadContract());
</script>

<div class="p-6">
	<a href="/contracts" class="text-sm text-surface-500 hover:text-surface-300">← Contratos</a>

	{#if isLoading}
		<div class="mt-4 text-surface-500">Carregando...</div>
	{:else if contract}
		<div class="mt-4 flex items-center gap-3">
			<h1 class="text-lg font-semibold text-surface-200">{contract.reference}</h1>
			<span class="rounded px-1.5 py-0.5 text-xs {contract.status === 'active' ? 'bg-success/20 text-success' : 'bg-surface-700 text-surface-400'}">
				{contract.status}
			</span>
		</div>

		<div class="mt-4 grid grid-cols-2 gap-4">
			<div class="rounded border border-surface-800 bg-surface-900 p-4 space-y-2">
				<h2 class="text-xs font-semibold uppercase text-surface-500">Detalhes</h2>
				<div class="text-sm"><span class="text-surface-500">Commodity:</span> <span class="text-surface-200">{contract.commodity}</span></div>
				<div class="text-sm"><span class="text-surface-500">Quantidade:</span> <span class="text-surface-200 tabular-nums">{formatNumber(contract.quantity_mt)} MT</span></div>
				<div class="text-sm"><span class="text-surface-500">Preço Fixo:</span> <span class="text-surface-200 tabular-nums">{formatNumber(contract.fixed_price_value)} {contract.fixed_price_unit ?? ''}</span></div>
				<div class="text-sm"><span class="text-surface-500">Classificação:</span> <span class="text-surface-200">{contract.classification ?? '—'}</span></div>
				<div class="text-sm"><span class="text-surface-500">Trade Date:</span> <span class="text-surface-200">{formatDate(contract.trade_date)}</span></div>
			</div>

			<div class="rounded border border-surface-800 bg-surface-900 p-4 space-y-2">
				<h2 class="text-xs font-semibold uppercase text-surface-500">Legs</h2>
				<div class="text-sm"><span class="text-surface-500">Fixed Leg:</span> <span class="text-surface-200">{contract.fixed_leg_side ?? '—'}</span></div>
				<div class="text-sm"><span class="text-surface-500">Variable Leg:</span> <span class="text-surface-200">{contract.variable_leg_side ?? '—'}</span></div>
				<div class="text-sm"><span class="text-surface-500">Float Convention:</span> <span class="text-surface-200">{contract.float_pricing_convention ?? '—'}</span></div>
				<div class="text-sm"><span class="text-surface-500">Source:</span> <span class="text-surface-200">{contract.source_type ?? '—'}</span></div>
			</div>
		</div>
	{/if}
</div>
