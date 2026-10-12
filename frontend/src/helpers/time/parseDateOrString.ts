// Only allow supported date math from route query values before task-filter interpolation.
const DATE_MATH_OPS = /^(?:[+-]\d+(?:ms|[smhdwMy])|\/[smhdwMy])+$/
const DATE_MATH_BASE = /^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?$/

export function parseDateOrString(rawValue: unknown, fallback: unknown): unknown | string | Date {
	if (typeof rawValue !== 'string' || rawValue.length === 0 || rawValue.length > 128) return fallback
	const value = rawValue.trim()
	if (value === 'now') return value
	if (value.startsWith('now')) {
		const operations = value.startsWith('now||') ? value.slice(5) : value.slice(3)
		return DATE_MATH_OPS.test(operations) ? value : fallback
	}
	if (value.includes('||')) {
		const pieces = value.split('||')
		if (pieces.length !== 2) return fallback
		const [base, operations] = pieces
		return DATE_MATH_BASE.test(base) && Number.isFinite(Date.parse(base)) && DATE_MATH_OPS.test(operations)
			? value
			: fallback
	}
	const date = new Date(value)
	return Number.isFinite(date.getTime()) ? date : fallback
}
