// GoreeCloud Tasks Todoist OAuth state binding.
// SPDX-License-Identifier: AGPL-3.0-or-later
package todoist

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"strconv"
	"strings"
	"time"
)

const todoistStateLifetime = 10 * time.Minute
const todoistStateDomain = "goreecloud/tasks/todoist/oauth-state/v1:"

// signTodoistState binds a generated, unpredictable nonce to a user and a
// timestamp. The backend secret never leaves the server.
func signTodoistState(userID int64, nonce string, issued time.Time, secret string) (string, error) {
	if userID <= 0 || secret == "" || len(nonce) < 32 || len(nonce) > 128 || strings.Contains(nonce, ".") {
		return "", fmt.Errorf("todoist migration: could not issue secure authorization state")
	}
	payload := fmt.Sprintf("v1.%d.%d.%s", userID, issued.Unix(), nonce)
	signature := todoistStateMAC(payload, secret)
	return payload + "." + base64.RawURLEncoding.EncodeToString(signature), nil
}

// verifyTodoistState is used before claiming a background migration. Failures
// deliberately omit user IDs, state bytes, secrets and authorization codes.
func verifyTodoistState(value string, userID int64, now time.Time, secret string) error {
	const invalid = "todoist migration: invalid or expired OAuth state"
	fields := strings.Split(value, ".")
	if len(fields) != 5 || fields[0] != "v1" || userID <= 0 || secret == "" ||
		len(fields[3]) < 32 || len(fields[3]) > 128 {
		return fmt.Errorf("%s", invalid)
	}
	signedUser, err := strconv.ParseInt(fields[1], 10, 64)
	if err != nil || signedUser != userID {
		return fmt.Errorf("%s", invalid)
	}
	issuedSeconds, err := strconv.ParseInt(fields[2], 10, 64)
	if err != nil {
		return fmt.Errorf("%s", invalid)
	}
	issued := time.Unix(issuedSeconds, 0)
	if issued.After(now) || now.Sub(issued) > todoistStateLifetime {
		return fmt.Errorf("%s", invalid)
	}
	actual, err := base64.RawURLEncoding.DecodeString(fields[4])
	if err != nil {
		return fmt.Errorf("%s", invalid)
	}
	payload := strings.Join(fields[:4], ".")
	if !hmac.Equal(actual, todoistStateMAC(payload, secret)) {
		return fmt.Errorf("%s", invalid)
	}
	return nil
}

func todoistStateMAC(payload string, secret string) []byte {
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = mac.Write([]byte(todoistStateDomain + payload))
	return mac.Sum(nil)
}
