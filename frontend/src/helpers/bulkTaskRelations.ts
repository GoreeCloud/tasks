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
	created.forEach((task, index) => {
		const id = task?.id
		if (index < tasks.length && typeof id === 'number' && Number.isSafeInteger(id) && id > 0) {
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
