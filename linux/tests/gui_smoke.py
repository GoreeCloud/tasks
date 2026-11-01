#!/usr/bin/env python3
"""Optional headless GTK4/libadwaita task editing smoke test.

Run with: xvfb-run -a python3 linux/tests/gui_smoke.py
Requires distribution GTK4/libadwaita/PyGObject packages.
All data is synthetic and stored under a disposable XDG directory.
"""
import os
from pathlib import Path
import sys
import tempfile


def main():
    if not os.environ.get("DISPLAY"):
        raise RuntimeError("GTK smoke requires a display; use xvfb-run")
    with tempfile.TemporaryDirectory(prefix="goreecloud-tasks-gui-smoke-") as directory:
        os.environ["XDG_DATA_HOME"] = directory
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from app import TasksApp, TasksWindow
        from gi.repository import Gtk

        app = TasksApp()
        if not app.register(None):
            raise RuntimeError("Could not register GTK application")
        window = TasksWindow(app)
        try:
            project = window.store.add_project("Synthetic project")
            task = window.store.add_task("Before", priority=3)
            window.refresh()
            window.on_edit(None, window.store.list_tasks()[0])

            title = Gtk.Entry()
            title.set_text("After")
            priority = Gtk.DropDown.new_from_strings(["P4", "P3", "P2", "P1"])
            priority.set_selected(3)
            due = Gtk.Entry()
            due.set_text("2026-11-09")
            project_picker = Gtk.DropDown.new_from_strings(
                ["Inbox", "Synthetic project"]
            )
            project_picker.set_selected(1)
            window.on_edit_response(
                None, "save", task, title, priority, due,
                project_picker, [None, project]
            )
            row = window.store.list_tasks()[0]
            assert row["title"] == "After"
            assert row["priority"] == 1
            assert row["due_date"] == "2026-11-09"
            assert row["project_id"] == project
            created_at = row["created_at"]
            window.on_delete_response(None, "delete", task)
            assert window.store.list_tasks() == []
            deleted = window.store.list_deleted_tasks()
            assert len(deleted) == 1 and deleted[0]["id"] == task
            window.view.set_selected(6)
            window.refresh()
            assert window.view.get_selected() == 6
            assert window.list_box.get_first_child() is not None
            window.on_restore(None, task)
            restored = window.store.list_tasks()[0]
            assert restored["title"] == "After"
            assert restored["project_id"] == project
            assert restored["created_at"] == created_at
            assert window.store.list_deleted_tasks() == []
            print("GTK4_LIBADWAITA_TASK_EDIT_AND_TRASH_RECOVERY_SMOKE_PASS")
        finally:
            window.close()


if __name__ == "__main__":
    main()
