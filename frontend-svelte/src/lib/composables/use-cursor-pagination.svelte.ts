/**
 * Cursor-based pagination composable.
 * Handles cursor/next_cursor pattern with in-flight guard.
 */

type FetchFn<T> = (cursor: string | null) => Promise<{ items: T[]; next_cursor: string | null }>;

export function useCursorPagination<T>(fetchFn: FetchFn<T>) {
	let items = $state<T[]>([]);
	let isLoading = $state(false);
	let hasMore = $state(true);
	let cursor = $state<string | null>(null);
	let error = $state<string | null>(null);

	async function loadMore() {
		if (isLoading || !hasMore) return;
		isLoading = true;
		error = null;
		try {
			const result = await fetchFn(cursor);
			items = [...items, ...result.items];
			cursor = result.next_cursor;
			hasMore = result.next_cursor !== null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erro ao carregar dados';
		} finally {
			isLoading = false;
		}
	}

	async function refresh() {
		items = [];
		cursor = null;
		hasMore = true;
		error = null;
		await loadMore();
	}

	return {
		get items() { return items; },
		get isLoading() { return isLoading; },
		get hasMore() { return hasMore; },
		get error() { return error; },
		loadMore,
		refresh,
	};
}
