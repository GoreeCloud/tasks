import {describe, expect, it, vi} from 'vitest'
import {mount} from '@vue/test-utils'

import About from './About.vue'
import en from '@/i18n/lang/en.json'

vi.mock('@/stores/config', () => ({
	useConfigStore: () => ({version: 'test', enabled_pro_features: []}),
}))

describe('About — GoreeCloud Waypoint identity', () => {
	it('presents Waypoint as part of Tasks and retains upstream attribution', () => {
		const wrapper = mount(About, {
			global: {
				mocks: {
					$t: (key: string) => {
						switch (key) {
							case 'about.waypointPresentation':
								return en.about.waypointPresentation
							case 'about.waypointScope':
								return en.about.waypointScope
							case 'about.upstreamAttribution':
								return en.about.upstreamAttribution
							case 'about.upstreamSource':
								return en.about.upstreamSource
							default:
								return key
						}
					},
				},
				stubs: {
					Modal: {template: '<div><slot /></div>'},
					Card: {template: '<section><slot /><slot name="footer" /></section>'},
					XButton: true,
				},
			},
		})

		expect(wrapper.text()).toContain('GoreeCloud Tasks — Powered by Waypoint')
		expect(wrapper.text()).toContain('not a separate application')
		expect(wrapper.text()).toContain('Vikunja')
		expect(wrapper.find('a[href="https://github.com/go-vikunja/vikunja"]').exists()).toBe(true)
	})
})
