package com.goreecloud.tasks

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class TaskItem(val id:String, val title:String, val dueDate:String?, val priority:Int, val version:Int)

/** Explicit connection only; no token persistence or telemetry. */
class TaskApi(private val base:String, private val token:String) {
    init {
        require(token.length>=32) {"API token must contain at least 32 characters"}
        val url=URL(base)
        require(url.protocol=="https" || (BuildConfig.DEBUG && url.protocol=="http" && url.host=="10.0.2.2")) {
            "HTTPS is required outside the Android debug emulator"
        }
        require(url.userInfo==null && (url.path.isEmpty() || url.path=="/")) {
            "Enter the server origin, not a path or embedded credentials"
        }
    }
    private suspend fun request(path:String, method:String="GET", body:JSONObject?=null):String =
        withContext(Dispatchers.IO) {
            val connection=(URL(base.trimEnd('/')+"/api/v1"+path).openConnection() as HttpURLConnection).apply {
                requestMethod=method
                connectTimeout=10000
                readTimeout=15000
                instanceFollowRedirects=false
                setRequestProperty("Authorization","Bearer "+token)
                setRequestProperty("Accept","application/json")
                setRequestProperty("Content-Type","application/json")
                if(body!=null) {
                    doOutput=true
                    outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
                }
            }
            try {
                val status=connection.responseCode
                if(status !in 200..299) throw IllegalStateException("Server returned HTTP "+status)
                connection.inputStream.bufferedReader().use { it.readText() }
            } finally {connection.disconnect()}
        }
    suspend fun listTasks():List<TaskItem> {
        val array=JSONArray(request("/tasks?status=active"))
        return (0 until array.length()).map { index ->
            val item=array.getJSONObject(index)
            TaskItem(item.getString("id"),item.getString("title"),
                item.optString("due_date").takeIf {it.isNotBlank()&&it!="null"},
                item.getInt("priority"),item.getInt("version"))
        }
    }
    suspend fun createTask(title:String,due:String?) {
        require(title.isNotBlank()) {"Enter a title"}
        request("/tasks","POST",JSONObject().put("title",title.trim())
            .put("due_date",if(due.isNullOrBlank()) JSONObject.NULL else due.trim()))
    }
    suspend fun completeTask(task:TaskItem) {
        request("/tasks/"+java.net.URLEncoder.encode(task.id,"UTF-8")+"/complete","POST",
            JSONObject().put("expected_version",task.version))
    }
}
