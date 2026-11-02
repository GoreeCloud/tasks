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
        os.environ["XDG_CONFIG_HOME"] = directory
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from app import TasksApp, TasksWindow
        from gi.repository import Gtk

        app = TasksApp()
        if not app.register(None):
            raise RuntimeError("Could not register GTK application")
        window = TasksWindow(app)
        try:
            # Owner-inspired list-first GTK navigation and task capture behavior.
            assert window.heading.get_text() == "Inbox"
            assert not window.bulk_actions.get_visible()
            assert not window.filter_revealer.get_reveal_child()
            window.on_toggle_filters(None)
            assert window.filter_revealer.get_reveal_child()
            window.on_toggle_filters(None)
            assert not window.filter_revealer.get_reveal_child()
            from gi.repository import Gdk
            assert window.on_keyboard(None, Gdk.KEY_n, 0, Gdk.ModifierType.CONTROL_MASK)
            assert window.capture_revealer.get_reveal_child()
            assert window.on_keyboard(None, Gdk.KEY_f, 0, Gdk.ModifierType.CONTROL_MASK)
            assert not window.on_keyboard(None, Gdk.KEY_n, 0, Gdk.ModifierType.SHIFT_MASK)
            window.on_toggle_capture(None)
            assert not window.capture_revealer.get_reveal_child()
            window.on_toggle_capture(None)
            assert window.capture_revealer.get_reveal_child()
            window.on_toggle_capture(None)
            assert not window.capture_revealer.get_reveal_child()
            window.on_nav_view(None, "Today")
            assert window.heading.get_text() == "Today"
            assert window.view.get_selected() == window.view_names.index("Today")
            assert window.nav_buttons["Today"].has_css_class("task-nav-selected")
            window.on_nav_view(None, "Open")
            assert window.heading.get_text() == "Inbox"
            assert not window.nav_buttons["Today"].has_css_class("task-nav-selected")
            # The compact Browse dropdown must actually switch views, not only paint labels.
            window.browse_view.set_selected(window.view_names.index("Upcoming"))
            assert window.heading.get_text() == "Upcoming"
            assert window.view.get_selected() == window.browse_view.get_selected()
            window.browse_view.set_selected(window.view_names.index("Open"))
            assert window.heading.get_text() == "Inbox"
            window.on_toggle_project_creation(None)
            assert window.project_creation.get_reveal_child()
            window.on_toggle_project_creation(None)
            assert not window.project_creation.get_reveal_child()
            # Verify theme controls never write task data or source backups.
            from theme import read_preferences
            assert window.theme_preferences == {"appearance": "light", "accent": "neutral"}
            mode = Gtk.DropDown.new_from_strings(["Light", "Dark"])
            mode.set_selected(1)
            palette = Gtk.DropDown.new_from_strings(["Neutral", "Lagoon", "Moss", "Ember", "Ocean", "Iris"])
            palette.set_selected(1)
            window.on_appearance_response(None, "save", mode, palette)
            assert read_preferences() == {"appearance": "dark", "accent": "lagoon"}
            assert window.theme_preferences == read_preferences()
            project = window.store.add_project("Synthetic project")
            window.update_projects()
            assert project in window.project_buttons
            window.browse_project.set_selected(1)
            assert window.heading.get_text() == "Synthetic project"
            assert window.selected_project_id() == project
            window.browse_project.set_selected(0)
            assert window.heading.get_text() == "Inbox"
            window.on_nav_project(None, project)
            assert window.heading.get_text() == "Synthetic project"
            assert window.view_names[window.view.get_selected()] == "Project"
            assert window.project_buttons[project].has_css_class("task-nav-selected")
            window.on_nav_view(None, "Open")
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
            description = Gtk.TextView()
            description.get_buffer().set_text("Synthetic release%_notes")
            labels = Gtk.Entry()
            labels.set_text("Work, Design 🧭")
            window.on_edit_response(
                None, "save", task, title, priority, due,
                project_picker, [None, project], description, labels
            )
            row = window.store.list_tasks()[0]
            assert row["description"] == "Synthetic release%_notes"
            import json
            assert json.loads(row["labels_json"]) == ["Work", "Design 🧭"]
            assert "Work" in window._available_labels
            window.label_filter.set_selected(window._available_labels.index("Work") + 1)
            window.refresh()
            assert window.visible_task_ids == [task]
            window.label_filter.set_selected(0)
            window.refresh()
            window.search.set_text("release%_")
            window.refresh() # SearchEntry notification is debounced by GTK
            assert window.visible_task_ids == [task]
            window.search.set_text("releaseZZ")
            window.refresh()
            assert window.visible_task_ids == []
            window.search.set_text("")
            assert row["title"] == "After"
            assert row["priority"] == 1
            assert row["due_date"] == "2026-11-09"
            assert row["project_id"] == project
            assert window.project_buttons[project].get_child().get_label().endswith("1")
            created_at = row["created_at"]
            window.on_delete_response(None, "delete", task)
            assert window.store.list_tasks() == []
            deleted = window.store.list_deleted_tasks()
            assert len(deleted) == 1 and deleted[0]["id"] == task
            assert deleted[0]["description"] == "Synthetic release%_notes"
            assert json.loads(deleted[0]["labels_json"]) == ["Work", "Design 🧭"]
            window.on_nav_view(None, "Trash")
            window.search.set_text("release%_")
            assert window.list_box.get_first_child() is not None
            assert len(window.store.list_deleted_tasks(query="release%_")) == 1
            window.search.set_text("")
            window.on_import(None)
            assert "including Trash" in window.message.get_text()
            assert "Next 7 days" in window.view_names
            assert "Overdue" in window.view_names
            for name in ("Next 7 days", "Overdue"):
                window.view.set_selected(window.view_names.index(name))
                window.refresh()
                assert window.list_box.get_first_child() is not None
            trash_index = window.view_names.index("Trash")
            window.view.set_selected(trash_index)
            window.refresh()
            assert window.view.get_selected() == trash_index
            assert window.on_keyboard(None, Gdk.KEY_n, 0, Gdk.ModifierType.CONTROL_MASK)
            assert not window.capture_revealer.get_reveal_child()
            assert window.list_box.get_first_child() is not None
            window.on_restore(None, task)
            restored = window.store.list_tasks()[0]
            assert restored["title"] == "After"
            assert restored["project_id"] == project
            assert restored["created_at"] == created_at
            assert window.store.list_deleted_tasks() == []
            # Exercise real GTK multi-selection and SQLite-backed actions.
            window.update_projects()
            window.view.set_selected(window.view_names.index("Open"))
            extra = window.store.add_task("Second synthetic task", priority=4)
            window.refresh()
            window.on_select_visible(None)
            assert window.bulk_actions.get_visible()
            selected = sorted(window.selected_task_ids)
            assert len(selected) == 2 and extra in selected
            window.bulk_priority.set_selected(1)
            window.on_bulk_priority(None)
            assert all(row["priority"] == 2 for row in window.store.list_tasks(view="Open"))
            window.on_select_visible(None)
            window.bulk_project.set_selected(1)
            window.on_bulk_project(None)
            assert all(row["project_id"] == project for row in window.store.list_tasks(view="Open"))
            window.on_select_visible(None)
            window.on_bulk_action(None, "complete", None)
            assert not window.bulk_actions.get_visible()
            assert window.project_buttons[project].get_child().get_label().endswith("0")
            assert not window.store.list_tasks(view="Open")
            window.view.set_selected(window.view_names.index("Completed"))
            window.on_select_visible(None)
            assert len(window.selected_task_ids) == 2
            window.on_bulk_action(None, "reopen", None)
            window.view.set_selected(window.view_names.index("Open"))
            window.on_select_visible(None)
            to_trash = sorted(window.selected_task_ids)
            window.on_bulk_trash_response(None, "trash", to_trash)
            assert not window.store.list_tasks(view="All")
            assert len(window.store.list_deleted_tasks()) == 2
            # Native Duplicate action must leave a new open task with notes.
            original = window.store.add_task("Reusable task", priority=2,
                                             description="Review checklist 🧭", labels=["Review"])
            window.store.complete_task(original, True)
            window.refresh()
            window.on_duplicate(None, original)
            created = [t for t in window.store.list_tasks() if t["title"] == "Reusable task"]
            assert len(created) == 1 and created[0]["id"] != original
            assert created[0]["description"] == "Review checklist 🧭"
            assert json.loads(created[0]["labels_json"]) == ["Review"]
            assert created[0]["completed"] == 0 and created[0]["completed_at"] is None
            assert window.store.list_tasks(view="Completed")[0]["id"] == original
            print("GTK4_LIBADWAITA_DUPLICATE_TASK_SMOKE_PASS")
            print("GTK4_LIBADWAITA_BULK_TASK_OPERATIONS_SMOKE_PASS")
            print("GTK4_LIBADWAITA_TASK_EDIT_AND_TRASH_RECOVERY_SMOKE_PASS")
        finally:
            window.close()


if __name__ == "__main__":
    main()
