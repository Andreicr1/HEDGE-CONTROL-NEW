/**
 * TanStack Table Svelte 5 adapter.
 *
 * Uses $state for table options and state, $effect for syncing.
 * Based on: https://github.com/walker-tx/svelte5-tanstack-table-reference
 */

import {
	createTable,
	type RowData,
	type TableOptions,
	type TableState,
	type Table,
	type TableOptionsResolved,
} from '@tanstack/table-core';

export function createSvelteTable<TData extends RowData>(
	optionsFn: () => TableOptions<TData>
): Table<TData> {
	const resolvedOptions = $derived(optionsFn());

	let tableState = $state<TableState>({} as TableState);

	const table = createTable({
		...resolvedOptions,
		state: {
			...tableState,
			...resolvedOptions.state,
		},
		onStateChange: (updater) => {
			const newState = typeof updater === 'function' ? updater(tableState) : updater;
			tableState = newState;
		},
		renderFallbackValue: null,
	} as TableOptionsResolved<TData>);

	$effect(() => {
		table.setOptions((prev) => ({
			...prev,
			...resolvedOptions,
			state: {
				...tableState,
				...resolvedOptions.state,
			},
			onStateChange: (updater) => {
				const newState = typeof updater === 'function' ? updater(tableState) : updater;
				tableState = newState;
			},
		}));
	});

	return table;
}
