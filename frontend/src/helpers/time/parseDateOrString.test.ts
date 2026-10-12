import {describe, expect, it} from 'vitest'
import {parseDateOrString} from './parseDateOrString'

describe('untrusted task-date route values', () => {
	const fallback = new Date('2026-10-10T00:00:00.000Z')

	it.each([
		'now', 'now/d', 'now/d+1d', 'now/w+1w', 'now/M+1M', 'now+7d', 'now||-1w',
		'2026-10-10||+1d', '2026-10-10T10:30:00Z||/d',
	])('retains supported date math: %s', value => {
		expect(parseDateOrString(value, fallback)).toBe(value)
	})

	it('parses absolute timestamps into Dates', () => {
		expect(parseDateOrString('2026-10-11T10:00:00.000Z', fallback))
			.toEqual(new Date('2026-10-11T10:00:00.000Z'))
	})

	it.each([
		"now/d' || done = true", 'hello now', 'now /d', 'now||', '2026-10-10||',
		'2026-13-45||/d', '2026-10-10||+1d && done = true', 'x'.repeat(129),
		'', 'bad-date', 'now/d||other', 'now/d+1d;foo',
	])('uses fallback for an invalid or injected date: %s', value => {
		expect(parseDateOrString(value, fallback)).toBe(fallback)
	})

	it('rejects repeated or non-string query input', () => {
		for (const value of [undefined, null, ['now/d', 'now/d+1d'], {date: 'now/d'}, 1234]) {
			expect(parseDateOrString(value, fallback)).toBe(fallback)
		}
	})
})
