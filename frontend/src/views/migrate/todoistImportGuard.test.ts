import {describe, expect, it} from 'vitest'

import {canStartTodoistImport} from './todoistImportGuard'

describe('Todoist import consent', () => {
	it('rejects a Todoist OAuth callback without user confirmation', () => {
		expect(canStartTodoistImport('todoist', 'code', false)).toBe(false)
	})
	it('rejects a confirmation without a valid authorization code', () => {
		expect(canStartTodoistImport('todoist', '', true)).toBe(false)
		expect(canStartTodoistImport('todoist', '   ', true)).toBe(false)
	})
	it('permits an explicitly confirmed authorized Todoist import', () => {
		expect(canStartTodoistImport('todoist', 'code', true)).toBe(true)
	})
	it('does not change the handling of unrelated import providers', () => {
		expect(canStartTodoistImport('ticktick', '', false)).toBe(true)
		expect(canStartTodoistImport('csv', '', false)).toBe(true)
	})
})
