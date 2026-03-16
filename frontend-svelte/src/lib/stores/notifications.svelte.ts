export type NotificationType = 'info' | 'success' | 'warning' | 'error';

export interface Notification {
	id: string;
	type: NotificationType;
	message: string;
	timeout?: number;
}

let nextId = 0;

class NotificationStore {
	items = $state<Notification[]>([]);

	add(type: NotificationType, message: string, timeout = 5000) {
		const id = String(++nextId);
		const notification: Notification = { id, type, message, timeout };
		this.items = [...this.items, notification];

		if (timeout > 0) {
			setTimeout(() => this.remove(id), timeout);
		}

		return id;
	}

	remove(id: string) {
		this.items = this.items.filter((n) => n.id !== id);
	}

	info(message: string, timeout?: number) {
		return this.add('info', message, timeout);
	}

	success(message: string, timeout?: number) {
		return this.add('success', message, timeout);
	}

	warning(message: string, timeout = 8000) {
		return this.add('warning', message, timeout);
	}

	error(message: string, timeout = 0) {
		return this.add('error', message, timeout);
	}

	clear() {
		this.items = [];
	}
}

export const notifications = new NotificationStore();
