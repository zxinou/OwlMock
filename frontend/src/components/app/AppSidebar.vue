<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  BriefcaseBusiness,
  FileSearch,
  FileUser,
  Github,
  MessageSquareText,
  ShieldCheck,
  X,
} from 'lucide-vue-next'

import OwlLogo from '@/components/common/OwlLogo.vue'
import UserAvatar from '@/components/app/UserAvatar.vue'
import { authStore } from '@/stores/auth.js'

const props = defineProps({
  open: { type: Boolean, default: false },
})

defineEmits(['close'])

const route = useRoute()
const mobile = ref(false)
let mobileMedia = null
const navItems = [
  { label: '岗位项目', to: { name: 'projects' }, match: '/projects', icon: BriefcaseBusiness },
  { label: 'JD 分析', to: { name: 'jd' }, match: '/analysis/jd', icon: FileSearch },
  { label: '简历中心', to: { name: 'resume' }, match: '/analysis/resume', icon: FileUser },
  { label: 'GitHub 分析', to: { name: 'github-list' }, match: '/analysis/github', icon: Github },
  { label: '模拟面试', to: { name: 'interview-list' }, match: '/interview', icon: MessageSquareText },
]

const accountName = computed(() => (
  authStore.user?.display_name
  || authStore.user?.email?.split('@')[0]
  || '我的求职空间'
))
const accountDetail = computed(() => authStore.user?.email || '个人工作区')
const navigationHidden = computed(() => mobile.value && !props.open)

function syncMobile(event) {
  mobile.value = event.matches
}

function isActive(item) {
  return route.path.startsWith(item.match)
}

onMounted(() => {
  mobileMedia = window.matchMedia('(max-width: 720px)')
  syncMobile(mobileMedia)
  mobileMedia.addEventListener('change', syncMobile)
})

onBeforeUnmount(() => mobileMedia?.removeEventListener('change', syncMobile))
</script>

<template>
  <aside
    id="app-navigation"
    class="app-sidebar"
    :class="{ 'app-sidebar--open': open }"
    :aria-hidden="navigationHidden ? 'true' : undefined"
    :inert="navigationHidden"
    aria-label="主导航"
  >
    <div class="app-sidebar__brand">
      <router-link :to="{ name: 'projects' }" class="app-sidebar__brand-link" @click="$emit('close')">
        <span class="app-sidebar__logo"><OwlLogo :size="30" style="filter: none; opacity: 1" /></span>
        <span class="app-sidebar__brand-name">OwlMock</span>
      </router-link>
      <button class="app-sidebar__close" type="button" aria-label="关闭导航" @click="$emit('close')">
        <X :size="19" />
      </button>
    </div>

    <div class="app-sidebar__owner">
      <UserAvatar :user="authStore.user" :size="31" />
      <span class="app-sidebar__owner-copy">
        <strong>{{ accountName }}</strong>
        <small>{{ accountDetail }}</small>
      </span>
    </div>

    <p class="app-sidebar__label">工作区</p>
    <nav class="app-sidebar__nav">
      <router-link
        v-for="item in navItems"
        :key="item.label"
        :to="item.to"
        class="app-sidebar__link"
        :class="{ 'app-sidebar__link--active': isActive(item) }"
        :aria-current="isActive(item) ? 'page' : undefined"
        :title="item.label"
        @click="$emit('close')"
      >
        <span class="app-sidebar__link-icon" aria-hidden="true">
          <component :is="item.icon" :size="17" :stroke-width="1.9" />
        </span>
        <span class="app-sidebar__link-label">{{ item.label }}</span>
      </router-link>
    </nav>

    <div class="app-sidebar__footer">
      <div class="app-sidebar__status">
        <span class="app-sidebar__status-icon" aria-hidden="true"><ShieldCheck :size="16" /></span>
        <span class="app-sidebar__status-copy">
          <strong>会话已保护</strong>
          <small>同源安全连接</small>
        </span>
        <span class="app-sidebar__status-dot" aria-hidden="true" />
      </div>
    </div>
  </aside>
</template>

<style scoped>
.app-sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 50;
  width: var(--app-sidebar-width);
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  color: var(--color-rail-ink);
  background: var(--color-rail);
  border-right: 1px solid var(--color-border);
}

.app-sidebar__brand {
  height: var(--app-topbar-height);
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--color-border);
}

.app-sidebar__brand-link {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0 1.25rem;
  color: var(--color-rail-ink);
  font-family: var(--font-heading);
  font-size: 1.08rem;
  font-weight: 700;
}

