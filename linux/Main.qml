import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 1020
    height: 720
    minimumWidth: 680
    minimumHeight: 500
    title: "GoreeCloud Tasks"
    color: "#F6F7FB"

    property color gcBrand: "#2346CA"
    property color gcCanvas: "#F6F7FB"
    property color gcText: "#1B2030"
    property color gcSoft: "#505B70"

    header: ToolBar {
        background: Rectangle { color: "white" }
        RowLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 16
            Label { text: "◈"; font.pixelSize: 27; color: window.gcBrand }
            ColumnLayout {
                spacing: 0
                Label { text: "GoreeCloud"; font.bold: true; font.pixelSize: 18; color: window.gcText }
                Label { text: "T A S K S"; font.pixelSize: 9; color: window.gcSoft }
            }
            Item { Layout.fillWidth: true }
            Label { text: tasksBackend.status; color: window.gcSoft }
            Button { text: "Refresh"; onClicked: tasksBackend.refresh() }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 24
        Rectangle {
            Layout.preferredWidth: 210
            Layout.fillHeight: true
            radius: 20
            color: "white"
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 24
                spacing: 14
                Label { text: "WORKSPACE"; font.bold: true; font.pixelSize: 11; color: window.gcSoft }
                Label { text: "My Tasks"; font.pixelSize: 22; font.bold: true; color: window.gcText }
                Label { text: "Private by design"; color: window.gcSoft }
                Item { Layout.fillHeight: true }
                Label {
                    text: "Native Qt Quick 6.12"
                    color: window.gcSoft
                    font.pixelSize: 11
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 18
            Label { text: "Your tasks"; font.pixelSize: 34; font.bold: true; color: window.gcText }
            Label { text: "A clear place for what matters."; font.pixelSize: 14; color: window.gcSoft }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 112
                radius: 18
                color: "white"
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10
                    TextField {
                        id: newTitle
                        Layout.fillWidth: true
                        placeholderText: "Add a task"
                        maximumLength: 240
                        Accessible.name: "New task title"
                        onAccepted: addButton.clicked()
                    }
                    TextField { id: dueDate; Layout.preferredWidth: 145; placeholderText: "YYYY-MM-DD"; Accessible.name: "Due date" }
                    Button {
                        id: addButton
                        text: "Add"
                        enabled: newTitle.text.trim().length > 0
                        onClicked: {
                            tasksBackend.addTask(newTitle.text, priority.currentIndex + 1, dueDate.text, repeat.currentText.toLowerCase())
                            newTitle.text = ""
                        }
                    }
                }
                RowLayout {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.leftMargin: 16
                    anchors.bottomMargin: 8
                    Label { text: "Priority"; color: window.gcSoft }
                    ComboBox { id: priority; model: ["P1", "P2", "P3", "P4"]; currentIndex: 1 }
                    Label { text: "Repeat"; color: window.gcSoft }
                    ComboBox { id: repeat; model: ["None", "Daily", "Weekly", "Monthly"] }
                }
            }

            Label {
                visible: tasksBackend.error.length > 0
                text: tasksBackend.error
                color: "#B3261E"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Accessible.role: Accessible.AlertMessage
            }

            ListView {
                id: taskList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 8
                model: tasksBackend.tasks
                ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    required property var modelData
                    width: taskList.width
                    height: 76
                    color: "white"
                    radius: 14
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 14
                        Button {
                            text: "○"
                            Accessible.name: "Complete " + modelData.title
                            onClicked: tasksBackend.completeTask(modelData.id, modelData.version)
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: modelData.title; textFormat: Text.PlainText; font.bold: true; color: window.gcText; elide: Text.ElideRight; Layout.fillWidth: true }
                            Label { text: modelData.due_date || "No due date"; color: window.gcSoft; font.pixelSize: 12 }
                        }
                        Label { text: "P" + modelData.priority; color: window.gcSoft }
                    }
                }
                Label {
                    anchors.centerIn: parent
                    visible: taskList.count === 0
                    text: "Nothing on the list yet. Add your first task."
                    color: window.gcSoft
                }
            }
        }
    }
}
