import {describe, expect, it, vi} from 'vitest'
import {shallowMount} from '@vue/test-utils'
import {nextTick} from 'vue'

vi.mock('@/composables/useProjects', () => ({
	useProjects: () => ({hasProjects: true}),
}))

import TodayTasks from './TodayTasks.vue'

describe('Today task list state', () => {
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
})
