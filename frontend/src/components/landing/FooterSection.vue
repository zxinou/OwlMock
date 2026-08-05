<script setup>
import OwlLogo from '@/components/common/OwlLogo.vue'
import { authStore } from '@/stores/auth.js'
</script>

<template>
  <footer :style="{ padding: '3rem 0 2rem', borderTop: '1px solid var(--color-border-light)' }">
    <div class="landing-footer__inner container flex items-center justify-between">
      <div class="flex items-center gap-3">
        <OwlLogo :size="28" class="opacity-50" light />
        <span class="text-sm" style="color: var(--color-ink-muted)">&copy; 2026 OwlMock. Made with care.</span>
      </div>
      <ul class="flex gap-6 list-none m-0 p-0">
        <li><a href="#features" class="landing-footer__link text-sm transition-colors hover:text-primary" style="color: var(--color-ink-muted)">智能分析</a></li>
        <li><a href="#interview" class="landing-footer__link text-sm transition-colors hover:text-primary" style="color: var(--color-ink-muted)">模拟面试</a></li>
        <li>
          <router-link
            :to="authStore.authenticated ? { name: 'projects' } : { name: 'login' }"
            class="landing-footer__link text-sm transition-colors hover:text-primary"
            style="color: var(--color-ink-muted)"
          >{{ authStore.authenticated ? '工作台' : '登录' }}</router-link>
        </li>
      </ul>
    </div>
  </footer>
</template>

<style scoped>
.landing-footer__link {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
}

@media (max-width: 640px) {
  .landing-footer__inner {
    flex-direction: column;
    align-items: flex-start;
    gap: 1.25rem;
  }
}
</style>
