<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { LogOut, Menu, Moon, Plus, Sun } from 'lucide-vue-next'

import { useTheme } from '@/stores/theme.js'

defineProps({
  loggingOut: { type: Boolean, default: false },
})

defineEmits(['open-navigation', 'logout'])

const route = useRoute()
const { state: theme, toggle: toggleTheme } = useTheme()
const section = computed(() => route.meta.section || 'OwlMock')
const pageTitle = computed(() => {
  const title = String(route.meta.title || '')
  return title.replace(/\s*-\s*OwlMock$/, '') || section.value
})
</script>

<template>
  <header class="app-topbar">
    <div class="app-topbar__context">
      <button
        class="app-topbar__icon-button app-topbar__menu"
        type="button"
        aria-label="打开导航"
        aria-controls="app-navigation"
        @click="$emit('open-navigation')"
      >
        <Menu :size="19" />
      </button>
      <p class="app-topbar__breadcrumb">
        <span>{{ section }}</span>
        <span v-if="pageTitle !== section" aria-hidden="true">/</span>
        <strong v-if="pageTitle !== section">{{ pageTitle }}</strong>
      </p>
    </div>

    <div class="app-topbar__actions">
      <button
        class="app-topbar__icon-button"
        type="button"
        :aria-label="theme.dark ? '切换到浅色模式' : '切换到深色模式'"
        :title="theme.dark ? '浅色模式' : '深色模式'"
        @click="toggleTheme"
      >
        <Sun v-if="theme.dark" :size="18" />
        <Moon v-else :size="18" />
      </button>
      <button
        class="app-topbar__icon-button"
        type="button"
        aria-label="退出登录"
        title="退出登录"
        :disabled="loggingOut"
        @click="$emit('logout')"
      >
        <LogOut :size="18" />
      </button>
      <router-link :to="{ name: 'project-create' }" class="app-topbar__primary">
        <Plus :size="17" :stroke-width="2.2" />
        <span>新建岗位</span>
      </router-link>
    </div>
  </header>
</template>

<style scoped>
.app-topbar {
  position: sticky;
  top: 0;
  z-index: 30;
  min-width: 0;
  height: var(--app-topbar-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.25rem;
  padding: 0 2rem;
  background: color-mix(in srgb, var(--color-base) 94%, transparent);
  border-bottom: 1px solid var(--color-border);
  backdrop-filter: blur(12px);
}

.app-topbar__context,
.app-topbar__actions {
  min-width: 0;
  display: flex;
  align-items: center;
}

.app-topbar__context {
  gap: 0.65rem;
}

.app-topbar__actions {
  flex: none;
  gap: 0.5rem;
}

.app-topbar__breadcrumb {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.45rem;
  color: var(--color-ink-muted);
  font-size: 0.75rem;
  white-space: nowrap;
}

.app-topbar__breadcrumb strong {
  max-width: min(36vw, 430px);
  overflow: hidden;
  color: var(--color-ink);
  font-weight: 650;
  text-overflow: ellipsis;
}

.app-topbar__icon-button {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  flex: none;
  color: var(--color-ink-light);
  background: var(--color-white);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  transition: color var(--duration-fast), border-color var(--duration-fast), background var(--duration-fast);
}

.app-topbar__icon-button:hover:not(:disabled) {
  color: var(--color-primary);
  border-color: var(--color-primary);
  background: var(--color-surface);
}

.app-topbar__menu {
  display: none;
}

.app-topbar__primary {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.42rem;
  padding: 0 0.9rem;
  color: #fff;
  background: #173f3b;
  border: 1px solid #173f3b;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  transition: background var(--duration-fast), border-color var(--duration-fast);
}

.app-topbar__primary:hover {
  background: #2d6b65;
  border-color: #2d6b65;
}

:global(.dark) .app-topbar__primary {
  color: #17312f;
  background: var(--color-secondary);
  border-color: var(--color-secondary);
}

@media (max-width: 1024px) {
  .app-topbar {
    padding-inline: 1.25rem;
  }
}

@media (max-width: 720px) {
  .app-topbar {
    height: var(--app-mobile-topbar-height);
    padding-inline: 0.9rem;
  }

  .app-topbar__menu {
    display: grid;
  }

  .app-topbar__breadcrumb > span:first-child,
  .app-topbar__breadcrumb > span[aria-hidden="true"] {
    display: none;
  }

  .app-topbar__breadcrumb strong {
    max-width: 36vw;
  }

  .app-topbar__primary {
    width: 36px;
    min-height: 36px;
    padding: 0;
  }

  .app-topbar__primary span {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
}

@media (max-width: 420px) {
  .app-topbar__actions {
    gap: 0.35rem;
  }

  .app-topbar__breadcrumb {
    font-size: 0.7rem;
  }
}
</style>
