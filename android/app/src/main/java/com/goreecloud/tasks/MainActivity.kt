package com.goreecloud.tasks

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.goreecloud.ui.material3.GoreeAccent
import com.goreecloud.ui.material3.GoreeCloudExpressiveTheme
import com.goreecloud.ui.multiplatform.GoreeCloudAction
import com.goreecloud.ui.multiplatform.GoreeCloudPanel
import kotlinx.coroutines.launch
import java.time.LocalDate

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            // One approved Material 3 Expressive outer host. Shared UI controls inherit its theme.
            GoreeCloudExpressiveTheme(accent = GoreeAccent.Iris) { TasksScreen() }
        }
    }
}

private data class TaskDraft(
    val title: String = "",
    val description: String = "",
    val dueDate: String = "",
    val priority: Int = 2,
    val projectId: String? = null,
    val parentId: String? = null,
    val recurrence: String = "none",
    val tags: String = ""
) {
    fun tagsList() = tags.split(",").map { it.trim() }.filter { it.isNotBlank() }

    companion object {
        fun from(task: TaskItem) = TaskDraft(
            title = task.title, description = task.description, dueDate = task.dueDate ?: "",
            priority = task.priority, projectId = task.projectId, parentId = task.parentId,
            recurrence = task.recurrence, tags = task.tags.joinToString(", ")
        )
    }
}

@Composable
private fun DraftFields(
    draft: TaskDraft,
    update: (TaskDraft) -> Unit,
    projects: List<ProjectItem>,
    parents: List<TaskItem>
) {
    OutlinedTextField(
        value = draft.title, onValueChange = { update(draft.copy(title = it)) },
        label = { Text("Title") }, singleLine = true, modifier = Modifier.fillMaxWidth()
    )
    OutlinedTextField(
        value = draft.description, onValueChange = { update(draft.copy(description = it)) },
        label = { Text("Notes") }, minLines = 2, maxLines = 4, modifier = Modifier.fillMaxWidth()
    )
    OutlinedTextField(
        value = draft.dueDate, onValueChange = { update(draft.copy(dueDate = it)) },
        label = { Text("Due (YYYY-MM-DD, optional)") }, singleLine = true, modifier = Modifier.fillMaxWidth()
    )
    Text("Priority", style = MaterialTheme.typography.labelMedium)
    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        items(listOf(1, 2, 3, 4)) { level ->
            FilterChip(selected = draft.priority == level,
                onClick = { update(draft.copy(priority = level)) },
                label = { Text("P" + level) })
        }
    }
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        var recurrenceMenu by remember { mutableStateOf(false) }
        Box {
            OutlinedButton(onClick = { recurrenceMenu = true }) {
                Text("Repeat: " + draft.recurrence)
            }
            DropdownMenu(expanded = recurrenceMenu, onDismissRequest = { recurrenceMenu = false }) {
                listOf("none", "daily", "weekdays", "weekly", "biweekly", "monthly", "yearly").forEach { option ->
                    DropdownMenuItem(text = { Text(if (option == "biweekly") "Every 2 weeks" else option) }, onClick = {
                        update(draft.copy(recurrence = option)); recurrenceMenu = false
                    })
                }
            }
        }
        var projectMenu by remember { mutableStateOf(false) }
        Box {
            val name = projects.find { it.id == draft.projectId }?.name ?: "Inbox"
            OutlinedButton(onClick = { projectMenu = true }) { Text(name, maxLines = 1) }
            DropdownMenu(expanded = projectMenu, onDismissRequest = { projectMenu = false }) {
                DropdownMenuItem(text = { Text("Inbox") }, onClick = {
                    update(draft.copy(projectId = null)); projectMenu = false
                })
                projects.forEach { project ->
                    DropdownMenuItem(text = { Text(project.name) }, onClick = {
                        update(draft.copy(projectId = project.id)); projectMenu = false
                    })
                }
            }
        }
    }
    var parentMenu by remember { mutableStateOf(false) }
    Box {
        val parentTitle = parents.find { it.id == draft.parentId }?.title ?: "Standalone task"
        OutlinedButton(onClick = { parentMenu = true }) {
            Text("Parent: " + parentTitle, maxLines = 1)
        }
        DropdownMenu(expanded = parentMenu, onDismissRequest = { parentMenu = false }) {
            DropdownMenuItem(text = { Text("Standalone task") }, onClick = {
                update(draft.copy(parentId = null)); parentMenu = false
            })
            parents.filter { !it.done }.forEach { parent ->
                DropdownMenuItem(text = { Text(parent.title) }, onClick = {
                    update(draft.copy(parentId = parent.id)); parentMenu = false
                })
            }
        }
    }
    OutlinedTextField(
        value = draft.tags, onValueChange = { update(draft.copy(tags = it)) },
        label = { Text("Tags (comma-separated)") }, singleLine = true, modifier = Modifier.fillMaxWidth()
    )
}

