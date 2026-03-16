import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useCursorPagination } from './use-cursor-pagination.svelte';

describe('useCursorPagination', () => {
	it('loads initial page', async () => {
		const fetchFn = vi.fn().mockResolvedValueOnce({
			items: [{ id: 1 }, { id: 2 }],
			next_cursor: 'cursor-1',
		});

		const pag = useCursorPagination(fetchFn);
		await pag.loadMore();

		expect(pag.items).toEqual([{ id: 1 }, { id: 2 }]);
		expect(pag.hasMore).toBe(true);
		expect(pag.isLoading).toBe(false);
		expect(fetchFn).toHaveBeenCalledWith(null);
	});

	it('appends items on loadMore', async () => {
		const fetchFn = vi.fn()
			.mockResolvedValueOnce({ items: [{ id: 1 }], next_cursor: 'c1' })
			.mockResolvedValueOnce({ items: [{ id: 2 }], next_cursor: null });

		const pag = useCursorPagination(fetchFn);
		await pag.loadMore();
		await pag.loadMore();

		expect(pag.items).toEqual([{ id: 1 }, { id: 2 }]);
		expect(pag.hasMore).toBe(false);
		expect(fetchFn).toHaveBeenCalledWith('c1');
	});

	it('does not load when already loading (in-flight guard)', async () => {
		let resolveFirst: (v: unknown) => void;
		const fetchFn = vi.fn().mockImplementation(() =>
			new Promise((resolve) => { resolveFirst = resolve; })
		);

		const pag = useCursorPagination(fetchFn);
		const p1 = pag.loadMore();
		pag.loadMore(); // should be ignored

		expect(fetchFn).toHaveBeenCalledTimes(1);

		resolveFirst!({ items: [], next_cursor: null });
		await p1;
	});

	it('does not load when hasMore is false', async () => {
		const fetchFn = vi.fn()
			.mockResolvedValueOnce({ items: [{ id: 1 }], next_cursor: null });

		const pag = useCursorPagination(fetchFn);
		await pag.loadMore();
		await pag.loadMore(); // hasMore is false

		expect(fetchFn).toHaveBeenCalledTimes(1);
	});

	it('handles errors gracefully', async () => {
		const fetchFn = vi.fn().mockRejectedValueOnce(new Error('Network error'));

		const pag = useCursorPagination(fetchFn);
		await pag.loadMore();

		expect(pag.error).toBe('Network error');
		expect(pag.isLoading).toBe(false);
	});

	it('refresh resets state and reloads', async () => {
		const fetchFn = vi.fn()
			.mockResolvedValueOnce({ items: [{ id: 1 }], next_cursor: 'c1' })
			.mockResolvedValueOnce({ items: [{ id: 10 }], next_cursor: null });

		const pag = useCursorPagination(fetchFn);
		await pag.loadMore();
		await pag.refresh();

		expect(pag.items).toEqual([{ id: 10 }]);
		expect(fetchFn).toHaveBeenCalledTimes(2);
		// Second call should use null cursor (refresh)
		expect(fetchFn.mock.calls[1][0]).toBeNull();
	});
});
