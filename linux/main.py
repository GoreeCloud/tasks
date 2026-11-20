"""Native Qt Quick 6.12.0 GoreeCloud Tasks Linux desktop client.

API token is read from the environment (never persisted). HTTP is allowed
only on loopback; nonlocal servers must use TLS.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtQml import QQmlApplicationEngine


class TasksBackend(QObject):
    tasksChanged = Signal()
    projectsChanged = Signal()
    statusChanged = Signal()
    errorChanged = Signal()

    def __init__(self, url: str, token: str):
        super().__init__()
        self._tasks: list[dict] = []
        self._projects: list[dict] = []
        self._status = "Ready"
        self._error = ""
        self._token = token
        self._url = url.rstrip("/")
        self._network = QNetworkAccessManager(self)

    @Property("QVariantList", notify=tasksChanged)
    def tasks(self):
        return self._tasks

    @Property("QVariantList", notify=projectsChanged)
    def projects(self):
        return self._projects

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    @Property(str, notify=errorChanged)
    def error(self):
        return self._error

    def _set_error(self, message: str):
        self._error = message
        self.errorChanged.emit()

    def _request(self, method: str, path: str, payload=None, callback=None):
        if not self._token:
            self._set_error("Set GOREECLOUD_TASKS_API_TOKEN before starting the app")
            return
        request = QNetworkRequest(QUrl(self._url + "/api/v1" + path))
        request.setRawHeader(b"Authorization", ("Bearer " + self._token).encode())
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        request.setTransferTimeout(15000)
        content = json.dumps(payload).encode() if payload is not None else b""
        reply = self._network.sendCustomRequest(request, method.encode(), content)

        def finished():
            data = bytes(reply.readAll())
            code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            if reply.error() != QNetworkReply.NetworkError.NoError or not isinstance(code, int) or code >= 400:
                self._set_error("Request failed (" + str(code or reply.errorString()) + ")")
            else:
                self._set_error("")
                if callback:
                    try:
                        callback(json.loads(data) if data else None)
                    except (ValueError, TypeError) as exc:
                        self._set_error("Invalid server response: " + str(exc))
            reply.deleteLater()

        reply.finished.connect(finished)

    @Slot()
    def refresh(self):
        self._status = "Refreshing"
        self.statusChanged.emit()

        def loaded(data):
            if not isinstance(data, list):
                self._set_error("Invalid task response")
                return
            self._tasks = data
            self.tasksChanged.emit()
            self._status = str(len(data)) + " tasks"
            self.statusChanged.emit()

        self._request("GET", "/tasks?status=active", callback=loaded)
        self._request("GET", "/projects", callback=self._update_projects)

    def _update_projects(self, data):
        if isinstance(data, list):
            self._projects = data
            self.projectsChanged.emit()

    @Slot(str, int, str, str)
    def addTask(self, title: str, priority: int, due_date: str, recurrence: str):
        title = title.strip()
        if not title or len(title) > 240:
            self._set_error("Task title must be 1–240 characters")
            return
        if due_date:
            from datetime import date
            try:
                date.fromisoformat(due_date)
            except ValueError:
                self._set_error("Due date must be YYYY-MM-DD")
                return
        if recurrence != "none" and not due_date:
            self._set_error("Recurring tasks require a due date")
            return
        self._request("POST", "/tasks", {
            "title": title, "priority": priority, "due_date": due_date or None,
            "recurrence": recurrence
        }, lambda _: self.refresh())

    @Slot(str, int)
    def completeTask(self, task_id: str, version: int):
        from urllib.parse import quote
        self._request("POST", "/tasks/" + quote(task_id, safe="") + "/complete",
                      {"expected_version": version}, lambda _: self.refresh())


def main():
    url = os.environ.get("GOREECLOUD_TASKS_URL", "http://127.0.0.1:8000").rstrip("/")
    parsed = urlsplit(url)
    if parsed.scheme not in ("https", "http") or not parsed.hostname:
        raise SystemExit("Invalid GOREECLOUD_TASKS_URL")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("Nonlocal API access requires HTTPS")
    token = os.environ.get("GOREECLOUD_TASKS_API_TOKEN", "")
    app = QGuiApplication(sys.argv)
    backend = TasksBackend(url, token)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("tasksBackend", backend)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
    if not engine.rootObjects():
        return 1
    backend.refresh()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