private fun isDescendant(candidate: TaskItem, ancestorId: String, all: List<TaskItem>): Boolean {
    var current = candidate.parentId
    val visited = mutableSetOf<String>()
    while (current != null && visited.add(current)) {
        if (current == ancestorId) return true
        current = all.find { it.id == current }?.parentId
    }
    return false
}

@Composable
private fun EditTaskDialog(
    task: TaskItem,
    projects: List<ProjectItem>,
    tasks: List<TaskItem>,
    loading: Boolean,
    onDismiss: () -> Unit,
    onSave: (TaskDraft) -> Unit,
    onDelete: () -> Unit
) {
    var draft by remember(task.id) { mutableStateOf(TaskDraft.from(task)) }
    var confirmDelete by remember(task.id) { mutableStateOf(false) }
    if (confirmDelete) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            title = { Text("Delete task?") },
            text = { Text("This permanently removes the task from the server.") },
            confirmButton = {
                TextButton(enabled = !loading, onClick = onDelete) { Text("Delete permanently") }
            },
            dismissButton = {
                TextButton(onClick = { confirmDelete = false }) { Text("Cancel") }
            }
        )
    } else {
        AlertDialog(
            onDismissRequest = onDismiss,
            title = { Text("Edit task") },
            text = {
                Column(
                    Modifier.heightIn(max = 460.dp).verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    DraftFields(draft, { draft = it }, projects,
                        tasks.filter { !it.done && it.id != task.id && !isDescendant(it, task.id, tasks) })
                    TextButton(onClick = { confirmDelete = true }, enabled = !loading) {
                        Text("Delete task", color = MaterialTheme.colorScheme.error)
                    }
                }
            },
            confirmButton = {
                TextButton(enabled = !loading && draft.title.isNotBlank(),
                    onClick = { onSave(draft) }) { Text("Save changes") }
            },
            dismissButton = {
                TextButton(onClick = onDismiss) { Text("Cancel") }
            }
        )
    }
}

