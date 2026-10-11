import {describe, expect, it} from 'vitest'
import {buildLabelFilter} from './buildLabelFilter'

describe('buildLabelFilter', () => {
	it('deduplicates and normalizes positive numeric IDs', () => {
		expect(buildLabelFilter(['1', '002', '1'])).toBe('labels in 1, 2')
	})
	it('fails closed on filter operators and extra terms', () => {
		expect(buildLabelFilter(['1) || done = true', '2'])).toBe('labels in 0')
	})
	it('rejects invalid, unsafe, and zero IDs', () => {
		for (const raw of ['9007199254740992', '1.5', '', '0', '-1', 'NaN', '1e3']) {
			expect(buildLabelFilter(['1', raw])).toBe('labels in 0')
		}
	})
	it('does not return an unrestricted predicate for an empty selection', () => {
		expect(buildLabelFilter([])).toBe('labels in 0')
	})
})
