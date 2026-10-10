// Todoist OAuth authorization URL construction.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"fmt"
	"net/url"
	"strings"

	"code.vikunja.io/api/pkg/config"
)

// makeTodoistAuthorizationURL returns an error if fresh unpredictable state
// cannot be generated. A fixed or missing OAuth state is never a safe fallback.
// This does not itself validate the state on the redirect callback.
func makeTodoistAuthorizationURL(generateState func(int64) (string, error)) (string, error) {
	state, err := generateState(32)
	if err != nil || strings.TrimSpace(state) == "" {
		return "", fmt.Errorf("todoist migration: cannot generate OAuth state")
	}
	u := url.URL{Scheme: "https", Host: "todoist.com", Path: "/oauth/authorize"}
	u.RawQuery = url.Values{
		"client_id": {config.MigrationTodoistClientID.GetString()},
		"scope": {"data:read"},
		"state": {state},
	}.Encode()
	return u.String(), nil
}
