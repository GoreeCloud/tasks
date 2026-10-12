// GoreeCloud Tasks Todoist importer HTTP boundary.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"code.vikunja.io/api/pkg/modules/migration"
)

// decodeTodoistResponse rejects upstream HTTP failures before decoding.
// Neither response bodies nor request URLs are included in error diagnostics:
// upstream failures can expose credentials or private task data. This helper
// closes the response body even when decoding fails.
func decodeTodoistResponse(resp *http.Response, destination any, stage string) error {
	if resp == nil || resp.Body == nil {
		return fmt.Errorf("todoist migration: %s returned no response body", stage)
	}
	defer resp.Body.Close()

	if resp.StatusCode < http.StatusOK || resp.StatusCode >= http.StatusMultipleChoices {
		return fmt.Errorf(
			"todoist migration: %s: %w",
			stage,
			migration.NewErrUpstreamRequestFailed("todoist "+stage, resp.StatusCode, ""),
		)
	}
	decoder := json.NewDecoder(resp.Body)
	if err := decoder.Decode(destination); err != nil {
		return fmt.Errorf("todoist migration: %s could not be decoded: %w", stage, err)
	}
	// Do not accept multiple JSON values in a single upstream response.
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		return fmt.Errorf("todoist migration: %s has unexpected trailing JSON data", stage)
	}
	return nil
}
