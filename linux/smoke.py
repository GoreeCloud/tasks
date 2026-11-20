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
    backend = TasksBackend("http://127.0.0.1:8000", "ci-development-only-token-at-least-32")
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("tasksBackend", backend)
    errors = []
    engine.warnings.connect(lambda warnings: errors.extend(str(x) for x in warnings))
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
    app.processEvents()
    if errors or not engine.rootObjects():
        raise RuntimeError("Qt Quick load failed: " + "; ".join(errors))
    print("Qt Quick offscreen load succeeded")


if __name__ == "__main__":
    main()
