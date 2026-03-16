<script lang="ts">
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';

	let token = $state('');
	let loading = $state(false);

	$effect(() => {
		if (authStore.isAuthenticated) {
			goto('/');
		}
	});

	function handleLogin(e: SubmitEvent) {
		e.preventDefault();
		loading = true;
		try {
			authStore.login(token.trim());
			goto('/');
		} catch {
			notifications.error('Token inválido. Verifique e tente novamente.');
		} finally {
			loading = false;
		}
	}
</script>

<div class="flex h-screen items-center justify-center bg-surface-950">
	<div class="w-full max-w-md rounded-lg border border-surface-800 bg-surface-900 p-8">
		<h1 class="text-xl font-semibold text-surface-200">Hedge Control</h1>
		<p class="mt-1 text-sm text-surface-500">Cole seu token JWT para acessar a plataforma.</p>

		<form onsubmit={handleLogin} class="mt-6 space-y-4">
			<div>
				<label for="token" class="block text-sm font-medium text-surface-400">JWT Token</label>
				<textarea
					id="token"
					bind:value={token}
					rows={4}
					class="mt-1 w-full rounded-md border border-surface-700 bg-surface-800 px-3 py-2 text-sm text-surface-200 placeholder-surface-600 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent font-mono"
					placeholder="eyJhbGciOiJSUzI1NiIs..."
					required
				></textarea>
			</div>

			<button
				type="submit"
				disabled={loading || !token.trim()}
				class="w-full rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed"
			>
				{loading ? 'Validando...' : 'Entrar'}
			</button>
		</form>

		<p class="mt-4 text-xs text-surface-600 text-center">
			Ambiente de desenvolvimento — autenticação via token manual.
		</p>
	</div>
</div>
