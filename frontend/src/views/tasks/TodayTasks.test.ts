import {beforeEach, describe, expect, it, vi} from 'vitest'
import {shallowMount} from '@vue/test-utils'
import {nextTick, reactive} from 'vue'

const projectList = reactive({hasProjects: true, isLoading: false})
vi.mock('@/composables/useProjects', () => ({
	useProjects: () => projectList,
}))

import TodayTasks from './TodayTasks.vue'

describe('Today task list state', () => {
	beforeEach(() => {
		projectList.hasProjects = true
		projectList.isLoading = false
	})

	it('keeps the same list instance after Quick Add emits a task', async () => {
		const wrapper = shallowMount(TodayTasks, {
			props: {showOverdue: false, showNulls: false},
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
			global: {stubs: {RouterLink: {name: 'RouterLink', props: ['to'], template: '<a><slot /></a>'}}},
		})
		expect(wrapper.findComponent({name: 'AddTask'}).exists()).toBe(false)
		expect(wrapper.findComponent({name: 'RouterLink'}).props('to')).toEqual({name: 'project.create'})
	})

	it('does not flash the empty-account action while projects load', () => {
		projectList.hasProjects = false
		projectList.isLoading = true
		const wrapper = shallowMount(TodayTasks, {
			props: {showOverdue: false, showNulls: false},
		})
		expect(wrapper.findComponent({name: 'RouterLink'}).exists()).toBe(false)
	})
})
