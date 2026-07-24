<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { FileImage, FileText, History, Sparkles, Trash2 } from 'lucide-vue-next'
import AnalysisLayout from '@/layouts/AnalysisLayout.vue'
import AnalysisErrorNotice from '@/components/common/AnalysisErrorNotice.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import FileUploadZone from '@/components/common/FileUploadZone.vue'
import JdHistoryList from '@/components/jd/JdHistoryList.vue'
import { api } from '@/api/index.js'

const router = useRouter()
const mode = ref('text')
const jdInput = ref('')
const jdImage = ref(null)
const submitting = ref(false)
const historyLoading = ref(false)
const history = ref([])
const error = ref(null)
const deleteTarget = ref(null)
const deleting = ref(false)
const managingHistory = ref(false)
const selectedHistoryIds = ref([])

const canSubmit = computed(() => mode.value === 'text' ? Boolean(jdInput.value.trim()) : Boolean(jdImage.value?.raw))

onMounted(loadHistory)

async function loadHistory() {
  historyLoading.value = true
  try { history.value = await api.getJdAnalyses() }
  catch (e) { error.value = e.message }
  finally { historyLoading.value = false }
}

async function submit() {
  if (!canSubmit.value || submitting.value) return
  submitting.value = true
  error.value = null
  try {
    const task = mode.value === 'text'
      ? await api.submitJd(jdInput.value.trim())
      : await api.submitJdImage(jdImage.value.raw)
    await router.push({ name: 'jd-task', params: { taskId: task.task_id } })
  } catch (e) { error.value = e.message || '提交分析失败，请稍后重试' }
  finally { submitting.value = false }
}

function openHistory(item) {
  const complete = item.status === 'completed' && item.result
  router.push({
    name: complete ? 'jd-report' : 'jd-task',
    params: complete ? { analysisId: item.id } : { taskId: item.id },
  })
}

function toggleHistoryItem(item) {
  selectedHistoryIds.value = selectedHistoryIds.value.includes(item.id)
    ? selectedHistoryIds.value.filter((id) => id !== item.id)
    : [...selectedHistoryIds.value, item.id]
}

function toggleManageHistory() {
  managingHistory.value = !managingHistory.value
  selectedHistoryIds.value = []
}

function toggleSelectAllHistory() {
  selectedHistoryIds.value = selectedHistoryIds.value.length === history.value.length
    ? [] : history.value.map((item) => item.id)
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  error.value = null
  try {
    const ids = deleteTarget.value.kind === 'batch' ? deleteTarget.value.ids : [deleteTarget.value.item.id]
    if (deleteTarget.value.kind === 'batch') await api.deleteJdAnalyses(ids)
    else await api.deleteJdAnalysis(ids[0])
    history.value = history.value.filter((item) => !ids.includes(item.id))
    selectedHistoryIds.value = []
    managingHistory.value = false
    deleteTarget.value = null
  } catch (e) { error.value = e.message || '删除失败，请稍后重试' }
  finally { deleting.value = false }
}
</script>

<template>
  <AnalysisLayout>
    <header class="jd-page-head">
      <div><h1>JD 智能分析</h1><p>看清岗位真正重视的能力，再决定面试准备顺序。</p></div>
      <div class="jd-head-mark" aria-hidden="true"><Sparkles :size="20" /></div>
    </header>

    <AnalysisErrorNotice v-if="error" class="mb-5" :message="error" :retryable="false" />

    <div class="jd-input-grid">
      <section class="jd-workbench">
        <div class="jd-mode-switch" role="tablist" aria-label="JD 输入方式">
          <button type="button" role="tab" :aria-selected="mode === 'text'" :class="{ active: mode === 'text' }" @click="mode = 'text'"><FileText :size="16" />粘贴文本</button>
          <button type="button" role="tab" :aria-selected="mode === 'image'" :class="{ active: mode === 'image' }" @click="mode = 'image'"><FileImage :size="16" />上传截图</button>
        </div>
        <div v-if="mode === 'text'" class="jd-text-mode">
          <label for="jd-input">职位描述</label>
          <textarea id="jd-input" v-model="jdInput" maxlength="12000" placeholder="粘贴完整的岗位职责和任职要求..."></textarea>
          <span class="jd-counter">{{ jdInput.length }} / 12000</span>
        </div>
        <div v-else class="jd-image-mode">
          <FileUploadZone :file="jdImage" label="上传 JD 截图" hint="PNG、JPG 或 JPEG，最大 10MB" :formats="['.png', '.jpg', '.jpeg']" accept=".png,.jpg,.jpeg" @select="jdImage = $event" @remove="jdImage = null" />
        </div>
        <div class="jd-submit-row">
          <span>{{ mode === 'text' ? '建议保留完整上下文和要求分组' : '请确保截图文字清晰完整' }}</span>
          <button type="button" class="btn btn--primary" :disabled="!canSubmit || submitting" @click="submit"><Sparkles :size="16" />{{ submitting ? '正在创建任务...' : '开始分析' }}</button>
        </div>
      </section>

      <aside class="jd-history-panel">
        <div class="jd-history-title">
          <div><History :size="17" /><h2>最近分析</h2></div>
          <div class="history-actions">
            <button v-if="managingHistory" type="button" @click="toggleSelectAllHistory">{{ selectedHistoryIds.length === history.length ? '取消全选' : '全选' }}</button>
            <button type="button" :disabled="!history.length" @click="toggleManageHistory">{{ managingHistory ? '完成' : '管理' }}</button>
            <button v-if="!managingHistory" type="button" :disabled="historyLoading" @click="loadHistory">刷新</button>
          </div>
        </div>
        <JdHistoryList :items="history" :loading="historyLoading" :managing="managingHistory" :selected-ids="selectedHistoryIds" @open="openHistory" @delete="deleteTarget = { kind: 'single', item: $event }" @toggle="toggleHistoryItem" />
        <button v-if="managingHistory" type="button" class="batch-delete-button" :disabled="!selectedHistoryIds.length || deleting" @click="deleteTarget = { kind: 'batch', ids: [...selectedHistoryIds] }"><Trash2 :size="14" />删除所选（{{ selectedHistoryIds.length }}）</button>
      </aside>
    </div>

    <ConfirmDialog :show="Boolean(deleteTarget)" :title="deleteTarget?.kind === 'batch' ? '批量删除 JD 分析' : '删除 JD 分析'" :message="deleteTarget?.kind === 'batch' ? `确定删除选中的 ${deleteTarget?.ids?.length || 0} 条 JD 分析吗？删除后无法恢复。` : `删除“${deleteTarget?.item?.result?.job?.title || '这条分析'}”后无法恢复。`" confirm-text="删除" :loading="deleting" @confirm="confirmDelete" @cancel="deleteTarget = null" />
  </AnalysisLayout>
