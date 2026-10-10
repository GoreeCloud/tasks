// Regression tests for GoreeCloud Tasks Todoist conversion.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"code.vikunja.io/api/pkg/config"
	"code.vikunja.io/api/pkg/models"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestGoreeCloudSubtaskNotesAndReminders(t *testing.T) {
	src := &sync{
		Projects: []*project{{ID: "p1", Name: "Personal"}},
		Items: []*item{
			{ID: "parent", ProjectID: "p1", Content: "Parent task"},
			{ID: "child", ProjectID: "p1", ParentID: "parent", Content: "Child task", Description: "Original"},
		},
		Notes:     []*note{{ID: "note-1", ItemID: "child", Content: "Preserved note"}},
		Reminders: []*reminder{{ID: "r1", ItemID: "child", Due: &dueDate{Date: "2026-10-10"}}},
	}
	result, err := convertTodoistToVikunja(src, nil)
	require.NoError(t, err)
	require.Len(t, result, 2)
	require.Len(t, result[1].Tasks, 1)
	children := result[1].Tasks[0].RelatedTasks[models.RelationKindSubtask]
	require.Len(t, children, 1)
	assert.Equal(t, "Original\nPreserved note", children[0].Description)
	require.Len(t, children[0].Reminders, 1)
}

func TestGoreeCloudNestedSubtaskRelations(t *testing.T) {
	src := &sync{
		Projects: []*project{{ID: "p1", Name: "Personal"}},
		Items: []*item{
			{ID: "parent", ProjectID: "p1", Content: "Parent"},
			{ID: "child", ProjectID: "p1", ParentID: "parent", Content: "Child"},
			{ID: "grandchild", ProjectID: "p1", ParentID: "child", Content: "Grandchild"},
		},
		Notes: []*note{{ID: "n1", ItemID: "grandchild", Content: "Nested note"}},
	}
	result, err := convertTodoistToVikunja(src, nil)
	require.NoError(t, err)
	require.Len(t, result, 2)
	require.Len(t, result[1].Tasks, 1)
	children := result[1].Tasks[0].RelatedTasks[models.RelationKindSubtask]
	require.Len(t, children, 1)
	grandkids := children[0].RelatedTasks[models.RelationKindSubtask]
	require.Len(t, grandkids, 1)
	assert.Equal(t, "Grandchild", grandkids[0].Title)
	assert.Equal(t, "Nested note", grandkids[0].Description)
}

func TestGoreeCloudAttachmentDownloadFailureStopsConversion(t *testing.T) {
	previous := config.OutgoingRequestsAllowNonRoutableIPs.GetBool()
	config.OutgoingRequestsAllowNonRoutableIPs.Set("true")
	t.Cleanup(func() { config.OutgoingRequestsAllowNonRoutableIPs.Set(previous) })

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	defer server.Close()

	source := &sync{
		Projects: []*project{{ID: "p1", Name: "Project"}},
		Items:    []*item{{ID: "task", ProjectID: "p1", Content: "Keep attachment"}},
		Notes: []*note{{
			ID: "note", ItemID: "task", Content: "Source note",
			FileAttachment: &fileAttachment{FileName: "required.txt", FileURL: server.URL},
		}},
	}
	result, err := convertTodoistToVikunja(source, nil)
	require.ErrorContains(t, err, "could not preserve attachment")
	require.Nil(t, result)
	assert.NotContains(t, err.Error(), server.URL)
}

func TestGoreeCloudEmptyAttachmentRejected(t *testing.T) {
	previous := config.OutgoingRequestsAllowNonRoutableIPs.GetBool()
	config.OutgoingRequestsAllowNonRoutableIPs.Set("true")
	t.Cleanup(func() { config.OutgoingRequestsAllowNonRoutableIPs.Set(previous) })

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	source := &sync{
		Projects: []*project{{ID: "p1", Name: "Project"}},
		Items: []*item{{ID: "task", ProjectID: "p1", Content: "Keep attachment"}},
		Notes: []*note{{ID: "note", ItemID: "task", FileAttachment: &fileAttachment{
			FileName: "empty.txt", FileURL: server.URL,
		}}},
	}
	result, err := convertTodoistToVikunja(source, nil)
	require.ErrorContains(t, err, "empty attachment")
	require.Nil(t, result)
	assert.NotContains(t, err.Error(), server.URL)
}
