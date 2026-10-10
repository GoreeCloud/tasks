// Regression tests for GoreeCloud Tasks Todoist import integrity.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/require"
)

func validGoreeCloudTodoistSnapshot() *sync {
	return &sync{
		Projects: []*project{{ID: "p1", Name: "Personal"}},
		Sections: []*section{{ID: "s1", ProjectID: "p1", Name: "Work"}},
		Labels: []*label{{ID: "l1", Name: "Important"}},
		Items: []*item{
			{ID: "root", ProjectID: "p1", SectionID: "s1", Content: "Root", Labels: []string{"Important"}},
			{ID: "child", ProjectID: "p1", ParentID: "root", Content: "Child"},
		},
		Notes: []*note{{ID: "n1", ItemID: "child", Content: "Preserve"}},
		ProjectNotes: []*projectNote{{ID: "pn1", ProjectID: "p1", Content: "Project description"}},
		Reminders: []*reminder{{ID: "r1", ItemID: "child", Due: &dueDate{Date: "2026-10-10"}}},
	}
}

func TestGoreeCloudTodoistPreflightValid(t *testing.T) {
	require.NoError(t, validateTodoistSync(validGoreeCloudTodoistSnapshot()))
}

func TestGoreeCloudTodoistPreflightRejectsIncompleteSource(t *testing.T) {
	cases := []struct {
		name string
		edit func(*sync)
		message string
	}{
		{"nil project", func(s *sync) { s.Projects[0] = nil }, "project with missing"},
		{"duplicate project", func(s *sync) { s.Projects = append(s.Projects, &project{ID: "p1"}) }, "duplicate project"},
		{"nested project", func(s *sync) { s.Projects[0].ParentID = "p2" }, "hierarchy"},
		{"orphan task", func(s *sync) { s.Items[0].ProjectID = "missing" }, "missing project"},
		{"duplicate task", func(s *sync) { s.Items[1].ID = "root" }, "duplicate task"},
		{"orphan subtask", func(s *sync) { s.Items[1].ParentID = "missing" }, "missing parent"},
		{"subtask cycle", func(s *sync) { s.Items[0].ParentID = "child" }, "cyclic"},
		{"foreign section", func(s *sync) { s.Items[1].SectionID = "missing" }, "section"},
		{"orphan section", func(s *sync) { s.Sections[0].ProjectID = "missing" }, "section"},
		{"orphan label", func(s *sync) { s.Items[0].Labels = []string{"missing"} }, "missing label"},
		{"orphan note", func(s *sync) { s.Notes[0].ItemID = "missing" }, "note"},
		{"orphan project note", func(s *sync) { s.ProjectNotes[0].ProjectID = "missing" }, "project note"},
		{"unsupported project note attachment", func(s *sync) { s.ProjectNotes[0].FileAttachment = &fileAttachment{FileName: "important.pdf"} }, "preservation"},
		{"orphan reminder", func(s *sync) { s.Reminders[0].ItemID = "missing" }, "reminder"},
		{"reminder with no due", func(s *sync) { s.Reminders[0].Due = nil }, "due timestamp"},
		{"unsupported recurrence", func(s *sync) { s.Items[0].Due = &dueDate{Date: "2026-10-10", IsRecurring: true, String: "every monday"} }, "unsupported recurring"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			s := validGoreeCloudTodoistSnapshot()
			tc.edit(s)
			err := validateTodoistSync(s)
			require.Error(t, err)
			require.True(t, strings.Contains(err.Error(), tc.message), "unexpected preflight result: %s", err)
			result, conversionError := convertTodoistToVikunja(s, nil)
			require.Error(t, conversionError, "conversion must not proceed on an invalid source graph")
			require.Nil(t, result)
		})
	}
}

func TestGoreeCloudTodoistPreflightRejectsNilSnapshot(t *testing.T) {
	require.Error(t, validateTodoistSync(nil))
	result, err := convertTodoistToVikunja(nil, nil)
	require.Error(t, err)
	require.Nil(t, result)
}
