<script setup>
import { computed } from 'vue'

const props = defineProps({
  repo: { type: Object, required: true },
})

const emit = defineEmits(['retry', 'delete'])

const isFailed = computed(() => props.repo.status === 'failed')

const avatarColor = computed(() => {
  const colors = ['#B8845C', '#7A9E6F', '#E07858', '#6B8EC4', '#9B7EC4']
  let hash = 0
  for (const ch of props.repo.owner || '') hash = ch.charCodeAt(0) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
})

const relativeTime = computed(() => {
  if (!props.repo.analyzedAt) return ''
  const now = Date.now()
  const then = new Date(props.repo.analyzedAt).getTime()
  const diff = now - then
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  if (days > 0) return `${days} 天前`
  if (hours > 0) return `${hours} 小时前`
  if (minutes > 0) return `${minutes} 分钟前`
  return '刚刚'
})

const visibleTags = computed(() => props.repo.techTags?.slice(0, 4) || [])

function handleRetry(e) {
  e.preventDefault()
  e.stopPropagation()
  emit('retry', props.repo.url)
}

function handleDelete(e) {
  e.preventDefault()
  e.stopPropagation()
  emit('delete', props.repo)
}
</script>

<template>
  <div
    v-if="isFailed"
    class="bg-white dark:bg-surface border border-red-200 dark:border-red-900/40 rounded-xl p-5 transition-all"
  >
    <div class="flex items-start gap-4">
      <div
        class="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0 opacity-60"
        :style="{ background: avatarColor }"
      >
        {{ repo.owner?.charAt(0)?.toUpperCase() }}
      </div>

      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-center gap-2 min-w-0">
            <h3 class="text-sm font-semibold text-ink truncate">{{ repo.fullName }}</h3>
            <span class="shrink-0 px-2 py-0.5 rounded-full text-[10px] font-medium bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400">
              分析失败
            </span>
          </div>
          <button
            class="w-8 h-8 rounded-full flex items-center justify-center text-ink-muted hover:bg-red-500/10 hover:text-red-500 transition-theme shrink-0"
            aria-label="删除源码分析记录"
            @click="handleDelete"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 4h8l-.7 8H3.7L3 4zM5 4V3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v1M2 4h10" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
          </button>
        </div>

        <p class="text-xs text-red-500/80 dark:text-red-400/70 mt-1 line-clamp-2 leading-relaxed">
          {{ repo.error || '分析过程中出现错误' }}
        </p>

        <div class="flex items-center gap-3 mt-3">
          <button class="btn btn--primary text-xs py-1.5 px-4" @click="handleRetry">
            重新分析
          </button>
          <span v-if="relativeTime" class="text-[11px] text-ink-muted">{{ relativeTime }}</span>
        </div>
      </div>
    </div>
  </div>

  <router-link
    v-else
    :to="`/analysis/github/${repo.id}`"
    class="block bg-white dark:bg-surface border border-border-light dark:border-border rounded-xl p-5 transition-all hover:shadow-md hover:border-primary/40 cursor-pointer no-underline"
  >
    <div class="flex items-start gap-4">
      <div
        class="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0"
        :style="{ background: avatarColor }"
      >
        {{ repo.owner?.charAt(0)?.toUpperCase() }}
      </div>

      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-3">
          <h3 class="text-sm font-semibold text-ink truncate">{{ repo.fullName }}</h3>
          <div class="flex items-center gap-2 shrink-0">
            <div
              v-if="repo.score"
              class="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold text-white"
              :style="{
                background: repo.score >= 80 ? 'var(--color-secondary)' : repo.score >= 60 ? 'var(--color-primary)' : 'var(--color-accent)',
              }"
            >
              {{ repo.score }}
            </div>
            <button
              class="w-8 h-8 rounded-full flex items-center justify-center text-ink-muted hover:bg-red-500/10 hover:text-red-500 transition-theme"
              aria-label="删除源码分析记录"
              @click="handleDelete"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 4h8l-.7 8H3.7L3 4zM5 4V3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v1M2 4h10" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
            </button>
          </div>
        </div>

        <p class="text-xs text-ink-muted mt-1 line-clamp-2 leading-relaxed">{{ repo.description }}</p>

        <div class="flex flex-wrap gap-1.5 mt-3">
          <span
            v-for="tag in visibleTags"
            :key="tag"
            class="px-2 py-0.5 rounded-full text-[10px] font-medium bg-primary/10 text-primary-dark"
          >
            {{ tag }}
          </span>
        </div>

        <div class="mt-3 text-[11px] text-ink-muted">{{ relativeTime }}</div>
      </div>
    </div>
  </router-link>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
