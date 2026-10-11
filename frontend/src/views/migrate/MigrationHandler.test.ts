import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {flushPromises, mount, type VueWrapper} from '@vue/test-utils'
import {createPinia, setActivePinia} from 'pinia'
import {createI18n} from 'vue-i18n'
import {VueQueryPlugin} from '@tanstack/vue-query'

import MigrationHandler from './MigrationHandler.vue'
import {queryClient} from '@/client/queryClient'
import {error} from '@/message'
import en from '@/i18n/lang/en.json'
import {clearTodoistOAuthState, rememberTodoistOAuthState} from './todoistOAuthState'

const sdk = vi.hoisted(() => ({
	migrationWekanStatus: vi.fn(),
	migrationPlankaStatus: vi.fn(),
	migrationTodoistStatus: vi.fn(),
	migrationTodoistAuth: vi.fn(),
	migrationTodoistMigrate: vi.fn(),
}))

vi.mock('@/client/generated', async importOriginal => ({
	...await importOriginal<typeof import('@/client/generated')>(),
	...sdk,
	migrationCsvStatus: vi.fn(async () => {
		throw {status: 500, detail: 'Status unavailable'}
	}),
}))

vi.mock('@/message', async importOriginal => ({
	...await importOriginal<typeof import('@/message')>(),
	error: vi.fn(),
	success: vi.fn(),
}))

const i18n = createI18n({legacy: false, locale: 'en', messages: {en}})

let wrapper: VueWrapper | undefined

describe('MigrationHandler', () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		queryClient.clear()
		vi.mocked(error).mockClear()
		sdk.migrationTodoistStatus.mockReset()
		sdk.migrationTodoistAuth.mockReset()
		sdk.migrationTodoistMigrate.mockReset()
	})

	afterEach(() => {
		wrapper?.unmount()
		wrapper = undefined
		clearTodoistOAuthState(sessionStorage)
		window.history.replaceState({}, '', '/')
	})

	it('reports a failed status read inline only', async () => {
		wrapper = mount(MigrationHandler, {
			props: {service: 'csv'},
			global: {
				plugins: [i18n, [VueQueryPlugin, {queryClient}]],
				stubs: {XButton: true},
			},
		})
		await flushPromises()

		expect(wrapper.text().split('Status unavailable')).toHaveLength(2)
		expect(error).not.toHaveBeenCalled()
	})

	it.each([
		['wekan', sdk.migrationWekanStatus, 'x-button-stub'],
		['planka', sdk.migrationPlankaStatus, 'migration-credentials-form-stub'],
		['todoist', sdk.migrationTodoistStatus, 'x-button-stub'],
	])('keeps the %s action busy until the status read settles', async (service, statusOperation, action) => {
		let settleStatus: (status: object) => void = () => {}
		statusOperation.mockReturnValueOnce(new Promise(resolve => {
			settleStatus = data => resolve({data})
		}))
		sdk.migrationTodoistAuth.mockResolvedValue({data: {url: 'https://todoist.example/auth'}})
		wrapper = mount(MigrationHandler, {
			props: {service},
			global: {
				plugins: [i18n, [VueQueryPlugin, {queryClient}]],
				stubs: {
					XButton: true,
					MigrationCredentialsForm: true,
				},
			},
		})
		await flushPromises()

		expect(wrapper.find(action).attributes('loading')).toBe('true')
		settleStatus({})
		await flushPromises()
		expect(wrapper.find(action).attributes('loading')).toBe('false')
	})
	it('blocks a Todoist callback with an unexpected OAuth state before showing import consent', async () => {
		const nonce = '0123456789abcdef0123456789abcdef'
		expect(rememberTodoistOAuthState('https://todoist.com/oauth/authorize?state=' + nonce, sessionStorage)).toBe(true)
		window.history.replaceState({}, '', '/migrate/todoist?code=authorized-code&state=unexpected')
		sdk.migrationTodoistStatus.mockResolvedValue({data: {}})
		wrapper = mount(MigrationHandler, {
			props: {service: 'todoist', code: 'authorized-code'},
			global: {plugins: [i18n, [VueQueryPlugin, {queryClient}]], stubs: {XButton: true}},
		})
		await flushPromises()
		expect(wrapper.text()).toContain('authorization could not be verified')
		expect(window.location.search).not.toContain('code=')
		expect(window.location.search).not.toContain('state=')
		expect(wrapper.find('input[type="checkbox"]').exists()).toBe(false)
		expect(sdk.migrationTodoistMigrate).not.toHaveBeenCalled()
		expect(sdk.migrationTodoistAuth).not.toHaveBeenCalled()
	})

	it('allows review but never auto-imports after a matching OAuth callback', async () => {
		const nonce = '0123456789abcdef0123456789abcdef'
		expect(rememberTodoistOAuthState('https://todoist.com/oauth/authorize?state=' + nonce, sessionStorage)).toBe(true)
		window.history.replaceState({}, '', '/migrate/todoist?code=authorized-code&state=' + nonce)
		sdk.migrationTodoistStatus.mockResolvedValue({data: {}})
		wrapper = mount(MigrationHandler, {
			props: {service: 'todoist', code: 'authorized-code'},
			global: {plugins: [i18n, [VueQueryPlugin, {queryClient}]], stubs: {XButton: true}},
		})
		await flushPromises()
		expect(wrapper.text()).toContain('Todoist authorization received')
		expect(window.location.search).not.toContain('code=')
		expect(window.location.search).not.toContain('state=')
		expect(wrapper.find('input[type="checkbox"]').exists()).toBe(true)
		expect(wrapper.find('x-button-stub[disabled="true"]').exists()).toBe(true)
		expect(sdk.migrationTodoistMigrate).not.toHaveBeenCalled()

		sdk.migrationTodoistMigrate.mockResolvedValue({data: {}})
		await wrapper.find('input[type="checkbox"]').setValue(true)
		await flushPromises()
		await wrapper.find('x-button-stub').trigger('click')
		await flushPromises()
		expect(sdk.migrationTodoistMigrate).toHaveBeenCalledWith({
			body: {code: 'authorized-code', state: nonce},
		})
	})

})
