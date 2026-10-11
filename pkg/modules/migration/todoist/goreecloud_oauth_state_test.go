// User-bound Todoist OAuth state security regression tests.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

const oauthTestNonce = "0123456789abcdef0123456789abcdef"

func TestTodoistSignedOAuthStateIsUserBoundAndTimeLimited(t *testing.T) {
	now := time.Date(2026, 10, 10, 12, 0, 0, 0, time.UTC)
	state, err := signTodoistState(42, oauthTestNonce, now, "fixture-key-not-production")
	require.NoError(t, err)
	require.NoError(t, verifyTodoistState(state, 42, now.Add(9*time.Minute), "fixture-key-not-production"))
	require.Error(t, verifyTodoistState(state, 43, now.Add(time.Minute), "fixture-key-not-production"))
	require.Error(t, verifyTodoistState(state, 42, now.Add(11*time.Minute), "fixture-key-not-production"))
	require.Error(t, verifyTodoistState(state, 42, now.Add(-time.Minute), "fixture-key-not-production"))
	require.Error(t, verifyTodoistState(state, 42, now, "another-key"))
	require.Error(t, verifyTodoistState(state+"x", 42, now, "fixture-key-not-production"))
	require.Error(t, verifyTodoistState(strings.Replace(state, "42", "41", 1), 42, now, "fixture-key-not-production"))
	require.Error(t, verifyTodoistState("", 42, now, "fixture-key-not-production"))
	require.Error(t, verifyTodoistState(state, 42, now, ""))
}

func TestTodoistSignedOAuthStateRefusesWeakInputs(t *testing.T) {
	now := time.Now()
	for _, tc := range []struct {
		uid int64
		nonce string
		key string
	}{
		{0, oauthTestNonce, "fixture-key"},
		{42, "short", "fixture-key"},
		{42, oauthTestNonce+".", "fixture-key"},
		{42, oauthTestNonce, ""},
	} {
		state, err := signTodoistState(tc.uid, tc.nonce, now, tc.key)
		require.Error(t, err)
		require.Empty(t, state)
	}
}

func TestTodoistOAuthHasNoUnsignedAuthorizationFallback(t *testing.T) {
	var migration Migration
	require.Empty(t, migration.AuthURL())
}
