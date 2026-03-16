<script lang="ts">
	import { onMount } from 'svelte';
	import { notifications } from '$lib/stores/notifications.svelte';
	import { formatNumber, formatDate } from '$lib/utils/format';
	import { apiFetch } from '$lib/api/fetch';
	import { type ColumnDef } from '@tanstack/table-core';
	import DataTable from '$lib/components/table/DataTable.svelte';

	let activeTab = $state<'analytics' | 'projections' | 'ledger'>('analytics');
	let isLoading = $state(true);

	// Data
	let analytics = $state<any[]>([]);
	let projections = $state<any[]>([]);
	let ledger = $state<any[]>([]);
	let summary = $state<any>(null);

	// Date filter
	let dateFrom = $state('');
	let dateTo = $state('');

	async function loadData() {
		isLoading = true;
		try {
			const params = new URLSearchParams();
			if (dateFrom) params.set('date_from', dateFrom);
			if (dateTo) params.set('date_to', dateTo);
			const qs = params.toString() ? `?${params}` : '';

			const [analyticsRes, projectionsRes, ledgerRes] = await Promise.all([
				apiFetch(`/cashflow/analytics${qs}`),
				apiFetch(`/cashflow/projections${qs}`),
				apiFetch(`/cashflow/ledger${qs}`),
			]);

			if (analyticsRes.ok) {
				const data = await analyticsRes.json();
				analytics = data.items ?? data.entries ?? data;
				summary = data.summary ?? null;
			}
			if (projectionsRes.ok) {
				const data = await projectionsRes.json();
				projections = data.items ?? data;
			}
			if (ledgerRes.ok) {
				const data = await ledgerRes.json();
				ledger = data.items ?? data;
			}
		} catch {
			notifications.error('Erro ao carregar cashflow');
		} finally {
			isLoading = false;
		}
	}

	onMount(() => loadData());

	// ─── Ledger Columns ─────────────────────────────────────────────────
	const ledgerColumns: ColumnDef<any, any>[] = [
		{
			accessorFn: (row) => row.date ?? row.settlement_date,
			id: 'date',
			header: 'Data',
			cell: (info) => formatDate(info.getValue() as string),
		},
		{
			accessorFn: (row) => row.contract_reference ?? row.reference,
			id: 'reference',
			header: 'Referência',
		},
		{
			accessorFn: (row) => row.counterparty_name ?? row.counterparty,
			id: 'counterparty',
			header: 'Contraparte',
		},
		{
			accessorFn: (row) => row.commodity,
			id: 'commodity',
			header: 'Commodity',
		},
		{
			accessorFn: (row) => row.inflow ?? (row.amount > 0 ? row.amount : null),
			id: 'inflow',
			header: 'Entrada',
			cell: (info) => {
				const v = info.getValue() as number | null;
				return v != null && v > 0 ? formatNumber(v) : '—';
			},
		},
		{
			accessorFn: (row) => row.outflow ?? (row.amount < 0 ? Math.abs(row.amount) : null),
			id: 'outflow',
			header: 'Saída',
			cell: (info) => {
				const v = info.getValue() as number | null;
				return v != null && v > 0 ? formatNumber(v) : '—';
			},
		},
		{
			accessorFn: (row) => row.balance ?? row.running_balance,
			id: 'balance',
			header: 'Saldo',
			cell: (info) => formatNumber(info.getValue() as number),
		},
	];
</script>

