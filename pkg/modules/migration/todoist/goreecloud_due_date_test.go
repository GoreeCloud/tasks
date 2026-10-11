// GoreeCloud Tasks Todoist due-date fidelity regressions.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

func TestTodoistDueDateFidelityGate(t *testing.T) {
	for _, tc := range []struct {
		name string
		due *dueDate
		wantError string
	}{
		{"nil due is optional", nil, ""},
		{"all-day", &dueDate{Date: "2026-10-10"}, ""},
		{"UTC fixed", &dueDate{Date: "2026-10-10T15:30:00Z", Timezone: "America/Chicago"}, ""},
		{"fractional fixed", &dueDate{Date: "2026-10-10T15:30:00.123456Z"}, ""},
		{"offset fixed", &dueDate{Date: "2026-10-10T10:30:00-05:00"}, ""},
		{"floating local", &dueDate{Date: "2026-10-10T10:30:00"}, "floating due times"},
		{"floating fractional", &dueDate{Date: "2026-10-10T10:30:00.000000"}, "floating due times"},
		{"malformed due", &dueDate{Date: "not-a-date"}, "malformed"},
		{"nonexistent day", &dueDate{Date: "2026-02-30"}, "malformed"},
		{"all-day with timezone", &dueDate{Date: "2026-10-10", Timezone: "America/Chicago"}, "all-day"},
		{"malformed timezone", &dueDate{Date: "2026-10-10T15:30:00Z", Timezone: 123}, "metadata"},
		{"unknown timezone", &dueDate{Date: "2026-10-10T15:30:00Z", Timezone: "Invalid/TimeZone"}, "unknown"},
		{"empty timezone", &dueDate{Date: "2026-10-10T15:30:00Z", Timezone: ""}, "empty"},
	} {
		t.Run(tc.name,func(t *testing.T) {
			err := validateTodoistDueDate(tc.due)
			if tc.wantError == "" {
				require.NoError(t, err)
			} else {
				require.ErrorContains(t, err, tc.wantError)
			}
		})
	}
}

func TestTodoistFixedTimestampPreservesInstantAndPrecision(t *testing.T) {
	for _, example := range []string{
		"2026-10-10T15:30:00.123456Z",
		"2026-10-10T10:30:00-05:00",
		"2026-10-10T16:30:00+01:00",
	} {
		actual, err := parseDate(example)
		require.NoError(t, err)
		expected, err := time.Parse(time.RFC3339Nano, example)
		require.NoError(t, err)
		require.True(t, actual.Equal(expected))
		require.Equal(t, expected.Nanosecond(), actual.Nanosecond())
	}
	allDay, err := parseDate("2026-10-10")
	require.NoError(t, err)
	require.Equal(t, 23, allDay.Hour())
	require.Equal(t, 59, allDay.Minute())
}

func TestTodoistPreflightRejectsUnresolvableTaskAndReminderDueTimes(t *testing.T) {
	source := validGoreeCloudTodoistSnapshot()
	source.Items[0].Due = &dueDate{Date:"2026-10-10T10:30:00"}
	require.ErrorContains(t, validateTodoistSync(source), "floating due times")
	source = validGoreeCloudTodoistSnapshot()
	source.Reminders[0].Due = &dueDate{Date:"2026-10-10T10:30:00"}
	require.ErrorContains(t, validateTodoistSync(source), "floating due times")
}
