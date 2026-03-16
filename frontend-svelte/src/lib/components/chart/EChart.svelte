<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { init, use, type ComposeOption } from 'echarts/core';
	import { SVGRenderer } from 'echarts/renderers';
	import { LineChart, BarChart, ScatterChart } from 'echarts/charts';
	import {
		GridComponent,
		TooltipComponent,
		LegendComponent,
		DataZoomComponent,
	} from 'echarts/components';
	import type { LineSeriesOption, BarSeriesOption, ScatterSeriesOption } from 'echarts/charts';
	import type {
		GridComponentOption,
		TooltipComponentOption,
		LegendComponentOption,
		DataZoomComponentOption,
	} from 'echarts/components';

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

	type TradingChartOption = ComposeOption<
		| LineSeriesOption
		| BarSeriesOption
		| ScatterSeriesOption
		| GridComponentOption
		| TooltipComponentOption
		| LegendComponentOption
		| DataZoomComponentOption
	>;

	type Props = {
		options: TradingChartOption;
		style?: string;
		theme?: string;
	};

	let { options, style = 'width:100%;height:400px', theme = 'dark' }: Props = $props();

	let container: HTMLDivElement;
	let chart: ReturnType<typeof init> | null = null;
	let resizeObserver: ResizeObserver | null = null;
	let rafId: number | null = null;

	onMount(() => {
		chart = init(container, theme === 'dark' ? tradingDarkTheme : undefined, {
			renderer: 'svg',
		});
		chart.setOption(options);

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
		chart?.dispose();
		chart = null;
	});

	const tradingDarkTheme = {
		color: ['#00c087', '#ef4444', '#3b82f6', '#f59e0b', '#8b5cf6'],
		backgroundColor: 'transparent',
		textStyle: { color: '#94a3b8' },
	};
</script>

<div bind:this={container} {style}></div>
