// Provider pagination integrity regressions.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestRequireUnseenTodoistCursor(t *testing.T) {
	seen := make(map[string]bool)
	require.NoError(t, requireUnseenTodoistCursor("", seen))
	require.Empty(t, seen)
	require.NoError(t, requireUnseenTodoistCursor("page-2", seen))
	require.NoError(t, requireUnseenTodoistCursor("page-3", seen))
	require.Equal(t, map[string]bool{"page-2": true, "page-3": true}, seen)
	require.ErrorContains(t, requireUnseenTodoistCursor("page-2", seen), "cursor repeated")
}
