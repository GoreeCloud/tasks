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
    property bool habitsMode: false

    function clearPrivateInputs() {
        // Dialogs may hold an unsaved title/description even after backend
        // task rows were cleared. Erase those local UI buffers on disconnect.
        editor.close()
        editHabitDialog.close()
        habitHistoryDialog.close()
        deleteHabitConfirm.close()
        deleteConfirm.close()
        editor.editing = ({})
        editHabitDialog.habit = ({})
        habitHistoryDialog.habit = ({})
        deleteHabitConfirm.habit = ({})
        deleteConfirm.editing = ({})
        projectName.text = ""
        newTitle.text = ""
        dueDate.text = ""
        newTags.text = ""
        habitName.text = ""
        habitNotes.text = ""
        editTitle.text = ""
        editNotes.text = ""
        editDue.text = ""
        editTags.text = ""
        editHabitName.text = ""
        editHabitNotes.text = ""
        search.text = ""
        window.habitsMode = false
        loginToken.text = ""
    }

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
            Button {
                text: "Refresh"
                enabled: tasksBackend ? tasksBackend.connected : false
                onClicked: tasksBackend.refresh()
            }
            Button {
                text: "Disconnect"
                visible: tasksBackend ? tasksBackend.connected : false
                onClicked: {
                    window.clearPrivateInputs()
                    tasksBackend.disconnect()
                }
            }
        }
    }

    RowLayout {
        visible: tasksBackend ? tasksBackend.connected : false
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
                Button { text: "Inbox"; Layout.fillWidth: true; onClicked: {window.habitsMode=false;tasksBackend.setView("inbox")} }
                Button { text: "Today"; Layout.fillWidth: true; onClicked: {window.habitsMode=false;tasksBackend.setView("today")} }
                Button { text: "Upcoming"; Layout.fillWidth: true; onClicked: {window.habitsMode=false;tasksBackend.setView("upcoming")} }
                Button { text: "Completed"; Layout.fillWidth: true; onClicked: {window.habitsMode=false;tasksBackend.setView("completed")} }
                Button {
                    text: "Daily habits"
                    Layout.fillWidth: true
                    Accessible.name: "Open daily habits"
                    onClicked: {window.habitsMode=true;tasksBackend.refreshHabits()}
                }
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
            visible: !window.habitsMode
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
                        ComboBox { id: repeat; model: ["None","Daily","Weekdays","Weekly","Every 2 weeks","Monthly","Yearly"] }
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
                                    dueDate.text, ["none","daily","weekdays","weekly","biweekly","monthly","yearly"][repeat.currentIndex],
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

        ColumnLayout {
            visible: window.habitsMode
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 13
            Label {
                text: "Daily habits"
                font.pixelSize: 32
                font.bold: true
                color: window.gcText
            }
            Label {
                text: "Private daily check-ins, stored on your self-hosted server."
                color: window.gcSoft
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 135
                color: "white"
                radius: 16
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    TextField {
                        id: habitName
                        Layout.fillWidth: true
                        maximumLength: 120
                        placeholderText: "A new habit, e.g. reading"
                        Accessible.name: "Habit name"
                        onAccepted: addHabitButton.clicked()
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField {
                            id: habitNotes
                            Layout.fillWidth: true
                            maximumLength: 16000
                            placeholderText: "Notes (optional)"
                            Accessible.name: "Habit notes"
                        }
                        Button {
                            id: addHabitButton
                            text: "+ Add habit"
                            enabled: habitName.text.trim().length > 0
                            onClicked: {
                                tasksBackend.addHabit(habitName.text, habitNotes.text)
                                habitName.text = ""; habitNotes.text = ""
                            }
                        }
                    }
                }
            }
            RowLayout {
                Label {
                    text: "Check-ins"
                    font.bold: true; font.pixelSize: 18
                    color: window.gcText
                    Layout.fillWidth: true
                }
                Button { text: "Refresh habits"; onClicked: tasksBackend.refreshHabits() }
            }
            ListView {
                id: habitsList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 8
                model: tasksBackend ? tasksBackend.habits : []
                ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    required property var modelData
                    width: habitsList.width
                    height: 91
                    color: "white"
                    radius: 14
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 10
                        CheckBox {
                            checked: Boolean(modelData.checked_in_today)
                            Accessible.name: (checked ? "Undo today's check-in for " : "Check in today for ") + modelData.name
                            onClicked: tasksBackend.toggleHabit(
                                modelData.id, modelData.version, !checked
                            )
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Label {
                                text: modelData.name
                                font.bold: true
                                font.pixelSize: 15
                                textFormat: Text.PlainText
                                color: window.gcText
                            }
                            Label {
                                text: modelData.current_streak + " day streak · " + modelData.total_checkins + " check-ins"
                                font.pixelSize: 12
                                color: window.gcSoft
                            }
                            Label {
                                text: modelData.description
                                visible: Boolean(modelData.description)
                                font.pixelSize: 11
                                color: window.gcSoft
                                elide: Label.ElideRight
                                Layout.maximumWidth: 500
                            }
                        }
                        Button {
                            text: "Edit..."
                            Accessible.name: "Edit habit " + modelData.name
                            onClicked: {
                                editHabitDialog.habit = modelData
                                editHabitDialog.open()
                            }
                        }
                        Button {
                            text: "History..."
                            Accessible.name: "View check-in history for " + modelData.name
                            onClicked: {
                                habitHistoryDialog.habit = modelData
                                habitHistoryDialog.open()
                            }
                        }
                        Button {
                            text: "Delete..."
                            onClicked: {
                                deleteHabitConfirm.habit = modelData
                                deleteHabitConfirm.open()
                            }
                        }
                    }
                }
                Label {
                    anchors.centerIn: parent
                    visible: habitsList.count === 0
                    text: "No daily habits yet."
                    color: window.gcSoft
                }
            }
        }
    }

    Rectangle {
        id: loginSurface
        objectName: "taskLoginSurface"
        anchors.fill: parent
        visible: tasksBackend ? !tasksBackend.connected : true
        color: window.gcCanvas
        z: 2

        ColumnLayout {
            width: Math.min(parent.width - 40, 510)
            anchors.centerIn: parent
            spacing: 14
            Label {
                text: "GoreeCloud Tasks"
                font.pixelSize: 29
                font.bold: true
                color: window.gcText
                Layout.fillWidth: true
            }
            Label {
                text: "Connect to your private self-hosted Tasks API."
                color: window.gcSoft
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Label {
                text: "Token and task data remain in memory. Never paste a token in a desktop launcher."
                color: window.gcSoft
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            TextField {
                id: loginUrl
                Accessible.name: "Tasks API server URL"
                Layout.fillWidth: true
                text: tasksBackend ? tasksBackend.serverUrl : "http://127.0.0.1:8000"
                placeholderText: "https://tasks.example.com"
                selectByMouse: true
                inputMethodHints: Qt.ImhNoPredictiveText
            }
            TextField {
                id: loginToken
                objectName: "taskLoginToken"
                Accessible.name: "Tasks API token"
                Layout.fillWidth: true
                maximumLength: 512
                echoMode: TextInput.Password
                readonly property bool passwordMasked: echoMode === TextInput.Password
                inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText
                placeholderText: "Paste your 32+ character API token"
                onAccepted: loginButton.clicked()
            }
            Button {
                id: loginButton
                objectName: "taskLoginButton"
                text: "Connect"
                Layout.fillWidth: true
                enabled: tasksBackend && loginToken.text.length >= 32
                onClicked: {
                    if (!tasksBackend) return
                    tasksBackend.connectToServer(loginUrl.text, loginToken.text)
                    loginToken.text = ""
                }
            }
            Label {
                text: tasksBackend ? tasksBackend.error : "Unavailable Tasks backend"
                visible: text.length > 0
                color: "#B3261E"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Accessible.role: Accessible.AlertMessage
            }
            Label {
                text: "Development preview · HTTPS required outside loopback"
                color: window.gcSoft
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
        }
    }

    Dialog {
        id: editHabitDialog
        title: "Edit daily habit"
        modal: true
        x: Math.max(10, (window.width - width) / 2)
        y: Math.max(10, (window.height - height) / 2)
        width: Math.min(window.width - 30, 460)
        standardButtons: Dialog.Save | Dialog.Cancel
        property var habit: ({})
        onOpened: {
            editHabitName.text = habit.name || ""
            editHabitNotes.text = habit.description || ""
        }
        onAccepted: tasksBackend.editHabit(
            habit.id, habit.version, editHabitName.text, editHabitNotes.text
        )
        contentItem: ColumnLayout {
            spacing: 10
            TextField {
                id: editHabitName
                Layout.fillWidth: true
                maximumLength: 120
                Accessible.name: "Edit habit name"
                placeholderText: "Habit name"
            }
            TextArea {
                id: editHabitNotes
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                wrapMode: TextArea.Wrap
                Accessible.name: "Edit habit notes"
                placeholderText: "Notes (optional)"
            }
            Label {
                Layout.fillWidth: true
                text: "A stale habit revision will be rejected; existing check-ins are preserved."
                wrapMode: Text.WordWrap
                color: window.gcSoft
            }
        }
    }

    Dialog {
        id: habitHistoryDialog
        title: "Habit check-in history"
        modal: true
        x: Math.max(10, (window.width - width) / 2)
        y: Math.max(10, (window.height - height) / 2)
        width: Math.min(window.width - 30, 460)
        height: Math.min(window.height - 30, 460)
        standardButtons: Dialog.Close
        property var habit: ({})
        onOpened: tasksBackend.loadHabitHistory(habit.id, 0)
        onClosed: tasksBackend.clearHabitHistory()
        contentItem: ColumnLayout {
            spacing: 10
            Label {
                text: habitHistoryDialog.habit.name || "Habit"
                textFormat: Text.PlainText
                font.bold: true
                color: window.gcText
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            Label {
                text: "Recorded check-in dates, newest first. 30 dates per page."
                color: window.gcSoft
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            ListView {
                id: habitHistoryList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 6
                model: tasksBackend ? tasksBackend.habitHistory : []
                ScrollBar.vertical: ScrollBar {}
                delegate: Label {
                    required property var modelData
                    text: modelData
                    textFormat: Text.PlainText
                    color: window.gcText
                    font.pixelSize: 14
                }
            }
            Label {
                text: "No recorded check-ins on this page."
                visible: habitHistoryList.count === 0
                color: window.gcSoft
            }
            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: "Newer dates"
                    enabled: tasksBackend ? tasksBackend.habitHistoryOffset > 0 : false
                    onClicked: tasksBackend.loadHabitHistory(
                        habitHistoryDialog.habit.id,
                        Math.max(0, tasksBackend.habitHistoryOffset - 30)
                    )
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: "Page " + (tasksBackend ? Math.floor(tasksBackend.habitHistoryOffset / 30) + 1 : 1)
                    color: window.gcSoft
                }
                Button {
                    text: "Older dates"
                    enabled: tasksBackend ? tasksBackend.habitHistoryHasMore : false
                    onClicked: tasksBackend.loadHabitHistory(
                        habitHistoryDialog.habit.id, tasksBackend.habitHistoryOffset + 30
                    )
                }
            }
        }
    }

    Dialog {
        id: deleteHabitConfirm
        title: "Delete habit and all check-ins?"
        modal: true
        x: Math.max(10, (window.width - width) / 2)
        y: Math.max(10, (window.height - height) / 2)
        width: Math.min(window.width - 30, 420)
        standardButtons: Dialog.Yes | Dialog.No
        property var habit: ({})
        onAccepted: tasksBackend.deleteHabit(habit.id, habit.version)
        Label {
            text: "This permanently erases the habit history."
            wrapMode: Text.WordWrap
            color: window.gcText
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
            editRepeat.currentIndex = ["none","daily","weekdays","weekly","biweekly","monthly","yearly"].indexOf(task.recurrence)
            editProject.currentIndex = window.projectIndex(task.project_id)
            editParent.currentIndex = window.taskIndex(task.parent_id)
            open()
        }
        onAccepted: {
            tasksBackend.editTaskDetailed(editing.id, editing.version, editTitle.text,
                editNotes.text, editPriority.currentIndex + 1, editDue.text,
                ["none","daily","weekdays","weekly","biweekly","monthly","yearly"][editRepeat.currentIndex], window.projectId(editProject.currentIndex),
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
                ComboBox { id: editRepeat; Layout.fillWidth: true; model: ["None","Daily","Weekdays","Weekly","Every 2 weeks","Monthly","Yearly"] }
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
