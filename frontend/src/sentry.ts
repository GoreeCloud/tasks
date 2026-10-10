import type {App} from 'vue'
import type {Router} from 'vue-router'
import {isReportableResourceUrl, redactSensitiveParams, shouldDropEvent, stripNavigationFragment} from './helpers/sentryFilters'
import {VERSION} from './version.json'
import {GOREECLOUD_TELEMETRY_SAMPLING} from './helpers/telemetrySampling'

export default async function setupSentry(app: App, router: Router) {
	const Sentry = await import('@sentry/vue')

	Sentry.init({
		app,
		dsn: window.SENTRY_DSN ?? '',
		release: `goreecloud-tasks@${VERSION}`,
		// Props of login and password forms hold plaintext credentials.
		attachProps: false,

		// Error reporting is opt-in; session recording is disabled.
		integrations: [Sentry.browserTracingIntegration({router})],
		...GOREECLOUD_TELEMETRY_SAMPLING,

		// Set `tracePropagationTargets` to control for which URLs trace propagation should be enabled
		tracePropagationTargets: [
			'localhost',
			/^\//,
			// /^https:\/\/yourserver\.io\/api/,
		],

		// Capture Replay for 10% of all sessions,
		// plus for 100% of sessions with an error
		replaysSessionSampleRate: 0.1,
		replaysOnErrorSampleRate: 1.0,

		// Extensions run their content scripts on our origin, so their errors end
		// up here even though we can neither reproduce nor fix them.
		denyUrls: [
			/^chrome-extension:\/\//i,
			/^moz-extension:\/\//i,
			/^safari-web-extension:\/\//i,
			/^safari-extension:\/\//i,
			/^ms-browser-extension:\/\//i,
		],


		beforeSendSpan: span => redactSensitiveParams(stripNavigationFragment(span)),
		beforeSend(event, hint) {
			if (shouldDropEvent(hint.originalException, event)) {
				return null
			}

			return event
		},
	})

	// Unlike beforeSend, this also runs for transactions and replay events.
	Sentry.addEventProcessor(event => redactSensitiveParams(event))

	// from https://docs.sentry.io/platforms/javascript/guides/vue/troubleshooting/
	// under "Capturing resource 404s"
	document.body.addEventListener(
		'error',
		(event) => {
			const target = event.target

			if (target instanceof HTMLImageElement) {
				if (!isReportableResourceUrl(target.src, document.URL)) return
				// Users can put any src into their descriptions and comments, a broken one is not our bug.
				if (target.closest('[data-user-content]')) return

				Sentry.captureMessage(
					`Failed to load image: ${target.src}`,
					'warning',
				)
			} else if (target instanceof HTMLLinkElement) {
				if (!isReportableResourceUrl(target.href, document.URL)) return

				Sentry.captureMessage(
					`Failed to load css: ${target.href}`,
					'warning',
				)
			}
		},
		true, // useCapture - necessary for resource loading errors
	)
}
