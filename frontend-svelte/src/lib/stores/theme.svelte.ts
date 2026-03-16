class ThemeStore {
	#dark = $state(true);

	readonly isDark = $derived(this.#dark);

	toggle() {
		this.#dark = !this.#dark;
		document.documentElement.classList.toggle('dark', this.#dark);
	}
}

export const themeStore = new ThemeStore();
