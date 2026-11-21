"""Native Qt Quick 6.12.0 GoreeCloud Tasks Linux desktop client.

A user-supplied API token stays in process memory and is never saved.
Only loopback HTTP or HTTPS with normal platform certificate validation is allowed.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlsplit
from uuid import uuid4

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtQml import QQmlApplicationEngine


class TasksBackend(QObject):
    tasksChanged = Signal()
    projectsChanged = Signal()
    habitsChanged = Signal()
    habitHistoryChanged = Signal()
    connectedChanged = Signal()
    statusChanged = Signal()
    errorChanged = Signal()

    def __init__(self, url: str, token: str):
        super().__init__()
        self._all_tasks: list[dict] = []
        self._tasks: list[dict] = []
        self._projects: list[dict] = []
        self._habits: list[dict] = []
        self._habit_history: list[str] = []
        self._habit_history_offset = 0
        self._habit_history_has_more = False
        self._habit_history_generation = 0
        self._status = "Ready" if self._valid_token(token) else "Disconnected"
        self._error = ""
        self._token = token if self._valid_token(token) else ""
        self._url = url.rstrip("/")
        self._session_generation = 0
        self._outstanding_replies = set()
        self._view = "inbox"
        self._project_filter: str | None = None
        self._query = ""
        self._network = QNetworkAccessManager(self)

    @Property("QVariantList", notify=tasksChanged)
    def tasks(self):
        return self._tasks

    @Property("QVariantList", notify=tasksChanged)
    def allTasks(self):
        return self._all_tasks

    @Property("QVariantList", notify=projectsChanged)
    def projects(self):
        return self._projects

    @Property("QVariantList", notify=habitsChanged)
    def habits(self):
        return self._habits

    @Property("QVariantList", notify=habitHistoryChanged)
    def habitHistory(self):
        return self._habit_history

    @Property(int, notify=habitHistoryChanged)
    def habitHistoryOffset(self):
        return self._habit_history_offset

    @Property(bool, notify=habitHistoryChanged)
    def habitHistoryHasMore(self):
        return self._habit_history_has_more

    @Slot()
    def clearHabitHistory(self):
        self._habit_history_generation += 1
        self._habit_history = []
        self._habit_history_offset = 0
        self._habit_history_has_more = False
        self.habitHistoryChanged.emit()

    @Slot(str, int)
    def loadHabitHistory(self, habit_id: str, offset: int):
        if not habit_id or not 0 <= offset <= 1_000_000:
            self._set_error("Invalid habit history page")
            return
        self.clearHabitHistory()
        generation = self._habit_history_generation

        def on_history(data):
            if generation != self._habit_history_generation:
                return  # A closed dialog/newer request must not display stale history.
            if not isinstance(data, list) or len(data) > 30:
                self._set_error("Invalid habit history response")
                return
            try:
                parsed = [date.fromisoformat(day).isoformat() for day in data
                          if isinstance(day, str)]
            except (ValueError, TypeError):
                self._set_error("Invalid habit history dates")
                return
            if len(parsed) != len(data) or parsed != sorted(set(parsed), reverse=True):
                self._set_error("Invalid habit history date order")
                return
            self._habit_history = parsed
            self._habit_history_offset = offset
            self._habit_history_has_more = len(parsed) == 30
            self.habitHistoryChanged.emit()

        self._request("GET", "/habits/" + quote(habit_id, safe="") +
                      "/checkins?limit=30&offset=" + str(offset),
                      callback=on_history)

    @staticmethod
    def _valid_token(token: str) -> bool:
        return 32 <= len(token) <= 512 and all(33 <= ord(char) <= 126
                                                for char in token)

    @staticmethod
    def _valid_url(value: str) -> bool:
        if not value or len(value) > 2048 or any(ord(char) <= 32 for char in value):
            return False
        try:
            parsed = urlsplit(value)
            port = parsed.port
            return (
                parsed.scheme in ("https", "http") and bool(parsed.hostname)
                and (port is None or 0 < port <= 65535)
                and parsed.username is None and parsed.password is None
                and not parsed.query and not parsed.fragment
                and not value.endswith("/")
                and (parsed.scheme == "https" or
                     parsed.hostname in {"127.0.0.1", "::1", "localhost"})
            )
        except ValueError:
            return False

    @Property(bool, notify=connectedChanged)
    def connected(self) -> bool:
        return self._valid_token(self._token)

    @Property(str, notify=connectedChanged)
    def serverUrl(self) -> str:
        return self._url

    @Slot(str, str)
    def connectToServer(self, url: str, token: str):
        candidate = url.strip().rstrip("/")
        if not self._valid_url(candidate):
            self._set_error("Use an HTTPS server URL or a loopback HTTP address")
            return
        if not self._valid_token(token):
            self._set_error("Token must contain 32–512 printable non-space ASCII characters")
            return
        self.disconnect()
        self._url = candidate
        self._token = token
        self._set_error("")
        self.connectedChanged.emit()
        self.refresh()

    @Slot()
    def disconnect(self):
        self._session_generation += 1
        for reply in tuple(self._outstanding_replies):
            reply.abort()
        self._token = ""
        self._all_tasks = []
        self._tasks = []
        self._projects = []
        self._habits = []
        self._habit_history = []
        self._habit_history_generation += 1
        self._habit_history_offset = 0
        self._habit_history_has_more = False
        self._project_filter = None
        self._query = ""
        self._view = "inbox"
        self._status = "Disconnected"
        self._set_error("")
        self.tasksChanged.emit()
        self.projectsChanged.emit()
        self.habitsChanged.emit()
        self.habitHistoryChanged.emit()
        self.statusChanged.emit()
        self.connectedChanged.emit()

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    @Property(str, notify=errorChanged)
    def error(self):
        return self._error

    def _set_error(self, message: str):
        self._error = message
        self.errorChanged.emit()

    def _apply_filters(self):
        today = date.today().isoformat()
        result = []
        for task in self._all_tasks:
            if self._project_filter and task.get("project_id") != self._project_filter:
                continue
            if self._query and self._query not in " ".join([
                task.get("title", ""), task.get("description", ""),
                " ".join(task.get("tags") or [])
            ]).casefold():
                continue
            completed = bool(task.get("completed_at"))
            due = task.get("due_date")
            if self._view == "completed":
                if not completed:
                    continue
            elif completed:
                continue
            elif self._view == "today" and (not due or due > today):
                continue
            elif self._view == "upcoming" and (not due or due <= today):
                continue
            result.append(task)
        self._tasks = result
        self.tasksChanged.emit()
        self._status = str(len(result)) + " tasks in this view"
        self.statusChanged.emit()

    @Slot(str)
    def setView(self, value: str):
        if value not in {"inbox", "today", "upcoming", "completed"}:
            self._set_error("Unknown task view")
            return
        self._view = value
        self._apply_filters()

    @Slot(str)
    def setProjectFilter(self, project_id: str):
        self._project_filter = project_id or None
        self._apply_filters()

    @Slot(str)
    def setSearch(self, value: str):
        self._query = value.casefold()[:120]
        self._apply_filters()

    def _request(self, method: str, path: str, payload=None, callback=None,
                 idempotency_key: str | None = None):
        if not self.connected:
            self._set_error("Connect with a 32+ character API token")
            return
        generation = self._session_generation
        request = QNetworkRequest(QUrl(self._url + "/api/v1" + path))
        request.setRawHeader(b"Authorization", ("Bearer " + self._token).encode())
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        if idempotency_key:
            request.setRawHeader(b"Idempotency-Key", idempotency_key.encode("ascii"))
        request.setTransferTimeout(15_000)
        content = json.dumps(payload).encode("utf-8") if payload is not None else b""
        reply = self._network.sendCustomRequest(request, method.encode("ascii"), content)
        self._outstanding_replies.add(reply)

        def finished():
            self._outstanding_replies.discard(reply)
            if generation != self._session_generation:
                reply.deleteLater()
                return
            data = bytes(reply.readAll())
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            if reply.error() != QNetworkReply.NetworkError.NoError or not isinstance(status, int) or status >= 400:
                if status == 409:
                    self._set_error("Task changed on the server. Refresh before editing.")
                else:
                    self._set_error("Request failed (" + str(status or reply.errorString()) + ")")
            else:
                self._set_error("")
                if callback is not None:
                    try:
                        callback(json.loads(data) if data else None)
                    except (ValueError, TypeError) as exc:
                        self._set_error("Invalid API response: " + type(exc).__name__)
            reply.deleteLater()

        reply.finished.connect(finished)

    @Slot()
    def refresh(self):
        self._status = "Refreshing"
        self.statusChanged.emit()
        self._request("GET", "/sync/bootstrap", callback=self._apply_snapshot)

    def _apply_snapshot(self, data):
        """Apply both task and project collections only after full validation.

        The paginated /tasks endpoint defaults to 1,000 items and cannot
        represent a complete workspace. Do not silently truncate or mix two
        independent server requests with mismatched revision points.
        """
        if not isinstance(data, dict) or data.get("format") != "goreecloud-tasks-sync-1":
            self._set_error("Unsupported task snapshot format")
            return
        cursor, tasks, projects = data.get("cursor"), data.get("tasks"), data.get("projects")
        if (not isinstance(cursor, int) or isinstance(cursor, bool) or cursor < 0
                or not isinstance(tasks, list) or len(tasks) > 5000
                or not isinstance(projects, list) or len(projects) > 5000
                or any(not isinstance(item, dict)
                       or not isinstance(item.get("id"), str)
                       or not isinstance(item.get("title"), str)
                       for item in tasks)
                or any(not isinstance(item, dict)
                       or not isinstance(item.get("id"), str)
                       or not isinstance(item.get("name"), str)
                       for item in projects)):
            self._set_error("Invalid or oversized task snapshot; previous data preserved")
            return
        self._all_tasks = tasks
        self._projects = projects
        self.projectsChanged.emit()
        self._apply_filters()

    @staticmethod
    def _task_data(title: str, description: str, priority: int, due_date: str,
                   recurrence: str, project_id: str, tags_csv: str, parent_id: str = "") -> dict:
        title = title.strip()
        if not 1 <= len(title) <= 240:
            raise ValueError("Task title must contain 1–240 characters")
        if len(description) > 16000:
            raise ValueError("Task notes are too long")
        if priority not in (1, 2, 3, 4):
            raise ValueError("Priority must be P1 through P4")
        if recurrence not in {"none", "daily", "weekdays", "weekly", "biweekly", "monthly", "yearly"}:
            raise ValueError("Unknown recurrence")
        if recurrence != "none" and not due_date:
            raise ValueError("Recurring tasks need a due date")
        if due_date:
            try:
                if date.fromisoformat(due_date).isoformat() != due_date:
                    raise ValueError()
            except ValueError:
                raise ValueError("Use YYYY-MM-DD for due dates") from None
        tags = []
        for value in tags_csv.split(","):
            tag = value.strip().casefold()
            if not tag:
                continue
            if len(tag) > 36:
                raise ValueError("Tag must have at most 36 characters")
            if tag not in tags:
                tags.append(tag)
        if len(tags) > 12:
            raise ValueError("Too many tags; maximum 12")
        return dict(title=title, description=description, due_date=due_date or None,
                    priority=priority, recurrence=recurrence, project_id=project_id or None,
                    tags=tags, parent_id=parent_id or None)

    @Slot(str, int, str, str)
    def addTask(self, title: str, priority: int, due_date: str, recurrence: str):
        self.addTaskDetailed(title, "", priority, due_date, recurrence, "", "", "")

    @Slot(str, str, int, str, str, str, str, str)
    def addTaskDetailed(self, title: str, description: str, priority: int,
                        due_date: str, recurrence: str, project_id: str, tags: str,
                        parent_id: str):
        try:
            data = self._task_data(title, description, priority, due_date,
                                   recurrence, project_id, tags, parent_id)
        except ValueError as exc:
            self._set_error(str(exc))
            return
        self._request("POST", "/tasks", data, lambda _: self.refresh(),
                      idempotency_key=str(uuid4()))

    @Slot(str, int, str, str, int, str, str, str, str, str)
    def editTaskDetailed(self, task_id: str, version: int, title: str,
                         description: str, priority: int, due_date: str,
                         recurrence: str, project_id: str, tags: str, parent_id: str):
        try:
            data = self._task_data(title, description, priority, due_date,
                                   recurrence, project_id, tags, parent_id)
        except ValueError as exc:
            self._set_error(str(exc))
            return
        data["expected_version"] = version
        self._request("PATCH", "/tasks/" + quote(task_id, safe=""),
                      data, lambda _: self.refresh())

    def _update_habits(self, data):
        if not isinstance(data, list):
            self._set_error("Invalid habit list response")
            return
        self._habits = data
        self.habitsChanged.emit()

    @Slot()
    def refreshHabits(self):
        self._request("GET", "/habits?as_of=" + date.today().isoformat(),
                      callback=self._update_habits)

    @Slot(str, str)
    def addHabit(self, name: str, description: str):
        name = name.strip()
        if not 1 <= len(name) <= 120 or len(description) > 16000:
            self._set_error("Habit name must be 1–120 characters; notes max 16000")
            return
        self._request("POST", "/habits",
                      {"name": name, "description": description},
                      lambda _: self.refreshHabits())

    @Slot(str, int, str, str)
    def editHabit(self, habit_id: str, version: int, name: str, description: str):
        name = name.strip()
        if not 1 <= len(name) <= 120 or len(description) > 16000:
            self._set_error("Habit name must be 1–120 characters; notes max 16000")
            return
        if version < 1 or not habit_id:
            self._set_error("Habit revision is invalid; refresh before editing")
            return
        self._request("PATCH", "/habits/" + quote(habit_id, safe=""),
                      {"expected_version": version, "name": name,
                       "description": description},
                      lambda _: self.refreshHabits())

    @Slot(str, int, bool)
    def toggleHabit(self, habit_id: str, version: int, checked: bool):
        today = date.today().isoformat()
        path = "/habits/" + quote(habit_id, safe="") + "/checkins"
        if checked:
            self._request("DELETE", path + "/" + today + "?expected_version=" + str(version),
                          callback=lambda _: self.refreshHabits())
        else:
            self._request("POST", path, {"day": today, "expected_version": version},
                          lambda _: self.refreshHabits())

    @Slot(str, int)
    def deleteHabit(self, habit_id: str, version: int):
        self._request("DELETE", "/habits/" + quote(habit_id, safe="") +
                      "?expected_version=" + str(version), callback=lambda _: self.refreshHabits())

    @Slot(str)
    def addProject(self, name: str):
        if not 1 <= len(name.strip()) <= 120:
            self._set_error("Project name must contain 1–120 characters")
            return
        self._request("POST", "/projects", {"name": name.strip()}, lambda _: self.refresh(),
                      idempotency_key=str(uuid4()))

    @Slot(str, int)
    def completeTask(self, task_id: str, version: int):
        self._request("POST", "/tasks/" + quote(task_id, safe="") + "/complete",
                      {"expected_version": version}, lambda _: self.refresh(),
                      idempotency_key=str(uuid4()))

    @Slot(str, int)
    def reopenTask(self, task_id: str, version: int):
        self._request("POST", "/tasks/" + quote(task_id, safe="") + "/reopen",
                      {"expected_version": version}, lambda _: self.refresh())

    @Slot(str, int)
    def deleteTask(self, task_id: str, version: int):
        self._request("DELETE", "/tasks/" + quote(task_id, safe="") +
                      "?expected_version=" + str(version), callback=lambda _: self.refresh())


def main():
    url = os.environ.get("GOREECLOUD_TASKS_URL", "http://127.0.0.1:8000").rstrip("/")
    if not TasksBackend._valid_url(url):
        raise SystemExit("GOREECLOUD_TASKS_URL must be HTTPS or loopback HTTP with no credentials")
    token = os.environ.get("GOREECLOUD_TASKS_API_TOKEN", "")
    app = QGuiApplication(sys.argv)
    backend = TasksBackend(url, token)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("tasksBackend", backend)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
    if not engine.rootObjects():
        return 1
    if backend.connected:
        backend.refresh()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
