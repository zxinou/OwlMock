<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  BriefcaseBusiness,
  FileUser,
  Github,
  MessageSquareText,
  ShieldCheck,
  X,
} from 'lucide-vue-next'

import OwlLogo from '@/components/common/OwlLogo.vue'
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
  { label: '简历库', to: { name: 'resume' }, match: '/analysis/resume', icon: FileUser },
  { label: '面试记录', to: { name: 'interview-list' }, match: '/interview', icon: MessageSquareText },
  { label: 'GitHub 分析', to: { name: 'github-list' }, match: '/analysis/github', icon: Github },
]

const accountName = computed(() => (
  authStore.user?.display_name
  || authStore.user?.email?.split('@')[0]
  || '我的求职空间'
))
const accountDetail = computed(() => authStore.user?.email || '个人工作区')
const ownerInitials = computed(() => accountName.value
  .trim()
  .split(/\s+/)
  .map((part) => part.slice(0, 1))
  .join('')
  .slice(0, 2)
  .toUpperCase())
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
      <span class="app-sidebar__avatar" aria-hidden="true">{{ ownerInitials }}</span>
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
  color: #edf7f4;
  background: #173f3b;
  border-right: 1px solid rgba(255, 255, 255, 0.09);
}

.app-sidebar__brand {
  height: var(--app-topbar-height);
  display: flex;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.app-sidebar__brand-link {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0 1.25rem;
  color: #fff;
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
  background: #f7faf7;
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
  color: #c8ddd8;
  border-radius: 6px;
}

.app-sidebar__close:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}

.app-sidebar__owner {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin: 1rem 0.85rem 0.7rem;
  padding: 0.65rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.13);
  border-radius: 7px;
}

.app-sidebar__avatar {
  width: 31px;
  height: 31px;
  display: grid;
  place-items: center;
  flex: none;
  color: #173f3b;
  background: var(--color-secondary);
  border-radius: 50%;
  font-family: var(--font-heading);
  font-size: 0.66rem;
  font-weight: 800;
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
  color: #f8fcfb;
  font-size: 0.75rem;
}

.app-sidebar__owner-copy small,
.app-sidebar__status-copy small {
  margin-top: 0.12rem;
  color: #a9c2bd;
  font-size: 0.64rem;
}

.app-sidebar__label {
  padding: 0.7rem 1.35rem 0.45rem;
  color: #88aaa3;
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
  color: #bad0cb;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  transition: color var(--duration-fast), background var(--duration-fast);
}

.app-sidebar__link:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.07);
}

.app-sidebar__link--active {
  color: #fff;
  background: #2d6b65;
  font-weight: 700;
}

.app-sidebar__link-icon {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  flex: none;
  border: 1px solid rgba(255, 255, 255, 0.23);
  border-radius: 5px;
}

.app-sidebar__link--active .app-sidebar__link-icon {
  color: #173f3b;
  background: #eaf4f1;
  border-color: #eaf4f1;
}

.app-sidebar__footer {
  margin-top: auto;
  padding: 0.85rem 0.65rem 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.09);
}

.app-sidebar__status {
  min-height: 52px;
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) 8px;
  align-items: center;
  gap: 0.55rem;
  padding: 0.62rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
}

.app-sidebar__status-icon {
  color: #b9d7d1;
}

.app-sidebar__status-dot {
  width: 7px;
  height: 7px;
  background: #75b8af;
  border-radius: 50%;
  box-shadow: 0 0 0 3px rgba(117, 184, 175, 0.16);
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
