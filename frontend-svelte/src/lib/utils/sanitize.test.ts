import { describe, it, expect } from 'vitest';
import { escapeHtml } from './sanitize';

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
