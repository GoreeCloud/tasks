<template>
	<div
		v-cy="'showTasks'"
		class="is-max-width-desktop has-text-start"
	>
		<h2 class="mbe-2 title">
			{{ pageTitle }}
		</h2>
		<Message
			v-if="filteredLabels.length > 0"
			class="label-filter-info mbe-2"
		>
			<i18n-t
				keypath="task.show.filterByLabel"
				tag="span"
				class="filter-label-text"
			>
				<template #label>
					<XLabel
						v-for="label in filteredLabels"
						:key="label.id"
						:label="label"
					/>
				</template>
			</i18n-t>
			<BaseButton
				v-tooltip="$t('task.show.clearLabelFilter')"
				class="clear-filter-button"
				:aria-label="$t('task.show.clearLabelFilter')"
				@click="clearLabelFilter"
			>
				<Icon icon="times" />
			</BaseButton>
		</Message>
		<Message
			v-if="savedFilterIgnored"
			class="mbe-2"
		>
			{{ $t('task.show.savedFilterIgnored') }}
		</Message>
		<div class="task-list-toolbar">
			<label class="task-search-control">
				<span class="is-sr-only">{{ $t('task.show.searchTasks') }}</span>
				<input
					v-model="searchText"
					type="search"
					:placeholder="$t('task.show.searchTasks')"
					autocomplete="off"
				>
			</label>
			<div class="task-sort-control">
				<label>
					<span>{{ $t('project.list.sort') }}</span>
					<select
						:value="selectedSort"
						@change="setSortFromEvent"
					>
						<option value="due">{{ $t('task.attributes.dueDate') }}</option>
						<option value="priority">{{ $t('task.attributes.priority') }}</option>
						<option value="newest">{{ $t('task.attributes.created') }}</option>
					</select>
				</label>
			</div>
		</div>
		<p
			v-if="!showAll"
			class="show-tasks-options"
		>
			<DatepickerWithRange
				:model-value="{dateFrom: dateFrom ?? null, dateTo: dateTo ?? null}"
				@update:modelValue="setDate"
			>
				<template #trigger="{toggle}">
					<XButton
						variant="primary"
						:shadow="false"
						class="mbe-2"
						@click.prevent.stop="toggle()"
					>
						{{ $t('task.show.select') }}
					</XButton>
				</template>
			</DatepickerWithRange>
			<FancyCheckbox
				:model-value="showNulls"
				class="mie-2"
				@update:modelValue="setShowNulls"
			>
				{{ $t('task.show.noDates') }}
			</FancyCheckbox>
			<FancyCheckbox
				:model-value="showOverdue"
				@update:modelValue="setShowOverdue"
			>
				{{ $t('task.show.overdue') }}
			</FancyCheckbox>
		</p>
		<Message v-if="loadError" variant="danger" class="task-load-error mbe-3">
			<span>{{ $t('error.error') }}. {{ $t('offline.text') }}</span>
			<XButton :shadow="false" @click="updateTasks">{{ $t('sharing.retry') }}</XButton>
		</Message>
		<template v-if="!loading && !loadError && !hasTasks && showNothingToDo">
			<div class="tasks-empty-state" role="status">
				<h3>{{ searchTerm.trim() ? $t('task.show.noSearchResults') : $t('task.show.noTasks') }}</h3>
				<XButton v-if="searchTerm.trim()" :shadow="false" @click="searchText = ''">{{ $t('task.show.clearSearch') }}</XButton>
				<LlamaCool v-else class="llama-cool" aria-hidden="true" />
				<RouterLink
					v-if="route.name === 'tasks.range' && !searchTerm.trim()"
					:to="{name: 'tasks.today'}"
				>
					{{ $t('input.datepickerRange.ranges.today') }}
				</RouterLink>
			</div>
		</template>

		<Card
			v-if="hasTasks"
			:padding="false"
			class="has-overflow"
			:has-content="false"
			:loading="loading"
		>
			<ul class="p-2 tasks">
				<li
					v-for="task in tasks"
					:key="task.id"
				>
					<SingleTaskInProject
						:show-project="true"
						:the-task="task"
						:can-mark-as-done="(projectList.projects[task.project_id]?.max_permission ?? 0) > PERMISSIONS.READ"
						@taskUpdated="updateTasks"
					/>
				</li>
			</ul>
		</Card>
		<PaginationEmit
			v-if="totalPages > 1"
			:total-pages="totalPages"
			:current-page="currentPage"
			@pageChanged="setPage"
		/>
		<div
			v-if="loading && !hasTasks && !loadError"
			:class="{ 'is-loading': showLoading}"
			class="spinner"
		/>
	</div>
</template>

<script setup lang="ts">
import {computed, ref, watch, watchEffect} from 'vue'
import {refDebounced} from '@vueuse/core'
import {useRoute, useRouter} from 'vue-router'
import {useI18n} from 'vue-i18n'

import {formatDate} from '@/helpers/time/formatDate'
import {setTitle} from '@/helpers/setTitle'

