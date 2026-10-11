import {describe, expect, it} from 'vitest'
import {indexCreatableTasks, resolveBulkTaskRelations} from './bulkTaskRelations'
import type {TaskWithParent} from '@/helpers/parseSubtasksViaIndention'

function parsed(title: string, parentIndex: number | null = null): TaskWithParent {
	return {title, parent: parentIndex === null ? null : 'same name', parentIndex, project: null}
}

describe('bulk task relations', () => {
	it('keeps two identically named parents and children separate', () => {
		const tasks = indexCreatableTasks([parsed('same name'), parsed('child', 0), parsed('same name'), parsed('child', 2)])
		expect(resolveBulkTaskRelations(tasks, [{id: 11}, {id: 12}, {id: 21}, {id: 22}]))
			.toEqual([{childId: 12, parentId: 11}, {childId: 22, parentId: 21}])
	})
	it('preserves source positions when an empty task is filtered', () => {
		const tasks = indexCreatableTasks([parsed('parent'), parsed(''), parsed('child', 0)])
		expect(tasks.map(t => t.sourceIndex)).toEqual([0, 2])
		expect(resolveBulkTaskRelations(tasks, [{id: 3}, {id: 4}])).toEqual([{childId: 4, parentId: 3}])
	})
	it('never links children to a missing parent or failed task', () => {
		const tasks = indexCreatableTasks([parsed('parent'), parsed('child', 0)])
		expect(resolveBulkTaskRelations(tasks, [null, {id: 5}])).toEqual([])
		expect(resolveBulkTaskRelations(tasks, [{id: 1}, null])).toEqual([])
		expect(resolveBulkTaskRelations(tasks, [{id: 1}, {id: 1}])).toEqual([])
	})
	it('rejects invalid destination identities', () => {
		const tasks = indexCreatableTasks([parsed('parent'), parsed('child', 0)])
		expect(resolveBulkTaskRelations(tasks, [{id: 0}, {id: 2}])).toEqual([])
		expect(resolveBulkTaskRelations(tasks, [{id: Number.NaN}, {id: 2}])).toEqual([])
	})
})
