// GoreeCloud Tasks full-source integrity gate.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"fmt"
	"strings"
)

// validateTodoistInitialSnapshot checks only the first Sync API response.
// Archived-project detail responses do not carry the same metadata.
func validateTodoistInitialSnapshot(source *sync) error {
	if source == nil || source.FullSync == nil || !*source.FullSync {
		return fmt.Errorf("todoist migration: initial response was not a confirmed full sync")
	}
	if strings.TrimSpace(source.SyncToken) == "" {
		return fmt.Errorf("todoist migration: initial response lacks a sync token")
	}
	// Missing/null collections must not be interpreted as an empty account.
	if source.Projects == nil || source.Items == nil || source.Labels == nil ||
		source.Notes == nil || source.ProjectNotes == nil ||
		source.Reminders == nil || source.Sections == nil {
		return fmt.Errorf("todoist migration: required source collections are absent")
	}
	return nil
}
