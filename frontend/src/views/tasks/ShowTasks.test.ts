import {createPinia} from 'pinia'
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {QueryClient, VueQueryPlugin} from '@tanstack/vue-query'
import {reactive} from 'vue'
import {enableAutoUnmount, flushPromises, mount, shallowMount} from '@vue/test-utils'
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
import XButton from '@/components/input/Button.vue'

enableAutoUnmount(afterEach)

async function mountUpcoming(realButtons = false) {
	const router = createRouter({
		history: createMemoryHistory(),
		routes: [{path: '/', component: {render: () => null}}],
	})
	await router.push('/')
	return (realButtons ? mount : shallowMount)(ShowTasks, {
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
				Message: {template: '<div><slot /></div>'},
				XButton: realButtons ? XButton : true,
				FancyCheckbox: true,
				SingleTaskInProject: true,
				LlamaCool: true,
				PaginationEmit: true,
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
		auth.authenticated = true
		sdk.tasksList.mockReset()
		sdk.tasksList.mockImplementation(async () => ({data: {items: [], total_pages: 1}}))
	})

	it('loads tasks when a previously unauthenticated session becomes ready', async () => {
		auth.authenticated = false
		await mountUpcoming()
		await flushPromises()
		expect(sdk.tasksList).not.toHaveBeenCalled()
		auth.authenticated = true
		await flushPromises()
		expect(sdk.tasksList).toHaveBeenCalledTimes(1)
	})
	it('disables manual refresh before a session is authenticated', async () => {
		auth.authenticated = false
		const wrapper = await mountUpcoming()
		await flushPromises()
		expect(wrapper.find('.task-refresh-button').attributes('disabled')).toBeDefined()
		expect(sdk.tasksList).not.toHaveBeenCalled()
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

	it('filters task lists by search text and resets pagination', async () => {
		sdk.tasksList.mockImplementation(async () => ({data: {items: [], total_pages: 3}}))
		const wrapper = await mountUpcoming()
		await flushPromises()
		wrapper.findComponent({name: 'PaginationEmit'}).vm.$emit('pageChanged', 2)
		await flushPromises()
		expect(lastQuery().page).toBe(2)
		await wrapper.find('input[type="search"]').setValue('weekly report')
		await vi.waitFor(() => expect(lastQuery().q).toBe('weekly report'), {timeout: 1500})
		expect(lastQuery().page).toBe(1)
		expect(lastQuery().filter).toBe("done = false && due_date < 'now/d+1d' && due_date > 'now/d'")
	})
	it('preserves valid label filters but fails closed for malformed route IDs', async () => {
		const wrapper = await mountUpcoming()
		await flushPromises()
		await wrapper.setProps({labelIds: ['02', '2', '3']})
		await flushPromises()
		expect(lastQuery().filter).toContain('labels in 2, 3')
		await wrapper.setProps({labelIds: ['2', '3) || done = true']})
		await flushPromises()
		expect(lastQuery().filter).toContain('labels in 0')
		expect(lastQuery().filter).not.toContain('done = true')
	})

	it('focuses search with / when focus is not in an editable element', async () => {
		const wrapper = await mountUpcoming()
		document.body.append(wrapper.element)
		await flushPromises()
		const search = wrapper.find<HTMLInputElement>('input[type="search"]').element
		const shortcut = new KeyboardEvent('keydown', {key: '/', bubbles: true, cancelable: true})
		document.dispatchEvent(shortcut)
		expect(shortcut.defaultPrevented).toBe(true)
		expect(document.activeElement).toBe(search)
		expect(search.getAttribute('aria-keyshortcuts')).toBe('/')
		wrapper.element.remove()
	})

	it('does not take / away from a textarea or an open modal', async () => {
		const wrapper = await mountUpcoming()
		document.body.append(wrapper.element)
		await flushPromises()
		const textarea = document.createElement('textarea')
		document.body.append(textarea)
		textarea.focus()
		const editing = new KeyboardEvent('keydown', {key: '/', bubbles: true, cancelable: true})
		textarea.dispatchEvent(editing)
		expect(editing.defaultPrevented).toBe(false)
		expect(document.activeElement).toBe(textarea)
		textarea.remove()
		const modal = document.createElement('dialog')
		modal.setAttribute('open', '')
		document.body.append(modal)
		const shortcut = new KeyboardEvent('keydown', {key: '/', bubbles: true, cancelable: true})
		document.dispatchEvent(shortcut)
		expect(shortcut.defaultPrevented).toBe(false)
		modal.remove()
		wrapper.element.remove()
	})

	it('shows a clear-search control while filtering and preserves date scope', async () => {
		const wrapper = await mountUpcoming()
		await flushPromises()
		expect(wrapper.find('.task-clear-search-button').exists()).toBe(false)
		await wrapper.find('input[type="search"]').setValue('review notes')
		expect(wrapper.find('.task-clear-search-button').exists()).toBe(true)
		await wrapper.find('.task-clear-search-button').trigger('click')
		expect((wrapper.find('input[type="search"]').element as HTMLInputElement).value).toBe('')
		await vi.waitFor(() => expect(lastQuery().q).toBe(''), {timeout: 1500})
		expect(lastQuery().filter).toContain("due_date < 'now/d+1d'")
	})


	it('ignores composing, repeated, and combobox-originated slash shortcuts', async () => {
		const wrapper = await mountUpcoming()
		document.body.append(wrapper.element)
		await flushPromises()
		const search = wrapper.find<HTMLInputElement>('input[type="search"]').element
		const editor = document.createElement('textarea')
		document.body.append(editor)
		editor.focus()
		for (const options of [{isComposing: true}, {repeat: true}]) {
			const event = new KeyboardEvent('keydown', {key: '/', bubbles: true, cancelable: true, ...options})
			document.dispatchEvent(event)
			expect(event.defaultPrevented).toBe(false)
			expect(document.activeElement).toBe(editor)
		}
		const combobox = document.createElement('div')
		combobox.setAttribute('role', 'combobox')
		const child = document.createElement('span')
		child.tabIndex = 0
		combobox.append(child)
		document.body.append(combobox)
		child.focus()
		const event = new KeyboardEvent('keydown', {key: '/', bubbles: true, cancelable: true})
		child.dispatchEvent(event)
		expect(event.defaultPrevented).toBe(false)
		expect(document.activeElement).toBe(child)
		expect(document.activeElement).not.toBe(search)
		combobox.remove()
		editor.remove()
		wrapper.element.remove()
	})

	it('restores search input focus after the real toolbar clear button is activated', async () => {
		const wrapper = await mountUpcoming(true)
		document.body.append(wrapper.element)
		await flushPromises()
		const search = wrapper.find<HTMLInputElement>('input[type="search"]')
		await search.setValue('review notes')
		const clear = wrapper.find<HTMLButtonElement>('button.task-clear-search-button')
		expect(clear.exists()).toBe(true)
		clear.element.focus()
		expect(document.activeElement).toBe(clear.element)
		await clear.trigger('click')
		expect(search.element.value).toBe('')
		expect(document.activeElement).toBe(search.element)
		wrapper.element.remove()
	})

	it('restores search input focus after the real empty-results clear button is activated', async () => {
		const wrapper = await mountUpcoming(true)
		document.body.append(wrapper.element)
		await flushPromises()
		const search = wrapper.find<HTMLInputElement>('input[type="search"]')
		await search.setValue('no matches')
		await vi.waitFor(() => expect(wrapper.find('.tasks-empty-state button').exists()).toBe(true), {timeout: 2000})
		const clear = wrapper.find<HTMLButtonElement>('.tasks-empty-state button')
		clear.element.focus()
		expect(document.activeElement).toBe(clear.element)
		await clear.trigger('click')
		expect(search.element.value).toBe('')
		expect(document.activeElement).toBe(search.element)
		wrapper.element.remove()
	})

	it('clears inline search with Escape while preserving list filters', async () => {
		const wrapper = await mountUpcoming()
		await flushPromises()
		const search = wrapper.find('input[type="search"]')
		await search.setValue('weekly report')
		await vi.waitFor(() => expect(lastQuery().q).toBe('weekly report'), {timeout: 1500})
		await search.trigger('keydown.esc')
		await vi.waitFor(() => expect(lastQuery().q).toBe(''), {timeout: 1500})
		expect(lastQuery().filter).toContain("due_date < 'now/d+1d'")
	})

	it('refreshes current tasks without resetting sort or search settings', async () => {
		const wrapper = await mountUpcoming()
		await flushPromises()
		await wrapper.setProps({sort: 'priority'})
		await flushPromises()
		const previousCalls = sdk.tasksList.mock.calls.length
		await wrapper.find('.task-refresh-button').trigger('click')
		await flushPromises()
		expect(sdk.tasksList).toHaveBeenCalledTimes(previousCalls + 1)
		expect(lastQuery().sort_by).toEqual(['priority', 'due_date', 'id'])
		expect(lastQuery().filter).toContain("due_date < 'now/d+1d'")
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

	it('shows a retry action rather than an empty state when loading fails', async () => {
		sdk.tasksList.mockRejectedValueOnce(new Error('Request failed'))
		const wrapper = await mountUpcoming()
		await flushPromises()
		expect(wrapper.find('.task-load-error').exists()).toBe(true)
		await wrapper.find('.task-load-error').findComponent({name: 'XButton'}).trigger('click')
		await flushPromises()
		expect(sdk.tasksList).toHaveBeenCalledTimes(2)
	})

	it('does not reload tasks when sidebar settings change', async () => {
		await mountUpcoming()
		await flushPromises()

		auth.settings = {frontend_settings: {filter_id_used_on_overview: undefined, sidebar_width: 300}}
		await flushPromises()
		expect(sdk.tasksList).toHaveBeenCalledTimes(1)
	})
})
