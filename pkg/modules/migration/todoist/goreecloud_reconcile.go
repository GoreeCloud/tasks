// GoreeCloud Tasks import count checks.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"fmt"

	"code.vikunja.io/api/pkg/models"
)

// importCounts is a metadata-only summary. It deliberately never contains
// source titles, note bodies, signed attachment URLs or credentials.
type importCounts struct {
	projects int
	sections int
	tasks int
	subtasks int
	reminders int
	attachments int
}

// expectedImportCounts derives counts from a preflight-validated source.
func expectedImportCounts(source *sync) importCounts {
	var counts importCounts
	counts.projects = len(source.Projects)
	counts.tasks = len(source.Items)
	for _, section := range source.Sections {
		if !section.IsDeleted {
			counts.sections++
		}
	}
	for _, task := range source.Items {
		if task.ParentID != "" {
			counts.subtasks++
		}
	}
	counts.reminders = len(source.Reminders)
	for _, note := range source.Notes {
		if note.FileAttachment != nil {
			counts.attachments++
		}
	}
	return counts
}

func convertedImportCounts(projects []*models.ProjectWithTasksAndBuckets) importCounts {
	var counts importCounts
	if len(projects) == 0 {
		return counts
	}
	// The first project is the synthetic Todoist import container.
	counts.projects = len(projects) - 1
	var countTask func(*models.Task, bool)
	countTask = func(task *models.Task, child bool) {
		if task == nil {
			return
		}
		counts.tasks++
		if child {
			counts.subtasks++
		}
		counts.reminders += len(task.Reminders)
		counts.attachments += len(task.Attachments)
		for _, nested := range task.RelatedTasks[models.RelationKindSubtask] {
			countTask(nested, true)
		}
	}
	for _, project := range projects[1:] {
		counts.sections += len(project.Buckets)
		for _, task := range project.Tasks {
			if task != nil {
				countTask(&task.Task, false)
			}
		}
	}
	return counts
}

// reconcileConvertedTodoistCounts runs before any destination DB mutation.
// Note/comment contents, exact dates and post-insert identities still require
// full source-to-destination reconciliation as a separate Stable gate.
func reconcileConvertedTodoistCounts(source *sync, converted []*models.ProjectWithTasksAndBuckets) error {
	want, got := expectedImportCounts(source), convertedImportCounts(converted)
	for _, metric := range []struct{name string; want, got int}{
		{"projects", want.projects, got.projects},
		{"sections", want.sections, got.sections},
		{"tasks", want.tasks, got.tasks},
		{"subtasks", want.subtasks, got.subtasks},
		{"reminders", want.reminders, got.reminders},
		{"attachments", want.attachments, got.attachments},
	} {
		if metric.want != metric.got {
			return fmt.Errorf("todoist migration: %s count mismatch before insertion: source %d, converted %d", metric.name, metric.want, metric.got)
		}
	}
	return nil
}
