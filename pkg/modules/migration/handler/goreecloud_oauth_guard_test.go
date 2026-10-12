// OAuth validation must occur before claiming migration work.
// SPDX-License-Identifier: AGPL-3.0-or-later
package handler

import (
	"fmt"
	"net/http"
	"testing"

	"code.vikunja.io/api/pkg/db"
	"code.vikunja.io/api/pkg/events"
	"code.vikunja.io/api/pkg/modules/migration"
	"code.vikunja.io/api/pkg/user"
	"github.com/labstack/echo/v5"
	"github.com/stretchr/testify/require"
)

type rejectingOAuthMigrator struct{ stubMigrator }

func (m *rejectingOAuthMigrator) AuthURLForUser(_ *user.User) (string, error) {
	return "", nil
}

func (m *rejectingOAuthMigrator) ValidateOAuthState(_ *user.User) error {
	return fmt.Errorf("unsafe callback state")
}

func TestStartMigrationRejectsUnverifiedOAuthBeforeClaim(t *testing.T) {
	clearMigrationStatus(t)
	events.ClearDispatchedEvents()
	currentUser := getTestUser(t)

	err := StartMigration(&rejectingOAuthMigrator{stubMigrator{NameValue: "oauth-test"}}, currentUser)
	require.Error(t, err)
	var apiError *echo.HTTPError
	require.ErrorAs(t, err, &apiError)
	require.Equal(t, http.StatusBadRequest, apiError.Code)
	require.NotContains(t, err.Error(), "unsafe callback state", "provider error details should not be disclosed")
	require.Empty(t, events.GetDispatchedEvents((&MigrationRequestedEvent{}).Name()))

	session := db.NewSession()
	defer session.Close()
	count, err := session.Where("user_id = ?", currentUser.ID).Count(&migration.Status{})
	require.NoError(t, err)
	require.Zero(t, count, "bad OAuth state must not create a claimed migration status")
}
