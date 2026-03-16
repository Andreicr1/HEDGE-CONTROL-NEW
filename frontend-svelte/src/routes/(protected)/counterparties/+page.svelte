<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';

	const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
	let counterparties = $state<any[]>([]);
	let isLoading = $state(true);
	let search = $state('');

	async function loadCounterparties() {
		isLoading = true;
		try {
			const headers: Record<string, string> = {};
			const auth = authStore.getAuthHeader();
			if (auth) headers['Authorization'] = auth;
			const res = await fetch(`${API_BASE}/counterparties?limit=200`, { headers });
			if (res.ok) {
				const data = await res.json();
				counterparties = data.items ?? data;
			}
		} catch {
			notifications.error('Erro ao carregar contrapartes');
		} finally {
			isLoading = false;
		}
	}

	onMount(() => loadCounterparties());

	let filtered = $derived(
		counterparties.filter((cp) => {
			if (!search) return true;
			const q = search.toLowerCase();
			return cp.name?.toLowerCase().includes(q) || cp.short_name?.toLowerCase().includes(q);
		})
	);
</script>

<div class="p-6">
	<h1 class="text-lg font-semibold text-surface-200">Contrapartes</h1>

	<input
		type="text"
		bind:value={search}
		placeholder="Buscar..."
		class="mt-4 w-64 rounded border border-surface-700 bg-surface-800 px-3 py-1.5 text-sm text-surface-200 placeholder-surface-600"
	/>

	<div class="mt-4 overflow-x-auto rounded border border-surface-800">
		<table class="w-full text-sm">
			<thead>
				<tr class="border-b border-surface-800 bg-surface-900 text-left text-xs text-surface-500">
					<th class="px-3 py-2">Nome</th>
					<th class="px-3 py-2">Abreviação</th>
					<th class="px-3 py-2">Tipo</th>
					<th class="px-3 py-2">Telefone</th>
					<th class="px-3 py-2">KYC</th>
				</tr>
			</thead>
			<tbody>
				{#each filtered as cp (cp.id)}
					<tr
						onclick={() => goto(`/counterparties/${cp.id}`)}
						class="border-b border-surface-800/50 cursor-pointer hover:bg-surface-800/30"
					>
						<td class="px-3 py-2 text-surface-200">{cp.name}</td>
						<td class="px-3 py-2 text-surface-400">{cp.short_name ?? '—'}</td>
						<td class="px-3 py-2 text-xs text-surface-400">{cp.type ?? '—'}</td>
						<td class="px-3 py-2 font-mono text-xs text-surface-400">{cp.whatsapp_phone ?? cp.phone ?? '—'}</td>
						<td class="px-3 py-2">
							<span class="rounded px-1.5 py-0.5 text-xs {cp.kyc_status === 'approved' ? 'bg-success/20 text-success' : cp.kyc_status === 'pending' ? 'bg-warning/20 text-warning' : 'bg-surface-700 text-surface-400'}">
								{cp.kyc_status ?? '—'}
							</span>
						</td>
					</tr>
				{:else}
					{#if !isLoading}
						<tr><td colspan="5" class="px-3 py-8 text-center text-surface-500">Nenhuma contraparte encontrada</td></tr>
					{/if}
				{/each}
			</tbody>
		</table>
	</div>
</div>
