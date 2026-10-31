#!/usr/bin/env python3
"""GoreeCloud Tasks — native GTK4 + libadwaita Linux client."""
import sys
from datetime import date
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk
from store import TaskStore

Adw.init()


class TasksWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="GoreeCloud Tasks", default_width=880, default_height=680)
        self.store = TaskStore()
        self.show_completed = False
        self.set_size_request(500, 410)
        css = Gtk.CssProvider()
        css.load_from_path(str(Path(__file__).with_name("style.css")))
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(display, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root)
        header = Adw.HeaderBar()
        header.add_css_class("flat")
        root.append(header)
        title = Gtk.Label(label="✦   GoreeCloud Tasks")
        title.add_css_class("title-3")
        header.set_title_widget(title)
        self.toggle_button = Gtk.ToggleButton(label="Show completed")
        self.toggle_button.connect("toggled", self.on_filter)
        header.pack_end(self.toggle_button)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(30)
        content.set_margin_end(30)
        root.append(content)
        label = Gtk.Label(label="Your focus, beautifully organized", xalign=0)
        label.add_css_class("title-1")
        content.append(label)
        subtitle = Gtk.Label(label="Capture a thought. Make progress. Everything stays on this device.", xalign=0)
        subtitle.add_css_class("dim-label")
        content.append(subtitle)

        entry_row = Gtk.Box(spacing=10)
        entry_row.set_margin_top(18)
        content.append(entry_row)
        self.entry = Gtk.Entry(placeholder_text="What needs to get done?")
        self.entry.set_hexpand(True)
        self.entry.set_max_length(240)
        self.entry.connect("activate", self.on_add)
        entry_row.append(self.entry)
        self.priority = Gtk.DropDown.new_from_strings(["P4 · Normal", "P3 · Medium", "P2 · High", "P1 · Urgent"])
        entry_row.append(self.priority)
        add = Gtk.Button(label="Add task")
        add.add_css_class("suggested-action")
        add.connect("clicked", self.on_add)
        entry_row.append(add)

        self.message = Gtk.Label(xalign=0)
        self.message.add_css_class("dim-label")
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
        self.refresh()

    def on_add(self, _widget):
        try:
            value = self.entry.get_text()
            priority = (4, 3, 2, 1)[self.priority.get_selected()]
            self.store.add_task(value, priority=priority)
            self.entry.set_text("")
            self.message.set_text("")
            self.refresh()
        except (ValueError, OSError) as error:
            self.message.set_text(str(error))

    def on_filter(self, _button):
        self.show_completed = self.toggle_button.get_active()
        self.refresh()

    def refresh(self):
        while (child := self.list_box.get_first_child()) is not None:
            self.list_box.remove(child)
        tasks = self.store.list_tasks(include_completed=self.show_completed)
        if not tasks:
            row = Adw.ActionRow(title="All clear here", subtitle="Add your first task above.")
            self.list_box.append(row)
        for task in tasks:
            row = Adw.ActionRow(title=task["title"],
                                subtitle="P{}{}".format(task["priority"],
                                    "  ·  Due " + task["due_date"] if task["due_date"] else ""))
            toggle = Gtk.CheckButton()
            toggle.set_active(bool(task["completed"]))
            toggle.set_valign(Gtk.Align.CENTER)
            toggle.update_property([Gtk.AccessibleProperty.LABEL], ["Complete " + task["title"]])
            toggle.connect("toggled", self.on_toggle, task["id"])
            row.add_prefix(toggle)
            delete = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Delete task")
            delete.set_valign(Gtk.Align.CENTER)
            delete.add_css_class("flat")
            delete.connect("clicked", self.on_delete, task["id"])
            row.add_suffix(delete)
            self.list_box.append(row)
        count = sum(not task["completed"] for task in self.store.list_tasks(include_completed=True))
        self.footer.set_text(f"{count} open task{'s' if count != 1 else ''} · Native Linux · Device-local SQLite")

    def on_toggle(self, check, task_id):
        self.store.complete_task(task_id, check.get_active())
        self.refresh()

    def on_delete(self, _button, task_id):
        self.store.delete_task(task_id)
        self.refresh()


class TasksApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.goreecloud.tasks", flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        window = self.props.active_window
        if not window:
            window = TasksWindow(self)
        window.present()


if __name__ == "__main__":
    sys.exit(TasksApp().run(sys.argv))
