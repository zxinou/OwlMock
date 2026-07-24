<script setup>
import { BriefcaseBusiness, Check, Image, Search } from 'lucide-vue-next'

defineProps({
  items: { type: Array, default: () => [] },
  selectedIds: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

defineEmits(['toggle'])

function formatDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}
</script>

<template>
  <div class="job-picker">
    <div v-if="loading" class="job-picker-empty">正在读取已分析岗位...</div>
    <div v-else-if="!items.length" class="job-picker-empty">
      <Search :size="22" />
      <strong>还没有可匹配的岗位</strong>
      <span>请先完成一次 JD 智能分析，再回来选择岗位。</span>
      <router-link :to="{ name: 'jd' }" class="btn btn--secondary">前往 JD 分析</router-link>
    </div>
    <div v-else class="job-picker-list">
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        class="job-option"
        :class="{ selected: selectedIds.includes(item.id) }"
        :aria-pressed="selectedIds.includes(item.id)"
        @click="$emit('toggle', item.id)"
      >
        <span class="job-option-check">
          <Check v-if="selectedIds.includes(item.id)" :size="14" />
        </span>
        <span class="job-option-icon">
          <Image v-if="item.source_type === 'image'" :size="17" />
          <BriefcaseBusiness v-else :size="17" />
        </span>
        <span class="job-option-copy">
          <strong>{{ item.result?.job?.title || '未命名岗位' }}</strong>
          <span>{{ item.result?.job?.company || '公司未注明' }}</span>
        </span>
        <span class="job-option-meta">
          <small>{{ item.result?.job?.difficulty?.level || '难度待定' }}</small>
          <time>{{ formatDate(item.created_at) }}</time>
        </span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.job-picker-list { display:grid; gap:.55rem; max-height:20rem; overflow:auto; padding-right:.2rem; }
.job-option { min-width:0; display:grid; grid-template-columns:1.35rem 2.25rem minmax(0,1fr) auto; align-items:center; gap:.7rem; width:100%; padding:.75rem; border:1px solid var(--color-border-light); border-radius:var(--radius-sm); color:var(--color-ink); background:var(--color-base); text-align:left; transition:border-color .2s, background .2s, box-shadow .2s; }
.job-option:hover { border-color:var(--color-border); background:var(--color-surface); }
.job-option.selected { border-color:var(--color-primary); background:color-mix(in srgb,var(--color-primary) 6%,var(--color-base)); box-shadow:inset 3px 0 var(--color-primary); }
.job-option-check { width:1.1rem; height:1.1rem; display:grid; place-items:center; border:1px solid var(--color-border); border-radius:4px; color:white; }
.job-option.selected .job-option-check { border-color:var(--color-primary); background:var(--color-primary); }
.job-option-icon { width:2.15rem; height:2.15rem; display:grid; place-items:center; border-radius:6px; color:var(--color-primary); background:var(--color-surface-alt); }
.job-option-copy { min-width:0; }
.job-option-copy strong, .job-option-copy span { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.job-option-copy strong { font-size:.82rem; }
.job-option-copy span { margin-top:.2rem; color:var(--color-ink-muted); font-size:.7rem; }
.job-option-meta { display:grid; justify-items:end; gap:.25rem; color:var(--color-ink-muted); font-size:.66rem; }
.job-option-meta small { color:#8a6515; font-weight:700; }
.job-picker-empty { min-height:11rem; display:flex; align-items:center; justify-content:center; flex-direction:column; gap:.55rem; padding:1rem; color:var(--color-ink-muted); text-align:center; }
.job-picker-empty strong { color:var(--color-ink); font-size:.88rem; }
.job-picker-empty span { font-size:.75rem; }
.job-picker-empty .btn { margin-top:.25rem; }
@media (max-width:560px) { .job-option { grid-template-columns:1.25rem 2rem minmax(0,1fr); } .job-option-meta { grid-column:3; grid-auto-flow:column; justify-content:start; } }
</style>
