<script lang="ts" module>
	import type { ComposeOption } from 'echarts/core';
	import type { LineSeriesOption, BarSeriesOption, ScatterSeriesOption } from 'echarts/charts';
	import type {
		GridComponentOption,
		TooltipComponentOption,
		LegendComponentOption,
		DataZoomComponentOption,
	} from 'echarts/components';

	export type TradingChartOption = ComposeOption<
		| LineSeriesOption
		| BarSeriesOption
		| ScatterSeriesOption
		| GridComponentOption
		| TooltipComponentOption
		| LegendComponentOption
		| DataZoomComponentOption
	>;
</script>

<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { init, use } from 'echarts/core';
	import { SVGRenderer } from 'echarts/renderers';
	import { LineChart, BarChart, ScatterChart } from 'echarts/charts';
	import {
		GridComponent,
		TooltipComponent,
		LegendComponent,
		DataZoomComponent,
	} from 'echarts/components';
	import type { LinkedChartGroup } from './LinkedChartGroup.svelte';

	use([
		SVGRenderer,
		LineChart,
		BarChart,
		ScatterChart,
		GridComponent,
		TooltipComponent,
		LegendComponent,
		DataZoomComponent,
	]);

	type Props = {
		options: TradingChartOption;
		style?: string;
		theme?: string;
		/** Optional chart group for crosshair sync between linked charts */
		group?: LinkedChartGroup;
		/** Unique ID within the group (required if group is provided) */
		groupId?: string;
	};

	let {
		options,
		style = 'width:100%;height:400px',
		theme = 'dark',
		group,
		groupId,
	}: Props = $props();

	let container: HTMLDivElement;
	let chart: ReturnType<typeof init> | null = null;
	let resizeObserver: ResizeObserver | null = null;
	let rafId: number | null = null;

	onMount(() => {
		chart = init(container, theme === 'dark' ? tradingDarkTheme : undefined, {
			renderer: 'svg',
		});
		chart.setOption(options);

		if (group && groupId) {
			group.register(groupId, chart);
		}

		// Debounced resize via RAF
		resizeObserver = new ResizeObserver(() => {
			if (rafId) cancelAnimationFrame(rafId);
			rafId = requestAnimationFrame(() => {
				chart?.resize();
			});
		});
		resizeObserver.observe(container);
	});

	$effect(() => {
		if (chart) {
			chart.setOption(options, { notMerge: false });
		}
	});

	onDestroy(() => {
		if (rafId) cancelAnimationFrame(rafId);
		resizeObserver?.disconnect();
		if (group && groupId) {
			group.unregister(groupId);
		}
		chart?.dispose();
		chart = null;
	});

	const tradingDarkTheme = {
		color: ['#3fb950', '#f85149', '#c9a84c', '#58a6ff', '#26a88f'],
		backgroundColor: 'transparent',
		textStyle: { color: '#8b949e' },
	};
</script>

<div bind:this={container} {style}></div>
