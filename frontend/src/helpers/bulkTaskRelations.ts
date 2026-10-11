import type {TaskWithParent} from '@/helpers/parseSubtasksViaIndention'

export type IndexedTask = TaskWithParent & {sourceIndex: number}

export function indexCreatableTasks(tasks: readonly TaskWithParent[]): IndexedTask[] {
	return tasks.flatMap((task, sourceIndex) => task.title !== '' ? [{...task, sourceIndex}] : [])
}

export interface BulkTaskRelation {
	childId: number
	parentId: number
}

export function resolveBulkTaskRelations<T extends {id?: number | null}>(
	tasks: readonly IndexedTask[],
	created: readonly (T | null | undefined)[],
): BulkTaskRelation[] {
	const sourceIdByIndex = new Map<number, number>()
	const seenIds = new Set<number>()
	const ambiguousIds = new Set<number>()
	for (const task of created) {
		const id = task?.id
		if (typeof id !== 'number' || !Number.isSafeInteger(id) || id <= 0) continue
		if (seenIds.has(id)) ambiguousIds.add(id)
		seenIds.add(id)
	}
	created.forEach((task, index) => {
		const id = task?.id
		if (index < tasks.length && typeof id === 'number' && Number.isSafeInteger(id) && id > 0 && !ambiguousIds.has(id)) {
			sourceIdByIndex.set(tasks[index].sourceIndex, id)
		}
	})

	return tasks.flatMap(({sourceIndex, parentIndex}) => {
		if (parentIndex === null || parentIndex >= sourceIndex) return []
		const childId = sourceIdByIndex.get(sourceIndex)
		const parentId = sourceIdByIndex.get(parentIndex)
		return childId && parentId && childId !== parentId ? [{childId, parentId}] : []
	})
}
