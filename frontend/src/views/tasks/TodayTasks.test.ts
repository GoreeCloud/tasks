import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {createPinia} from 'pinia'
import {enableAutoUnmount, shallowMount} from '@vue/test-utils'
import {nextTick, reactive} from 'vue'

const projectList = reactive({hasProjects: true, isLoading: false})
const auth = reactive({authenticated: true})
vi.mock('@/stores/auth', () => ({useAuthStore: () => auth}))
vi.mock('@/composables/useProjects', () => ({
	useProjects: () => projectList,
}))

import TodayTasks from './TodayTasks.vue'

enableAutoUnmount(afterEach)

describe('Today task list state', () => {
	beforeEach(() => {
		projectList.hasProjects = true
		projectList.isLoading = false
	})

	it('keeps the same list instance after Quick Add emits a task', async () => {
		const wrapper = shallowMount(TodayTasks, {
			props: {showOverdue: false, showNulls: false},
			global: {plugins: [createPinia()], mocks: {$t: (key: string) => key}},
		})
		const list = wrapper.findComponent({name: 'ShowTasks'})
		const add = wrapper.findComponent({name: 'AddTask'})
		expect(list.exists()).toBe(true)
		expect(add.exists()).toBe(true)
		const previousInstance = list.vm
		add.vm.$emit('tasksAdded', [{id: 1}])
		await nextTick()
		expect(wrapper.findComponent({name: 'ShowTasks'}).vm).toBe(previousInstance)
	})

	it('offers project creation after loading an account with no projects', async () => {
		projectList.hasProjects = false
		const wrapper = shallowMount(TodayTasks, {
			props: {showOverdue: false, showNulls: false},
			global: {plugins: [createPinia()], mocks: {$t: (key: string) => key}, stubs: {RouterLink: {name: 'RouterLink', props: ['to'], template: '<a><slot /></a>'}}},
		})
		expect(wrapper.findComponent({name: 'AddTask'}).exists()).toBe(false)
		expect(wrapper.findComponent({name: 'RouterLink'}).props('to')).toEqual({name: 'project.create'})
	})

	it('does not flash the empty-account action while projects load', () => {
		projectList.hasProjects = false
		projectList.isLoading = true
		const wrapper = shallowMount(TodayTasks, {
			props: {showOverdue: false, showNulls: false},
			global: {plugins: [createPinia()], mocks: {$t: (key: string) => key}},
		})
		expect(wrapper.find('a.button').exists()).toBe(false)
	})
})

describe('Today Quick Add keyboard shortcut', () => {
	const focusTaskInput = vi.fn()

	function mountShortcutView() {
		return shallowMount(TodayTasks, {
			props: {showOverdue: false, showNulls: false},
			global: {
				plugins: [createPinia()],
				mocks: {$t: (key: string) => key},
				stubs: {AddTask: {name: 'AddTask', template: '<div />', methods: {focusTaskInput}}},
			},
		})
	}

	function pressN(target: EventTarget = document, options: KeyboardEventInit = {}) {
		const event = new KeyboardEvent('keydown', {key: 'n', bubbles: true, cancelable: true, ...options})
		target.dispatchEvent(event)
		return event
	}

	beforeEach(() => {
		auth.authenticated = true
		projectList.hasProjects = true
		projectList.isLoading = false
		focusTaskInput.mockReset()
	})

	it('focuses Quick Add for an authenticated user and consumes the key', () => {
		const wrapper = mountShortcutView()
		const event = pressN()
		expect(event.defaultPrevented).toBe(true)
		expect(focusTaskInput).toHaveBeenCalledOnce()
		wrapper.unmount()
	})

	it('does not activate without authentication or an available project', () => {
		auth.authenticated = false
		const unauthenticated = mountShortcutView()
		expect(pressN().defaultPrevented).toBe(false)
		expect(focusTaskInput).not.toHaveBeenCalled()
		unauthenticated.unmount()

		auth.authenticated = true
		projectList.hasProjects = false
		const noProject = mountShortcutView()
		expect(pressN().defaultPrevented).toBe(false)
		expect(focusTaskInput).not.toHaveBeenCalled()
		noProject.unmount()
	})

	it('does not steal keys from editable controls or an open modal', () => {
		const wrapper = mountShortcutView()
		const editor = document.createElement('textarea')
		document.body.append(editor)
		expect(pressN(editor).defaultPrevented).toBe(false)
		editor.remove()
		const dialog = document.createElement('dialog')
		dialog.setAttribute('open', '')
		document.body.append(dialog)
		expect(pressN().defaultPrevented).toBe(false)
		dialog.remove()
		expect(focusTaskInput).not.toHaveBeenCalled()
		wrapper.unmount()
	})

	it('ignores composing, repeated, and modified keystrokes', () => {
		const wrapper = mountShortcutView()
		for (const options of [{isComposing: true}, {repeat: true}, {ctrlKey: true}, {shiftKey: true}]) {
			expect(pressN(document, options).defaultPrevented).toBe(false)
		}
		expect(focusTaskInput).not.toHaveBeenCalled()
		wrapper.unmount()
	})

	it('removes the global listener after unmount', () => {
		const wrapper = mountShortcutView()
		wrapper.unmount()
		expect(pressN().defaultPrevented).toBe(false)
		expect(focusTaskInput).not.toHaveBeenCalled()
	})
})
