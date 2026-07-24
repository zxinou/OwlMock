<script setup>
import { FileImage, FileText, Trash2 } from 'lucide-vue-next'

defineProps({
  items: { type: Array, default: () => [] },
  selectedId: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

defineEmits(['select', 'legacy', 'delete'])

function formatDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}
</script>

<template>
  <div class="resume-library">
    <div v-if="loading" class="resume-empty">正在读取简历库...</div>
    <div v-else-if="!items.length" class="resume-empty">还没有简历，请先上传一份。</div>
    <div v-else class="resume-options">
      <div
        v-for="item in items"
        :key="item.id"
        class="resume-option"
        :class="{ selected: item.id === selectedId }"
      >
        <button type="button" class="resume-select" @click="$emit('select', item.id)">
          <span class="resume-file-icon">
            <FileText v-if="item.file_type === 'pdf'" :size="18" />
            <FileImage v-else :size="18" />
          </span>
          <span class="resume-copy">
            <strong>{{ item.file_name || '未命名简历' }}</strong>
            <small>{{ item.file_type?.toUpperCase() }} · {{ formatDate(item.created_at) }}</small>
          </span>
          <span class="resume-radio" aria-hidden="true"></span>
        </button>
        <div class="resume-actions">
          <button v-if="item.has_analysis" type="button" @click="$emit('legacy', item)">旧版报告</button>
          <button type="button" class="icon-command" aria-label="删除简历" @click="$emit('delete', item)">
            <Trash2 :size="14" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.resume-options { display:grid; gap:.65rem; }
.resume-option { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; gap:.5rem; padding:.6rem; border:1px solid var(--color-border); border-radius:var(--radius-sm); background:var(--color-base); transition:border-color .2s, background .2s; }
.resume-option.selected { border-color:var(--color-primary); background:color-mix(in srgb,var(--color-primary) 7%,var(--color-base)); }
.resume-select { min-width:0; display:grid; grid-template-columns:2.25rem minmax(0,1fr) 1rem; align-items:center; gap:.65rem; text-align:left; }
.resume-file-icon { width:2.25rem; height:2.25rem; display:grid; place-items:center; border-radius:6px; color:var(--color-primary); background:var(--color-surface-alt); }
.resume-copy { min-width:0; }
.resume-copy strong, .resume-copy small { display:block; }
.resume-copy strong { overflow:hidden; color:var(--color-ink); font-size:.82rem; text-overflow:ellipsis; white-space:nowrap; }
.resume-copy small { margin-top:.2rem; color:var(--color-ink-muted); font-size:.7rem; }
.resume-radio { width:.9rem; height:.9rem; border:1px solid var(--color-border); border-radius:50%; }
.selected .resume-radio { border:4px solid var(--color-primary); }
.resume-actions { display:flex; align-items:center; gap:.35rem; }
.resume-actions button { color:var(--color-ink-muted); font-size:.7rem; }
.resume-actions button:hover { color:var(--color-primary); }
.icon-command { width:1.9rem; height:1.9rem; display:grid; place-items:center; border-radius:6px; }
.icon-command:hover { color:var(--color-accent) !important; background:color-mix(in srgb,var(--color-accent) 9%,transparent); }
.resume-empty { padding:2rem 1rem; color:var(--color-ink-muted); font-size:.8rem; text-align:center; }
@media (max-width:560px) { .resume-option { grid-template-columns:1fr; } .resume-actions { justify-content:flex-end; } }
</style>