<div class="p-6">
	<h1 class="text-lg font-semibold text-surface-200">Cashflow</h1>

	<!-- Summary cards -->
	{#if summary}
		<div class="mt-4 grid grid-cols-3 gap-4">
			<div class="rounded border border-surface-800 bg-surface-900 p-3">
				<div class="text-xs text-surface-500">Total Entradas</div>
				<div class="text-lg font-semibold tabular-nums text-success">{formatNumber(summary.total_inflows)}</div>
			</div>
			<div class="rounded border border-surface-800 bg-surface-900 p-3">
				<div class="text-xs text-surface-500">Total Saídas</div>
				<div class="text-lg font-semibold tabular-nums text-danger">{formatNumber(summary.total_outflows)}</div>
			</div>
			<div class="rounded border border-surface-800 bg-surface-900 p-3">
				<div class="text-xs text-surface-500">Saldo Líquido</div>
				<div class="text-lg font-semibold tabular-nums text-surface-200">{formatNumber(summary.net_balance)}</div>
			</div>
		</div>
	{/if}

	<!-- Date filter -->
	<div class="mt-4 flex gap-3 items-end">
		<div>
			<label class="block text-xs text-surface-500" for="cf-from">De</label>
			<input id="cf-from" type="date" bind:value={dateFrom} class="rounded border border-surface-700 bg-surface-800 px-2 py-1 text-sm text-surface-200" />
		</div>
		<div>
			<label class="block text-xs text-surface-500" for="cf-to">Até</label>
			<input id="cf-to" type="date" bind:value={dateTo} class="rounded border border-surface-700 bg-surface-800 px-2 py-1 text-sm text-surface-200" />
		</div>
		<button onclick={loadData} class="rounded border border-surface-700 px-3 py-1 text-sm text-surface-400 hover:bg-surface-800">
			Filtrar
		</button>
	</div>

	<!-- Tabs -->
	<div class="mt-6 flex gap-4 border-b border-surface-800">
		<button
			onclick={() => activeTab = 'analytics'}
			class="pb-2 text-sm {activeTab === 'analytics' ? 'border-b-2 border-accent text-accent' : 'text-surface-500 hover:text-surface-300'}"
		>
			Analytics
		</button>
		<button
			onclick={() => activeTab = 'projections'}
			class="pb-2 text-sm {activeTab === 'projections' ? 'border-b-2 border-accent text-accent' : 'text-surface-500 hover:text-surface-300'}"
		>
			Projeções
		</button>
		<button
			onclick={() => activeTab = 'ledger'}
			class="pb-2 text-sm {activeTab === 'ledger' ? 'border-b-2 border-accent text-accent' : 'text-surface-500 hover:text-surface-300'}"
		>
			Ledger
		</button>
	</div>

	<div class="mt-4">
		{#if activeTab === 'analytics'}
			{#if Array.isArray(analytics) && analytics.length > 0}
				<div class="space-y-3">
					{#each analytics as entry (entry.id ?? entry.month ?? entry.period)}
						<div class="rounded border border-surface-800 bg-surface-900 p-3">
							<div class="flex items-center justify-between">
								<span class="text-sm font-medium text-surface-200">{entry.period ?? entry.month ?? entry.commodity}</span>
								<span class="text-sm tabular-nums text-surface-300">{formatNumber(entry.net_amount ?? entry.net)}</span>
							</div>
							<div class="mt-1 flex gap-4 text-xs text-surface-500">
								<span class="text-success">+{formatNumber(entry.inflows ?? entry.total_inflows)}</span>
								<span class="text-danger">-{formatNumber(entry.outflows ?? entry.total_outflows)}</span>
							</div>
						</div>
					{/each}
				</div>
			{:else if !isLoading}
				<div class="text-sm text-surface-500">Nenhum dado analítico disponível</div>
			{/if}

		{:else if activeTab === 'projections'}
			{#if projections.length > 0}
				<div class="space-y-2">
					{#each projections as proj (proj.id ?? proj.month)}
						<div class="flex items-center gap-3 rounded border border-surface-800 bg-surface-900 px-4 py-2">
							<span class="text-sm text-surface-300 w-24">{proj.month ?? proj.period}</span>
							<div class="flex-1 h-4 rounded bg-surface-800 overflow-hidden">
								{#if proj.projected_inflow || proj.inflow}
									<div
										class="h-full bg-success/60"
										style="width: {Math.min(((proj.projected_inflow ?? proj.inflow ?? 0) / (Math.max(proj.projected_inflow ?? proj.inflow ?? 1, proj.projected_outflow ?? proj.outflow ?? 1))) * 100, 100)}%"
									></div>
								{/if}
							</div>
							<span class="text-xs tabular-nums text-surface-400 w-24 text-right">
								{formatNumber(proj.net ?? proj.projected_net)}
							</span>
						</div>
					{/each}
				</div>
			{:else if !isLoading}
				<div class="text-sm text-surface-500">Nenhuma projeção disponível</div>
			{/if}

		{:else}
			<DataTable
				data={ledger}
				columns={ledgerColumns}
				{isLoading}
				emptyMessage="Nenhum lançamento encontrado"
			/>
		{/if}
	</div>
</div>
