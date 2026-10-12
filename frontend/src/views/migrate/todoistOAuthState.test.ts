import {describe, expect, it} from 'vitest'

import {clearTodoistOAuthState, consumeTodoistOAuthState, rememberTodoistOAuthState} from './todoistOAuthState'

function store() {
	const state = new Map<string, string>()
	return {
		getItem: (key: string) => state.get(key) ?? null,
		setItem: (key: string, value: string) => { state.set(key, value) },
		removeItem: (key: string) => { state.delete(key) },
	}
}

const nonce = '0123456789abcdef0123456789abcdef'
const authorize = 'https://todoist.com/oauth/authorize?client_id=example&scope=data%3Aread&state=' + nonce

describe('Todoist OAuth callback state', () => {
	it('accepts a matching callback once, then rejects replay', () => {
		const storage = store()
		expect(rememberTodoistOAuthState(authorize, storage)).toBe(true)
		expect(consumeTodoistOAuthState(nonce, storage)).toBe(true)
		expect(consumeTodoistOAuthState(nonce, storage)).toBe(false)
	})

	it('fails closed on missing or mismatched callback state and consumes pending state', () => {
		const storage = store()
		expect(rememberTodoistOAuthState(authorize, storage)).toBe(true)
		expect(consumeTodoistOAuthState(null, storage)).toBe(false)
		expect(consumeTodoistOAuthState(nonce, storage)).toBe(false)
		expect(rememberTodoistOAuthState(authorize, storage)).toBe(true)
		expect(consumeTodoistOAuthState('wrong', storage)).toBe(false)
		expect(consumeTodoistOAuthState(nonce, storage)).toBe(false)
	})

	it('rejects invalid authorization URLs, missing randomness, and other hosts', () => {
		for (const url of [
			'https://todoist.com/oauth/authorize',
			'https://todoist.com/oauth/authorize?state=short',
			'https://evil.example/oauth/authorize?state=' + nonce,
			'http://todoist.com/oauth/authorize?state=' + nonce,
			'https://todoist.com/not-authorize?state=' + nonce,
			'not-a-url',
		]) {
			expect(rememberTodoistOAuthState(url, store())).toBe(false)
		}
	})

	it('rejects unavailable storage instead of silently accepting authorization', () => {
		expect(rememberTodoistOAuthState(authorize, undefined)).toBe(false)
		expect(consumeTodoistOAuthState(nonce, undefined)).toBe(false)
		const throwingStorage = {
			getItem: () => { throw new Error('blocked') },
			setItem: () => { throw new Error('blocked') },
			removeItem: () => { throw new Error('blocked') },
		}
		expect(rememberTodoistOAuthState(authorize, throwingStorage)).toBe(false)
		expect(consumeTodoistOAuthState(nonce, throwingStorage)).toBe(false)
		expect(() => clearTodoistOAuthState(throwingStorage)).not.toThrow()
	})

	it('clears an unfinished authorization before reimport', () => {
		const storage = store()
		expect(rememberTodoistOAuthState(authorize, storage)).toBe(true)
		clearTodoistOAuthState(storage)
		expect(consumeTodoistOAuthState(nonce, storage)).toBe(false)
	})
})