</template>

<style scoped>
.jd-page-head { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; margin-bottom:1.5rem; }
.jd-page-head h1 { font-size:1.5rem; }.jd-page-head p { margin-top:.4rem; color:var(--color-ink-muted); font-size:.9rem; }
.jd-head-mark { width:2.75rem; height:2.75rem; display:grid; place-items:center; flex:none; border-radius:var(--radius-md); color:var(--color-primary); background:var(--color-surface-alt); }
.jd-input-grid { display:grid; grid-template-columns:minmax(0,1fr) 18rem; gap:1.25rem; align-items:start; }
.jd-workbench { min-width:0; padding:1.5rem; border:1px solid var(--color-border); border-radius:var(--radius-lg); background:var(--color-white); box-shadow:var(--shadow-sm); }
.jd-mode-switch { display:inline-flex; gap:.25rem; padding:.25rem; margin-bottom:1.25rem; border-radius:var(--radius-sm); background:var(--color-surface); }
.jd-mode-switch button { min-height:2.25rem; display:inline-flex; align-items:center; gap:.45rem; padding:0 .85rem; border-radius:6px; color:var(--color-ink-light); font-size:.85rem; font-weight:600; }
.jd-mode-switch button.active { color:white; background:var(--color-primary); box-shadow:var(--shadow-sm); }
.jd-text-mode { position:relative; }.jd-text-mode label { display:block; margin-bottom:.55rem; color:var(--color-ink); font-size:.85rem; font-weight:600; }
.jd-text-mode textarea { width:100%; min-height:17rem; resize:vertical; padding:1rem; border:1px solid var(--color-border); border-radius:var(--radius-sm); outline:none; color:var(--color-ink); background:var(--color-base); line-height:1.7; }
.jd-text-mode textarea:focus { border-color:var(--color-primary); box-shadow:var(--shadow-glow); }.jd-counter { position:absolute; right:.75rem; bottom:.55rem; color:var(--color-ink-muted); font-size:.72rem; }
.jd-image-mode { min-height:19rem; }.jd-submit-row { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-top:1.25rem; }.jd-submit-row > span { color:var(--color-ink-muted); font-size:.78rem; }
.jd-history-panel { min-width:0; padding-left:1.25rem; border-left:1px solid var(--color-border-light); }.jd-history-title { display:flex; align-items:center; justify-content:space-between; gap:.5rem; margin-bottom:.8rem; }
.jd-history-title > div:first-child { display:flex; align-items:center; gap:.5rem; color:var(--color-primary); }.jd-history-title h2 { font-size:.9rem; }.history-actions { display:flex; align-items:center; gap:.45rem; }.history-actions button { color:var(--color-ink-muted); font-size:.72rem; }.history-actions button:hover { color:var(--color-primary); }
.batch-delete-button { width:100%; min-height:2.35rem; display:flex; align-items:center; justify-content:center; gap:.4rem; margin-top:.75rem; border-radius:var(--radius-sm); color:white; background:var(--color-accent); font-size:.75rem; font-weight:700; }.batch-delete-button:disabled { opacity:.45; cursor:not-allowed; }
@media (max-width:900px) { .jd-input-grid { grid-template-columns:1fr; }.jd-history-panel { padding:1.25rem 0 0; border-left:0; border-top:1px solid var(--color-border-light); } }
@media (max-width:560px) { .jd-workbench { padding:1rem; }.jd-submit-row { align-items:stretch; flex-direction:column; }.jd-submit-row .btn { justify-content:center; }.jd-history-title { align-items:flex-start; flex-direction:column; } }
</style>
