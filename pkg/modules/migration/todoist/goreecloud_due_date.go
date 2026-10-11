// GoreeCloud Tasks Todoist due-date fidelity gate.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"fmt"
	"strings"
	"time"
)

// validateTodoistDueDate refuses floating wall-clock timestamps because the
// source user's timezone is not yet available in this importer. time.Parse
// would interpret them as UTC and silently change the user's local due time.
// An explicit RFC3339 offset/Z is a verifiable instant; all-day dates retain
// their existing calendar-date conversion pending native all-day support.
func validateTodoistDueDate(due *dueDate) error {
	if due == nil {
		return nil
	}
	if len(due.Date) == len("2006-01-02") {
		if _, err := time.Parse("2006-01-02", due.Date); err != nil {
			return fmt.Errorf("todoist migration: malformed all-day due date")
		}
		if due.Timezone != nil {
			return fmt.Errorf("todoist migration: all-day due date unexpectedly supplies a timezone")
		}
		return nil
	}

	_, err := time.Parse(time.RFC3339Nano, due.Date)
	if err != nil {
		if _, floatingErr := time.Parse("2006-01-02T15:04:05.999999999", due.Date); floatingErr == nil {
			return fmt.Errorf("todoist migration: floating due times require a source timezone preservation strategy")
		}
		return fmt.Errorf("todoist migration: malformed due timestamp")
	}

	switch timezone := due.Timezone.(type) {
	case nil:
		return nil
	case string:
		if strings.TrimSpace(timezone) == "" {
			return fmt.Errorf("todoist migration: empty source due timezone")
		}
		// Metadata has to be well-defined even though the absolute due instant
		// is already encoded in the RFC3339 timestamp.
		if _, err := time.LoadLocation(timezone); err != nil {
			return fmt.Errorf("todoist migration: unknown source due timezone")
		}
		return nil
	default:
		return fmt.Errorf("todoist migration: invalid source due timezone metadata")
	}
}
