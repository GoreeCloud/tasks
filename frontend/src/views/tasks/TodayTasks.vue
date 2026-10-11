<template>
	<div class="content is-max-width-desktop">
		<AddTask v-if="projectList.hasProjects" :default-due-today="true" />
		<RouterLink
			v-if="!projectList.isLoading && !projectList.hasProjects"
			:to="{name: 'project.create'}"
			class="button is-primary mbe-3"
		>
			{{ $t('project.create.header') }}
		</RouterLink>
		<ShowTasks
			:date-from="DATE_RANGES.today[0]"
			:date-to="DATE_RANGES.today[1]"
			:show-overdue="showOverdue"
			:show-nulls="showNulls"
			:sort="sort"
		/>
	</div>
</template>

<script setup lang="ts">
import AddTask from '@/components/tasks/AddTask.vue'
import ShowTasks from '@/views/tasks/ShowTasks.vue'
import {DATE_RANGES} from '@/components/date/dateRanges'
import {useProjects} from '@/composables/useProjects'

defineProps<{showOverdue: boolean, showNulls: boolean, sort?: string}>()
const projectList = useProjects()
</script>
