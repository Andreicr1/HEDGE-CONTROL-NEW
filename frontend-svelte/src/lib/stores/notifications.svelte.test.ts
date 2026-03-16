import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('NotificationStore', () => {
	let notifications: typeof import('./notifications.svelte').notifications;

	beforeEach(async () => {
		vi.useFakeTimers();
		vi.resetModules();
		const mod = await import('./notifications.svelte');
		notifications = mod.notifications;
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('adds a notification and returns id', () => {
		const id = notifications.info('Hello');
		expect(notifications.items).toHaveLength(1);
		expect(notifications.items[0]).toMatchObject({
			id,
			type: 'info',
			message: 'Hello',
		});
	});

	it('removes notification by id', () => {
		const id = notifications.info('Hello', 0);
		expect(notifications.items).toHaveLength(1);
		notifications.remove(id);
		expect(notifications.items).toHaveLength(0);
	});

	it('auto-removes after timeout', () => {
		notifications.info('Temp', 3000);
		expect(notifications.items).toHaveLength(1);
		vi.advanceTimersByTime(3001);
		expect(notifications.items).toHaveLength(0);
	});

	it('does not auto-remove when timeout is 0', () => {
		notifications.error('Persistent');
		expect(notifications.items).toHaveLength(1);
		vi.advanceTimersByTime(60000);
		expect(notifications.items).toHaveLength(1);
	});

	it('convenience methods set correct type', () => {
		notifications.info('i');
		notifications.success('s');
		notifications.warning('w');
		notifications.error('e');

		expect(notifications.items.map((n) => n.type)).toEqual([
			'info', 'success', 'warning', 'error',
		]);
	});

	it('warning has default 8s timeout', () => {
		notifications.warning('w');
		vi.advanceTimersByTime(7999);
		expect(notifications.items).toHaveLength(1);
		vi.advanceTimersByTime(2);
		expect(notifications.items).toHaveLength(0);
	});

	it('clear removes all notifications', () => {
		notifications.info('a', 0);
		notifications.info('b', 0);
		notifications.info('c', 0);
		expect(notifications.items).toHaveLength(3);
		notifications.clear();
		expect(notifications.items).toHaveLength(0);
	});
});
