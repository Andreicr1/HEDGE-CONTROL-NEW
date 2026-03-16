import { describe, it, expect } from 'vitest';
import { escapeHtml, sanitizeChartStrings } from './sanitize';

describe('escapeHtml', () => {
	it('escapes ampersand', () => {
		expect(escapeHtml('A & B')).toBe('A &amp; B');
	});

	it('escapes angle brackets', () => {
		expect(escapeHtml('<script>alert("xss")</script>')).toBe(
			'&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;',
		);
	});

	it('escapes quotes', () => {
		expect(escapeHtml(`"double" and 'single'`)).toBe(
			'&quot;double&quot; and &#39;single&#39;',
		);
	});

	it('returns empty string unchanged', () => {
		expect(escapeHtml('')).toBe('');
	});

	it('returns safe string unchanged', () => {
		expect(escapeHtml('Hello World 123')).toBe('Hello World 123');
	});

	it('handles all special chars together', () => {
		expect(escapeHtml(`<b>"Tom & Jerry's"</b>`)).toBe(
			'&lt;b&gt;&quot;Tom &amp; Jerry&#39;s&quot;&lt;/b&gt;',
		);
	});
});

describe('sanitizeChartStrings', () => {
	it('sanitizes strings in flat objects', () => {
		const input = { name: '<b>Counterparty</b>', value: 42 };
		const result = sanitizeChartStrings(input);
		expect(result.name).toBe('&lt;b&gt;Counterparty&lt;/b&gt;');
		expect(result.value).toBe(42);
	});

	it('sanitizes nested objects', () => {
		const input = {
			tooltip: {
				formatter: '{b}: {c}',
			},
			series: [{ name: '<img src=x onerror=alert(1)>', data: [1, 2, 3] }],
		};
		const result = sanitizeChartStrings(input);
		expect(result.series[0].name).toBe('&lt;img src=x onerror=alert(1)&gt;');
		expect(result.tooltip.formatter).toBe('{b}: {c}');
		expect(result.series[0].data).toEqual([1, 2, 3]);
	});

	it('preserves function values', () => {
		const fn = () => 'formatted';
		const input = { tooltip: { formatter: fn } };
		const result = sanitizeChartStrings(input);
		expect(result.tooltip.formatter).toBe(fn);
	});

	it('handles null and undefined', () => {
		expect(sanitizeChartStrings(null)).toBeNull();
		expect(sanitizeChartStrings(undefined)).toBeUndefined();
	});

	it('handles arrays of strings', () => {
		const input = ['<a>', 'safe', '<b>'];
		const result = sanitizeChartStrings(input);
		expect(result).toEqual(['&lt;a&gt;', 'safe', '&lt;b&gt;']);
	});

	it('handles plain string input', () => {
		expect(sanitizeChartStrings('<script>')).toBe('&lt;script&gt;');
	});

	it('handles boolean and number pass-through', () => {
		expect(sanitizeChartStrings(true)).toBe(true);
		expect(sanitizeChartStrings(42)).toBe(42);
	});
});
