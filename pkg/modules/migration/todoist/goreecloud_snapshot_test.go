// GoreeCloud Tasks initial-sync completeness regression tests.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"encoding/json"
	"strings"
	"testing"
)

func validInitialTodoistSnapshot() *sync {
	full := true
	return &sync{
		FullSync: &full,
		SyncToken: "fixture",
		Projects: []*project{},
		Items: []*item{},
		Labels: []*label{},
		Notes: []*note{},
		ProjectNotes: []*projectNote{},
		Reminders: []*reminder{},
		Sections: []*section{},
	}
}

func TestTodoistInitialSyncValidEmptyCollections(t *testing.T) {
	if err := validateTodoistInitialSnapshot(validInitialTodoistSnapshot()); err != nil {
		t.Fatalf("a full snapshot with empty collections must be valid: %v", err)
	}
}

func TestTodoistInitialSyncMetadataRequired(t *testing.T) {
	checks := []struct {
		name string
		edit func(*sync)
	}{
		{"missing full-sync marker", func(s *sync) { s.FullSync = nil }},
		{"incremental response", func(s *sync) { no := false; s.FullSync = &no }},
		{"missing token", func(s *sync) { s.SyncToken = "" }},
		{"blank token", func(s *sync) { s.SyncToken = "   " }},
		{"missing projects", func(s *sync) { s.Projects = nil }},
		{"missing items", func(s *sync) { s.Items = nil }},
		{"missing labels", func(s *sync) { s.Labels = nil }},
		{"missing notes", func(s *sync) { s.Notes = nil }},
		{"missing project notes", func(s *sync) { s.ProjectNotes = nil }},
		{"missing reminders", func(s *sync) { s.Reminders = nil }},
		{"missing sections", func(s *sync) { s.Sections = nil }},
	}
	if validateTodoistInitialSnapshot(nil) == nil {
		t.Fatal("nil snapshot must fail")
	}
	for _, tc := range checks {
		t.Run(tc.name, func(t *testing.T) {
			input := validInitialTodoistSnapshot()
			tc.edit(input)
			if err := validateTodoistInitialSnapshot(input); err == nil {
				t.Fatal("incomplete response must fail before conversion")
			}
		})
	}
}

func TestTodoistInitialSyncJSONCannotMasqueradeAsEmptyAccount(t *testing.T) {
	var incomplete sync
	if err := json.Unmarshal([]byte(`{"full_sync":true,"sync_token":"token","projects":[],"items":[]}`), &incomplete); err != nil {
		t.Fatal(err)
	}
	if err := validateTodoistInitialSnapshot(&incomplete); err == nil || !strings.Contains(err.Error(), "collections") {
		t.Fatalf("omitted resources must fail: %v", err)
	}
	var complete sync
	if err := json.Unmarshal([]byte(`{"full_sync":true,"sync_token":"token","projects":[],"items":[],"labels":[],"notes":[],"project_notes":[],"reminders":[],"sections":[]}`), &complete); err != nil {
		t.Fatal(err)
	}
	if err := validateTodoistInitialSnapshot(&complete); err != nil {
		t.Fatalf("explicit empty source arrays should be accepted: %v", err)
	}
}
