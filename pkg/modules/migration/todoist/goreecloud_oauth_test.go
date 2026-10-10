// OAuth state creation regressions for the Todoist importer.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"errors"
	"net/url"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestMakeTodoistAuthorizationURLRequiresSecureState(t *testing.T) {
	for _, tc := range []struct {
		name string
		generate func(int) (string, error)
	}{
		{"generator error", func(int) (string, error) { return "", errors.New("secret diagnostic") }},
		{"empty state", func(int) (string, error) { return "", nil }},
		{"whitespace state", func(int) (string, error) { return "  ", nil }},
	} {
		t.Run(tc.name, func(t *testing.T) {
			uri, err := makeTodoistAuthorizationURL(tc.generate)
			require.Empty(t, uri)
			require.ErrorContains(t, err, "cannot generate OAuth state")
			require.NotContains(t, err.Error(), "secret diagnostic")
		})
	}
}

func TestMakeTodoistAuthorizationURLKeepsStateAndReadScope(t *testing.T) {
	uri, err := makeTodoistAuthorizationURL(func(length int) (string, error) {
		require.Equal(t, 32, length)
		return "fresh-test-state", nil
	})
	require.NoError(t, err)
	u, err := url.Parse(uri)
	require.NoError(t, err)
	require.Equal(t, "https", u.Scheme)
	require.Equal(t, "todoist.com", u.Host)
	require.Equal(t, "/oauth/authorize", u.Path)
	require.Equal(t, "fresh-test-state", u.Query().Get("state"))
	require.Equal(t, "data:read", u.Query().Get("scope"))
}
