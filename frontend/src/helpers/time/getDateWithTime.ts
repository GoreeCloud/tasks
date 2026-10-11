import {calculateNearestHours} from '@/helpers/time/calculateNearestHours'
import {useAuthStore} from '@/stores/auth'

export function parseUserDefaultTime(defaultDueTime?: string): {hours: number, minutes: number} | null {
	if (!defaultDueTime) {
		return null
	}

	const match = /^(\d{2}):(\d{2})$/.exec(defaultDueTime)
	if (!match) {
		return null
	}

	const hours = Number(match[1])
	const minutes = Number(match[2])
	if (hours > 23 || minutes > 59) {
		return null
	}

	return {hours, minutes}
}

export function getDefaultTimeParts(date: Date): {hours: number, minutes: number} {
	const defaultDueTime = useAuthStore().settings.frontend_settings.default_due_time
	const parsedTime = parseUserDefaultTime(defaultDueTime)

	if (parsedTime !== null) {
		return parsedTime
	}

	return {
		hours: calculateNearestHours(date),
		minutes: 0,
	}
}

export function getDateWithTime(date: Date): Date {
	const newDate = new Date(date)
	const timeParts = getDefaultTimeParts(newDate)
	newDate.setHours(timeParts.hours, timeParts.minutes, 0, 0)
	return newDate
}

/**
 * Today quick capture must not create tasks that are already overdue.
 * Prefer the user's selected due time while it is still ahead today;
 * otherwise use the end of the current local day.
 */
export function getTodayQuickAddDueDate(now: Date): Date {
	const due = getDateWithTime(now)
	if (due.getTime() <= now.getTime()) {
		due.setHours(23, 59, 59, 999)
	}
	return due
}
