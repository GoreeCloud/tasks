// Todoist import source-data integrity regression tests.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

func validTodoistCompletedPage() *paginatedCompletedTasks {
	return &paginatedCompletedTasks{
		Items: []*doneItem{{TaskID: "t1", ProjectID: "p1", CompletedDate: time.Date(2026, 10, 10, 12, 0, 0, 0, time.UTC)}},
		Projects: map[string]*project{"p1": {ID: "p1", Name: "Personal"}},
	}
}

func TestValidateTodoistCompletedPage(t *testing.T) {
	require.NoError(t, validateTodoistCompletedPage(validTodoistCompletedPage()))
	require.ErrorContains(t, validateTodoistCompletedPage(nil), "missing completed")
	tests := []struct {
		name   string
		mutate func(*paginatedCompletedTasks)
	}{
		{"nil task", func(p *paginatedCompletedTasks) { p.Items[0] = nil }},
		{"missing task ID", func(p *paginatedCompletedTasks) { p.Items[0].TaskID = "" }},
		{"missing project ID", func(p *paginatedCompletedTasks) { p.Items[0].ProjectID = "" }},
		{"missing completion date", func(p *paginatedCompletedTasks) { p.Items[0].CompletedDate = time.Time{} }},
		{"nil project metadata", func(p *paginatedCompletedTasks) { p.Projects["p1"] = nil }},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			page := validTodoistCompletedPage()
			tt.mutate(page)
			require.Error(t, validateTodoistCompletedPage(page))
		})
	}
}

func TestValidateTodoistCompletedDetail(t *testing.T) {
	source := validTodoistCompletedPage().Items[0]
	require.NoError(t, validateTodoistCompletedDetail(source, &item{ID: "t1", ProjectID: "p1"}))
	require.Error(t, validateTodoistCompletedDetail(nil, &item{ID: "t1", ProjectID: "p1"}))
	require.Error(t, validateTodoistCompletedDetail(source, nil))
	require.ErrorContains(t, validateTodoistCompletedDetail(source, &item{ID: "another", ProjectID: "p1"}), "does not match")
	require.ErrorContains(t, validateTodoistCompletedDetail(source, &item{ID: "t1", ProjectID: "another"}), "does not match")
}

func TestValidateTodoistArchivedPage(t *testing.T) {
	require.NoError(t, validateTodoistArchivedPage(&paginatedProjects{
		Results: []*project{{ID: "p1"}, {ID: "p2"}},
	}))
	require.NoError(t, validateTodoistArchivedPage(&paginatedProjects{}))
	require.ErrorContains(t, validateTodoistArchivedPage(nil), "missing archived")
	require.Error(t, validateTodoistArchivedPage(&paginatedProjects{Results: []*project{nil}}))
	require.Error(t, validateTodoistArchivedPage(&paginatedProjects{Results: []*project{{ID: ""}}}))
	require.ErrorContains(t, validateTodoistArchivedPage(&paginatedProjects{
		Results: []*project{{ID: "p1"}, {ID: "p1"}},
	}), "duplicate")
}
