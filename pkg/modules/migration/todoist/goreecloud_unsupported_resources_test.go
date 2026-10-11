// GoreeCloud Tasks Todoist unsupported-source-loss regression tests.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"encoding/json"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestTodoistPreflightDoesNotSilentlyDiscardGeoOrCollaboration(t *testing.T) {
	for _, tc := range []struct {
		name string
		edit func(*sync)
		match string
	}{
		{
			name: "location reminder",
			edit: func(s *sync) { s.LocationReminders = []json.RawMessage{json.RawMessage(`{"id":"geo-reminder"}`)} },
			match: "location reminder",
		},
		{
			name: "location saved with no reminders",
			edit: func(s *sync) { s.Locations = []json.RawMessage{json.RawMessage(`["Home","40","-73"]`)} },
			match: "location",
		},
		{
			name: "shared project loses access permissions",
			edit: func(s *sync) { s.Projects[0].Shared = true },
			match: "shared project permissions",
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			source := validGoreeCloudTodoistSnapshot()
			tc.edit(source)
			require.ErrorContains(t, validateTodoistSync(source), tc.match)
			projects, err := convertTodoistToVikunja(source, nil)
			require.Nil(t, projects)
			require.ErrorContains(t, err, tc.match)
		})
	}
}

func TestTodoistDecodesGeoResourcesForPreflight(t *testing.T) {
	var source sync
	err := json.Unmarshal([]byte(`{"reminders_location":[{"id":"r1"}],"locations":[["Office","1","2"]]}`), &source)
	require.NoError(t, err)
	require.Len(t, source.LocationReminders, 1)
	require.Len(t, source.Locations, 1)
	require.ErrorContains(t, validateTodoistSync(&source), "location")
}
