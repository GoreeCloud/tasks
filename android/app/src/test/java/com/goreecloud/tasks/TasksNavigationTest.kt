package com.goreecloud.tasks

import org.junit.Assert.assertEquals
import org.junit.Test

class TasksNavigationTest {
    @Test fun nativeTabsShowInboxTodayOrBrowseForOtherViews() {
        assertEquals("Inbox", TasksNavigation.tabFor("Open"))
        assertEquals("Today", TasksNavigation.tabFor("Today"))
        for (destination in listOf("Next 7 days", "Overdue", "Upcoming",
                "Priority", "Completed", "Project", "Trash")) {
            assertEquals("Browse", TasksNavigation.tabFor(destination))
        }
    }

    @Test fun screenTitleKeepsProjectContextAndDoesNotRenameData() {
        assertEquals("Inbox", TasksNavigation.title("Open", "Client Work"))
        assertEquals("Client Work", TasksNavigation.title("Project", "Client Work"))
        assertEquals("Trash", TasksNavigation.title("Trash", "Client Work"))
        assertEquals("Today", TasksNavigation.title("Today", "Inbox"))
    }
}
