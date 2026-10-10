<script setup lang="ts">
import {computed} from 'vue'
import {useColorScheme} from '@/composables/useColorScheme'

const {isDark} = useColorScheme()

// Organization-supplied logo overrides remain supported; local default avoids
// carrying Vikunja's trademark into the GoreeCloud product experience.
const customLogo = computed(() => {
    const light = window.CUSTOM_LOGO_URL
    const dark = window.CUSTOM_LOGO_URL_DARK
    return isDark.value ? (dark || light || '') : (light || dark || '')
})
</script>

<template>
    <div class="goreecloud-tasks-logo">
        <img v-if="customLogo" :src="customLogo" alt="GoreeCloud Tasks" class="logo">
        <span v-else class="wordmark" aria-label="GoreeCloud Tasks">
            <span class="wordmark-family">GoreeCloud</span>
            <strong class="wordmark-product">Tasks</strong>
        </span>
    </div>
</template>

<style scoped>
.goreecloud-tasks-logo { display: flex; align-items: center; min-block-size: 44px; }
.wordmark { display: inline-flex; align-items: baseline; gap: .45rem; white-space: nowrap; color: var(--glaze-text, var(--text)); letter-spacing: -.025em; }
.wordmark-family { font-size: 1.07rem; font-weight: 600; }
.wordmark-product { font-size: 1.12rem; color: var(--glaze-accent, var(--primary)); font-weight: 750; }
.logo { max-inline-size: 168px; max-block-size: 48px; object-fit: contain; }
@media (max-width: 480px) { .wordmark-family { font-size: .97rem; } .wordmark-product { font-size: 1.03rem; } }
</style>
