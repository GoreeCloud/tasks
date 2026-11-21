"""Offscreen native QML loading smoke; no network or user-data request."""
import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from main import TasksBackend


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication([])
    backend = TasksBackend("http://127.0.0.1:8000", "")
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("tasksBackend", backend)
    errors = []
    engine.warnings.connect(lambda warnings: errors.extend(str(x) for x in warnings))
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
    app.processEvents()
    if errors or not engine.rootObjects():
        raise RuntimeError("Qt Quick load failed: " + "; ".join(errors))
    from PySide6.QtQuick import QQuickItem
    root = engine.rootObjects()[0]
    surface = root.findChild(QQuickItem, "taskLoginSurface")
    password = root.findChild(QQuickItem, "taskLoginToken")
    if not surface or not password or not surface.isVisible():
        raise RuntimeError("Private sign-in must be visible without a token")
    if password.property("passwordMasked") is not True:
        raise RuntimeError("The API token input must mask its characters")
    # Real QML reactivity without any live network connection.
    backend.refresh = lambda: None
    backend.connectToServer("http://127.0.0.1:8000",
                            "ci-development-only-token-at-least-32")
    app.processEvents()
    if surface.isVisible():
        raise RuntimeError("Private workspace did not open after in-memory token entry")
    backend.disconnect()
    app.processEvents()
    if not surface.isVisible() or backend.tasks or backend.habits:
        raise RuntimeError("Disconnect did not restore empty private login state")
    if errors:
        raise RuntimeError("Qt Quick runtime warning: " + "; ".join(errors))
    print("Qt Quick offscreen login/workspace/logout and masked token load succeeded")


if __name__ == "__main__":
    main()
