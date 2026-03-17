import { describe, it, expect } from 'vitest';
import { isWsEvent, isControlMessage } from './ws-events';

describe('isWsEvent', () => {
	it('validates a correct quote_received event', () => {
		expect(isWsEvent({
			event: 'quote_received',
			rfq_id: 'rfq-1',
			data: { quote_id: 'q1' },
			timestamp: '2026-01-01T00:00:00Z',
			seq: 1,
		})).toBe(true);
	});

	it('validates all known event types', () => {
		const events = [
			'quote_received', 'quote_updated', 'status_changed',
			'invitation_delivered', 'invitation_failed', 'rfq_closed',
		];
		for (const event of events) {
			expect(isWsEvent({
				event, rfq_id: 'r', data: {}, timestamp: 't', seq: 0,
			})).toBe(true);
		}
	});

	it('rejects unknown event type', () => {
		expect(isWsEvent({
			event: 'unknown_event',
			rfq_id: 'r', data: {}, timestamp: 't', seq: 0,
		})).toBe(false);
	});

	it('rejects missing fields', () => {
		expect(isWsEvent({ event: 'quote_received' })).toBe(false);
		expect(isWsEvent({ event: 'quote_received', rfq_id: 'r' })).toBe(false);
	});

	it('rejects non-objects', () => {
		expect(isWsEvent(null)).toBe(false);
		expect(isWsEvent(undefined)).toBe(false);
		expect(isWsEvent('string')).toBe(false);
		expect(isWsEvent(42)).toBe(false);
	});

	it('rejects when data is null', () => {
		expect(isWsEvent({
			event: 'quote_received', rfq_id: 'r', data: null, timestamp: 't', seq: 0,
		})).toBe(false);
	});

	it('rejects when seq is not a number', () => {
		expect(isWsEvent({
			event: 'quote_received', rfq_id: 'r', data: {}, timestamp: 't', seq: '1',
		})).toBe(false);
	});
});

describe('isControlMessage', () => {
	it('validates auth_ack', () => {
		expect(isControlMessage({ type: 'auth_ack', user: 'test' })).toBe(true);
	});

	it('validates subscription_ack', () => {
		expect(isControlMessage({ type: 'subscription_ack', topic: 'rfq', id: '1' })).toBe(true);
	});

	it('validates subscription_error', () => {
		expect(isControlMessage({ type: 'subscription_error', reason: 'bad' })).toBe(true);
	});

	it('rejects objects without type', () => {
		expect(isControlMessage({ event: 'quote_received' })).toBe(false);
	});

	it('validates error message', () => {
		expect(isControlMessage({ type: 'error', reason: 'fail' })).toBe(true);
	});

	it('accepts all known control types', () => {
		const types = ['auth_ack', 'subscription_ack', 'subscription_error', 'error'];
		for (const type of types) {
			expect(isControlMessage({ type })).toBe(true);
		}
	});

	it('rejects unknown type values', () => {
		expect(isControlMessage({ type: 'quote_received' })).toBe(false);
		expect(isControlMessage({ type: 'unknown_type' })).toBe(false);
		expect(isControlMessage({ type: 'status_changed' })).toBe(false);
	});

	it('rejects non-objects', () => {
		expect(isControlMessage(null)).toBe(false);
		expect(isControlMessage('string')).toBe(false);
	});
});
