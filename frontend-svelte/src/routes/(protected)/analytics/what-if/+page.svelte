<script lang="ts">
	import { authStore } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';
	import { formatNumber } from '$lib/utils/format';
	import EChart from '$lib/components/chart/EChart.svelte';

	const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

	// Only risk_manager and auditor
	let allowed = $derived(authStore.hasAnyRole('risk_manager', 'auditor'));

	// Parameters
	let priceShock = $state(0);
	let volumeChange = $state(0);
	let commodity = $state('ALUMINIUM');
	let result = $state<any>(null);
	let isRunning = $state(false);

	async function runScenario() {
		isRunning = true;
		try {
			const headers: Record<string, string> = { 'Content-Type': 'application/json' };
			const auth = authStore.getAuthHeader();
			if (auth) headers['Authorization'] = auth;

			const res = await fetch(`${API_BASE}/scenario/what-if/run`, {
				method: 'POST',
				headers,
				body: JSON.stringify({
					price_shock_pct: priceShock,
					volume_change_pct: volumeChange,
					commodity,
				}),
			});
			if (res.ok) {
				result = await res.json();
			} else {
				const err = await res.json().catch(() => ({ detail: 'Erro' }));
				notifications.error(typeof err.detail === 'string' ? err.detail : 'Erro no cenário');
			}
		} catch {
			notifications.error('Erro ao executar cenário');
		} finally {
			isRunning = false;
		}
	}

	let chartOptions = $derived(() => {
		if (!result) return {};
		const base = result.base ?? {};
		const scenario = result.scenario ?? {};
		const categories = Object.keys(base).length > 0 ? Object.keys(base) : ['P&L'];

		return {
			tooltip: { trigger: 'axis' as const },
			legend: { data: ['Base', 'Cenário'] },
			xAxis: { type: 'category' as const, data: categories },
			yAxis: { type: 'value' as const },
			series: [
				{
					name: 'Base',
					type: 'bar' as const,
					data: categories.map((k) => base[k] ?? result.base_pnl ?? 0),
					itemStyle: { color: '#64748b' },
				},
				{
					name: 'Cenário',
					type: 'bar' as const,
					data: categories.map((k) => scenario[k] ?? result.scenario_pnl ?? 0),
					itemStyle: { color: '#f59e0b' },
				},
			],
		};
	});
</script>

{#if !allowed}
	<div class="text-surface-500">Acesso restrito a Risk Manager e Auditor.</div>
{:else}
	<div class="grid grid-cols-[300px_1fr] gap-6">
		<!-- Parameters -->
		<div class="space-y-4">
			<div>
				<label class="block text-xs text-surface-500" for="wif-commodity">Commodity</label>
				<select id="wif-commodity" bind:value={commodity} class="mt-1 w-full rounded border border-surface-700 bg-surface-800 px-2 py-1.5 text-sm text-surface-200">
					<option value="ALUMINIUM">Aluminium</option>
					<option value="COPPER">Copper</option>
					<option value="ZINC">Zinc</option>
				</select>
			</div>
			<div>
				<label class="block text-xs text-surface-500" for="wif-price">Price Shock (%)</label>
				<input id="wif-price" type="number" step="0.5" bind:value={priceShock} class="mt-1 w-full rounded border border-surface-700 bg-surface-800 px-2 py-1.5 text-sm text-surface-200 tabular-nums" />
			</div>
			<div>
				<label class="block text-xs text-surface-500" for="wif-volume">Volume Change (%)</label>
				<input id="wif-volume" type="number" step="0.5" bind:value={volumeChange} class="mt-1 w-full rounded border border-surface-700 bg-surface-800 px-2 py-1.5 text-sm text-surface-200 tabular-nums" />
			</div>
			<button
				onclick={runScenario}
				disabled={isRunning}
				class="w-full rounded bg-warning px-4 py-2 text-sm font-medium text-surface-950 hover:bg-warning-hover disabled:opacity-50"
			>
				{isRunning ? 'Executando...' : 'Executar Cenário'}
			</button>

			{#if result}
				<div class="rounded border border-surface-800 bg-surface-900 p-3 space-y-1">
					<div class="text-xs text-surface-500">Impacto</div>
					<div class="text-sm tabular-nums text-surface-200">
						Base: {formatNumber(result.base_pnl ?? result.base_total)}
					</div>
					<div class="text-sm tabular-nums text-warning">
						Cenário: {formatNumber(result.scenario_pnl ?? result.scenario_total)}
					</div>
					<div class="text-sm tabular-nums font-medium {(result.delta ?? result.impact ?? 0) >= 0 ? 'text-success' : 'text-danger'}">
						Delta: {formatNumber(result.delta ?? result.impact)}
					</div>
				</div>
			{/if}
		</div>

		<!-- Chart -->
		<div>
			{#if result}
				<EChart options={chartOptions()} style="width:100%;height:450px" />
			{:else}
				<div class="flex h-[450px] items-center justify-center text-surface-500">
					Configure os parâmetros e execute o cenário
				</div>
			{/if}
		</div>
	</div>
{/if}
