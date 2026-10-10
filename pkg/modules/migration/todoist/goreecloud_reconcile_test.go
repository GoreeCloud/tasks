// GoreeCloud Tasks migration reconciliation regressions.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"testing"

	"code.vikunja.io/api/pkg/models"
	"github.com/stretchr/testify/require"
)

func TestGoreeCloudTodoistConvertedCountsMatchSource(t *testing.T) {
	source := validGoreeCloudTodoistSnapshot()
	result, err := convertTodoistToVikunja(source, nil)
	require.NoError(t, err)
	require.NoError(t, reconcileConvertedTodoistCounts(source, result))
	got := convertedImportCounts(result)
	require.Equal(t, 1, got.projects)
	require.Equal(t, 1, got.sections)
	require.Equal(t, 2, got.tasks)
	require.Equal(t, 1, got.subtasks)
	require.Equal(t, 1, got.reminders)
}

func TestGoreeCloudTodoistConvertedCountsRejectMissingRecords(t *testing.T) {
	cases := []struct {
		name string
		drop func(*sync, []*models.ProjectWithTasksAndBuckets) []*models.ProjectWithTasksAndBuckets
		expected string
	}{
		{"project", func(_ *sync, result []*models.ProjectWithTasksAndBuckets) []*models.ProjectWithTasksAndBuckets {
			return result[:1]
		}, "projects count mismatch"},
		{"section", func(_ *sync, result []*models.ProjectWithTasksAndBuckets) []*models.ProjectWithTasksAndBuckets {
			result[1].Buckets = nil
			return result
		}, "sections count mismatch"},
		{"task", func(_ *sync, result []*models.ProjectWithTasksAndBuckets) []*models.ProjectWithTasksAndBuckets {
			result[1].Tasks = nil
			return result
		}, "tasks count mismatch"},
		{"subtask", func(_ *sync, result []*models.ProjectWithTasksAndBuckets) []*models.ProjectWithTasksAndBuckets {
			result[1].Tasks[0].RelatedTasks[models.RelationKindSubtask] = nil
			return result
		}, "tasks count mismatch"},
		{"reminder", func(_ *sync, result []*models.ProjectWithTasksAndBuckets) []*models.ProjectWithTasksAndBuckets {
			result[1].Tasks[0].RelatedTasks[models.RelationKindSubtask][0].Reminders = nil
			return result
		}, "reminders count mismatch"},
		{"attachment", func(source *sync, result []*models.ProjectWithTasksAndBuckets) []*models.ProjectWithTasksAndBuckets {
			source.Notes[0].FileAttachment = &fileAttachment{FileName: "lost.txt"}
			return result
		}, "attachments count mismatch"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			source := validGoreeCloudTodoistSnapshot()
			result, err := convertTodoistToVikunja(source, nil)
			require.NoError(t, err)
			result = tc.drop(source, result)
			require.ErrorContains(t, reconcileConvertedTodoistCounts(source, result), tc.expected)
		})
	}
}
