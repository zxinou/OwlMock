<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppSidebar from '@/components/app/AppSidebar.vue'
import AppTopbar from '@/components/app/AppTopbar.vue'
import { authStore } from '@/stores/auth.js'

const route = useRoute()
const router = useRouter()
const navigationOpen = ref(false)
const loggingOut = ref(false)
const sidebar = ref(null)

function closeNavigation() {
  navigationOpen.value = false
}

async function openNavigation() {
  navigationOpen.value = true
  await nextTick()
  sidebar.value?.$el?.querySelector('.app-sidebar__close')?.focus()
}

async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    await authStore.logout()
  } catch {
    // Local auth state is cleared by the store even if the network request fails.
  } finally {
    loggingOut.value = false
    await router.replace({ name: 'login' })
  }
}

function handleKeydown(event) {
  if (event.key === 'Escape' && navigationOpen.value) closeNavigation()
}

watch(() => route.fullPath, closeNavigation)
watch(navigationOpen, (open) => {
  document.body.classList.toggle('app-navigation-open', open)
})

onMounted(() => document.addEventListener('keydown', handleKeydown))
onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.body.classList.remove('app-navigation-open')
})
</script>

<template>
  <div class="app-shell">
    <a class="app-shell__skip-link" href="#main-content">跳到主要内容</a>
    <AppSidebar ref="sidebar" :open="navigationOpen" @close="closeNavigation" />
    <button
      v-if="navigationOpen"
      type="button"
      class="app-shell__backdrop"
      aria-label="关闭导航"
      @click="closeNavigation"
    />

    <div class="app-shell__workspace">
      <AppTopbar
        :logging-out="loggingOut"
        @open-navigation="openNavigation"
        @logout="logout"
      />
      <main id="main-content" class="app-shell__main" tabindex="-1">
        <div class="app-shell__content">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: var(--color-base);
}

.app-shell__workspace {
  min-width: 0;
  min-height: 100vh;
  margin-left: var(--app-sidebar-width);
}

.app-shell__main {
  min-width: 0;
  min-height: calc(100vh - var(--app-topbar-height));
  outline: none;
}

.app-shell__content {
  width: min(100%, 1232px);
  margin: 0 auto;
  padding: 1.85rem 2.25rem 3.5rem;
}

.app-shell__skip-link {
  position: fixed;
  top: 0.75rem;
  left: calc(var(--app-sidebar-width) + 1rem);
  z-index: 100;
  padding: 0.55rem 0.8rem;
  color: var(--color-on-primary);
  background: var(--color-primary);
  border-radius: 6px;
  transform: translateY(-180%);
  transition: transform var(--duration-fast);
}

.app-shell__skip-link:focus {
  transform: translateY(0);
}

.app-shell__backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: none;
  background: rgba(5, 21, 19, 0.52);
  backdrop-filter: blur(2px);
}

@media (max-width: 1024px) and (min-width: 721px) {
  .app-shell__workspace {
    margin-left: var(--app-sidebar-collapsed-width);
  }

  .app-shell__skip-link {
    left: calc(var(--app-sidebar-collapsed-width) + 1rem);
  }

  .app-shell__content {
    padding-inline: 1.5rem;
  }
}

@media (max-width: 720px) {
  .app-shell__workspace {
    margin-left: 0;
  }

  .app-shell__main {
    min-height: calc(100vh - var(--app-mobile-topbar-height));
  }

  .app-shell__content {
    padding: 1.3rem 0.95rem 2.75rem;
  }

  .app-shell__skip-link {
    left: 0.75rem;
  }

  .app-shell__backdrop {
    display: block;
  }
}
</style>
