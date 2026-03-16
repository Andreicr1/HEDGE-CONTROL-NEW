<script lang="ts">
	import { onMount } from 'svelte';
	import { authStore } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';
	import { formatNumber } from '$lib/utils/format';
	import EChart from '$lib/components/chart/EChart.svelte';

	const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
	let pnlData = $state<any>(null);
	let isLoading = $state(true);

	async function loadData() {
		isLoading = true;
		try {
			const headers: Record<string, string> = {};
			const auth = authStore.getAuthHeader();
			if (auth) headers['Authorization'] = auth;

			const res = await fetch(`${API_BASE}/pl/snapshot/latest`, { headers });
			if (res.ok) pnlData = await res.json();
		} catch {
			notifications.error('Erro ao carregar P&L');
		} finally {
			isLoading = false;
		}
	}

	onMount(() => loadData());

	let chartOptions = $derived(() => {
		if (!pnlData?.items && !pnlData?.entries) return {};
		const entries = pnlData.items ?? pnlData.entries ?? [];
		return {
			tooltip: { trigger: 'axis' as const },
			legend: { data: ['Realizado', 'Não-realizado'] },
			xAxis: {
				type: 'category' as const,
				data: entries.map((e: any) => e.commodity ?? e.label ?? ''),
			},
			yAxis: { type: 'value' as const },
			series: [
				{
					name: 'Realizado',
					type: 'bar' as const,
					stack: 'pnl',
					data: entries.map((e: any) => e.realized_pnl ?? e.realized ?? 0),
					itemStyle: { color: '#00c087' },
				},
				{
					name: 'Não-realizado',
					type: 'bar' as const,
					stack: 'pnl',
					data: entries.map((e: any) => e.unrealized_pnl ?? e.unrealized ?? 0),
					itemStyle: { color: '#3b82f6' },
				},
			],
		};
	});
</script>

{#if isLoading}
	<div class="text-surface-500">Carregando P&L...</div>
{:else if pnlData}
	<div class="grid grid-cols-3 gap-4 mb-6">
		<div class="rounded border border-surface-800 bg-surface-900 p-3">
			<div class="text-xs text-surface-500">P&L Realizado</div>
			<div class="text-lg font-semibold tabular-nums text-success">
				{formatNumber(pnlData.total_realized ?? pnlData.realized_total)}
			</div>
		</div>
		<div class="rounded border border-surface-800 bg-surface-900 p-3">
			<div class="text-xs text-surface-500">P&L Não-realizado</div>
			<div class="text-lg font-semibold tabular-nums text-accent">
				{formatNumber(pnlData.total_unrealized ?? pnlData.unrealized_total)}
			</div>
		</div>
		<div class="rounded border border-surface-800 bg-surface-900 p-3">
			<div class="text-xs text-surface-500">P&L Total</div>
			<div class="text-lg font-semibold tabular-nums text-surface-200">
				{formatNumber((pnlData.total_realized ?? 0) + (pnlData.total_unrealized ?? 0))}
			</div>
		</div>
	</div>

	<EChart options={chartOptions()} style="width:100%;height:400px" />
{:else}
	<div class="text-surface-500">Nenhum dado de P&L disponível</div>
{/if}
