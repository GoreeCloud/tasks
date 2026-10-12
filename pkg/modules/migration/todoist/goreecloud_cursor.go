// Provider pagination integrity safeguards.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import "fmt"

// requireUnseenTodoistCursor rejects a repeated nonempty pagination cursor.
// This prevents loops or duplicate reads from being mistaken for a full source.
func requireUnseenTodoistCursor(next string, seen map[string]bool) error {
	if next == "" {
		return nil
	}
	if seen[next] {
		return fmt.Errorf("todoist migration: upstream pagination cursor repeated")
	}
	seen[next] = true
	return nil
}
