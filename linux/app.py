#!/usr/bin/env python3
"""First-party native GTK4 + libadwaita GoreeCloud Tasks desktop client."""
import sqlite3
import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk, GLib

from backup import BackupError, export_file, import_data, read_backup
from store import TaskStore

Adw.init()


class TasksWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="GoreeCloud Tasks", default_width=940, default_height=760)
        self.store = TaskStore()
        self.projects = []
        self.set_size_request(600, 480)
        self.connect("close-request", self.on_close)
        css = Gtk.CssProvider()
        css.load_from_path(str(Path(__file__).with_name("style.css")))
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root)
        header = Adw.HeaderBar()
        header.add_css_class("flat")
        root.append(header)
        title = Gtk.Label(label="✦   GoreeCloud Tasks")
        title.add_css_class("title-3")
        header.set_title_widget(title)
        export_button = Gtk.Button(label="Export JSON", tooltip_text="Save a portable task backup")
        export_button.connect("clicked", self.on_export)
        header.pack_start(export_button)
        import_button = Gtk.Button(label="Import JSON", tooltip_text="Restore into an empty local database")
        import_button.connect("clicked", self.on_import)
        header.pack_start(import_button)


        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=13)
        content.set_margin_top(22)
        content.set_margin_bottom(22)
        content.set_margin_start(28)
        content.set_margin_end(28)
        root.append(content)
        heading = Gtk.Label(label="Your focus, beautifully organized", xalign=0)
        heading.add_css_class("title-1")
        content.append(heading)
        subtitle = Gtk.Label(label="Create projects, plan your day, and get things done — on this device.", xalign=0)
        subtitle.add_css_class("dim-label")
        subtitle.set_wrap(True)
        content.append(subtitle)

        project_row = Gtk.Box(spacing=10)
        project_row.set_margin_top(18)
        content.append(project_row)
        project_label = Gtk.Label(label="Project")
        project_row.append(project_label)
        self.project_picker = Gtk.DropDown.new_from_strings(["Inbox"])
        self.project_picker.set_hexpand(True)
        project_row.append(self.project_picker)
        self.project_picker.connect("notify::selected", self.on_project_change)
        self.project_name = Gtk.Entry(placeholder_text="New project name")
        self.project_name.set_max_length(100)
        self.project_name.set_hexpand(True)
        self.project_name.connect("activate", self.on_create_project)
        project_row.append(self.project_name)
        create = Gtk.Button(label="+ Project")
        create.add_css_class("pill")
        create.connect("clicked", self.on_create_project)
        project_row.append(create)

        task_row = Gtk.Box(spacing=10)
        content.append(task_row)
        self.entry = Gtk.Entry(placeholder_text="What needs to get done?")
        self.entry.set_max_length(240)
        self.entry.set_hexpand(True)
        self.entry.connect("activate", self.on_add)
        task_row.append(self.entry)
        self.priority = Gtk.DropDown.new_from_strings(
            ["P4 · Normal", "P3 · Medium", "P2 · High", "P1 · Urgent"]
        )
        task_row.append(self.priority)
        add = Gtk.Button(label="Add task")
        add.add_css_class("suggested-action")
        add.connect("clicked", self.on_add)
        task_row.append(add)

        schedule_row = Gtk.Box(spacing=10)
        schedule_row.set_margin_top(3)
        content.append(schedule_row)
        schedule_row.append(Gtk.Label(label="Due"))
        self.due = Gtk.Entry(placeholder_text="YYYY-MM-DD (optional)")
        self.due.set_max_length(10)
        self.due.set_width_chars(22)
        schedule_row.append(self.due)
        schedule_row.append(Gtk.Label(label="View"))
        self.view_names = (
            "Open", "Today", "Next 7 days", "Overdue", "Upcoming", "Priority",
            "Completed", "Project", "Trash"
        )
        self.view = Gtk.DropDown.new_from_strings(self.view_names)
        self.view.connect("notify::selected", self.on_filter)
        schedule_row.append(self.view)
        self.search = Gtk.SearchEntry(placeholder_text="Search tasks")
        self.search.set_hexpand(True)
        self.search.connect("search-changed", self.on_filter)
        schedule_row.append(self.search)

        filter_row = Gtk.Box(spacing=10)
        content.append(filter_row)
        filter_row.append(Gtk.Label(label="Priority filter"))
        self.priority_filter = Gtk.DropDown.new_from_strings(
            ["All priorities", "P1 · Urgent", "P2 · High", "P3 · Medium", "P4 · Normal"]
        )
        self.priority_filter.set_tooltip_text("Filter visible tasks by priority")
        self.priority_filter.connect("notify::selected", self.on_filter)
        filter_row.append(self.priority_filter)
        filter_row.append(Gtk.Label(label="Sort"))
        self.sort_picker = Gtk.DropDown.new_from_strings(["Smart", "Due date", "Title"])
        self.sort_picker.set_tooltip_text("Sort the task list")
        self.sort_picker.connect("notify::selected", self.on_filter)
        filter_row.append(self.sort_picker)

        self.message = Gtk.Label(xalign=0)
        self.message.add_css_class("dim-label")
        self.message.set_wrap(True)
        content.append(self.message)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        content.append(scroll)
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")
        scroll.set_child(self.list_box)
        self.footer = Gtk.Label(xalign=0)
        self.footer.add_css_class("dim-label")
        content.append(self.footer)

        self.update_projects()
        self.refresh()

    def update_projects(self, selected_id=None):
        self.projects = self.store.list_projects()
        ids = [None] + [project["id"] for project in self.projects]
        names = ["Inbox"] + [project["name"] for project in self.projects]
        self.project_picker.set_model(Gtk.StringList.new(names))
        self.project_picker.set_selected(ids.index(selected_id) if selected_id in ids else 0)

    def selected_project_id(self):
        position = self.project_picker.get_selected()
        if position > 0 and position - 1 < len(self.projects):
            return self.projects[position - 1]["id"]
        return None

    def on_create_project(self, _widget):
        try:
            name = self.project_name.get_text()
            project_id = self.store.add_project(name)
            self.update_projects(project_id)
            self.project_name.set_text("")
            self.message.set_text("Project created locally.")
            self.refresh()
        except (ValueError, OSError, sqlite3.Error) as error:
            self.message.set_text(str(error))

    def on_export(self, _button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Export GoreeCloud Tasks backup")
        dialog.set_initial_name("goreecloud-tasks-backup.json")
        dialog.save(self, None, self.on_export_selected)

    def on_export_selected(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if not file or not file.get_path():
                raise BackupError("Please select a local file path")
            bytes_saved = export_file(self.store, Path(file.get_path()))
            self.message.set_text(f"Saved {bytes_saved} bytes. Verify the backup before relying on it.")
        except GLib.Error as error:
            if not error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                self.message.set_text(f"File selection failed: {error.message}")
        except (BackupError, OSError, ValueError) as error:
            self.message.set_text(f"Export failed: {error}")

    def on_import(self, _button):
        if (self.store.list_tasks(include_completed=True) or
                self.store.list_projects() or self.store.list_deleted_tasks()):
            self.message.set_text(
                "Import requires an empty local database, including Trash. "
                "Use a new database to protect existing recovery history."
            )
            return
        dialog = Gtk.FileDialog()
        dialog.set_title("Import GoreeCloud Tasks JSON backup")
        dialog.open(self, None, self.on_import_selected)

    def on_import_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if not file or not file.get_path():
                raise BackupError("Please select a local JSON file")
            tasks, projects = import_data(self.store, read_backup(Path(file.get_path())))
            self.update_projects()
            self.refresh()
            self.message.set_text(f"Imported {tasks} tasks and {projects} projects into the empty database.")
        except GLib.Error as error:
            if not error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                self.message.set_text(f"File selection failed: {error.message}")
        except (BackupError, OSError, ValueError, sqlite3.Error) as error:
            self.message.set_text(f"Import failed: {error}")

    def on_add(self, _widget):
        try:
            self.store.add_task(
                self.entry.get_text(),
                priority=(4, 3, 2, 1)[self.priority.get_selected()],
                due_date=self.due.get_text().strip() or None,
                project_id=self.selected_project_id()
            )
            self.entry.set_text("")
            self.due.set_text("")
            self.message.set_text("")
            self.refresh()
        except (ValueError, OSError, sqlite3.Error) as error:
            self.message.set_text(str(error))

    def on_filter(self, *args):
        self.refresh()

    def on_project_change(self, *args):
        if self.view_names[self.view.get_selected()] == "Project":
            self.refresh()

    def refresh(self):
        while (child := self.list_box.get_first_child()) is not None:
            self.list_box.remove(child)
        active = self.view.get_selected()
        view = self.view_names[active]
        self.priority_filter.set_sensitive(view != "Trash")
        self.sort_picker.set_sensitive(view != "Trash")
        if view == "Trash":
            tasks = self.store.list_deleted_tasks(query=self.search.get_text())
        else:
            tasks = self.store.list_tasks(
                view=view, query=self.search.get_text(),
                project_id=self.selected_project_id(),
                priority_filter=(None, 1, 2, 3, 4)[self.priority_filter.get_selected()],
                sort_by=("Smart", "Due date", "Title")[self.sort_picker.get_selected()]
            )
        if not tasks:
            empty = Adw.ActionRow(
                title="Trash is empty" if view == "Trash" else "All clear here",
                subtitle=("Deleted tasks will appear here until restored."
                          if view == "Trash" else "Capture a task or choose another view.")
            )
            self.list_box.append(empty)
        for task in tasks:
            project = next((p["name"] for p in self.projects if p["id"] == task["project_id"]), None)
            info = ["P" + str(task["priority"])]
            if task["due_date"]:
                info.append("Due " + task["due_date"])
            if project:
                info.append(project)
            row = Adw.ActionRow(title=task["title"], subtitle="  ·  ".join(info))
            if view == "Trash":
                restore = Gtk.Button(label="Restore", tooltip_text="Restore " + task["title"])
                restore.set_valign(Gtk.Align.CENTER)
                restore.connect("clicked", self.on_restore, task["id"])
                row.add_suffix(restore)
                self.list_box.append(row)
                continue
            checkbox = Gtk.CheckButton()
            checkbox.set_active(bool(task["completed"]))
            checkbox.set_valign(Gtk.Align.CENTER)
            checkbox.update_property([Gtk.AccessibleProperty.LABEL], [
                ("Reopen " if task["completed"] else "Complete ") + task["title"]
            ])
            checkbox.connect("toggled", self.on_toggle, task["id"])
            row.add_prefix(checkbox)
            edit = Gtk.Button(label="Edit", tooltip_text="Edit " + task["title"])
            edit.set_valign(Gtk.Align.CENTER)
            edit.add_css_class("flat")
            edit.connect("clicked", self.on_edit, task)
            row.add_suffix(edit)
            delete = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Delete task")
            delete.set_valign(Gtk.Align.CENTER)
            delete.add_css_class("flat")
            delete.connect("clicked", self.on_delete, task["id"])
            row.add_suffix(delete)
            self.list_box.append(row)
        count = len(self.store.list_tasks())
        self.footer.set_text(
            f"{count} open task{'s' if count != 1 else ''} · Native Linux · Device-local SQLite · No sync"
        )

    def on_toggle(self, checkbox, task_id):
        try:
            self.store.complete_task(task_id, checkbox.get_active())
            self.refresh()
        except sqlite3.Error as error:
            self.message.set_text(str(error))

    def on_edit(self, _button, task):
        dialog = Adw.AlertDialog.new("Edit task", "Update this task on this device.")
        form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)

        form.append(Gtk.Label(label="Title", xalign=0))
        title = Gtk.Entry()
        title.set_max_length(240)
        title.set_text(task["title"])
        form.append(title)

        form.append(Gtk.Label(label="Priority", xalign=0))
        priority = Gtk.DropDown.new_from_strings(
            ["P4 · Normal", "P3 · Medium", "P2 · High", "P1 · Urgent"]
        )
        priority.set_selected((4, 3, 2, 1).index(task["priority"]))
        form.append(priority)

        form.append(Gtk.Label(label="Due date (YYYY-MM-DD, optional)", xalign=0))
        due = Gtk.Entry()
        due.set_max_length(10)
        due.set_text(task["due_date"] or "")
        form.append(due)

        project_ids = [None] + [project["id"] for project in self.projects]
        names = ["Inbox"] + [project["name"] for project in self.projects]
        form.append(Gtk.Label(label="Project", xalign=0))
        project = Gtk.DropDown.new_from_strings(names)
        project.set_selected(
            project_ids.index(task["project_id"]) if task["project_id"] in project_ids else 0
        )
        form.append(project)

        dialog.set_extra_child(form)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")
        dialog.connect(
            "response", self.on_edit_response, task["id"], title, priority,
            due, project, project_ids
        )
        dialog.present(self)

    def on_edit_response(self, _dialog, response, task_id, title, priority,
                         due, project, project_ids):
        if response != "save":
            return
        try:
            found = self.store.update_task(
                task_id,
                title=title.get_text(),
                priority=(4, 3, 2, 1)[priority.get_selected()],
                due_date=due.get_text().strip() or None,
                project_id=project_ids[project.get_selected()]
            )
            if not found:
                self.message.set_text("Task was deleted; nothing was changed.")
            else:
                self.message.set_text("Task updated locally.")
            self.refresh()
        except (ValueError, sqlite3.Error, OSError) as error:
            self.message.set_text(f"Edit failed: {error}")

    def on_restore(self, _button, task_id):
        try:
            if self.store.restore_deleted_task(task_id):
                self.message.set_text("Task restored with original completion history.")
            else:
                self.message.set_text("This task is no longer in Trash.")
            self.refresh()
        except (ValueError, sqlite3.Error, OSError) as error:
            self.message.set_text(f"Restore failed; task remains in Trash: {error}")

    def on_delete(self, _button, task_id):
        dialog = Adw.AlertDialog.new(
            "Move this task to Trash?",
            "The task can be restored later from the local Trash view."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Move to Trash")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self.on_delete_response, task_id)
        dialog.present(self)

    def on_delete_response(self, _dialog, response, task_id):
        if response == "delete":
            try:
                if self.store.delete_task(task_id):
                    self.message.set_text("Task moved to local Trash; restore it from the Trash view.")
                else:
                    self.message.set_text("Task no longer exists; nothing was deleted.")
                self.refresh()
            except (sqlite3.Error, ValueError) as error:
                self.message.set_text(f"Delete failed: {error}")

    def on_close(self, *_args):
        self.store.close()
        return False


class TasksApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.goreecloud.tasks",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        window = self.props.active_window
        if not window:
            window = TasksWindow(self)
        window.present()


if __name__ == "__main__":
    sys.exit(TasksApp().run(sys.argv))
