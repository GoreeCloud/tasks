// Source-boundary regression tests for Todoist HTTP responses.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"io"
	"net/http"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"
)

type trackedTodoistBody struct {
	io.Reader
	closed bool
}

func (b *trackedTodoistBody) Close() error {
	b.closed = true
	return nil
}

func TestDecodeTodoistResponseValid(t *testing.T) {
	body := &trackedTodoistBody{Reader: strings.NewReader(`{"value":"saved"}`)}
	response := &http.Response{StatusCode: http.StatusOK, Body: body}
	var decoded struct {
		Value string `json:"value"`
	}
	require.NoError(t, decodeTodoistResponse(response, &decoded, "task detail"))
	require.Equal(t, "saved", decoded.Value)
	require.True(t, body.closed, "the HTTP body must close on success")
}

func TestDecodeTodoistResponseRejectsUpstreamStatusWithoutBodyLeak(t *testing.T) {
	for _, status := range []int{http.StatusMovedPermanently, http.StatusUnauthorized, http.StatusTooManyRequests, http.StatusInternalServerError} {
		t.Run(http.StatusText(status), func(t *testing.T) {
			body := &trackedTodoistBody{Reader: strings.NewReader(`{"token":"PRIVATE_SOURCE_SECRET"}`)}
			response := &http.Response{StatusCode: status, Body: body}
			var destination map[string]any
			err := decodeTodoistResponse(response, &destination, "task snapshot")
			require.Error(t, err)
			require.ErrorContains(t, err, "task snapshot")
			require.NotContains(t, err.Error(), "PRIVATE_SOURCE_SECRET")
			require.Nil(t, destination)
			require.True(t, body.closed, "the HTTP body must close on non-success")
		})
	}
}

func TestDecodeTodoistResponseRejectsMalformedJSONAndClosesBody(t *testing.T) {
	body := &trackedTodoistBody{Reader: strings.NewReader("not-json")}
	var destination map[string]any
	err := decodeTodoistResponse(&http.Response{StatusCode: http.StatusOK, Body: body}, &destination, "archived projects")
	require.ErrorContains(t, err, "could not be decoded")
	require.True(t, body.closed, "the HTTP body must close on parse failures")
}

func TestDecodeTodoistResponseRejectsMissingResponse(t *testing.T) {
	var destination map[string]any
	require.ErrorContains(t, decodeTodoistResponse(nil, &destination, "sync"), "no response body")
	require.ErrorContains(t, decodeTodoistResponse(&http.Response{StatusCode: http.StatusOK}, &destination, "sync"), "no response body")
}
