<script lang="ts">
	import { createSvelteTable } from '$lib/components/table/create-table.svelte';
	import { getCoreRowModel, getSortedRowModel, getFilteredRowModel, type TableOptions, type RowData } from '@tanstack/table-core';

	let { options, onTable }: { options: () => TableOptions<any>; onTable: (t: any) => void } = $props();

	const table = createSvelteTable(() => options());

	// Expose table to test via callback
	$effect(() => {
		onTable(table);
	});
</script>

<div data-testid="table-wrapper">
	{#each table.getRowModel().rows as row}
		<div data-testid="row">{row.id}</div>
	{/each}
</div>
