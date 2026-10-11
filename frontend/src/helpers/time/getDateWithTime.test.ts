import {queryClient} from '@/client/queryClient'
import {accountKeys} from '@/client/queries/account'
import {beforeEach, describe, expect, it, vi} from 'vitest'
import {setActivePinia, createPinia} from 'pinia'

import {getDateWithTime, getDefaultTimeParts, getTodayQuickAddDueDate, parseUserDefaultTime} from './getDateWithTime'
import {useAuthStore} from '@/stores/auth'

function setDefaultDueTime(default_due_time?: string) {
	const authStore = useAuthStore()
	queryClient.setQueryData(accountKeys.user(0), {settings: {
		...authStore.settings,
		frontend_settings: {
			...authStore.settings.frontend_settings,
			default_due_time,
		},
	}})
}

describe('getDateWithTime', () => {
	beforeEach(() => {
		queryClient.clear()
		setActivePinia(createPinia())
		useAuthStore()
	})

	it('uses the user default due time when configured', () => {
		setDefaultDueTime('14:30')

		const date = new Date(2026, 7, 4, 9, 15)
		const result = getDateWithTime(date)

		expect(result.getFullYear()).toBe(2026)
		expect(result.getMonth()).toBe(7)
		expect(result.getDate()).toBe(4)
		expect(result.getHours()).toBe(14)
		expect(result.getMinutes()).toBe(30)
	})

	it('falls back to the current nearest-hours default when the setting is empty', () => {
		setDefaultDueTime(undefined)

		const date = new Date(2026, 7, 4, 10, 15)
		const result = getDateWithTime(date)

		expect(result.getHours()).toBe(12)
		expect(result.getMinutes()).toBe(0)
	})

	it('falls back when the stored time cannot be parsed', () => {
		setDefaultDueTime('25:99')

		const date = new Date(2026, 7, 4, 10, 15)
		const result = getDateWithTime(date)

		expect(result.getHours()).toBe(12)
		expect(result.getMinutes()).toBe(0)
	})
})

describe('parseUserDefaultTime', () => {
	it('returns fallback parts when no user value is configured', () => {
		setDefaultDueTime(undefined)

		expect(getDefaultTimeParts(new Date(2026, 7, 4, 10, 15))).toStrictEqual({hours: 12, minutes: 0})
	})

	it('parses valid times', () => {
		expect(parseUserDefaultTime('09:45')).toStrictEqual({hours: 9, minutes: 45})
	})

	it('rejects invalid values', () => {
		expect(parseUserDefaultTime(undefined)).toBeNull()
		expect(parseUserDefaultTime('9:45')).toBeNull()
		expect(parseUserDefaultTime('24:00')).toBeNull()
		expect(parseUserDefaultTime('12:60')).toBeNull()
	})
})

describe('getTodayQuickAddDueDate', () => {
	beforeEach(() => {
		queryClient.clear()
		setActivePinia(createPinia())
		useAuthStore()
	})

	it('preserves a preferred due time when it is still ahead today', () => {
		setDefaultDueTime('18:45')
		const now = new Date(2026, 9, 10, 10, 15)
		const due = getTodayQuickAddDueDate(now)
		expect([due.getDate(), due.getHours(), due.getMinutes()]).toEqual([10, 18, 45])
		expect(due.getTime()).toBeGreaterThan(now.getTime())
	})

	it('uses the end of the same day when the preferred time has passed', () => {
		setDefaultDueTime('09:00')
		const now = new Date(2026, 9, 10, 17, 0)
		const due = getTodayQuickAddDueDate(now)
		expect([due.getDate(), due.getHours(), due.getMinutes(), due.getSeconds()]).toEqual([10, 23, 59, 59])
		expect(due.getTime()).toBeGreaterThan(now.getTime())
	})

	it('keeps a late-night capture today when no default time is configured', () => {
		setDefaultDueTime(undefined)
		const now = new Date(2026, 9, 10, 22, 30)
		const due = getTodayQuickAddDueDate(now)
		expect([due.getDate(), due.getHours(), due.getMinutes()]).toEqual([10, 23, 59])
		expect(due.getTime()).toBeGreaterThan(now.getTime())
	})

	it('does not change the supplied date', () => {
		setDefaultDueTime('08:00')
		const now = new Date(2026, 9, 10, 14, 15)
		getTodayQuickAddDueDate(now)
		expect([now.getHours(), now.getMinutes()]).toEqual([14, 15])
	})
})
