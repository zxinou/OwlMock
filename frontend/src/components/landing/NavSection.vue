<script setup>
import { computed } from 'vue'
import { ArrowDown, LayoutDashboard, LogIn } from 'lucide-vue-next'

import UserAvatar from '@/components/app/UserAvatar.vue'
import OwlLogo from '@/components/common/OwlLogo.vue'
import { useScrollState } from '@/composables/useScrollState.js'
import { authStore } from '@/stores/auth.js'

const { scrolled } = useScrollState()
const accountName = computed(() => (
  authStore.user?.display_name
  || authStore.user?.email?.split('@')[0]
  || '我的账户'
))
</script>

<template>
  <nav
    class="nav-glass fixed top-0 left-0 right-0 z-[100] flex items-center transition-shadow"
    :class="scrolled ? 'shadow-sm' : ''"
    :style="{ height: 'var(--nav-height)', background: 'rgba(247,250,247,0.88)', backdropFilter: 'blur(16px)', borderBottom: '1px solid var(--color-border-light)' }"
  >
    <div class="w-full flex items-center justify-between mx-auto px-6" style="max-width: var(--max-width)">
      <!-- Logo -->
      <router-link to="/" class="landing-nav__brand flex items-center gap-3 text-xl font-bold" style="font-family: var(--font-heading); color: var(--color-ink);">
        <OwlLogo :size="36" light />
        <span>OwlMock</span>
      </router-link>

      <!-- Nav links -->
      <ul class="hidden md:flex items-center gap-8 list-none m-0 p-0">
        <li>
          <a href="#features" class="landing-nav__section-link text-sm font-medium transition-colors relative hover:text-primary" style="color: var(--color-ink-light)">智能分析</a>
        </li>
        <li>
          <a href="#interview" class="landing-nav__section-link text-sm font-medium transition-colors relative hover:text-primary" style="color: var(--color-ink-light)">模拟面试</a>
        </li>
      </ul>

      <!-- Right actions -->
      <div class="flex items-center gap-3">
        <router-link
          v-if="authStore.ready && authStore.authenticated"
          :to="{ name: 'projects' }"
          class="landing-nav__account inline-flex items-center gap-2 text-sm font-semibold no-underline"
          :aria-label="`${accountName}，进入工作台`"
        >
          <UserAvatar :user="authStore.user" :size="32" />
          <span class="landing-nav__account-name">{{ accountName }}</span>
        </router-link>
        <router-link
          v-else-if="authStore.ready"
          :to="{ name: 'login' }"
          class="landing-nav__login inline-flex items-center gap-2 text-sm font-medium transition-colors no-underline"
        >
          <LogIn :size="17" />
          <span>登录</span>
        </router-link>
        <span v-else class="landing-nav__account-loading" aria-label="正在读取登录状态" />

        <router-link
          v-if="authStore.ready && authStore.authenticated"
          :to="{ name: 'projects' }"
          class="landing-nav__preview inline-flex items-center gap-2 text-sm font-semibold transition-all hover:-translate-y-px no-underline"
        >
          <LayoutDashboard :size="17" />
          进入工作台
        </router-link>
        <a
          v-else
          href="#features"
          class="landing-nav__preview inline-flex items-center gap-2 text-sm font-semibold transition-all hover:-translate-y-px no-underline"
        >
          <ArrowDown :size="17" />
          开始使用
        </a>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.landing-nav__brand,
.landing-nav__section-link {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
}

.landing-nav__login {
  min-height: 44px;
  color: var(--color-ink-light);
}

.landing-nav__login:hover,
.landing-nav__account:hover {
  color: var(--color-primary);
}

.landing-nav__account {
  min-height: 44px;
  max-width: 190px;
  color: var(--color-ink);
}

.landing-nav__account-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.landing-nav__account-loading {
  width: 44px;
  height: 32px;
  display: inline-block;
  background: var(--color-surface);
  border-radius: 999px;
}

.landing-nav__preview {
  min-height: 42px;
  padding: 0 1rem;
  color: var(--color-on-primary);
  background: var(--color-primary);
  border-radius: 8px;
}

.landing-nav__preview:hover {
  background: var(--color-primary-dark);
}

@media (max-width: 560px) {
  .landing-nav__brand span,
  .landing-nav__login span,
  .landing-nav__account-name {
    display: none;
  }

  .landing-nav__login,
  .landing-nav__account {
    width: 44px;
    justify-content: center;
  }

  .landing-nav__preview {
    padding-inline: 0.75rem;
  }
}

@media (max-width: 400px) {
  .landing-nav__preview {
    width: 44px;
    padding: 0;
    justify-content: center;
    font-size: 0;
  }
}
</style>
