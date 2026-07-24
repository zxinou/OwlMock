<script setup>
import { Check, ChevronRight, Clock3, Trash2 } from 'lucide-vue-next'

const props = defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  managing: { type: Boolean, default: false },
  selectedIds: { type: Array, default: () => [] },
})

const emit = defineEmits(['open', 'delete', 'toggle'])

function title(item) {
  return item.result?.job?.title || (item.source_type === 'image' ? '图片 JD' : '未完成分析')
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}

function statusLabel(item) {
  if (item.status === 'completed') return item.result?.job?.difficulty?.level ? `难度 ${item.result.job.difficulty.level}` : '已完成'
  if (item.status === 'failed') return '分析失败'
  return '分析中'
}

function activate(item) {
  emit(props.managing ? 'toggle' : 'open', item)
}
</script>

<template>
  <div v-if="loading" class="jd-history-empty">正在加载...</div>
  <div v-else-if="!items.length" class="jd-history-empty">暂无分析记录</div>
  <div v-else class="jd-history-list">
    <article v-for="item in items" :key="item.id" class="jd-history-item" :class="{ selected: selectedIds.includes(item.id) }">
      <button v-if="managing" type="button" class="history-check" :aria-label="`选择 ${title(item)}`" :aria-pressed="selectedIds.includes(item.id)" @click="emit('toggle', item)">
        <Check v-if="selectedIds.includes(item.id)" :size="13" />
      </button>
      <button type="button" class="jd-history-open" @click="activate(item)">
        <div class="jd-history-copy">
          <strong>{{ title(item) }}</strong>
          <span><Clock3 :size="12" />{{ formatDate(item.created_at) }} · {{ statusLabel(item) }}</span>
        </div>
        <ChevronRight v-if="!managing" :size="16" />
      </button>
      <button v-if="!managing" type="button" class="jd-history-delete" aria-label="删除 JD 分析" @click="emit('delete', item)">
        <Trash2 :size="14" />
      </button>
    </article>
  </div>
</template>

<style scoped>
.jd-history-empty { padding:2rem .5rem; color:var(--color-ink-muted); font-size:.82rem; text-align:center; }
.jd-history-list { display:grid; gap:.55rem; }
.jd-history-item { display:flex; align-items:stretch; border:1px solid var(--color-border-light); border-radius:var(--radius-sm); background:var(--color-white); transition:border-color .2s, background .2s; }
.jd-history-item:hover { border-color:var(--color-primary-light); background:var(--color-surface); }
.jd-history-item.selected { border-color:var(--color-primary); background:color-mix(in srgb,var(--color-primary) 6%,var(--color-white)); }
.history-check { width:2rem; flex:none; display:grid; place-items:center; margin:.6rem 0 .6rem .55rem; border:1px solid var(--color-border); border-radius:4px; color:white; }
.selected .history-check { border-color:var(--color-primary); background:var(--color-primary); }
.jd-history-open { min-width:0; flex:1; display:flex; align-items:center; justify-content:space-between; gap:.5rem; padding:.75rem .5rem .75rem .75rem; text-align:left; color:var(--color-ink-muted); }
.jd-history-copy { min-width:0; display:grid; gap:.28rem; }
.jd-history-copy strong { overflow:hidden; color:var(--color-ink); font-size:.82rem; text-overflow:ellipsis; white-space:nowrap; }
.jd-history-copy span { display:flex; align-items:center; gap:.25rem; color:var(--color-ink-muted); font-size:.68rem; }
.jd-history-delete { width:2.25rem; flex:none; display:grid; place-items:center; color:var(--color-ink-muted); border-radius:0 var(--radius-sm) var(--radius-sm) 0; }
.jd-history-delete:hover { color:var(--color-accent); background:color-mix(in srgb,var(--color-accent) 9%,transparent); }
</style>
