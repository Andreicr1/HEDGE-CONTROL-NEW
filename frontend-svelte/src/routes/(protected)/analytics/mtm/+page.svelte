<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { notifications } from '$lib/stores/notifications.svelte';
	import { apiFetch } from '$lib/api/fetch';
	import EChart from '$lib/components/chart/EChart.svelte';
	import type { MtmSnapshot } from '$lib/api/types/entities';

	let mtmData = $state<MtmSnapshot | null>(null);
	let isLoading = $state(true);
	let abortController: AbortController;

	async function loadData(signal?: AbortSignal) {
		isLoading = true;
		try {
			const res = await apiFetch('/mtm/snapshots/latest', { signal });
			if (res.ok) mtmData = await res.json();
		} catch (e) {
			if (e instanceof DOMException && e.name === 'AbortError') return;
			notifications.error('Erro ao carregar MTM');
		} finally {
			isLoading = false;
		}
	}

	onMount(() => {
		abortController = new AbortController();
		loadData(abortController.signal);
	});

	onDestroy(() => { abortController?.abort(); });

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
