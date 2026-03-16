<script lang="ts">
	import { authStore } from '$lib/stores/auth.svelte';
	import { wsStore } from '$lib/stores/ws.svelte';

	let wsLabel = $derived(
		wsStore.status === 'authenticated' ? 'WS Conectado'
		: wsStore.status === 'connecting' ? 'Conectando...'
		: wsStore.status === 'error' ? 'WS Erro'
		: 'WS Desconectado'
	);

	let wsColor = $derived(
		wsStore.status === 'authenticated' ? 'text-success'
		: wsStore.status === 'connecting' ? 'text-warning'
		: wsStore.status === 'error' ? 'text-danger'
		: 'text-surface-500'
	);

	let env = $derived(
		(import.meta.env.MODE === 'production') ? 'PROD' : 'DEV'
	);
</script>

<div class="flex items-center gap-4 border-t border-surface-800 bg-surface-900 px-4 py-1 text-xs">
	<span class={wsColor}>{wsLabel}</span>
	<span class="text-surface-600">|</span>
	<span class="text-surface-500">{authStore.userName}</span>
	<span class="text-surface-600">|</span>
	<span class="text-surface-500">{authStore.userRoles.join(', ')}</span>
	<span class="ml-auto rounded bg-surface-800 px-1.5 py-0.5 text-surface-500">{env}</span>
</div>
