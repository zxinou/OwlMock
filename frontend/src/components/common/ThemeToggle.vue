<script setup>
import { Moon, Sun } from 'lucide-vue-next'

import { useTheme } from '@/stores/theme.js'

const { state, toggle } = useTheme()
</script>

<template>
  <button
    class="flex items-center justify-center transition-all hover:bg-surface-alt hover:text-primary hover:rotate-12"
    :style="{
      width: '44px', height: '44px', borderRadius: 'var(--radius-full)',
      background: 'var(--color-surface)', border: '1px solid var(--color-border)',
      color: 'var(--color-ink-light)',
    }"
    @click="toggle"
    :aria-label="state.dark ? '切换浅色模式' : '切换深色模式'"
    :aria-pressed="state.dark"
  >
    <Moon v-if="!state.dark" :size="18" />
    <Sun v-else :size="18" />
  </button>
</template>
