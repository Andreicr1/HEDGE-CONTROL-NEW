const dateFormatter = new Intl.DateTimeFormat('pt-BR', {
	dateStyle: 'short',
	timeStyle: 'short',
});

const numberFormatter = new Intl.NumberFormat('pt-BR', {
	minimumFractionDigits: 2,
	maximumFractionDigits: 2,
});

export function formatDate(iso: string | null | undefined): string {
	if (!iso) return '—';
	return dateFormatter.format(new Date(iso));
}

export function formatNumber(value: number | null | undefined): string {
	if (value == null) return '—';
	return numberFormatter.format(value);
}

export function formatCurrency(value: number | null | undefined, unit?: string): string {
	if (value == null) return '—';
	const formatted = numberFormatter.format(value);
	return unit ? `${formatted} ${unit}` : formatted;
}

const STATE_LABELS: Record<string, string> = {
	CREATED: 'Criado',
	SENT: 'Enviado',
	QUOTED: 'Cotado',
	AWARDED: 'Premiado',
	CLOSED: 'Fechado',
};

const STATE_COLORS: Record<string, string> = {
	CREATED: 'bg-surface-600 text-surface-200',
	SENT: 'bg-accent/20 text-accent',
	QUOTED: 'bg-warning/20 text-warning',
	AWARDED: 'bg-success/20 text-success',
	CLOSED: 'bg-surface-700 text-surface-400',
};

export function stateLabel(state: string | undefined): string {
	if (!state) return '—';
	return STATE_LABELS[state] ?? state;
}

export function stateColor(state: string | undefined): string {
	if (!state) return 'bg-surface-700 text-surface-400';
	return STATE_COLORS[state] ?? 'bg-surface-700 text-surface-400';
}

const INTENT_LABELS: Record<string, string> = {
	COMMERCIAL_HEDGE: 'Hedge Comercial',
	GLOBAL_POSITION: 'Posição Global',
	SPREAD: 'Spread',
};

export function intentLabel(intent: string | undefined): string {
	if (!intent) return '—';
	return INTENT_LABELS[intent] ?? intent;
}

export function directionLabel(direction: string | undefined): string {
	if (!direction) return '—';
	return direction === 'BUY' ? 'Compra' : 'Venda';
}

export function directionColor(direction: string | undefined): string {
	if (!direction) return 'text-surface-400';
	return direction === 'BUY' ? 'text-success' : 'text-danger';
}