@Composable
private fun HabitsDialog(
    habits: List<HabitItem>,
    busy: Boolean,
    onDismiss: () -> Unit,
    onCreate: (String, String) -> Unit,
    onUpdate: (HabitItem, String, String) -> Unit,
    historyHabitId: String?,
    historyDates: List<String>,
    historyOffset: Int,
    historyHasMore: Boolean,
    historyError: String,
    onHistoryPage: (HabitItem, Int) -> Unit,
    onCheckin: (HabitItem) -> Unit,
    onDelete: (HabitItem) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Daily habits") },
        text = {
            Column(
                Modifier.heightIn(max = 470.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text("Check in once per local calendar day. Data stays on your self-hosted server.",
                    style = MaterialTheme.typography.bodySmall)
                if (historyError.isNotBlank()) Text(
                    historyError, color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodyMedium
                )
                OutlinedTextField(value = name, onValueChange = { name = it },
                    label = { Text("New habit") }, modifier = Modifier.fillMaxWidth(),
                    singleLine = true)
                OutlinedTextField(value = description, onValueChange = { description = it },
                    label = { Text("Notes (optional)") }, modifier = Modifier.fillMaxWidth())
                TextButton(
                    enabled = !busy && name.isNotBlank(),
                    onClick = {
                        onCreate(name.trim(), description)
                        name = ""; description = ""
                    }
                ) { Text("Create habit") }
                habits.forEach { habit ->
                    GoreeCloudPanel(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Checkbox(checked = habit.checkedInToday, enabled = !busy,
                                    onCheckedChange = { onCheckin(habit) })
                                Column(Modifier.weight(1f)) {
                                    Text(habit.name, style = MaterialTheme.typography.titleMedium)
                                    if (habit.description.isNotBlank())
                                        Text(habit.description, style = MaterialTheme.typography.bodySmall)
                                    Text(habit.currentStreak.toString() + " day streak · " +
                                        habit.totalCheckins + " check-ins",
                                        style = MaterialTheme.typography.labelMedium)
                                }
                            }
                            var editing by remember(habit.id) { mutableStateOf(false) }
                            var editedName by remember(habit.id) { mutableStateOf(habit.name) }
                            var editedNotes by remember(habit.id) { mutableStateOf(habit.description) }
                            if (editing) {
                                OutlinedTextField(
                                    value = editedName, onValueChange = { editedName = it },
                                    label = { Text("Edit habit name") },
                                    modifier = Modifier.fillMaxWidth(), singleLine = true,
                                    enabled = !busy
                                )
                                OutlinedTextField(
                                    value = editedNotes, onValueChange = { editedNotes = it },
                                    label = { Text("Edit habit notes") },
                                    modifier = Modifier.fillMaxWidth(), enabled = !busy
                                )
                                Row {
                                    TextButton(onClick = { editing = false }, enabled = !busy) {
                                        Text("Cancel editing")
                                    }
                                    TextButton(
                                        enabled = !busy && editedName.trim().length in 1..120 &&
                                            editedNotes.length <= 16000,
                                        onClick = {
                                            onUpdate(habit, editedName.trim(), editedNotes)
                                            editing = false
                                        }
                                    ) { Text("Save habit") }
                                }
                            } else {
                                TextButton(enabled = !busy, onClick = {
                                    editedName = habit.name
                                    editedNotes = habit.description
                                    editing = true
                                }) { Text("Edit habit") }
                            }
                            TextButton(enabled = !busy, onClick = {
                                onHistoryPage(habit, if (historyHabitId == habit.id) -1 else 0)
                            }) {
                                Text(if (historyHabitId == habit.id) "Hide check-in history"
                                     else "View check-in history")
                            }
                            if (historyHabitId == habit.id) {
                                Text("Recorded dates, newest first · 30 per page",
                                    style = MaterialTheme.typography.labelMedium)
                                if (historyDates.isEmpty()) Text("No check-ins on this page.",
                                    style = MaterialTheme.typography.bodySmall)
                                historyDates.forEach { day ->
                                    Text(day, style = MaterialTheme.typography.bodySmall)
                                }
                                Row(
                                    Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    TextButton(
                                        enabled = !busy && historyOffset > 0,
                                        onClick = { onHistoryPage(habit, (historyOffset - 30).coerceAtLeast(0)) }
                                    ) { Text("Newer dates") }
                                    Text("Page " + (historyOffset / 30 + 1),
                                        style = MaterialTheme.typography.labelSmall)
                                    TextButton(
                                        enabled = !busy && historyHasMore,
                                        onClick = { onHistoryPage(habit, historyOffset + 30) }
                                    ) { Text("Older dates") }
                                }
                            }
                            var showDelete by remember(habit.id) { mutableStateOf(false) }
                            if (showDelete) {
                                Text("Erase this habit and all check-ins?",
                                    color = MaterialTheme.colorScheme.error)
                                Row {
                                    TextButton(onClick = { showDelete = false }) { Text("Cancel") }
                                    TextButton(enabled = !busy, onClick = {
                                        showDelete = false; onDelete(habit)
                                    }) { Text("Delete permanently") }
                                }
                            } else {
                                TextButton(enabled = !busy, onClick = { showDelete = true }) {
                                    Text("Delete habit")
                                }
                            }
                        }
                    }
                }
                if (habits.isEmpty()) Text("No habits created yet.")
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text("Close") }
        }
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TasksScreen() {
    var serverUrl by remember { mutableStateOf("https://") }
    var token by remember { mutableStateOf("") }
    var api by remember { mutableStateOf<TaskApi?>(null) }
    var tasks by remember { mutableStateOf<List<TaskItem>>(emptyList()) }
    var projects by remember { mutableStateOf<List<ProjectItem>>(emptyList()) }
    var habits by remember { mutableStateOf<List<HabitItem>>(emptyList()) }
    var showHabits by remember { mutableStateOf(false) }
    var historyHabitId by remember { mutableStateOf<String?>(null) }
    var historyDates by remember { mutableStateOf<List<String>>(emptyList()) }
    var historyOffset by remember { mutableIntStateOf(0) }
    var historyHasMore by remember { mutableStateOf(false) }
    var draft by remember { mutableStateOf(TaskDraft()) }
    var projectName by remember { mutableStateOf("") }
    var error by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var selectedTask by remember { mutableStateOf<TaskItem?>(null) }
    var view by remember { mutableStateOf("Inbox") }
    var projectFilter by remember { mutableStateOf<String?>(null) }
    var query by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()

    suspend fun reload(client: TaskApi) {
        val snapshot = client.loadWorkspace()
        tasks = snapshot.tasks
        projects = snapshot.projects
    }
    suspend fun reloadHabits(client: TaskApi) {
        habits = client.listHabits(LocalDate.now().toString())
    }
    fun execute(operation: suspend () -> Unit) {
        scope.launch {
            loading = true
            error = ""
            try { operation() }
            catch (e: Exception) { error = e.message ?: "Unable to connect" }
            finally { loading = false }
        }
    }
    val now = LocalDate.now().toString()
    val visible = tasks.filter { task ->
        (projectFilter == null || task.projectId == projectFilter) &&
        (query.isBlank() || task.title.contains(query, ignoreCase = true) ||
            task.description.contains(query, ignoreCase = true) ||
            task.tags.any { it.contains(query, ignoreCase = true) }) &&
        when (view) {
            "Completed" -> task.done
            "Today" -> !task.done && task.dueDate != null && task.dueDate <= now
            "Upcoming" -> !task.done && task.dueDate != null && task.dueDate > now
            else -> !task.done
        }
    }
    Scaffold(topBar = { TopAppBar(title = { Text("GoreeCloud Tasks") }) }) { insets ->
        if (api == null) {
            Column(
                Modifier.fillMaxSize().padding(insets).verticalScroll(rememberScrollState())
                    .padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text("Private workspace", style = MaterialTheme.typography.headlineMedium)
                Text("Self-hosted. Clear by default.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (error.isNotBlank()) Text(error, color = MaterialTheme.colorScheme.error)
                GoreeCloudPanel(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                        OutlinedTextField(value = serverUrl, onValueChange = { serverUrl = it },
                            label = { Text("Server HTTPS URL") }, singleLine = true,
                            modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(value = token, onValueChange = { token = it },
                            label = { Text("API token") }, modifier = Modifier.fillMaxWidth(),
                            visualTransformation = PasswordVisualTransformation(), singleLine = true)
                        GoreeCloudAction(label = "Connect", enabled = !loading, onClick = {
                            execute {
                                val client = TaskApi(serverUrl.trim(), token)
                                reload(client)
                                api = client
                                token = ""
                            }
                        })
                        Text("No token is saved. Release builds require HTTPS. Debug emulators may use local 10.0.2.2.",
                            style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        } else {
            LazyColumn(
                Modifier.fillMaxSize().padding(insets),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 14.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                item {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("My tasks", style = MaterialTheme.typography.headlineMedium)
                        Text(tasks.count { !it.done }.toString() + " active tasks",
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                if (error.isNotBlank()) item {
                    Text(error, color = MaterialTheme.colorScheme.error)
                }
                item {
                    TextButton(enabled = !loading, onClick = {
                        execute {
                            reloadHabits(requireNotNull(api))
                            showHabits = true
                        }
                    }) { Text("Open daily habits") }
                }
                item {
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(listOf("Inbox", "Today", "Upcoming", "Completed")) { screen ->
                            FilterChip(selected = view == screen, onClick = { view = screen },
                                label = { Text(screen) })
                        }
                    }
                }
                item {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        var menu by remember { mutableStateOf(false) }
                        Box {
                            val name = projects.find { it.id == projectFilter }?.name ?: "All projects"
                            OutlinedButton(onClick = { menu = true }) { Text(name, maxLines = 1) }
                            DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                                DropdownMenuItem(text = { Text("All projects") }, onClick = {
                                    projectFilter = null; menu = false
                                })
                                projects.forEach { project ->
                                    DropdownMenuItem(text = { Text(project.name) }, onClick = {
                                        projectFilter = project.id; menu = false
                                    })
                                }
                            }
                        }
                        TextButton(onClick = { execute { reload(requireNotNull(api)) } },
                            enabled = !loading) { Text("Refresh") }
                    }
                    OutlinedTextField(value = query, onValueChange = { query = it },
                        label = { Text("Search tasks") }, modifier = Modifier.fillMaxWidth(),
                        singleLine = true)
                }
                item {
                    GoreeCloudPanel(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text("Plan a task", style = MaterialTheme.typography.titleMedium)
                            DraftFields(draft, { draft = it }, projects, tasks.filter { !it.done })
                            GoreeCloudAction(label = "Add task", enabled = !loading && draft.title.isNotBlank(),
                                onClick = {
                                    execute {
                                        val client = requireNotNull(api)
                                        client.createTask(draft.title, draft.description,
                                            draft.dueDate.ifBlank { null }, draft.priority,
                                            draft.projectId, draft.parentId, draft.recurrence, draft.tagsList())
                                        reload(client)
                                        draft = TaskDraft()
                                    }
                                })
                        }
                    }
                }
                item {
                    GoreeCloudPanel(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("Create project", style = MaterialTheme.typography.titleSmall)
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                OutlinedTextField(value = projectName, onValueChange = { projectName = it },
                                    label = { Text("Project name") }, singleLine = true,
                                    modifier = Modifier.weight(1f))
                                TextButton(enabled = !loading && projectName.isNotBlank(),
                                    onClick = {
                                        execute {
                                            val client = requireNotNull(api)
                                            client.createProject(projectName)
                                            reload(client)
                                            projectName = ""
                                        }
                                    }) { Text("Add") }
                            }
                        }
                    }
                }
                item {
                    Text(view + " · " + visible.size + " tasks",
                        style = MaterialTheme.typography.titleMedium)
                }
                items(visible, key = { it.id }) { task ->
                    GoreeCloudPanel(Modifier.fillMaxWidth()) {
                        Row(Modifier.fillMaxWidth().padding(12.dp),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Checkbox(checked = task.done, enabled = !loading,
                                onCheckedChange = {
                                    execute {
                                        val client = requireNotNull(api)
                                        if (task.done) client.reopenTask(task) else client.completeTask(task)
                                        reload(client)
                                    }
                                })
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                                TextButton(onClick = { selectedTask = task }) {
                                    Text(task.title, style = MaterialTheme.typography.titleMedium)
                                }
                                Text((task.parentId?.let { parentId -> tasks.find { it.id == parentId }?.title?.let { "↳ " + it + " · " } } ?: "") +
                                    (task.dueDate ?: "No due date") + " · P" + task.priority +
                                    (if (task.recurrence != "none") " · " + task.recurrence else ""),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                                if (task.tags.isNotEmpty()) {
                                    Text(task.tags.joinToString(" · ") { "#" + it },
                                        style = MaterialTheme.typography.labelSmall)
                                }
                            }
                        }
                    }
                }
                if (visible.isEmpty()) item {
                    Text("Nothing in this view.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                item {
                    TextButton(onClick = {
                        api = null; tasks = emptyList(); projects = emptyList()
                        selectedTask = null; query = ""; projectFilter = null
                        showHabits = false; habits = emptyList()
                        historyHabitId = null; historyDates = emptyList(); historyOffset = 0
                    }, enabled = !loading) { Text("Disconnect") }
                }
            }
        }
    }
    if (showHabits && api != null) {
        HabitsDialog(habits = habits, busy = loading, onDismiss = {
                showHabits = false; historyHabitId = null; historyDates = emptyList()
            }, historyHabitId = historyHabitId, historyDates = historyDates,
            historyOffset = historyOffset, historyHasMore = historyHasMore,
            historyError = error,
            onHistoryPage = { habit, offset ->
                if (offset < 0) {
                    historyHabitId = null; historyDates = emptyList()
                    historyOffset = 0; historyHasMore = false
                } else {
                    execute {
                        val dates = requireNotNull(api).habitHistory(habit.id, offset)
                        historyHabitId = habit.id
                        historyDates = dates
                        historyOffset = offset
                        historyHasMore = dates.size == 30
                    }
                }
            },
            onCreate = { name, notes ->
                execute {
                    val client = requireNotNull(api)
                    client.createHabit(name, notes)
                    reloadHabits(client)
                }
            },
            onUpdate = { habit, name, notes ->
                execute {
                    val client = requireNotNull(api)
                    client.editHabit(habit, name, notes)
                    reloadHabits(client)
                }
            },
            onCheckin = { habit ->
                execute {
                    val client = requireNotNull(api)
                    val day = LocalDate.now().toString()
                    if (habit.checkedInToday) client.undoCheckIn(habit, day)
                    else client.checkIn(habit, day)
                    reloadHabits(client)
                    if (historyHabitId == habit.id) {
                        historyHabitId = null; historyDates = emptyList()
                    }
                }
            },
            onDelete = { habit ->
                execute {
                    val client = requireNotNull(api)
                    client.deleteHabit(habit)
                    reloadHabits(client)
                    if (historyHabitId == habit.id) {
                        historyHabitId = null; historyDates = emptyList()
                    }
                }
            })
    }
    val edit = selectedTask
    if (edit != null && api != null) {
        EditTaskDialog(task = edit, projects = projects, tasks = tasks, loading = loading,
            onDismiss = { selectedTask = null },
            onSave = { form ->
                execute {
                    val client = requireNotNull(api)
                    client.updateTask(edit, form.title, form.description, form.dueDate.ifBlank { null },
                        form.priority, form.projectId, form.parentId, form.recurrence, form.tagsList())
                    reload(client)
                    selectedTask = null
                }
            },
            onDelete = {
                execute {
                    val client = requireNotNull(api)
                    client.deleteTask(edit)
                    reload(client)
                    selectedTask = null
                }
            })
    }
}
