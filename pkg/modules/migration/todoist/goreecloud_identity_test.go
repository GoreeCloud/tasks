// Todoist identity preservation regression coverage.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestGoreeCloudTodoistRecordIdentityPreflight(t *testing.T) {
	cases := []struct {
		name string
		alter func(*sync)
		want string
	}{
		{"missing note ID", func(s *sync) { s.Notes[0].ID = "" }, "note ID missing or repeated"},
		{"duplicate note ID", func(s *sync) { s.Notes = append(s.Notes, &note{ID: "n1", ItemID: "root"}) }, "note ID missing or repeated"},
		{"missing project note ID", func(s *sync) { s.ProjectNotes[0].ID = "" }, "project-note ID missing or repeated"},
		{"duplicate project note ID", func(s *sync) { s.ProjectNotes = append(s.ProjectNotes, &projectNote{ID: "pn1", ProjectID: "p1"}) }, "project-note ID missing or repeated"},
		{"missing reminder ID", func(s *sync) { s.Reminders[0].ID = "" }, "reminder ID missing or repeated"},
		{"duplicate reminder ID", func(s *sync) { s.Reminders = append(s.Reminders, &reminder{ID: "r1", ItemID: "root", Due: &dueDate{Date: "2026-10-10"}}) }, "reminder ID missing or repeated"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			source := validGoreeCloudTodoistSnapshot()
			tc.alter(source)
			require.ErrorContains(t, validateTodoistSync(source), tc.want)
			structure, err := convertTodoistToVikunja(source, nil)
			require.ErrorContains(t, err, tc.want)
			require.Nil(t, structure)
		})
	}
}
