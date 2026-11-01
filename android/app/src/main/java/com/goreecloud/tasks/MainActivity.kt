package com.goreecloud.tasks

import android.app.DatePickerDialog
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
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

private val Iris = Color(0xFF5145D9)
private val Ink = Color(0xFF20243A)
private val Canvas = Color(0xFFECF0F8)

@Composable
private fun TasksScreen(db: TasksDatabase) {
    val dark = androidx.compose.foundation.isSystemInDarkTheme()
    val colors = if (dark) darkColorScheme(
        primary = Color(0xFFC5BFFF), onPrimary = Color(0xFF241B66),
        background = Color(0xFF10131E), surface = Color(0xFF1D2231)
    ) else lightColorScheme(
        primary = Iris, onPrimary = Color.White,
        background = Canvas, surface = Color(0xFFF9FAFD), onSurface = Ink
    )
    MaterialTheme(colorScheme = colors) {
        val context = LocalContext.current
        val tasks = remember { mutableStateListOf<TaskRecord>().apply { addAll(db.listTasks()) } }
        val projects = remember { mutableStateListOf<ProjectRecord>().apply { addAll(db.listProjects()) } }
        var title by remember { mutableStateOf("") }
        var priority by remember { mutableIntStateOf(4) }
        var priorityMenu by remember { mutableStateOf(false) }
        var selectedProjectId by remember { mutableStateOf<String?>(null) }
        var projectMenu by remember { mutableStateOf(false) }
        var showProjectDialog by remember { mutableStateOf(false) }
        var newProjectName by remember { mutableStateOf("") }
        var dueDate by remember { mutableStateOf<String?>(null) }
        var view by remember { mutableStateOf("Open") }
        var search by remember { mutableStateOf("") }
        var error by remember { mutableStateOf("") }
        var deletion by remember { mutableStateOf<TaskRecord?>(null) }
        fun reload() {
            tasks.clear()
            tasks.addAll(db.listTasks())
            projects.clear()
            projects.addAll(db.listProjects())
        }
        val visible = TaskViews.select(tasks, view, LocalDate.now().toString(), selectedProjectId, search)
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
        Surface(color = MaterialTheme.colorScheme.background, modifier = Modifier.fillMaxSize()) {
            Column(modifier = Modifier.fillMaxSize().padding(horizontal = 18.dp, vertical = 18.dp)) {
                Text(
                    "✦  GOREECLOUD TASKS", color = MaterialTheme.colorScheme.primary,
                    fontSize = 13.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = 1.sp
                )
                Spacer(Modifier.height(18.dp))
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
                    shape = RoundedCornerShape(26.dp), modifier = Modifier.fillMaxWidth()
                ) {
                    Column(Modifier.padding(22.dp)) {
                        Text("Make space for", style = MaterialTheme.typography.headlineMedium,
                            fontWeight = FontWeight.SemiBold)
                        Text("what matters.", style = MaterialTheme.typography.headlineMedium,
                            fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(7.dp))
                        Text("Capture ideas. Take action. Stay in your flow.",
                            style = MaterialTheme.typography.bodySmall)
                        Spacer(Modifier.height(14.dp))
                        Text(
                            "${tasks.count { !it.completed }} open  ·  ${tasks.count { it.completed }} accomplished",
                            fontWeight = FontWeight.SemiBold, fontSize = 12.sp
                        )
                    }
                }
                Spacer(Modifier.height(16.dp))
                Text("Quick capture", style = MaterialTheme.typography.titleLarge,
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
                            reload()
                        } catch (failure: Exception) {
                            error = failure.message ?: "Task could not be saved."
                        }
                    }, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(14.dp)
                ) { Text("＋  Add task") }
                if (error.isNotBlank()) {
                    Text(error, color = MaterialTheme.colorScheme.error, fontSize = 12.sp)
                }
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = search, onValueChange = { search = it },
                    singleLine = true, label = { Text("Search tasks") },
                    modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(14.dp)
                )
                Spacer(Modifier.height(4.dp))
                LazyRow(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    items(TaskViews.names) { name ->
                        FilterChip(
                            selected = view == name, onClick = { view = name },
                            label = { Text(name) }
                        )
                    }
                }
                Spacer(Modifier.height(8.dp))
                if (visible.isEmpty()) {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(Modifier.padding(22.dp)) {
                            Text("All clear here ✦", fontWeight = FontWeight.Bold)
                            Text("Capture a task or choose a different view.",
                                style = MaterialTheme.typography.bodySmall)
                        }
                    }
                } else {
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                        contentPadding = PaddingValues(bottom = 24.dp)
                    ) {
                        items(visible, key = { it.id }) { task ->
                            Card(
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                shape = RoundedCornerShape(17.dp), modifier = Modifier.fillMaxWidth()
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 7.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Checkbox(checked = task.completed, onCheckedChange = {
                                        try { db.setCompleted(task.id, it); reload() }
                                        catch (failure: Exception) {
                                            error = failure.message ?: "Unable to save task."
                                        }
                                    })
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
                                    TextButton(onClick = { deletion = task }) { Text("Delete") }
                                }
                            }
                        }
                    }
                }
            }
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
        deletion?.let { task ->
            AlertDialog(
                onDismissRequest = { deletion = null },
                title = { Text("Delete task?") },
                text = { Text("This permanently removes \"${task.title}\" from this device.") },
                confirmButton = {
                    TextButton(onClick = {
                        try { db.delete(task.id); reload(); error = "" }
                        catch (failure: Exception) {
                            error = failure.message ?: "Unable to delete task."
                        }
                        deletion = null
                    }) { Text("Delete") }
                },
                dismissButton = {
                    TextButton(onClick = { deletion = null }) { Text("Cancel") }
                }
            )
        }
    }
}
