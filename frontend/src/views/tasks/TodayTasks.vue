<template>
	<div class="content is-max-width-desktop">
		<AddTask v-if="projectList.hasProjects" :default-due-today="true" @tasksAdded="taskListVersion++" />
		<ShowTasks
			:key="taskListVersion"
			:date-from="DATE_RANGES.today[0]"
			:date-to="DATE_RANGES.today[1]"
			:show-overdue="showOverdue"
			:show-nulls="showNulls"
			:sort="sort"
		/>
	</div>
</template>

<script setup lang="ts">
import {ref} from 'vue'
import AddTask from '@/components/tasks/AddTask.vue'
import ShowTasks from '@/views/tasks/ShowTasks.vue'
import {DATE_RANGES} from '@/components/date/dateRanges'
import {useProjects} from '@/composables/useProjects'

defineProps<{showOverdue: boolean, showNulls: boolean, sort?: string}>()
const projectList = useProjects()
const taskListVersion = ref(0)
</script>
