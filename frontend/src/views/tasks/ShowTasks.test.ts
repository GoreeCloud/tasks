import {createPinia} from 'pinia'
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {QueryClient, VueQueryPlugin} from '@tanstack/vue-query'
import {reactive} from 'vue'
import {enableAutoUnmount, flushPromises, shallowMount} from '@vue/test-utils'
import {createMemoryHistory, createRouter} from 'vue-router'

const sdk = vi.hoisted(() => ({
	tasksList: vi.fn(async (_request: {query: Record<string, unknown>}) => ({
		data: {items: [], total_pages: 1},
	})),
}))

vi.mock('@/client/generated', () => sdk)

const auth = reactive({
	authenticated: true,
	settings: {frontend_settings: {filter_id_used_on_overview: undefined, sidebar_width: 250}},
})

vi.mock('@/stores/auth', () => ({useAuthStore: () => auth}))
vi.mock('@/composables/useProjects', () => ({useProjects: () => ({projects: {}})}))
vi.mock('@/composables/useLabels', () => ({useLabels: () => ({getLabelById: vi.fn()})}))
vi.mock('@/helpers/setTitle', () => ({setTitle: vi.fn()}))
vi.mock('vue-i18n', async importOriginal => ({
	...await importOriginal<typeof import('vue-i18n')>(),
	useI18n: () => ({t: (key: string) => key}),
}))

import ShowTasks from './ShowTasks.vue'

enableAutoUnmount(afterEach)

async function mountUpcoming() {
	const router = createRouter({
		history: createMemoryHistory(),
		routes: [{path: '/', component: {render: () => null}}],
	})
	await router.push('/')
	return shallowMount(ShowTasks, {
		props: {
			dateFrom: 'now/d',
			dateTo: 'now/d+1d',
		},
		global: {
			plugins: [
				createPinia(),
				router,
				[VueQueryPlugin, {queryClient: new QueryClient({defaultOptions: {queries: {staleTime: 0, retry: false}}})}],
			],
			mocks: {$t: (key: string) => key},
			stubs: {
				Card: true,
				XButton: true,
				'i18n-t': true,
				DatepickerWithRange: {render: () => null},
			},
			directives: {tooltip: () => {}, cy: () => {}},
		},
	})
}

function lastQuery(): Record<string, unknown> {
	return sdk.tasksList.mock.lastCall![0].query
}

describe('Upcoming filters', () => {
	beforeEach(() => {
		sdk.tasksList.mockReset()
		sdk.tasksList.mockImplementation(async () => ({data: {items: [], total_pages: 1}}))
	})

	it('reloads tasks when overdue tasks are enabled and disabled', async () => {
		const wrapper = await mountUpcoming()
		await flushPromises()
		expect(sdk.tasksList).toHaveBeenCalledTimes(1)
		expect(lastQuery().filter).toBe("done = false && due_date < 'now/d+1d' && due_date > 'now/d'")

		await wrapper.setProps({showOverdue: true})
		await flushPromises()
		expect(sdk.tasksList).toHaveBeenCalledTimes(2)
		expect(lastQuery().filter).toBe("done = false && due_date < 'now/d+1d'")

		await wrapper.setProps({showOverdue: false})
		await flushPromises()
		expect(sdk.tasksList).toHaveBeenCalledTimes(3)
		expect(lastQuery().filter).toBe("done = false && due_date < 'now/d+1d' && due_date > 'now/d'")
	})

	it('reloads tasks when undated tasks are enabled and disabled', async () => {
		const wrapper = await mountUpcoming()
		await flushPromises()

		await wrapper.setProps({showNulls: true})
		await flushPromises()
		expect(sdk.tasksList).toHaveBeenCalledTimes(2)
		expect(lastQuery().filter_include_nulls).toBe(true)

		await wrapper.setProps({showNulls: false})
		await flushPromises()
		expect(sdk.tasksList).toHaveBeenCalledTimes(3)
		expect(lastQuery().filter_include_nulls).toBe(false)
	})

	it('changes sort order without changing the active date filter', async () => {
		const wrapper = await mountUpcoming()
		await flushPromises()
		await wrapper.setProps({sort: 'priority'})
		await flushPromises()
		expect(lastQuery().sort_by).toEqual(['priority', 'due_date', 'id'])
		expect(lastQuery().order_by).toEqual(['desc', 'asc', 'desc'])
		expect(lastQuery().filter).toBe("done = false && due_date < 'now/d+1d' && due_date > 'now/d'")

		await wrapper.setProps({sort: 'newest'})
		await flushPromises()
		expect(lastQuery().sort_by).toEqual(['created', 'id'])
		expect(lastQuery().order_by).toEqual(['desc', 'desc'])
	})

	it('uses the default sort order for unexpected deep-link values', async () => {
		const wrapper = await mountUpcoming()
		await flushPromises()
		await wrapper.setProps({sort: 'unknown'})
		await flushPromises()
		expect(lastQuery().sort_by).toEqual(['due_date', 'id'])
		expect(lastQuery().order_by).toEqual(['asc', 'desc'])
	})

	it('pages through all matching tasks and resets pagination on filter changes', async () => {
		sdk.tasksList.mockImplementation(async () => ({data: {items: [], total_pages: 3}}))
		const wrapper = await mountUpcoming()
		await flushPromises()
		const pages = wrapper.findComponent({name: 'PaginationEmit'})
		expect(pages.exists()).toBe(true)
		pages.vm.$emit('pageChanged', 2)
		await flushPromises()
		expect(lastQuery().page).toBe(2)
		await wrapper.setProps({showOverdue: true})
		await flushPromises()
		expect(lastQuery().page).toBe(1)
	})

	it('does not reload tasks when sidebar settings change', async () => {
		await mountUpcoming()
		await flushPromises()

		auth.settings = {frontend_settings: {filter_id_used_on_overview: undefined, sidebar_width: 300}}
		await flushPromises()
		expect(sdk.tasksList).toHaveBeenCalledTimes(1)
	})
})
