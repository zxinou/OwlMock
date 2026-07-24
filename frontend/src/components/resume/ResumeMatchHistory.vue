<script setup>
import { Check, ChevronRight, Clock3, Trash2 } from 'lucide-vue-next'

const props = defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  managing: { type: Boolean, default: false },
  selectedIds: { type: Array, default: () => [] },
})

const emit = defineEmits(['open', 'delete', 'toggle'])

function formatTime(value) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function titleOf(item) {
  return item.result?.job?.title || item.jd_analysis?.job?.title || '匹配任务'
}

function activate(item) {
  emit(props.managing ? 'toggle' : 'open', item)
}
</script>

<template>
  <div class="match-history">
    <div v-if="loading" class="history-empty">正在读取历史...</div>
    <div v-else-if="!items.length" class="history-empty">完成首次匹配后，报告会出现在这里。</div>
    <div v-else class="history-list">
      <div v-for="item in items" :key="item.id" class="history-row" :class="{ selected: selectedIds.includes(item.id) }">
        <button v-if="managing" type="button" class="history-check" :aria-label="`选择 ${titleOf(item)}`" :aria-pressed="selectedIds.includes(item.id)" @click="emit('toggle', item)">
          <Check v-if="selectedIds.includes(item.id)" :size="13" />
        </button>
        <button type="button" class="history-open" @click="activate(item)">
          <span class="history-main">
            <strong>{{ titleOf(item) }}</strong>
            <small>{{ item.resume?.file_name || '简历' }}</small>
            <span><Clock3 :size="12" />{{ formatTime(item.created_at) }} · {{ item.status === 'completed' ? `${item.result?.score?.value ?? '--'} 分` : item.status === 'failed' ? '失败' : '分析中' }}</span>
          </span>
          <ChevronRight v-if="!managing" :size="15" />
        </button>
        <button v-if="!managing" type="button" class="history-delete" aria-label="删除匹配记录" @click="emit('delete', item)">
          <Trash2 :size="14" />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-list { display:grid; gap:.55rem; }
.history-row { display:flex; align-items:center; border:1px solid var(--color-border-light); border-radius:var(--radius-sm); background:var(--color-white); }
.history-row.selected { border-color:var(--color-primary); background:color-mix(in srgb,var(--color-primary) 6%,var(--color-white)); }
.history-check { width:1.9rem; height:2rem; flex:none; display:grid; place-items:center; margin-left:.5rem; border:1px solid var(--color-border); border-radius:4px; color:white; }
.selected .history-check { border-color:var(--color-primary); background:var(--color-primary); }
.history-open { min-width:0; flex:1; display:flex; align-items:center; justify-content:space-between; gap:.5rem; padding:.75rem .35rem .75rem .8rem; text-align:left; }
.history-main { min-width:0; }
.history-main strong, .history-main small, .history-main span { display:block; }
.history-main strong { overflow:hidden; color:var(--color-ink); font-size:.78rem; text-overflow:ellipsis; white-space:nowrap; }
.history-main small { overflow:hidden; margin-top:.2rem; color:var(--color-ink-light); font-size:.69rem; text-overflow:ellipsis; white-space:nowrap; }
.history-main span { display:flex; align-items:center; gap:.25rem; margin-top:.3rem; color:var(--color-ink-muted); font-size:.66rem; }
.history-open > svg { flex:none; color:var(--color-ink-muted); }
.history-delete { width:2rem; height:2rem; flex:none; display:grid; place-items:center; border-radius:6px; color:var(--color-ink-muted); }
.history-delete:hover { color:var(--color-accent); background:color-mix(in srgb,var(--color-accent) 9%,transparent); }
.history-empty { padding:2rem .5rem; color:var(--color-ink-muted); font-size:.75rem; line-height:1.6; text-align:center; }
</style>