import BaseButton from '@/components/base/BaseButton.vue'
import Icon from '@/components/misc/Icon'
import Message from '@/components/misc/Message.vue'
import FancyCheckbox from '@/components/input/FancyCheckbox.vue'
import SingleTaskInProject from '@/components/tasks/partials/SingleTaskInProject.vue'
import DatepickerWithRange from '@/components/date/DatepickerWithRange.vue'
import PaginationEmit from '@/components/misc/PaginationEmit.vue'
import XLabel from '@/components/tasks/partials/Label.vue'
import {DATE_RANGES} from '@/components/date/dateRanges'
import {buildLabelFilter} from '@/helpers/buildLabelFilter'
import LlamaCool from '@/assets/llama-cool.svg?component'
import {useAuthStore} from '@/stores/auth'
import {useProjects} from '@/composables/useProjects'
import {useLabels} from '@/composables/useLabels'
import type {TaskFilterParams} from '@/client/queries/tasks'
import {useTasks} from '@/composables/useTasks'
import {useDelayedLoading} from '@/composables/useDelayedLoading'
import type {TaskScope} from '@/client/queries/tasks'
import {PERMISSIONS} from '@/constants/permissions'

const props = withDefaults(defineProps<{
	dateFrom?: Date | string,
	dateTo?: Date | string,
	showNulls?: boolean,
	showOverdue?: boolean,
	labelIds?: string[],
	sort?: string,
}>(), {
	showNulls: false,
	showOverdue: false,
	dateFrom: undefined,
	dateTo: undefined,
	labelIds: undefined,
	sort: undefined,
})

const emit = defineEmits<{
	'tasksLoaded': [loaded: true],
	'clearLabelFilter': [],
}>()

const authStore = useAuthStore()
const projectList = useProjects()
const {getLabelById} = useLabels()

const route = useRoute()
const router = useRouter()
const {t} = useI18n({useScope: 'global'})

const taskScope = ref<TaskScope | null>(null)
const currentPage = ref(1)
const searchText = ref('')
const searchTerm = refDebounced(searchText, 250)
const taskQuery = useTasks(
	() => taskScope.value ?? {},
	{enabled: () => authStore.authenticated && taskScope.value !== null, page: () => currentPage.value},
)
const tasks = taskQuery.tasks
const totalPages = taskQuery.totalPages
const loadError = taskQuery.isError
const showNothingToDo = ref<boolean>(false)


setTimeout(() => showNothingToDo.value = true, 100)

const showAll = computed(() => typeof props.dateFrom === 'undefined' || typeof props.dateTo === 'undefined')
const selectedSort = computed(() => props.sort === 'priority' || props.sort === 'newest' ? props.sort : 'due')

const filteredLabels = computed(() => {
	if (!props.labelIds || props.labelIds.length === 0) {
		return []
	}
	return props.labelIds
		.map(id => getLabelById(Number(id)))
		.filter(label => label !== null && label !== undefined)
})

const savedFilterIgnored = computed(() => {
	return filteredLabels.value.length > 0
		&& filterIdUsedOnOverview.value
		&& typeof projectList.projects[filterIdUsedOnOverview.value] !== 'undefined'
})

const pageTitle = computed(() => {
	// We need to define "key" because it is the first parameter in the array and we need the second
	const predefinedRange = Object.entries(DATE_RANGES)
		.find(([, value]) => props.dateFrom === value[0] && props.dateTo === value[1])
		?.[0]
	if (typeof predefinedRange !== 'undefined') {
		return t(`input.datepickerRange.ranges.${predefinedRange}`)
	}

	return showAll.value
		? t('task.show.titleCurrent')
		: t('task.show.fromuntil', {
			from: formatDate(props.dateFrom, 'LL'),
			until: formatDate(props.dateTo, 'LL'),
		})
})
const hasTasks = computed(() => tasks.value && tasks.value.length > 0)
const userAuthenticated = computed(() => authStore.authenticated)
const loading = taskQuery.isFetching
const showLoading = useDelayedLoading(loading)
const filterIdUsedOnOverview = computed(() => authStore.settings?.frontend_settings?.filter_id_used_on_overview)

interface dateStrings {
	dateFrom: Date | string | null,
	dateTo: Date | string | null,
}

function setDate(dates: dateStrings) {
	const from = dates.dateFrom ?? props.dateFrom
	const to = dates.dateTo ?? props.dateTo
	router.push({
		name: route.name === 'tasks.today' ? 'tasks.range' : route.name as string,
		query: {
			...route.query,
			from: from instanceof Date ? from.toISOString() : from,
			to: to instanceof Date ? to.toISOString() : to,
			showOverdue: props.showOverdue ? 'true' : 'false',
			showNulls: props.showNulls ? 'true' : 'false',
		},
	})
}

function setShowOverdue(show: boolean) {
	router.push({
		name: route.name as string,
		query: {
			...route.query,
			showOverdue: show ? 'true' : 'false',
		},
	})
}

function setShowNulls(show: boolean) {
	router.push({
		name: route.name as string,
		query: {
			...route.query,
			showNulls: show ? 'true' : 'false',
		},
	})
}

