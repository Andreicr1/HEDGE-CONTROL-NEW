/**
 * WebSocket event types — discriminated union with runtime type guards.
 *
 * Protocol:
 *   Server → Client: { event, rfq_id, data, timestamp, seq }
 *   Client → Server: { action, ... }
 */

// ─── Base ──────────────────────────────────────────────────────────────────

interface BaseWsEvent {
	event: string;
	rfq_id: string;
	timestamp: string;
	seq: number;
}

// ─── Event Types ───────────────────────────────────────────────────────────

export interface QuoteReceivedEvent extends BaseWsEvent {
	event: 'quote_received';
	data: {
		quote_id: string;
		counterparty_id: string;
		fixed_price_value: number;
		fixed_price_unit: string;
		float_pricing_convention: string;
		received_at: string;
	};
}

export interface QuoteUpdatedEvent extends BaseWsEvent {
	event: 'quote_updated';
	data: {
		quote_id: string;
		counterparty_id: string;
		fixed_price_value: number;
		fixed_price_unit: string;
	};
}

export interface StatusChangedEvent extends BaseWsEvent {
	event: 'status_changed';
	data: {
		from_state: string;
		to_state: string;
		user_id?: string;
		created_contract_ids?: string[];
	};
}

export interface InvitationDeliveredEvent extends BaseWsEvent {
	event: 'invitation_delivered';
	data: {
		invitation_id: string;
		counterparty_id: string;
		recipient_phone: string;
	};
}

export interface InvitationFailedEvent extends BaseWsEvent {
	event: 'invitation_failed';
	data: {
		invitation_id: string;
		counterparty_id: string;
		recipient_phone: string;
		error_message?: string;
	};
}

export interface RfqClosedEvent extends BaseWsEvent {
	event: 'rfq_closed';
	data: {
		reason: string;
		user_id?: string;
	};
}

// ─── Union ─────────────────────────────────────────────────────────────────

export type WsEvent =
	| QuoteReceivedEvent
	| QuoteUpdatedEvent
	| StatusChangedEvent
	| InvitationDeliveredEvent
	| InvitationFailedEvent
	| RfqClosedEvent;

export type WsEventType = WsEvent['event'];

// ─── Type Map (for typed handlers) ─────────────────────────────────────────

export type WsEventMap = {
	quote_received: QuoteReceivedEvent;
	quote_updated: QuoteUpdatedEvent;
	status_changed: StatusChangedEvent;
	invitation_delivered: InvitationDeliveredEvent;
	invitation_failed: InvitationFailedEvent;
	rfq_closed: RfqClosedEvent;
};

// ─── Runtime Type Guard ────────────────────────────────────────────────────

const VALID_EVENTS = new Set<string>([
	'quote_received',
	'quote_updated',
	'status_changed',
	'invitation_delivered',
	'invitation_failed',
	'rfq_closed',
]);

export function isWsEvent(value: unknown): value is WsEvent {
	if (typeof value !== 'object' || value === null) return false;
	const obj = value as Record<string, unknown>;
	return (
		typeof obj.event === 'string' &&
		VALID_EVENTS.has(obj.event) &&
		typeof obj.rfq_id === 'string' &&
		typeof obj.timestamp === 'string' &&
		typeof obj.seq === 'number' &&
		typeof obj.data === 'object' &&
		obj.data !== null
	);
}

// ─── Control Messages (Server → Client) ────────────────────────────────────

export interface AuthAckMessage {
	type: 'auth_ack';
	user: string;
}

export interface SubscriptionAckMessage {
	type: 'subscription_ack';
	topic: string;
	id: string;
}

export interface SubscriptionErrorMessage {
	type: 'subscription_error';
	reason: string;
}

export interface WsErrorMessage {
	type: 'error';
	reason: string;
}

export type WsControlMessage =
	| AuthAckMessage
	| SubscriptionAckMessage
	| SubscriptionErrorMessage
	| WsErrorMessage;

export function isControlMessage(value: unknown): value is WsControlMessage {
	if (typeof value !== 'object' || value === null) return false;
	const obj = value as Record<string, unknown>;
	return typeof obj.type === 'string';
}
