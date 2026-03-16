import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock echarts/core before importing the module under test
vi.mock('echarts/core', () => ({
	connect: vi.fn(),
}));

import { LinkedChartGroup } from './LinkedChartGroup.svelte';
import { connect } from 'echarts/core';

describe('LinkedChartGroup', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('starts with size 0 and not connected', () => {
		const group = new LinkedChartGroup(2);
		expect(group.size).toBe(0);
		expect(group.connected).toBe(false);
	});

	it('tracks registered instances', () => {
		const group = new LinkedChartGroup(2);
		const mockChart1 = {} as any;
		group.register('a', mockChart1);
		expect(group.size).toBe(1);
		expect(group.connected).toBe(false);
	});

	it('calls echarts.connect when all expected charts register', () => {
		const group = new LinkedChartGroup(2);
		const chart1 = { id: '1' } as any;
		const chart2 = { id: '2' } as any;

		group.register('a', chart1);
		expect(connect).not.toHaveBeenCalled();

		group.register('b', chart2);
		expect(connect).toHaveBeenCalledOnce();
		expect(connect).toHaveBeenCalledWith([chart1, chart2]);
		expect(group.connected).toBe(true);
	});

	it('unregister removes instance and resets connected', () => {
		const group = new LinkedChartGroup(2);
		group.register('a', {} as any);
		group.register('b', {} as any);
		expect(group.connected).toBe(true);

		group.unregister('a');
		expect(group.size).toBe(1);
		expect(group.connected).toBe(false);
	});

	it('handles single chart group', () => {
		const group = new LinkedChartGroup(1);
		const chart = {} as any;
		group.register('only', chart);
		expect(connect).toHaveBeenCalledWith([chart]);
		expect(group.connected).toBe(true);
	});
});
