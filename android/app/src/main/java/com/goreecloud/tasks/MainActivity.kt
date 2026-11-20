package com.goreecloud.tasks

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
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

class MainActivity:ComponentActivity() {
    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { GoreeCloudExpressiveTheme(accent=GoreeAccent.Iris) { TasksScreen() } }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TasksScreen() {
    var serverUrl by remember {mutableStateOf("https://")}
    var token by remember {mutableStateOf("")}
    var api by remember {mutableStateOf<TaskApi?>(null)}
    var tasks by remember {mutableStateOf<List<TaskItem>>(emptyList())}
    var title by remember {mutableStateOf("")}
    var due by remember {mutableStateOf("")}
    var error by remember {mutableStateOf("")}
    var loading by remember {mutableStateOf(false)}
    val scope=rememberCoroutineScope()
    fun execute(operation:suspend ()->Unit) {
        scope.launch {
            loading=true;error=""
            try {operation()} catch(e:Exception) {error=e.message?:"Request failed"}
            finally {loading=false}
        }
    }
    Scaffold(topBar={TopAppBar(title={Text("◈ GoreeCloud Tasks")})}) { insets ->
        Column(Modifier.fillMaxSize().padding(insets).padding(20.dp),
            verticalArrangement=Arrangement.spacedBy(16.dp)) {
            Text(if(api==null) "Private workspace" else "My tasks",
                style=MaterialTheme.typography.headlineMedium)
            Text("Self-hosted. Clear by default.",color=MaterialTheme.colorScheme.onSurfaceVariant)
            if(error.isNotBlank()) Text(error,color=MaterialTheme.colorScheme.error)
            if(api==null) {
                GoreeCloudPanel(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(18.dp).verticalScroll(rememberScrollState()),
                        verticalArrangement=Arrangement.spacedBy(14.dp)) {
                        OutlinedTextField(value=serverUrl,onValueChange={serverUrl=it},
                            label={Text("Server HTTPS URL")},modifier=Modifier.fillMaxWidth(),singleLine=true)
                        OutlinedTextField(value=token,onValueChange={token=it},
                            label={Text("API token")},modifier=Modifier.fillMaxWidth(),
                            visualTransformation=PasswordVisualTransformation(),singleLine=true)
                        GoreeCloudAction("Connect",onClick={
                            execute {
                                val client=TaskApi(serverUrl.trim(),token)
                                tasks=client.listTasks()
                                api=client
                                token=""
                            }
                        },enabled=!loading)
                        Text("Tokens stay in memory. Debug emulator may use http://10.0.2.2:8000; releases require HTTPS.",
                            style=MaterialTheme.typography.bodySmall)
                    }
                }
            } else {
                GoreeCloudPanel(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(18.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
                        OutlinedTextField(value=title,onValueChange={title=it},
                            label={Text("Task title")},modifier=Modifier.fillMaxWidth(),singleLine=true)
                        OutlinedTextField(value=due,onValueChange={due=it},
                            label={Text("Due date YYYY-MM-DD (optional)")},modifier=Modifier.fillMaxWidth(),singleLine=true)
                        Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                            GoreeCloudAction("Add task",onClick={
                                execute {
                                    val client=requireNotNull(api)
                                    client.createTask(title,due.ifBlank {null})
                                    tasks=client.listTasks()
                                    title="";due=""
                                }
                            },enabled=!loading&&title.isNotBlank())
                            TextButton(onClick={execute {tasks=requireNotNull(api).listTasks()}},
                                enabled=!loading) {Text("Refresh")}
                        }
                    }
                }
                Text(tasks.size.toString()+" active tasks",style=MaterialTheme.typography.titleMedium)
                LazyColumn(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(10.dp)) {
                    items(tasks,key={it.id}) { task ->
                        GoreeCloudPanel(Modifier.fillMaxWidth()) {
                            Row(Modifier.fillMaxWidth().padding(12.dp),
                                horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                                Checkbox(checked=false,enabled=!loading,onCheckedChange={
                                    execute {
                                        val client=requireNotNull(api)
                                        client.completeTask(task)
                                        tasks=client.listTasks()
                                    }
                                })
                                Column(Modifier.weight(1f)) {
                                    Text(task.title,style=MaterialTheme.typography.titleMedium)
                                    Text((task.dueDate?:"No due date")+" · P"+task.priority,
                                        style=MaterialTheme.typography.bodySmall)
                                }
                            }
                        }
                    }
                }
                TextButton(onClick={api=null;tasks=emptyList()},enabled=!loading) {Text("Disconnect")}
            }
        }
    }
}
