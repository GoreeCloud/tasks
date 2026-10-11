/**
 * Build the backend label predicate from untrusted URL/route values.
 * A malformed label ID must never turn a restricted view into an unfiltered one.
 * Label IDs are positive safe integers; zero is intentionally a no-match sentinel.
 */
export function buildLabelFilter(rawIds: readonly string[]): string {
	const ids: number[] = []
	for (const raw of rawIds) {
		if (!/^\d+$/.test(raw)) return 'labels in 0'
		const id = Number(raw)
		if (!Number.isSafeInteger(id) || id < 1) return 'labels in 0'
		ids.push(id)
	}
	return ids.length ? `labels in ${[...new Set(ids)].join(', ')}` : 'labels in 0'
}
