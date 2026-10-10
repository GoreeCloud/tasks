<template>
	<BaseButton
		class="menu-bottom-link"
		:to="{name: 'about'}"
	>
		{{ $t('misc.goreecloudAbout') }}
	</BaseButton>
</template>

<script setup lang="ts">
import BaseButton from '@/components/base/BaseButton.vue'

// Keep the existing prop for compatibility with navigation callers.
defineProps<{utmMedium: string}>()
</script>

<style lang="scss">
.menu-bottom-link {
	color: var(--grey-300);
	text-align: center;
	display: block;
	padding-block-start: 1rem;
	padding-block-end: 1rem;
	font-size: .8rem;
}
</style>
