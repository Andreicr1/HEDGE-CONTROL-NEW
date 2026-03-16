<script lang="ts">
	import { page } from '$app/state';
	let { children } = $props();

	const tabs = [
		{ href: '/analytics/pnl', label: 'P&L' },
		{ href: '/analytics/mtm', label: 'MTM' },
		{ href: '/analytics/what-if', label: 'What-If' },
	];
</script>

<div class="p-6">
	<h1 class="text-lg font-semibold text-surface-200">Analytics</h1>

	<div class="mt-4 flex gap-4 border-b border-surface-800">
		{#each tabs as tab}
			<a
				href={tab.href}
				class="pb-2 text-sm {page.url.pathname.startsWith(tab.href) ? 'border-b-2 border-accent text-accent' : 'text-surface-500 hover:text-surface-300'}"
			>
				{tab.label}
			</a>
		{/each}
	</div>

	<div class="mt-4">
		{@render children()}
	</div>
</div>
