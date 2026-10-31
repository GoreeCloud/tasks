package com.goreecloud.tasks

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.UUID

private data class TaskRecord(val id: String, val title: String, val priority: Int, val completed: Boolean)

private class TasksDatabase(context: Context) : SQLiteOpenHelper(context, "goreecloud-tasks.db", null, 1) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT NOT NULL, priority INTEGER NOT NULL DEFAULT 4 CHECK(priority BETWEEN 1 AND 4), completed INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL)")
        db.execSQL("CREATE INDEX idx_tasks_priority ON tasks(completed, priority, created_at)")
    }
    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // No destructive upgrade: future schema migrations must be explicitly versioned.
    }
    fun list(): List<TaskRecord> {
        val rows = mutableListOf<TaskRecord>()
        readableDatabase.rawQuery("SELECT id,title,priority,completed FROM tasks ORDER BY completed ASC,priority ASC,created_at DESC", null).use { cursor ->
            while (cursor.moveToNext()) {
                rows.add(TaskRecord(cursor.getString(0), cursor.getString(1), cursor.getInt(2), cursor.getInt(3) == 1))
            }
        }
        return rows
    }
    fun add(title: String, priority: Int) {
        val normalized = title.trim()
        require(normalized.isNotEmpty() && normalized.length <= 240) { "Task title must be 1–240 characters" }
        require(priority in 1..4) { "Invalid priority" }
        val record = ContentValues().apply {
            put("id", UUID.randomUUID().toString())
            put("title", normalized)
            put("priority", priority)
            put("completed", 0)
            put("created_at", System.currentTimeMillis())
        }
        writableDatabase.insertOrThrow("tasks", null, record)
    }
    fun setCompleted(id: String, value: Boolean) {
        val changes = ContentValues().apply { put("completed", if (value) 1 else 0) }
        writableDatabase.update("tasks", changes, "id=?", arrayOf(id))
    }
    fun delete(id: String) { writableDatabase.delete("tasks", "id=?", arrayOf(id)) }
}

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
    val scheme = if (dark) darkColorScheme(primary = Color(0xFFC5BFFF), onPrimary = Color(0xFF241B66), background = Color(0xFF10131E), surface = Color(0xFF1D2231))
                 else lightColorScheme(primary = Iris, onPrimary = Color.White, background = Canvas, surface = Color(0xFFF9FAFD), onSurface = Ink)
    MaterialTheme(colorScheme = scheme) {
        val tasks = remember { mutableStateListOf<TaskRecord>().apply { addAll(db.list()) } }
        var title by remember { mutableStateOf("") }
        var priority by remember { mutableIntStateOf(4) }
        var priorityMenu by remember { mutableStateOf(false) }
        var filter by remember { mutableStateOf("Open") }
        var message by remember { mutableStateOf("") }
        fun reload() { tasks.clear(); tasks.addAll(db.list()) }
        val visible = tasks.filter { when (filter) {
            "Completed" -> it.completed
            "Priority" -> !it.completed && it.priority <= 2
            else -> !it.completed
        } }
        Surface(color = MaterialTheme.colorScheme.background, modifier = Modifier.fillMaxSize()) {
            Column(modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 24.dp)) {
                Text("✦  GOREECLOUD TASKS", color = MaterialTheme.colorScheme.primary, fontSize = 13.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = 1.sp)
                Spacer(Modifier.height(24.dp))
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
                    shape = RoundedCornerShape(28.dp), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(25.dp)) {
                        Text("Make space for", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.SemiBold)
                        Text("what matters.", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(9.dp))
                        Text("Capture ideas. Take action. Stay in your flow.", style = MaterialTheme.typography.bodyMedium)
                        Spacer(Modifier.height(18.dp))
                        Text(tasks.count { !it.completed }.toString() + " open  ·  " + tasks.count { it.completed } + " accomplished", fontWeight = FontWeight.SemiBold, fontSize = 12.sp)
                    }
                }
                Spacer(Modifier.height(22.dp))
                Text("Quick capture", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(10.dp))
                OutlinedTextField(value = title, onValueChange = { if (it.length <= 240) title = it }, singleLine = true,
                    label = { Text("What needs to get done?") }, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box {
                        OutlinedButton(onClick = { priorityMenu = true }) { Text("P" + priority + "  ▾") }
                        DropdownMenu(expanded = priorityMenu, onDismissRequest = { priorityMenu = false }) {
                            (1..4).forEach { p -> DropdownMenuItem(text = { Text("P" + p) }, onClick = { priority = p; priorityMenu = false }) }
                        }
                    }
                    Button(onClick = {
                        if (title.trim().isEmpty()) message = "Enter a task title."
                        else try { db.add(title, priority); title = ""; message = ""; reload() }
                        catch (e: Exception) { message = e.message ?: "Could not add task" }
                    }, modifier = Modifier.weight(1f), shape = RoundedCornerShape(14.dp)) { Text("＋  Add task") }
                }
                if (message.isNotBlank()) { Text(message, color = MaterialTheme.colorScheme.error, fontSize = 12.sp) }
                Spacer(Modifier.height(17.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    listOf("Open", "Priority", "Completed").forEach { option ->
                        FilterChip(selected = filter == option, onClick = { filter = option }, label = { Text(option) })
                    }
                }
                Spacer(Modifier.height(7.dp))
                if (visible.isEmpty()) {
                    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(24.dp)) {
                            Text("All clear here ✦", fontWeight = FontWeight.Bold)
                            Text("Add a task to begin.", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                } else {
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(9.dp), contentPadding = PaddingValues(bottom = 24.dp)) {
                        items(visible, key = { it.id }) { task ->
                            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) {
                                Row(modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                                    Checkbox(checked = task.completed, onCheckedChange = { db.setCompleted(task.id, it); reload() })
                                    Column(Modifier.weight(1f).padding(start = 8.dp)) {
                                        Text(task.title, maxLines = 3, overflow = TextOverflow.Ellipsis, fontWeight = FontWeight.SemiBold)
                                        Text("Priority " + task.priority, color = MaterialTheme.colorScheme.primary, fontSize = 12.sp)
                                    }
                                    TextButton(onClick = { db.delete(task.id); reload() }) { Text("Delete") }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