.app-sidebar__logo {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  flex: none;
  padding: 2px;
  overflow: hidden;
  background: var(--color-white);
  border-radius: 6px;
}

.app-sidebar__brand-name,
.app-sidebar__link-label,
.app-sidebar__owner-copy,
.app-sidebar__status-copy {
  min-width: 0;
}

.app-sidebar__close {
  width: 38px;
  height: 38px;
  display: none;
  place-items: center;
  margin-left: auto;
  margin-right: 0.75rem;
  color: var(--color-rail-muted);
  border-radius: 6px;
}

.app-sidebar__close:hover {
  color: var(--color-rail-ink);
  background: var(--color-surface-alt);
}

.app-sidebar__owner {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin: 1rem 0.85rem 0.7rem;
  padding: 0.65rem;
  background: var(--color-white);
  border: 1px solid var(--color-border);
  border-radius: 7px;
}

.app-sidebar__owner-copy strong,
.app-sidebar__owner-copy small,
.app-sidebar__status-copy strong,
.app-sidebar__status-copy small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-sidebar__owner-copy strong,
.app-sidebar__status-copy strong {
  color: var(--color-rail-ink);
  font-size: 0.75rem;
}

.app-sidebar__owner-copy small,
.app-sidebar__status-copy small {
  margin-top: 0.12rem;
  color: var(--color-rail-muted);
  font-size: 0.64rem;
}

.app-sidebar__label {
  padding: 0.7rem 1.35rem 0.45rem;
  color: var(--color-rail-subtle);
  font-size: 0.64rem;
  font-weight: 700;
  text-transform: uppercase;
}

.app-sidebar__nav {
  display: grid;
  gap: 3px;
  padding: 0 0.65rem;
}

.app-sidebar__link {
  min-height: 42px;
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0 0.7rem;
  color: var(--color-rail-muted);
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  transition: color var(--duration-fast), background var(--duration-fast);
}

.app-sidebar__link:hover {
  color: var(--color-rail-ink);
  background: var(--color-surface-alt);
}

.app-sidebar__link--active {
  color: var(--color-rail-ink);
  background: var(--color-rail-hover);
  font-weight: 700;
}

.app-sidebar__link-icon {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  flex: none;
  border: 1px solid var(--color-border);
  border-radius: 5px;
}

.app-sidebar__link--active .app-sidebar__link-icon {
  color: var(--color-primary-dark);
  background: var(--color-surface);
  border-color: var(--color-surface);
}

.app-sidebar__footer {
  margin-top: auto;
  padding: 0.85rem 0.65rem 1rem;
  border-top: 1px solid var(--color-border);
}

.app-sidebar__status {
  min-height: 52px;
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) 8px;
  align-items: center;
  gap: 0.55rem;
  padding: 0.62rem;
  background: var(--color-white);
  border-radius: 6px;
}

.app-sidebar__status-icon {
  color: var(--color-rail-muted);
}

.app-sidebar__status-dot {
  width: 7px;
  height: 7px;
  background: var(--color-primary-light);
  border-radius: 50%;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary-light) 20%, transparent);
}

@media (max-width: 1024px) and (min-width: 721px) {
  .app-sidebar {
    width: var(--app-sidebar-collapsed-width);
  }

  .app-sidebar__brand {
    justify-content: center;
  }

  .app-sidebar__brand-link {
    padding: 0;
  }

  .app-sidebar__brand-name,
  .app-sidebar__owner-copy,
  .app-sidebar__label,
  .app-sidebar__link-label,
  .app-sidebar__status-copy,
  .app-sidebar__status-dot {
    display: none;
  }

  .app-sidebar__owner {
    justify-content: center;
    margin-inline: 0.5rem;
    padding-inline: 0;
    background: transparent;
    border-color: transparent;
  }

  .app-sidebar__nav {
    padding-inline: 0.5rem;
  }

  .app-sidebar__link {
    justify-content: center;
    padding: 0;
  }

  .app-sidebar__status {
    display: grid;
    grid-template-columns: 1fr;
    justify-items: center;
    padding-inline: 0;
  }
}

@media (max-width: 720px) {
  .app-sidebar {
    width: min(292px, calc(100vw - 40px));
    transform: translateX(-100%);
    box-shadow: 16px 0 42px rgba(5, 21, 19, 0.24);
    transition: transform var(--duration-normal) var(--ease-out);
  }

  .app-sidebar--open {
    transform: translateX(0);
  }

  .app-sidebar__close {
    display: grid;
  }
}
</style>
