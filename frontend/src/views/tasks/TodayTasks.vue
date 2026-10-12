<template>
	<div class="content is-max-width-desktop">
		<AddTask v-if="projectList.hasProjects" ref="quickAdd" :default-due-today="true" />
		<p v-if="projectList.hasProjects" class="help quick-add-shortcut-hint mbe-3">
			{{ $t('task.quickAddShortcutHint') }}
		</p>
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
import {useAuthStore} from '@/stores/auth'
import {ref} from 'vue'
import {useEventListener} from '@vueuse/core'

defineProps<{showOverdue: boolean, showNulls: boolean, sort?: string}>()
const projectList = useProjects()
const authStore = useAuthStore()
const quickAdd = ref<InstanceType<typeof AddTask> | null>(null)

useEventListener(document, 'keydown', event => {
	if (event.defaultPrevented || event.isComposing || event.repeat || event.key.toLowerCase() !== 'n') return
	if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey || !authStore.authenticated) return
	const target = event.target
	if (target instanceof Element && target.closest('input, textarea, select, [contenteditable], [role="textbox"], [role="combobox"]')) return
	if (document.querySelector('dialog[open], [role="dialog"][aria-modal="true"]')) return
	if (!projectList.hasProjects || !quickAdd.value) return
	event.preventDefault()
	quickAdd.value.focusTaskInput()
})
</script>
