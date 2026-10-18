// Vikunja is a to-do list application to facilitate your life.
// Copyright 2018-present Vikunja and contributors. All rights reserved.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

package webtests

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"testing"
	"time"

	"code.vikunja.io/api/pkg/config"
	"code.vikunja.io/api/pkg/db"
	"code.vikunja.io/api/pkg/events"
	"code.vikunja.io/api/pkg/modules/migration"
	migrationHandler "code.vikunja.io/api/pkg/modules/migration/handler"
	"code.vikunja.io/api/pkg/routes"

	"github.com/labstack/echo/v5"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupMigrationTestEnv(t *testing.T) *echo.Echo {
	t.Helper()
	_, err := setupTestEnv()
	require.NoError(t, err)

	// SetupTests cannot own migration_status without an import cycle.
	s := db.NewSession()
	require.NoError(t, s.Sync2(&migration.Status{}))
	_, err = s.Where("1 = 1").Delete(&migration.Status{})
	require.NoError(t, err)
	require.NoError(t, s.Commit())
	require.NoError(t, s.Close())

	previousSecret := config.ServiceSecret.GetString()
	config.ServiceSecret.Set("goreecloud-huma-test-only-secret")
	t.Cleanup(func() { config.ServiceSecret.Set(previousSecret) })
	config.MigrationTodoistEnable.Set(true)
	config.MigrationTrelloEnable.Set(true)
	config.MigrationMicrosoftTodoEnable.Set(true)
	t.Cleanup(func() {
		config.MigrationTodoistEnable.Set(false)
		config.MigrationTrelloEnable.Set(false)
		config.MigrationMicrosoftTodoEnable.Set(false)
	})

	e := routes.NewEcho()
	routes.RegisterRoutes(e)
	return e
}

func signedTodoistMigrationState(t *testing.T, e *echo.Echo, token string) string {
	t.Helper()
	rec := humaRequest(t, e, http.MethodGet, "/api/v2/migration/todoist/auth", "", token, "")
	require.Equal(t, http.StatusOK, rec.Code)
	var response struct {
		URL string `json:"url"`
	}
	require.NoError(t, json.Unmarshal(rec.Body.Bytes(), &response))
	parsed, err := url.Parse(response.URL)
	require.NoError(t, err)
	require.Equal(t, "todoist.com", parsed.Host)
	state := parsed.Query().Get("state")
	require.NotEmpty(t, state)
	return state
}

func signedTodoistMigrationBody(code, state string) string {
	return fmt.Sprintf(`{"code":%q,"state":%q}`, code, state)
}

func TestHumaMigrationOAuth(t *testing.T) {
	e := setupMigrationTestEnv(t)
	token := humaTokenFor(t, &testuser1)

	for _, name := range []string{"todoist", "trello", "microsoft-todo"} {
		t.Run(name+" auth url", func(t *testing.T) {
			rec := humaRequest(t, e, http.MethodGet, "/api/v2/migration/"+name+"/auth", "", token, "")
			require.Equal(t, http.StatusOK, rec.Code, "body: %s", rec.Body.String())
			assert.Contains(t, rec.Body.String(), `"url":"http`, "auth url must be returned; body: %s", rec.Body.String())
		})

		t.Run(name+" status - never migrated", func(t *testing.T) {
			rec := humaRequest(t, e, http.MethodGet, "/api/v2/migration/"+name+"/status", "", token, "")
			require.Equal(t, http.StatusOK, rec.Code, "body: %s", rec.Body.String())
			assert.Contains(t, rec.Body.String(), `"started_at":"0001-01-01T00:00:00Z"`, "body: %s", rec.Body.String())
		})
	}

	t.Run("migrate kicks off the migration", func(t *testing.T) {
		events.ClearDispatchedEvents()
		state := signedTodoistMigrationState(t, e, token)
		rec := humaRequest(t, e, http.MethodPost, "/api/v2/migration/todoist/migrate", signedTodoistMigrationBody("test-code", state), token, "")
		// 200, not the wrapper's POST default 201: this queues a job, it does
		// not create a REST resource.
		require.Equal(t, http.StatusOK, rec.Code, "body: %s", rec.Body.String())
		assert.Contains(t, rec.Body.String(), `"message":"Migration was started successfully."`)
		events.AssertDispatched(t, &migrationHandler.MigrationRequestedEvent{})
	})
}

func TestHumaMigrationOAuth_AlreadyRunning(t *testing.T) {
	e := setupMigrationTestEnv(t)
	token := humaTokenFor(t, &testuser1)

	s := db.NewSession()
	_, err := s.Insert(&migration.Status{
		UserID:       testuser1.ID,
		MigratorName: "todoist",
		StartedAt:    time.Now(),
	})
	require.NoError(t, err)
	require.NoError(t, s.Commit())
	_ = s.Close()

	state := signedTodoistMigrationState(t, e, token)
	rec := humaRequest(t, e, http.MethodPost, "/api/v2/migration/todoist/migrate", signedTodoistMigrationBody("test-code", state), token, "")
	assert.Equal(t, http.StatusPreconditionFailed, rec.Code, "body: %s", rec.Body.String())
}

func TestHumaMigrationOAuth_RejectsMissingAndTamperedState(t *testing.T) {
	e := setupMigrationTestEnv(t)
	token := humaTokenFor(t, &testuser1)
	state := signedTodoistMigrationState(t, e, token)
	otherUserToken := humaTokenFor(t, &testuser2)

	for _, tc := range []struct {
		name  string
		state string
		token string
	}{
		{"missing", "", token},
		{"tampered", state + "x", token},
		{"other-user", state, otherUserToken},
	} {
		t.Run(tc.name, func(t *testing.T) {
			events.ClearDispatchedEvents()
			rec := humaRequest(t, e, http.MethodPost, "/api/v2/migration/todoist/migrate",
				signedTodoistMigrationBody("test-code", tc.state), tc.token, "")
			require.Equal(t, http.StatusBadRequest, rec.Code, "body: %s", rec.Body.String())
			require.NotContains(t, rec.Body.String(), "internal server error")
		})
	}
}

func TestHumaMigrationOAuth_Unauthenticated(t *testing.T) {
	e := setupMigrationTestEnv(t)

	t.Run("auth", func(t *testing.T) {
		rec := humaRequest(t, e, http.MethodGet, "/api/v2/migration/todoist/auth", "", "", "")
		assert.Equal(t, http.StatusUnauthorized, rec.Code, "body: %s", rec.Body.String())
	})
	t.Run("status", func(t *testing.T) {
		rec := humaRequest(t, e, http.MethodGet, "/api/v2/migration/todoist/status", "", "", "")
		assert.Equal(t, http.StatusUnauthorized, rec.Code, "body: %s", rec.Body.String())
	})
	t.Run("migrate", func(t *testing.T) {
		rec := humaRequest(t, e, http.MethodPost, "/api/v2/migration/todoist/migrate", `{"code":"x"}`, "", "")
		assert.Equal(t, http.StatusUnauthorized, rec.Code, "body: %s", rec.Body.String())
	})
}

func TestHumaMigrationOAuth_Disabled(t *testing.T) {
	_, err := setupTestEnv()
	require.NoError(t, err)
	e := routes.NewEcho()
	routes.RegisterRoutes(e)
	token := humaTokenFor(t, &testuser1)

	rec := humaRequest(t, e, http.MethodGet, "/api/v2/migration/todoist/auth", "", token, "")
	assert.Equal(t, http.StatusNotFound, rec.Code,
		"migration routes must not be registered when the flag is off; body: %s", rec.Body.String())
}
