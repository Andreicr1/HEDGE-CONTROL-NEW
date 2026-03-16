import { connect, type ECharts } from 'echarts/core';

/**
 * Coordinates crosshair sync between multiple EChart instances.
 *
 * Usage:
 *   const group = new LinkedChartGroup(2);
 *   <EChart options={opts1} {group} groupId="original" />
 *   <EChart options={opts2} {group} groupId="scenario" />
 *
 * When all expected charts register, echarts.connect() links them
 * so tooltip/crosshair events propagate across all charts in the group.
 */
export class LinkedChartGroup {
	#instances = $state(new Map<string, ECharts>());
	#expectedCount: number;
	#connected = $state(false);

	constructor(expectedCount: number) {
		this.#expectedCount = expectedCount;
	}

	get connected(): boolean {
		return this.#connected;
	}

	get size(): number {
		return this.#instances.size;
	}

	register(id: string, instance: ECharts): void {
		this.#instances.set(id, instance);
		if (this.#instances.size === this.#expectedCount) {
			connect(Array.from(this.#instances.values()));
			this.#connected = true;
		}
	}

	unregister(id: string): void {
		this.#instances.delete(id);
		this.#connected = false;
	}
}
