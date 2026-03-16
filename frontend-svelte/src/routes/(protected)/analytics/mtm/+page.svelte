<script lang="ts">
	import { onMount } from 'svelte';
	import { authStore } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';
	import EChart from '$lib/components/chart/EChart.svelte';

	const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
	let mtmData = $state<any>(null);
	let isLoading = $state(true);

	async function loadData() {
		isLoading = true;
		try {
			const headers: Record<string, string> = {};
			const auth = authStore.getAuthHeader();
			if (auth) headers['Authorization'] = auth;
			const res = await fetch(`${API_BASE}/mtm/snapshots/latest`, { headers });
			if (res.ok) mtmData = await res.json();
		} catch {
			notifications.error('Erro ao carregar MTM');
		} finally {
			isLoading = false;
		}
	}

	onMount(() => loadData());

	let chartOptions = $derived.by(() => {
		if (!mtmData?.items && !mtmData?.entries) return {};
		const entries = mtmData.items ?? mtmData.entries ?? [];
		return {
			tooltip: { trigger: 'axis' as const },
			xAxis: {
				type: 'category' as const,
				data: entries.map((e: any) => e.date ?? e.snapshot_date ?? e.label ?? ''),
			},
			yAxis: { type: 'value' as const },
			series: [
				{
					name: 'MTM',
					type: 'line' as const,
					data: entries.map((e: any) => e.mtm_value ?? e.value ?? 0),
					smooth: true,
					areaStyle: { opacity: 0.1 },
					itemStyle: { color: '#3b82f6' },
				},
			],
			dataZoom: [{ type: 'inside' as const }],
		};
	});
</script>

{#if isLoading}
	<div class="text-surface-500">Carregando MTM...</div>
{:else if mtmData}
	<EChart options={chartOptions} style="width:100%;height:450px" />
{:else}
	<div class="text-surface-500">Nenhum dado de MTM disponível</div>
{/if}
