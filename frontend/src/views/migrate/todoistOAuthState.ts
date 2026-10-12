// GoreeCloud Tasks Todoist OAuth callback defense-in-depth.
// Browser-tab state checks complement, but cannot replace, server validation.
const TODOIST_OAUTH_STATE_KEY = 'goreecloud:todoist:oauth-state'

type StateStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>

export function rememberTodoistOAuthState(authUrl: string, storage?: StateStorage): boolean {
	if (!storage) return false
	try {
		const url = new URL(authUrl)
		const state = url.searchParams.get('state')
		if (url.protocol !== 'https:' || url.hostname !== 'todoist.com' || url.pathname !== '/oauth/authorize' || !state || state.length < 32) {
			return false
		}
		storage.setItem(TODOIST_OAUTH_STATE_KEY, state)
		return true
	} catch {
		return false
	}
}

export function consumeTodoistOAuthState(callbackState: string | null, storage?: StateStorage): boolean {
	if (!storage) return false
	try {
		const expected = storage.getItem(TODOIST_OAUTH_STATE_KEY)
		// A state is a single-use value even if an invalid callback is received.
		storage.removeItem(TODOIST_OAUTH_STATE_KEY)
		return Boolean(callbackState && expected && expected === callbackState)
	} catch {
		return false
	}
}

export function clearTodoistOAuthState(storage?: StateStorage): void {
	try {
		storage?.removeItem(TODOIST_OAUTH_STATE_KEY)
	} catch {
		// If storage is unavailable, subsequent callback validation fails closed.
	}
}
