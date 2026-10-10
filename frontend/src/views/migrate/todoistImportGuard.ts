// Explicit import consent is separate from an OAuth authorization redirect.
// GoreeCloud Tasks development: importing is not a verified authority cutover.
export function canStartTodoistImport(
	provider: string,
	authorizationCode: string,
	confirmed: boolean,
): boolean {
	if (provider !== 'todoist') return true
	return authorizationCode.trim().length > 0 && confirmed
}
