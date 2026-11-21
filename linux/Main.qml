import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 1080
    height: 760
    minimumWidth: 710
    minimumHeight: 540
    title: "GoreeCloud Tasks"
    color: "#F6F7FB"

    // Reviewed GoreeCloud UI semantic alpha tokens, not a separate product palette.
    property color gcBrand: "#2346CA"
    property color gcCanvas: "#F6F7FB"
    property color gcText: "#1B2030"
    property color gcSoft: "#505B70"

    function projectNames() {
        var output = ["Inbox"]
        var current = tasksBackend ? tasksBackend.projects : []
        for (var i = 0; i < current.length; i++)
            output.push(current[i].name)
        return output
    }

    function taskNames() {
        var output = ["Standalone task"]
        var current = tasksBackend ? tasksBackend.allTasks : []
        for (var i = 0; i < current.length; i++)
            if (!current[i].completed_at) output.push(current[i].title)
        return output
    }
    function taskId(index) {
        var current = tasksBackend ? tasksBackend.allTasks : []
        var active = []
        for (var i = 0; i < current.length; i++)
            if (!current[i].completed_at) active.push(current[i].id)
        return index > 0 && index <= active.length ? active[index - 1] : ""
    }
    function taskIndex(id) {
        var current = tasksBackend ? tasksBackend.allTasks : []
        var position = 1
        for (var i = 0; i < current.length; i++) {
            if (current[i].completed_at) continue
            if (current[i].id === id) return position
            position++
        }
        return 0
    }
    function projectId(index) {
        var current = tasksBackend ? tasksBackend.projects : []
        return index > 0 && index <= current.length ? current[index - 1].id : ""
    }

    function projectIndex(id) {
        var current = tasksBackend ? tasksBackend.projects : []
        for (var i = 0; i < current.length; i++) {
            if (current[i].id === id) return i + 1
        }
        return 0
    }

    header: ToolBar {
        background: Rectangle { color: "white" }
        RowLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 14
            Label { text: "◈"; font.pixelSize: 27; color: window.gcBrand }
            ColumnLayout {
                spacing: 0
                Label { text: "GoreeCloud"; font.bold: true; font.pixelSize: 18; color: window.gcText }
                Label { text: "T A S K S"; font.pixelSize: 9; color: window.gcSoft }
            }
            Item { Layout.fillWidth: true }
            Label {
                text: tasksBackend ? tasksBackend.status : "Disconnected"
                color: window.gcSoft
            }
            Button { text: "Refresh"; onClicked: tasksBackend.refresh() }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        Rectangle {
            Layout.preferredWidth: 214
            Layout.fillHeight: true
            radius: 20
            color: "white"
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 8
                Label { text: "WORKSPACE"; font.bold: true; font.pixelSize: 11; color: window.gcSoft }
                Button { text: "Inbox"; Layout.fillWidth: true; onClicked: tasksBackend.setView("inbox") }
                Button { text: "Today"; Layout.fillWidth: true; onClicked: tasksBackend.setView("today") }
                Button { text: "Upcoming"; Layout.fillWidth: true; onClicked: tasksBackend.setView("upcoming") }
                Button { text: "Completed"; Layout.fillWidth: true; onClicked: tasksBackend.setView("completed") }
                Label {
                    text: "PROJECTS"; font.bold: true; font.pixelSize: 11
                    color: window.gcSoft; Layout.topMargin: 20
                }
                Button {
                    text: "All projects"
                    Layout.fillWidth: true
                    onClicked: tasksBackend.setProjectFilter("")
                }
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    Column {
                        width: 175
                        spacing: 4
                        Repeater {
                            model: tasksBackend ? tasksBackend.projects : []
                            Button {
                                required property var modelData
                                text: modelData.name
                                width: 175
                                onClicked: tasksBackend.setProjectFilter(modelData.id)
                            }
                        }
                    }
                }
                TextField {
                    id: projectName
                    Layout.fillWidth: true
                    maximumLength: 120
                    placeholderText: "New project"
                    Accessible.name: "New project name"
                    onAccepted: projectButton.clicked()
                }
                Button {
                    id: projectButton
                    Layout.fillWidth: true
                    enabled: projectName.text.trim().length > 0
                    text: "+ Add project"
                    onClicked: {
                        tasksBackend.addProject(projectName.text)
                        projectName.text = ""
                    }
                }
                Label { text: "Native Qt Quick 6.12"; font.pixelSize: 11; color: window.gcSoft }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 13
            Label { text: "Your tasks"; font.pixelSize: 32; font.bold: true; color: window.gcText }
            Label { text: "A clear place for what matters."; font.pixelSize: 13; color: window.gcSoft }

            TextField {
                id: search
                Layout.fillWidth: true
                placeholderText: "Search by title, notes or tags"
                Accessible.name: "Search tasks"
                onTextChanged: tasksBackend.setSearch(text)
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 190
                radius: 18
                color: "white"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 7
                    TextField {
                        id: newTitle
                        Layout.fillWidth: true
                        placeholderText: "What needs to get done?"
                        maximumLength: 240
                        Accessible.name: "New task title"
                        onAccepted: addButton.clicked()
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 9
                        TextField {
                            id: dueDate
                            Layout.preferredWidth: 130
                            placeholderText: "YYYY-MM-DD"
                            Accessible.name: "Task due date"
                        }
                        ComboBox { id: priority; model: ["P1","P2","P3","P4"]; currentIndex: 1 }
                        ComboBox { id: repeat; model: ["None","Daily","Weekly","Monthly"] }
                        ComboBox { id: taskProject; Layout.fillWidth: true; model: window.projectNames() }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        ComboBox {
                            id: taskParent
                            Layout.preferredWidth: 165
                            model: window.taskNames()
                            Accessible.name: "Subtask parent"
                        }
                        TextField {
                            id: newTags
                            Layout.fillWidth: true
                            placeholderText: "Tags: home, work..."
                            Accessible.name: "Task tags"
                        }
                        Button {
                            id: addButton
                            text: "+ Add task"
                            enabled: newTitle.text.trim().length > 0
                            onClicked: {
                                tasksBackend.addTaskDetailed(newTitle.text, "", priority.currentIndex + 1,
                                    dueDate.text, repeat.currentText.toLowerCase(),
                                    window.projectId(taskProject.currentIndex), newTags.text,
                                    window.taskId(taskParent.currentIndex))
                                newTitle.text = ""
                            }
                        }
                    }
                }
            }

            Label {
                visible: tasksBackend && tasksBackend.error.length > 0
                text: tasksBackend ? tasksBackend.error : ""
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
                model: tasksBackend ? tasksBackend.tasks : []
                ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    required property var modelData
                    width: taskList.width
                    height: 79
                    color: "white"
                    radius: 14
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 13
                        spacing: 10
                        CheckBox {
                            checked: Boolean(modelData.completed_at)
                            Accessible.name: (checked ? "Reopen " : "Complete ") + modelData.title
                            onClicked: {
                                if (modelData.completed_at)
                                    tasksBackend.reopenTask(modelData.id, modelData.version)
                                else
                                    tasksBackend.completeTask(modelData.id, modelData.version)
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Button {
                                text: modelData.title
                                flat: true
                                Layout.fillWidth: true
                                onClicked: editor.openFor(modelData)
                                Accessible.name: "Edit " + modelData.title
                            }
                            Label {
                                text: (modelData.parent_id ? "↳ Subtask · " : "") +
                                      (modelData.due_date || "No due date") +
                                    (modelData.recurrence !== "none" ? " · " + modelData.recurrence : "")
                                textFormat: Text.PlainText
                                color: window.gcSoft
                                font.pixelSize: 12
                            }
                        }
                        Label { text: "P" + modelData.priority; color: window.gcSoft }
                    }
                }
                Label {
                    anchors.centerIn: parent
                    visible: taskList.count === 0
                    text: "Nothing in this view."
                    color: window.gcSoft
                }
            }
        }
    }

    Dialog {
        id: editor
        title: "Edit task"
        modal: true
        x: Math.max(10, (window.width - width) / 2)
        y: Math.max(10, (window.height - height) / 2)
        width: Math.min(window.width - 30, 510)
        height: Math.min(window.height - 35, 585)
        standardButtons: Dialog.Save | Dialog.Cancel
        property var editing: ({})
        function openFor(task) {
            editing = task
            editTitle.text = task.title
            editNotes.text = task.description || ""
            editDue.text = task.due_date || ""
            editTags.text = (task.tags || []).join(", ")
            editPriority.currentIndex = task.priority - 1
            editRepeat.currentIndex = ["none","daily","weekly","monthly"].indexOf(task.recurrence)
            editProject.currentIndex = window.projectIndex(task.project_id)
            editParent.currentIndex = window.taskIndex(task.parent_id)
            open()
        }
        onAccepted: {
            tasksBackend.editTaskDetailed(editing.id, editing.version, editTitle.text,
                editNotes.text, editPriority.currentIndex + 1, editDue.text,
                editRepeat.currentText.toLowerCase(), window.projectId(editProject.currentIndex),
                editTags.text, window.taskId(editParent.currentIndex))
        }
        contentItem: ScrollView {
            clip: true
            ColumnLayout {
                width: editor.width - 45
                spacing: 10
                Label { text: "Title"; color: window.gcText }
                TextField { id: editTitle; Layout.fillWidth: true; maximumLength: 240 }
                Label { text: "Notes"; color: window.gcText }
                TextArea {
                    id: editNotes
                    Layout.fillWidth: true
                    Layout.preferredHeight: 100
                    wrapMode: TextEdit.Wrap
                }
                Label { text: "Due date (YYYY-MM-DD)"; color: window.gcText }
                TextField { id: editDue; Layout.fillWidth: true }
                Label { text: "Priority"; color: window.gcText }
                ComboBox { id: editPriority; Layout.fillWidth: true; model: ["P1","P2","P3","P4"] }
                Label { text: "Repeat"; color: window.gcText }
                ComboBox { id: editRepeat; Layout.fillWidth: true; model: ["None","Daily","Weekly","Monthly"] }
                Label { text: "Project"; color: window.gcText }
                ComboBox { id: editProject; Layout.fillWidth: true; model: window.projectNames() }
                Label { text: "Parent task"; color: window.gcText }
                ComboBox {
                    id: editParent
                    Layout.fillWidth: true
                    model: window.taskNames()
                    Accessible.name: "Parent task"
                }
                Label { text: "Tags (comma-separated)"; color: window.gcText }
                TextField { id: editTags; Layout.fillWidth: true }
                Button {
                    text: "Delete task..."
                    onClicked: {
                        deleteConfirm.editing = editor.editing
                        editor.close()
                        deleteConfirm.open()
                    }
                }
            }
        }
    }

    Dialog {
        id: deleteConfirm
        title: "Delete task permanently?"
        modal: true
        x: Math.max(10, (window.width - width) / 2)
        y: Math.max(10, (window.height - height) / 2)
        width: Math.min(window.width - 30, 420)
        standardButtons: Dialog.Yes | Dialog.No
        property var editing: ({})
        onAccepted: tasksBackend.deleteTask(editing.id, editing.version)
        Label {
            text: "This action cannot be undone."
            wrapMode: Text.WordWrap
            color: window.gcText
        }
    }
}
