#!/usr/bin/env python3
"""Real mapped GTK window geometry check; synthetic Tasks data only.

Run under xvfb-run. No screenshots or production profile access.
"""
import os
from pathlib import Path
import sys
import tempfile


def main(width):
    if not os.environ.get("DISPLAY"):
        raise RuntimeError("Use xvfb-run to supply a synthetic X display")
    if width not in (600, 940):
        raise ValueError("Supported synthetic QA widths: 600 and 940")

    with tempfile.TemporaryDirectory(prefix="goreecloud-tasks-gtk-layout-") as tmp:
        os.environ["XDG_DATA_HOME"] = tmp
        os.environ["XDG_CONFIG_HOME"] = tmp
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from store import TaskStore
        from app import TasksApp, TasksWindow
        from gi.repository import GLib

        store = TaskStore()
        project_id = store.add_project("Synthetic client project")
        store.add_task("First synthetic task", priority=1, project_id=project_id)
        store.add_task("Second synthetic task", priority=2)
        store.close()

        class LayoutApp(TasksApp):
            result = None
            exception = None

            def do_activate(self):
                self.window = TasksWindow(self)
                self.window.set_default_size(width, 480 if width == 600 else 760)
                self.window.present()
                GLib.timeout_add(800, self.verify_window)

            def verify_window(self):
                try:
                    window = self.window
                    measured = window.get_width()
                    compact = width == 600
                    assert 600 <= measured <= (650 if compact else 1000), measured
                    assert window.get_height() >= 480
                    assert window.navigation_rail.get_visible() is not compact
                    assert window.list_box.get_height() > 0
                    assert window.list_box.get_first_child() is not None
                    assert window.browse_view.get_selected() == window.view.get_selected()
                    # Navigation must operate even when the sidebar is collapsed.
                    window.browse_view.set_selected(window.view_names.index("Today"))
                    assert window.heading.get_label() == "Today"
                    window.browse_project.set_selected(1)
                    assert window.heading.get_label() == "Synthetic client project"
                    assert window.selected_project_id() == project_id
                    self.result = (measured, window.get_height())
                except Exception as error:
                    self.exception = error
                finally:
                    self.window.close()
                    self.quit()
                return GLib.SOURCE_REMOVE

        app = LayoutApp()
        code = app.run([])
        if app.exception is not None:
            raise app.exception
        assert app.result is not None and code == 0
        print(f"GTK4_MAPPED_LAYOUT_PASS width={width} allocated={app.result}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 600)