function setSortFromEvent(event: Event) {
	const selected = (event.target as HTMLSelectElement).value
	if (selected !== 'due' && selected !== 'priority' && selected !== 'newest') return
	void router.push({
		name: route.name as string,
		query: {...route.query, sort: selected === 'due' ? undefined : selected},
	})
}

function clearLabelFilter() {
	emit('clearLabelFilter')
}

async function loadPendingTasks(from: Date|string|undefined, to: Date|string|undefined, filterId: number | null | undefined) {
	// FIXME: HACK! This should never happen.
	// Since this route is authentication only, users would get an error message if they access the page unauthenticated.
	// Since this component is mounted as the home page before unauthenticated users get redirected
	// to the login page, they will almost always see the error message.
	if (!userAuthenticated.value) {
		return
	}

	const params: TaskFilterParams = {
		sort_by: selectedSort.value === 'priority' ? ['priority', 'due_date', 'id'] : selectedSort.value === 'newest' ? ['created', 'id'] : ['due_date', 'id'],
		order_by: selectedSort.value === 'priority' ? ['desc', 'asc', 'desc'] : selectedSort.value === 'newest' ? ['desc', 'desc'] : ['asc', 'desc'],
		filter: 'done = false',
		filter_include_nulls: props.showNulls,
		q: searchTerm.value.trim(),
		expand: ['comment_count', 'is_unread'],
	}

	if (!showAll.value) {

		params.filter += ` && due_date < '${to instanceof Date ? to.toISOString() : to}'`

		// NOTE: Ideally we could also show tasks with a start or end date in the specified range, but the api
		//       is not capable (yet) of combining multiple filters with 'and' and 'or'.

		if (!props.showOverdue) {
			params.filter += ` && due_date > '${from instanceof Date ? from.toISOString() : from}'`
		}
	}

	// Add label filtering
	if (props.labelIds && props.labelIds.length > 0) {
		const labelFilter = buildLabelFilter(props.labelIds)
		params.filter += params.filter ? ` && ${labelFilter}` : labelFilter
	}

	let projectId = null
	if (showAll.value && filterId && typeof projectList.projects[filterId] !== 'undefined'
		&& (!props.labelIds || props.labelIds.length === 0)) {
		projectId = filterId
	}

	taskScope.value = {project: projectId, params: {...params, filter_timezone: authStore.settings.timezone}}
}

watch(taskQuery.data, data => { if (data) emit('tasksLoaded', true) })

function updateTasks() { return taskQuery.refetch() }

function setPage(page: number) {
	if (Number.isSafeInteger(page) && page >= 1 && page <= totalPages.value) {
		currentPage.value = page
	}
}

watch(totalPages, pages => {
	if (pages > 0 && currentPage.value > pages) currentPage.value = pages
})

// Keep sidebar setting changes from reloading tasks.
watch(
	[
		() => props.dateFrom,
		() => props.dateTo,
		filterIdUsedOnOverview,
		() => props.showOverdue,
		() => props.showNulls,
		() => props.labelIds,
		() => props.sort,
		searchTerm,
		userAuthenticated,
	],
	([from, to, filterId]) => {
		currentPage.value = 1
		void loadPendingTasks(from, to, filterId)
	},
	{immediate: true},
)
watchEffect(() => setTitle(pageTitle.value))
</script>

<style lang="scss" scoped>
.tasks {
	list-style: none;
	margin: 0;
}

.show-tasks-options {
	display: flex;
	flex-direction: column;
}

.task-list-toolbar {
	display: flex;
	gap: 0.75rem;
	flex-wrap: wrap;
	align-items: center;
	justify-content: space-between;
	margin-block-end: 0.75rem;
}

.task-search-control {
	flex: 1 1 13rem;
	input {
		inline-size: 100%;
		padding: 0.375rem 0.75rem;
		border: 1px solid var(--grey-300);
		border-radius: 0.5rem;
		background: var(--site-background);
		color: inherit;
		&:focus-visible { outline: 3px solid var(--primary); outline-offset: 2px; }
	}
}

.task-sort-control {
	display: flex;
	justify-content: flex-end;
	label { display: inline-flex; gap: 0.5rem; align-items: center; font-weight: 600; }
	select {
		padding: 0.375rem 0.75rem;
		border: 1px solid var(--grey-300);
		border-radius: 0.5rem;
		background: var(--site-background);
		color: inherit;
		&:focus-visible { outline: 3px solid var(--primary); outline-offset: 2px; }
	}
}

.task-load-error {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	flex-wrap: wrap;
}

.tasks-empty-state {
	padding: 1.5rem;
	text-align: center;
	border: 1px solid var(--grey-200);
	border-radius: 1rem;
	background: var(--site-background);
}

.llama-cool {
	margin: 3rem auto 0;
	display: block;
}

.label-filter-info {
	margin-block-end: 1rem;
	
	.clear-filter-button {
		margin-inline-start: auto;
		padding: 0.25rem 0.5rem;
		
		&:hover {
			color: var(--danger);
		}
	}

	:deep(.message.info) {
		inline-size: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
	}
}
</style>
