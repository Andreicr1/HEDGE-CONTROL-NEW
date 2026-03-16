const HTML_ESCAPE_MAP: Record<string, string> = {
	'&': '&amp;',
	'<': '&lt;',
	'>': '&gt;',
	'"': '&quot;',
	"'": '&#39;',
};

const HTML_ESCAPE_RE = /[&<>"']/g;

/**
 * Escape HTML special characters to prevent XSS in contexts that render HTML
 * (e.g. ECharts tooltip formatters which use innerHTML by default).
 */
export function escapeHtml(str: string): string {
	return str.replace(HTML_ESCAPE_RE, (ch) => HTML_ESCAPE_MAP[ch]);
}

/**
 * Sanitize an ECharts option object by escaping all string values recursively.
 * Use on options that include user-generated data (counterparty names, messages).
 * Skips keys that are known safe (formatter functions, rich text style keys).
 */
export function sanitizeChartStrings<T>(obj: T): T {
	if (typeof obj === 'string') return escapeHtml(obj) as T;
	if (obj == null || typeof obj !== 'object') return obj;
	if (Array.isArray(obj)) return obj.map(sanitizeChartStrings) as T;

	const result: Record<string, unknown> = {};
	for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
		// Skip function values (formatters, callbacks) and rich text style objects
		if (typeof value === 'function') {
			result[key] = value;
		} else {
			result[key] = sanitizeChartStrings(value);
		}
	}
	return result as T;
}
