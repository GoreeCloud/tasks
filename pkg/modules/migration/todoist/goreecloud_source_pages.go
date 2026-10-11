// GoreeCloud Tasks Todoist source response validation.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import "fmt"

// validateTodoistCompletedPage runs before the importer sorts or dereferences
// records returned by the completed-task API. Reject incomplete pages instead
// of panicking, losing task metadata or reporting an apparent successful import.
func validateTodoistCompletedPage(page *paginatedCompletedTasks) error {
	if page == nil || page.Items == nil {
		return fmt.Errorf("todoist migration: completed task page omitted the items collection")
	}
	for _, task := range page.Items {
		if task == nil || task.TaskID == "" || task.ProjectID == "" {
			return fmt.Errorf("todoist migration: completed task has a missing identity or project")
		}
		if task.CompletedDate.IsZero() {
			return fmt.Errorf("todoist migration: completed task has no completion timestamp")
		}
		if project, exists := page.Projects[task.ProjectID]; exists {
			if project == nil {
				return fmt.Errorf("todoist migration: completed task references an invalid project record")
			}
			if project.IsDeleted {
				return fmt.Errorf("todoist migration: completed task belongs to a deleted project and cannot be preserved")
			}
		}
	}
	return nil
}

// validateTodoistCompletedDetail ensures the task detail endpoint returned the
// *requested* item. A valid-looking response for the wrong task or project must
// not be appended to the source snapshot.
func validateTodoistCompletedDetail(expected *doneItem, actual *item) error {
	if expected == nil || actual == nil ||
		expected.TaskID == "" || expected.ProjectID == "" ||
		actual.ID != expected.TaskID || actual.ProjectID != expected.ProjectID {
		return fmt.Errorf("todoist migration: completed task detail does not match requested source identity")
	}
	return nil
}

// validateTodoistArchivedPage runs before dereferencing archived project IDs.
// A malformed page must never trigger a panic or silently discard source data.
func validateTodoistArchivedPage(page *paginatedProjects) error {
	if page == nil || page.Results == nil {
		return fmt.Errorf("todoist migration: archived project page omitted the results collection")
	}
	seen := make(map[string]bool, len(page.Results))
	for _, project := range page.Results {
		if project == nil || project.ID == "" {
			return fmt.Errorf("todoist migration: archived project with a missing identity")
		}
		if seen[project.ID] {
			return fmt.Errorf("todoist migration: duplicate archived project identity")
		}
		seen[project.ID] = true
	}
	return nil
}
