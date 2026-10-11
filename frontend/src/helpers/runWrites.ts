// runWrites applies a write to each item. SQLite deadlocks on concurrent writes
// (read-then-write upgrade conflict), so callers pass concurrent=false to serialize.
export async function runWrites<T>(
	items: readonly T[],
	write: (item: T) => Promise<unknown>,
	concurrent: boolean,
): Promise<void> {
	if (concurrent) {
		await Promise.all(items.map(item => write(item)))
		return
	}
	for (const item of items) {
		await write(item)
	}
}

/**
 * Wait for every independent write to settle before reporting partial failures.
 * Serial mode continues after a failed write to preserve independent details.
 */
export async function runWritesSettled<T>(
	items: readonly T[],
	write: (item: T) => Promise<unknown>,
	concurrent: boolean,
): Promise<{succeeded: number, failed: number}> {
	let succeeded = 0
	let failed = 0
	const attempt = async (item: T) => {
		try {
			await write(item)
			succeeded++
		} catch {
			failed++
		}
	}
	if (concurrent) {
		await Promise.all(items.map(attempt))
	} else {
		for (const item of items) await attempt(item)
	}
	return {succeeded, failed}
}
