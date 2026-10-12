// GoreeCloud Tasks does not sample performance traces or session recordings.
export const GOREECLOUD_TELEMETRY_SAMPLING = {
	tracesSampleRate: 0,
	replaysSessionSampleRate: 0,
	replaysOnErrorSampleRate: 0,
} as const
