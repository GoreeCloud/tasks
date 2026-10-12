import {describe, expect, it} from 'vitest'

import {runWrites, runWritesSettled} from './runWrites'

describe('runWrites', () => {
	function deferredWrite() {
		const inFlight: string[] = []
		let maxConcurrent = 0
		const completed: string[] = []
		const write = async (item: string) => {
			inFlight.push(item)
			maxConcurrent = Math.max(maxConcurrent, inFlight.length)
			await Promise.resolve()
			inFlight.splice(inFlight.indexOf(item), 1)
			completed.push(item)
		}
		return {write, completed, getMaxConcurrent: () => maxConcurrent}
	}

	it('runs all writes in parallel when concurrent', async () => {
		const {write, completed, getMaxConcurrent} = deferredWrite()
		await runWrites(['a', 'b', 'c'], write, true)
		expect(completed).toHaveLength(3)
		expect(getMaxConcurrent()).toBeGreaterThan(1)
	})

	it('runs writes one at a time when not concurrent', async () => {
		const {write, completed, getMaxConcurrent} = deferredWrite()
		await runWrites(['a', 'b', 'c'], write, false)
		expect(completed).toEqual(['a', 'b', 'c'])
		expect(getMaxConcurrent()).toBe(1)
	})

	it('does nothing for an empty list', async () => {
		const {write, completed} = deferredWrite()
		await runWrites([], write, false)
		expect(completed).toHaveLength(0)
	})
})

describe('runWritesSettled', () => {
	it('waits for successful writes that outlast a concurrent rejection', async () => {
		let release!: () => void
		const slow = new Promise<void>(resolve => { release = resolve })
		const pending = runWritesSettled([1, 2], async id => {
			if (id === 1) return slow
			throw new Error('failed')
		}, true)
		let settled = false
		void pending.then(() => { settled = true })
		await Promise.resolve()
		expect(settled).toBe(false)
		release()
		await expect(pending).resolves.toEqual({succeeded: 1, failed: 1})
	})

	it('continues serial attempts after a rejected write', async () => {
		const attempted: number[] = []
		const result = await runWritesSettled([1, 2, 3], async id => {
			attempted.push(id)
			if (id === 2) throw new Error('partial failure')
		}, false)
		expect(attempted).toEqual([1, 2, 3])
		expect(result).toEqual({succeeded: 2, failed: 1})
	})

	it('handles an empty batch without calling the writer', async () => {
		let attempts = 0
		expect(await runWritesSettled([], async () => { attempts++ }, true))
			.toEqual({succeeded: 0, failed: 0})
		expect(attempts).toBe(0)
	})
})
