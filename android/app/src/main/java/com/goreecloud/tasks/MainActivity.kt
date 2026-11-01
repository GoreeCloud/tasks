package com.goreecloud.tasks

import android.app.DatePickerDialog
import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.time.LocalDate
import java.util.Locale

/** Standalone first-party Android UI; never embeds the browser application. */
class MainActivity : ComponentActivity() {
    private lateinit var database: TasksDatabase

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        database = TasksDatabase(applicationContext)
        setContent { TasksScreen(database) }
    }

    override fun onDestroy() {
        database.close()
        super.onDestroy()
    }
}

@Composable
private fun TasksScreen(db: TasksDatabase) {
    val context = LocalContext.current
    val prefs = remember(context) {
        context.getSharedPreferences("goreecloud-tasks-appearance", Context.MODE_PRIVATE)
    }
    var appearance by remember { mutableStateOf(TasksTheme.appearance(prefs.getString("appearance", null))) }
    var accent by remember { mutableStateOf(TasksTheme.accent(prefs.getString("accent", null))) }
    var showAppearanceSettings by remember { mutableStateOf(false) }
    var draftAppearance by remember { mutableStateOf("light") }
    var draftAccent by remember { mutableStateOf("neutral") }
    MaterialTheme(colorScheme = TasksTheme.scheme(appearance, accent)) {
        val tasks = remember { mutableStateListOf<TaskRecord>().apply { addAll(db.listTasks()) } }
        val projects = remember { mutableStateListOf<ProjectRecord>().apply { addAll(db.listProjects()) } }
        val deletedTasks = remember { mutableStateListOf<TaskRecord>().apply { addAll(db.listDeletedTasks()) } }
        var title by remember { mutableStateOf("") }
        var priority by remember { mutableIntStateOf(4) }
        var priorityMenu by remember { mutableStateOf(false) }
        var selectedProjectId by remember { mutableStateOf<String?>(null) }
        var projectMenu by remember { mutableStateOf(false) }
        var showProjectDialog by remember { mutableStateOf(false) }
        var newProjectName by remember { mutableStateOf("") }
        var dueDate by remember { mutableStateOf<String?>(null) }
        var view by remember { mutableStateOf("Open") }
        var showCapture by remember { mutableStateOf(false) }
        var showTools by remember { mutableStateOf(false) }
        var showBrowse by remember { mutableStateOf(false) }
        val searchFocusRequester = remember { FocusRequester() }
        val keyboardController = LocalSoftwareKeyboardController.current
        var focusSearchAfterCapture by remember { mutableStateOf(false) }
        LaunchedEffect(showCapture, focusSearchAfterCapture) {
            if (!showCapture && focusSearchAfterCapture) {
                searchFocusRequester.requestFocus()
                keyboardController?.show()
                focusSearchAfterCapture = false
            }
        }
        var search by remember { mutableStateOf("") }
        var priorityFilter by remember { mutableStateOf<Int?>(null) }
        var priorityFilterMenu by remember { mutableStateOf(false) }
        var sortBy by remember { mutableStateOf("Smart") }
        var sortMenu by remember { mutableStateOf(false) }
        val selectedTaskIds = remember { mutableStateListOf<String>() }
        var bulkPriority by remember { mutableIntStateOf(4) }
        var bulkPriorityMenu by remember { mutableStateOf(false) }
        var bulkProjectId by remember { mutableStateOf<String?>(null) }
        var bulkProjectMenu by remember { mutableStateOf(false) }
        var pendingBulkTrash by remember { mutableStateOf<List<String>?>(null) }
        var error by remember { mutableStateOf("") }
        var backupNotice by remember { mutableStateOf("") }
        var preparedBackup by remember { mutableStateOf<ByteArray?>(null) }
        var pendingRestore by remember { mutableStateOf<RestoreSnapshot?>(null) }
        val importLauncher = rememberLauncherForActivityResult(
            ActivityResultContracts.OpenDocument()
        ) { document ->
            if (document != null) {
                try {
                    require(db.isEmptyForRestore()) {
                        "Restore requires an empty workspace. Export current tasks first."
                    }
                    val stream = context.contentResolver.openInputStream(document)
                        ?: throw IllegalStateException("Could not read selected document.")
                    val snapshot = stream.use { PortableRestore.parse(PortableRestore.readLimited(it)) }
                    pendingRestore = snapshot
                    error = ""
                    backupNotice = ""
                } catch (failure: Exception) {
                    pendingRestore = null
                    error = failure.message ?: "Backup could not be validated."
                }
            }
        }
        val exportLauncher = rememberLauncherForActivityResult(
            ActivityResultContracts.CreateDocument("application/json")
        ) { document ->
            val bytes = preparedBackup
            preparedBackup = null
            if (document != null && bytes != null) {
                try {
                    val stream = context.contentResolver.openOutputStream(document, "w")
                        ?: throw IllegalStateException("Could not open selected document.")
                    stream.use { it.write(bytes); it.flush() }
                    error = ""
                    backupNotice = "Backup exported. Local Trash is not included. Keep this private."
                } catch (failure: Exception) {
                    error = failure.message ?: "Could not write backup."
                    backupNotice = ""
                }
            }
        }
        var editing by remember { mutableStateOf<TaskRecord?>(null) }
        var editTitle by remember { mutableStateOf("") }
        var editPriority by remember { mutableIntStateOf(4) }
        var editDueDate by remember { mutableStateOf<String?>(null) }
        var editProjectId by remember { mutableStateOf<String?>(null) }
        var editPriorityMenu by remember { mutableStateOf(false) }
        var editProjectMenu by remember { mutableStateOf(false) }
        var deletion by remember { mutableStateOf<TaskRecord?>(null) }
        fun reload() {
            tasks.clear()
            tasks.addAll(db.listTasks())
            projects.clear()
            projects.addAll(db.listProjects())
            deletedTasks.clear()
            deletedTasks.addAll(db.listDeletedTasks())
        }
        LaunchedEffect(view, search, selectedProjectId, priorityFilter, sortBy) {
            selectedTaskIds.clear()
        }
        val visible = if (view == "Trash") {
            deletedTasks.filter {
                search.isBlank() || it.title.contains(search.trim(), ignoreCase = true)
            }
        } else TaskViews.select(tasks, view, LocalDate.now().toString(), selectedProjectId, search,
            priorityFilter, sortBy)
        val visibleIds = if (view == "Trash") emptySet() else visible.map { it.id }.toSet()
        val batchIds = selectedTaskIds.filter { it in visibleIds }
        fun applyBulk(action: String, value: String? = null) {
            try {
                val count = db.bulkEdit(batchIds, action, value)
                selectedTaskIds.clear()
                error = ""
                backupNotice = "Updated $count tasks on this device."
                reload()
            } catch (failure: Exception) {
                error = failure.message ?: "Bulk action failed; nothing was saved."
            }
        }
        val activeProjectName = projects.find { it.id == selectedProjectId }?.name ?: "Inbox"
        val chooseDate = {
            val initial = dueDate?.let { runCatching { LocalDate.parse(it) }.getOrNull() } ?: LocalDate.now()
            DatePickerDialog(
                context,
                { _, year, month, day ->
                    dueDate = String.format(Locale.ROOT, "%04d-%02d-%02d", year, month + 1, day)
                },
                initial.year, initial.monthValue - 1, initial.dayOfMonth
            ).show()
        }
        Scaffold(
            containerColor = MaterialTheme.colorScheme.background,
            bottomBar = {
                NavigationBar(containerColor = MaterialTheme.colorScheme.surface) {
                    NavigationBarItem(selected = TasksNavigation.tabFor(view) == "Today",
                        onClick = { view = "Today"; showCapture = false },
                        icon = { Text("◷") }, label = { Text("Today") })
                    NavigationBarItem(selected = TasksNavigation.tabFor(view) == "Inbox",
                        onClick = { view = "Open"; showCapture = false },
                        icon = { Text("▣") }, label = { Text("Inbox") })
                    NavigationBarItem(selected = false, onClick = {
                        if (showCapture) {
                            focusSearchAfterCapture = true
                            showCapture = false
                        } else {
                            searchFocusRequester.requestFocus()
                            keyboardController?.show()
                        }
                    }, icon = { Text("⌕") }, label = { Text("Search") })
                    NavigationBarItem(selected = showBrowse || TasksNavigation.tabFor(view) == "Browse",
                        onClick = { showCapture = false; showBrowse = true },
                        icon = { Text("☷") }, label = { Text("Browse") })
                }
            },
            floatingActionButton = {
                if (view != "Trash") {
                    FloatingActionButton(
                        onClick = { showCapture = !showCapture },
                        containerColor = MaterialTheme.colorScheme.primary,
                        contentColor = MaterialTheme.colorScheme.onPrimary,
                        modifier = Modifier.semantics {
                            contentDescription = if (showCapture) "Close task composer" else "Add task"
                        }
                    ) { Text(if (showCapture) "×" else "+", fontSize = 28.sp) }
                }
            }
        ) { insets ->
            Column(modifier = Modifier.fillMaxSize().padding(insets)
                .padding(horizontal = 16.dp, vertical = 12.dp)) {
                Row(modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("✦  GOREECLOUD TASKS", color = MaterialTheme.colorScheme.primary,
                        fontSize = 13.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = 1.sp)
                    TextButton(onClick = { showTools = !showTools }) {
                        Text(if (showTools) "Close settings" else "Settings")
                    }
                }
                Spacer(Modifier.height(12.dp))
                Text(TasksNavigation.title(view, activeProjectName),
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold)
                Text("${tasks.count { !it.completed }} open · ${tasks.count { it.completed }} completed · On this device",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(12.dp))
                if (showTools) {
                    OutlinedButton(onClick = {
                        draftAppearance = appearance
                        draftAccent = accent
                        showAppearanceSettings = true
                    }, modifier = Modifier.fillMaxWidth()) { Text("Appearance & color") }
                OutlinedButton(
                    onClick = {
                        try {
                            preparedBackup = db.exportPortableBackup()
                            backupNotice = ""
                            exportLauncher.launch("goreecloud-tasks-backup.json")
                        } catch (failure: Exception) {
                            error = failure.message ?: "Backup cannot be exported."
                            backupNotice = ""
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
                ) { Text("Export private JSON backup") }
                OutlinedButton(
                    onClick = {
                        try {
                            require(db.isEmptyForRestore()) {
                                "Import only works in an empty workspace. Export your tasks first."
                            }
                            error = ""
                            importLauncher.launch(arrayOf("application/json", "text/plain", "application/octet-stream"))
                        } catch (failure: Exception) {
                            error = failure.message ?: "Cannot import into this workspace."
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
                ) { Text("Import JSON into empty workspace") }
                }
                if (backupNotice.isNotBlank()) {
                    // Backup status stays visible after closing Settings.
                    Text(backupNotice, style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary)
                }
                if (showCapture && view != "Trash") {
                    Column(modifier = Modifier.weight(1f)
                        .verticalScroll(rememberScrollState())) {
                Spacer(Modifier.height(12.dp))
                Text("Add task", style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = title, onValueChange = { if (it.length <= 240) title = it },
                    singleLine = true, label = { Text("What needs to get done?") },
                    modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(15.dp)
                )
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically) {
                    Box(modifier = Modifier.weight(1f)) {
                        OutlinedButton(
                            onClick = { projectMenu = true }, modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(activeProjectName, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                        DropdownMenu(expanded = projectMenu, onDismissRequest = { projectMenu = false }) {
                            DropdownMenuItem(text = { Text("Inbox") }, onClick = {
                                selectedProjectId = null; projectMenu = false
                            })
                            projects.forEach { project ->
                                DropdownMenuItem(text = { Text(project.name) }, onClick = {
                                    selectedProjectId = project.id; projectMenu = false
                                })
                            }
                        }
                    }
                    OutlinedButton(onClick = { showProjectDialog = true }) { Text("+ Project") }
                }
                Row(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box {
                        OutlinedButton(onClick = { priorityMenu = true }) { Text("P$priority ▾") }
                        DropdownMenu(expanded = priorityMenu, onDismissRequest = { priorityMenu = false }) {
                            (1..4).forEach { level ->
                                DropdownMenuItem(text = { Text("P$level") }, onClick = {
                                    priority = level; priorityMenu = false
                                })
                            }
                        }
                    }
                    OutlinedButton(onClick = chooseDate, modifier = Modifier.weight(1f)) {
                        Text(dueDate ?: "Due date", maxLines = 1)
                    }
                    if (dueDate != null) TextButton(onClick = { dueDate = null }) { Text("Clear") }
                }
                Button(
                    onClick = {
                        try {
                            db.add(title, priority, dueDate, selectedProjectId)
                            title = ""
                            dueDate = null
                            error = ""
                            showCapture = false
                            reload()
                        } catch (failure: Exception) {
                            error = failure.message ?: "Task could not be saved."
                        }
                    }, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(14.dp)
                ) { Text("＋  Add task") }
                if (error.isNotBlank()) {
                    Text(error, color = MaterialTheme.colorScheme.error, fontSize = 12.sp)
                }
                    }
                } else {
                    if (error.isNotBlank()) {
                        Text(error, color = MaterialTheme.colorScheme.error, fontSize = 12.sp)
                    }
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = search, onValueChange = { search = it },
                    singleLine = true, label = { Text("Search tasks") },
                    modifier = Modifier.fillMaxWidth().focusRequester(searchFocusRequester), shape = RoundedCornerShape(14.dp)
                )
                Spacer(Modifier.height(4.dp))
                LazyRow(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    items(TaskViews.names + "Trash") { name ->
                        FilterChip(
                            selected = view == name, onClick = { view = name },
                            label = { Text(name) }
                        )
                    }
                }
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxWidth()) {
                    Box(modifier = Modifier.weight(1f)) {
                        OutlinedButton(onClick = { priorityFilterMenu = true },
                            enabled = view != "Trash", modifier = Modifier.fillMaxWidth()) {
                            Text(priorityFilter?.let { "Filter P$it" } ?: "All priorities", maxLines = 1)
                        }
                        DropdownMenu(expanded = priorityFilterMenu,
                            onDismissRequest = { priorityFilterMenu = false }) {
                            DropdownMenuItem(text = { Text("All priorities") }, onClick = {
                                priorityFilter = null; priorityFilterMenu = false
                            })
                            (1..4).forEach { level ->
                                DropdownMenuItem(text = { Text("P$level") }, onClick = {
                                    priorityFilter = level; priorityFilterMenu = false
                                })
                            }
                        }
                    }
                    Box(modifier = Modifier.weight(1f)) {
                        OutlinedButton(onClick = { sortMenu = true }, enabled = view != "Trash",
                            modifier = Modifier.fillMaxWidth()) { Text("Sort: $sortBy", maxLines = 1) }
                        DropdownMenu(expanded = sortMenu, onDismissRequest = { sortMenu = false }) {
                            listOf("Smart", "Due date", "Title").forEach { mode ->
                                DropdownMenuItem(text = { Text(mode) }, onClick = {
                                    sortBy = mode; sortMenu = false
                                })
                            }
                        }
                    }
                }
                if (view != "Trash") {
                    Row(verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("${batchIds.size} selected", style = MaterialTheme.typography.bodySmall)
                        TextButton(onClick = {
                            if (visible.size <= 200) {
                                selectedTaskIds.clear()
                                selectedTaskIds.addAll(visible.map { it.id })
                            } else error = "Select at most 200 tasks; narrow the view first."
                        }) { Text("Select visible") }
                        TextButton(onClick = { selectedTaskIds.clear() },
                            enabled = batchIds.isNotEmpty()) { Text("Clear") }
                    }
                    if (batchIds.isNotEmpty()) {
                        Row(modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(onClick = { applyBulk("complete") }) { Text("Complete") }
                            OutlinedButton(onClick = { applyBulk("reopen") }) { Text("Reopen") }
                            Box {
                                OutlinedButton(onClick = { bulkPriorityMenu = true }) {
                                    Text("P$bulkPriority ▾")
                                }
                                DropdownMenu(expanded = bulkPriorityMenu,
                                    onDismissRequest = { bulkPriorityMenu = false }) {
                                    (1..4).forEach { level ->
                                        DropdownMenuItem(text = { Text("P$level") }, onClick = {
                                            bulkPriority = level
                                            bulkPriorityMenu = false
                                        })
                                    }
                                }
                            }
                            OutlinedButton(onClick = {
                                applyBulk("priority", bulkPriority.toString())
                            }) { Text("Apply priority") }
                            Box {
                                OutlinedButton(onClick = { bulkProjectMenu = true }) {
                                    Text(projects.find { it.id == bulkProjectId }?.name ?: "Inbox",
                                        maxLines = 1)
                                }
                                DropdownMenu(expanded = bulkProjectMenu,
                                    onDismissRequest = { bulkProjectMenu = false }) {
                                    DropdownMenuItem(text = { Text("Inbox") }, onClick = {
                                        bulkProjectId = null; bulkProjectMenu = false
                                    })
                                    projects.forEach { project ->
                                        DropdownMenuItem(text = { Text(project.name) }, onClick = {
                                            bulkProjectId = project.id; bulkProjectMenu = false
                                        })
                                    }
                                }
                            }
                            OutlinedButton(onClick = { applyBulk("project", bulkProjectId) }) {
                                Text("Move to project")
                            }
                            OutlinedButton(onClick = { pendingBulkTrash = batchIds.toList() }) {
                                Text("Move to Trash")
                            }
                        }
                    }
                }
                Spacer(Modifier.height(8.dp))
                if (visible.isEmpty()) {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(Modifier.padding(22.dp)) {
                            Text(if (view == "Trash") "Trash is empty ✦" else "All clear here ✦",
                                fontWeight = FontWeight.Bold)
                            Text(if (view == "Trash") "Deleted tasks remain recoverable on this device."
                                else "Capture a task or choose a different view.",
                                style = MaterialTheme.typography.bodySmall)
                        }
                    }
                } else {
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(4.dp),
                        contentPadding = PaddingValues(bottom = 24.dp)
                    ) {
                        items(visible, key = { it.id }) { task ->
                            Card(
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                shape = RoundedCornerShape(10.dp), modifier = Modifier.fillMaxWidth()
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 7.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    if (view != "Trash") {
                                        Checkbox(
                                            checked = task.id in batchIds,
                                            onCheckedChange = { checked ->
                                                if (checked && task.id !in selectedTaskIds) {
                                                    if (selectedTaskIds.size < 200) selectedTaskIds.add(task.id)
                                                    else error = "Selection is limited to 200 tasks."
                                                } else if (!checked) selectedTaskIds.remove(task.id)
                                            },
                                            modifier = Modifier.semantics {
                                                contentDescription = "Select ${task.title} for bulk actions"
                                            }
                                        )
                                        Checkbox(checked = task.completed, onCheckedChange = {
                                            try { db.setCompleted(task.id, it); reload() }
                                            catch (failure: Exception) {
                                                error = failure.message ?: "Unable to save task."
                                            }
                                        }, modifier = Modifier.semantics {
                                            contentDescription = if (task.completed) "Reopen ${task.title}" else "Complete ${task.title}"
                                        })
                                    }
                                    Column(Modifier.weight(1f).padding(start = 5.dp)) {
                                        Text(
                                            task.title, maxLines = 3,
                                            overflow = TextOverflow.Ellipsis,
                                            fontWeight = FontWeight.SemiBold
                                        )
                                        val detail = buildList {
                                            add("P${task.priority}")
                                            task.dueDate?.let { add("Due $it") }
                                            projects.find { it.id == task.projectId }?.let { add(it.name) }
                                        }.joinToString(" · ")
                                        Text(detail, color = MaterialTheme.colorScheme.primary,
                                            fontSize = 12.sp)
                                    }
                                    if (view == "Trash") {
                                        TextButton(onClick = {
                                            try {
                                                if (db.restoreDeletedTask(task.id)) {
                                                    error = ""
                                                    backupNotice = "Restored task from local Trash."
                                                } else error = "Task is no longer in Trash."
                                                reload()
                                            } catch (failure: Exception) {
                                                error = failure.message ?: "Could not restore task."
                                            }
                                        }) { Text("Restore") }
                                    } else {
                                        var actionsOpen by remember(task.id) { mutableStateOf(false) }
                                        Box {
                                            TextButton(onClick = { actionsOpen = true },
                                                modifier = Modifier.semantics {
                                                    contentDescription = "Actions for ${task.title}"
                                                }) { Text("⋯", fontSize = 22.sp) }
                                            DropdownMenu(expanded = actionsOpen,
                                                onDismissRequest = { actionsOpen = false }) {
                                                DropdownMenuItem(text = { Text("Edit task") }, onClick = {
                                                    actionsOpen = false
                                                    editing = task
                                                    editTitle = task.title
                                                    editPriority = task.priority
                                                    editDueDate = task.dueDate
                                                    editProjectId = task.projectId
                                                })
                                                DropdownMenuItem(text = { Text("Move to Trash") }, onClick = {
                                                    actionsOpen = false
                                                    deletion = task
                                                })
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                }
            }
        }

        if (showBrowse) {
            AlertDialog(
                onDismissRequest = { showBrowse = false },
                title = { Text("Browse tasks") },
                text = {
                    Column(modifier = Modifier.heightIn(max = 460.dp)
                        .verticalScroll(rememberScrollState())) {
                        (TaskViews.names + "Trash").distinct().forEach { destination ->
                            TextButton(onClick = {
                                view = destination
                                showBrowse = false
                            }, modifier = Modifier.fillMaxWidth()) {
                                Text(if (destination == "Open") "Inbox" else destination)
                            }
                        }
                        HorizontalDivider()
                        Text("Projects", style = MaterialTheme.typography.titleSmall)
                        projects.forEach { project ->
                            TextButton(onClick = {
                                selectedProjectId = project.id
                                view = "Project"
                                showBrowse = false
                            }, modifier = Modifier.fillMaxWidth()) { Text(project.name) }
                        }
                        TextButton(onClick = {
                            showBrowse = false
                            showProjectDialog = true
                        }) { Text("+ Create project") }
                    }
                },
                confirmButton = {
                    TextButton(onClick = { showBrowse = false }) { Text("Close") }
                }
            )
        }

        if (showAppearanceSettings) {
            AlertDialog(
                onDismissRequest = { showAppearanceSettings = false },
                title = { Text("Appearance & color") },
                text = {
                    Column(
                        modifier = Modifier.heightIn(max = 420.dp).verticalScroll(rememberScrollState()),
                        verticalArrangement = Arrangement.spacedBy(5.dp)
                    ) {
                        Text("Appearance", style = MaterialTheme.typography.titleSmall)
                        TasksTheme.appearances.forEach { choice ->
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                RadioButton(
                                    selected = draftAppearance == choice,
                                    onClick = { draftAppearance = choice }
                                )
                                Text(choice.replaceFirstChar { it.uppercase() })
                            }
                        }
                        Spacer(Modifier.height(7.dp))
                        Text("Accent", style = MaterialTheme.typography.titleSmall)
                        TasksTheme.accents.forEach { choice ->
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                RadioButton(
                                    selected = draftAccent == choice,
                                    onClick = { draftAccent = choice }
                                )
                                Text(choice.replaceFirstChar { it.uppercase() })
                            }
                        }
                        Text("Stored on this device only. Tasks and backups are unchanged.",
                            style = MaterialTheme.typography.bodySmall)
                    }
                },
                confirmButton = {
                    TextButton(onClick = {
                        val stored = prefs.edit()
                            .putString("appearance", draftAppearance)
                            .putString("accent", draftAccent)
                            .commit()
                        appearance = draftAppearance
                        accent = draftAccent
                        showAppearanceSettings = false
                        backupNotice = if (stored) "Appearance saved on this device."
                            else "Appearance applied, but preference saving failed."
                    }) { Text("Save appearance") }
                },
                dismissButton = {
                    TextButton(onClick = { showAppearanceSettings = false }) { Text("Cancel") }
                }
            )
        }

        pendingBulkTrash?.let { original ->
            AlertDialog(
                onDismissRequest = { pendingBulkTrash = null },
                title = { Text("Move ${original.size} tasks to Trash?") },
                text = { Text("These tasks can be restored individually from local Trash.") },
                confirmButton = {
                    TextButton(onClick = {
                        if (batchIds != original) {
                            error = "Selection changed; review the tasks and try again."
                        } else {
                            applyBulk("trash")
                        }
                        pendingBulkTrash = null
                    }) { Text("Move to Trash") }
                },
                dismissButton = {
                    TextButton(onClick = { pendingBulkTrash = null }) { Text("Cancel") }
                }
            )
        }

        pendingRestore?.let { snapshot ->
            AlertDialog(
                onDismissRequest = { pendingRestore = null },
                title = { Text("Import task backup?") },
                text = {
                    Text(
                        "This validated backup contains ${snapshot.tasks.size} tasks and " +
                            "${snapshot.projects.size} projects. It can only be restored " +
                            "into an empty workspace. No existing tasks will be replaced."
                    )
                },
                confirmButton = {
                    TextButton(onClick = {
                        try {
                            db.restorePortableBackup(snapshot)
                            pendingRestore = null
                            selectedProjectId = null
                            reload()
                            error = ""
                            backupNotice = "Imported ${snapshot.tasks.size} tasks and " +
                                "${snapshot.projects.size} projects. Verify your data."
                        } catch (failure: Exception) {
                            error = failure.message ?: "Restore failed; no changes committed."
                            pendingRestore = null
                        }
                    }) { Text("Import") }
                },
                dismissButton = {
                    TextButton(onClick = { pendingRestore = null }) { Text("Cancel") }
                }
            )
        }

        if (showProjectDialog) {
            AlertDialog(
                onDismissRequest = { showProjectDialog = false },
                title = { Text("Create project") },
                text = {
                    OutlinedTextField(
                        value = newProjectName,
                        onValueChange = { if (it.length <= 100) newProjectName = it },
                        label = { Text("Project name") },
                        singleLine = true
                    )
                },
                confirmButton = {
                    TextButton(onClick = {
                        try {
                            val id = db.addProject(newProjectName)
                            reload()
                            selectedProjectId = id
                            newProjectName = ""
                            showProjectDialog = false
                            error = ""
                        } catch (failure: Exception) {
                            error = failure.message ?: "Could not create project."
                        }
                    }) { Text("Create") }
                },
                dismissButton = {
                    TextButton(onClick = { showProjectDialog = false }) { Text("Cancel") }
                }
            )
        }
        editing?.let { task ->
            AlertDialog(
                onDismissRequest = { editing = null },
                title = { Text("Edit task") },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = editTitle,
                            onValueChange = { if (it.length <= 240) editTitle = it },
                            label = { Text("Task title") }, singleLine = true
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            Box {
                                OutlinedButton(onClick = { editPriorityMenu = true }) {
                                    Text("P$editPriority ▾")
                                }
                                DropdownMenu(
                                    expanded = editPriorityMenu,
                                    onDismissRequest = { editPriorityMenu = false }
                                ) {
                                    (1..4).forEach { level ->
                                        DropdownMenuItem(text = { Text("P$level") }, onClick = {
                                            editPriority = level
                                            editPriorityMenu = false
                                        })
                                    }
                                }
                            }
                            Box {
                                OutlinedButton(onClick = { editProjectMenu = true }) {
                                    val name = projects.find { it.id == editProjectId }?.name ?: "Inbox"
                                    Text(name, maxLines = 1)
                                }
                                DropdownMenu(
                                    expanded = editProjectMenu,
                                    onDismissRequest = { editProjectMenu = false }
                                ) {
                                    DropdownMenuItem(text = { Text("Inbox") }, onClick = {
                                        editProjectId = null
                                        editProjectMenu = false
                                    })
                                    projects.forEach { project ->
                                        DropdownMenuItem(text = { Text(project.name) }, onClick = {
                                            editProjectId = project.id
                                            editProjectMenu = false
                                        })
                                    }
                                }
                            }
                        }
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            TextButton(onClick = {
                                val initial = editDueDate?.let {
                                    runCatching { LocalDate.parse(it) }.getOrNull()
                                } ?: LocalDate.now()
                                DatePickerDialog(
                                    context,
                                    { _, year, month, day ->
                                        editDueDate = String.format(
                                            Locale.ROOT, "%04d-%02d-%02d", year, month + 1, day
                                        )
                                    },
                                    initial.year, initial.monthValue - 1, initial.dayOfMonth
                                ).show()
                            }) { Text(editDueDate ?: "Choose due date") }
                            if (editDueDate != null) TextButton(onClick = {
                                editDueDate = null
                            }) { Text("Clear") }
                        }
                    }
                },
                confirmButton = {
                    TextButton(onClick = {
                        try {
                            db.update(task.id, editTitle, editPriority, editDueDate, editProjectId)
                            reload()
                            editing = null
                            error = ""
                        } catch (failure: Exception) {
                            error = failure.message ?: "Unable to update task"
                        }
                    }) { Text("Save") }
                },
                dismissButton = {
                    TextButton(onClick = { editing = null }) { Text("Cancel") }
                }
            )
        }
        deletion?.let { task ->
            AlertDialog(
                onDismissRequest = { deletion = null },
                title = { Text("Move task to Trash?") },
                text = { Text("You can restore \"${task.title}\" from local Trash.") },
                confirmButton = {
                    TextButton(onClick = {
                        try {
                            if (db.delete(task.id)) {
                                error = ""
                                backupNotice = "Task moved to local Trash."
                            } else error = "Task no longer exists."
                            reload()
                        }
                        catch (failure: Exception) {
                            error = failure.message ?: "Unable to delete task."
                        }
                        deletion = null
                    }) { Text("Move to Trash") }
                },
                dismissButton = {
                    TextButton(onClick = { deletion = null }) { Text("Cancel") }
                }
            )
        }
    }
}
