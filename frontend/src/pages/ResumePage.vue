<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { BriefcaseBusiness, FilePlus2, FolderOpen, History, Sparkles, Trash2, Upload } from 'lucide-vue-next'
import AnalysisLayout from '@/layouts/AnalysisLayout.vue'
import AnalysisErrorNotice from '@/components/common/AnalysisErrorNotice.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import FileUploadZone from '@/components/common/FileUploadZone.vue'
import AnalyzedJobPicker from '@/components/resume/AnalyzedJobPicker.vue'
import ResumeLibrary from '@/components/resume/ResumeLibrary.vue'
import ResumeMatchHistory from '@/components/resume/ResumeMatchHistory.vue'
import { api } from '@/api/index.js'

const router = useRouter()
const resumeMode = ref('library')
const resumes = ref([])
const completedJds = ref([])
const history = ref([])
const selectedResumeId = ref('')
const selectedJdIds = ref([])
const uploadFile = ref(null)
const loadingResumes = ref(false)
const loadingJds = ref(false)
const loadingHistory = ref(false)
const uploading = ref(false)
const submitting = ref(false)
const error = ref(null)
const deleteTarget = ref(null)
const deleting = ref(false)
const managingHistory = ref(false)
const selectedHistoryIds = ref([])

const canSubmit = computed(() => Boolean(selectedResumeId.value && selectedJdIds.value.length))
const submitLabel = computed(() => selectedJdIds.value.length
  ? `开始匹配 ${selectedJdIds.value.length} 个岗位`
  : '请选择岗位')

onMounted(async () => {
  await Promise.all([loadResumes(), loadJds(), loadHistory()])
})

async function loadResumes() {
  loadingResumes.value = true
  try {
    resumes.value = await api.getResumes()
    if (!selectedResumeId.value && resumes.value.length) selectedResumeId.value = resumes.value[0].id
    if (!resumes.value.length) resumeMode.value = 'upload'
  } catch (e) {
    error.value = e.message
  } finally {
    loadingResumes.value = false
  }
}

async function loadJds() {
  loadingJds.value = true
  try {
    const records = await api.getJdAnalyses()
    completedJds.value = records.filter((item) => item.status === 'completed' && item.result)
    const available = new Set(completedJds.value.map((item) => item.id))
    selectedJdIds.value = selectedJdIds.value.filter((id) => available.has(id))
  } catch (e) {
    error.value = e.message
  } finally {
    loadingJds.value = false
  }
}

async function loadHistory() {
  loadingHistory.value = true
  try {
    history.value = await api.getResumeMatches()
  } catch (e) {
    error.value = e.message
  } finally {
    loadingHistory.value = false
  }
}

function toggleJd(id) {
  selectedJdIds.value = selectedJdIds.value.includes(id)
    ? selectedJdIds.value.filter((value) => value !== id)
    : [...selectedJdIds.value, id]
}

async function uploadResume() {
  if (!uploadFile.value?.raw || uploading.value) return
  uploading.value = true
  error.value = null
  try {
    const created = await api.uploadResume(uploadFile.value.raw)
    await loadResumes()
    selectedResumeId.value = created.id
    uploadFile.value = null
    resumeMode.value = 'library'
  } catch (e) {
    error.value = e.message || '简历上传失败，请稍后重试'
  } finally {
    uploading.value = false
  }
}

async function submitMatch() {
  if (!canSubmit.value || submitting.value) return
  submitting.value = true
  error.value = null
  try {
    const batch = await api.submitResumeMatchBatch({
      resumeId: selectedResumeId.value,
      jdAnalysisIds: selectedJdIds.value,
    })
    await router.push({ name: 'resume-match-batch', params: { batchId: batch.batch_id } })
  } catch (e) {
    error.value = e.message || '创建匹配任务失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

function openHistory(item) {
  if (item.batch_id) {
    router.push({ name: 'resume-match-batch', params: { batchId: item.batch_id } })
    return
  }
  const completed = item.status === 'completed' && item.result
  router.push({
    name: completed ? 'resume-match-report' : 'resume-match-task',
    params: completed ? { matchId: item.id } : { taskId: item.id },
  })
}

function openLegacy(item) {
  router.push({ name: 'resume-legacy-report', params: { resumeId: item.id } })
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  error.value = null
  try {
    if (deleteTarget.value.kind === 'batch-match') {
      await api.deleteResumeMatches(deleteTarget.value.ids)
      history.value = history.value.filter((item) => !deleteTarget.value.ids.includes(item.id))
      selectedHistoryIds.value = []
      managingHistory.value = false
    } else if (deleteTarget.value.kind === 'match') {
      await api.deleteResumeMatch(deleteTarget.value.item.id)
      history.value = history.value.filter((item) => item.id !== deleteTarget.value.item.id)
    } else {
      const resumeId = deleteTarget.value.item.id
      await api.deleteResume(resumeId)
      resumes.value = resumes.value.filter((item) => item.id !== resumeId)
      history.value = history.value.filter((item) => item.resume_id !== resumeId)
      if (selectedResumeId.value === resumeId) selectedResumeId.value = resumes.value[0]?.id || ''
      if (!resumes.value.length) resumeMode.value = 'upload'
    }
    deleteTarget.value = null
  } catch (e) {
    error.value = e.message || '删除失败，请稍后重试'
  } finally {
    deleting.value = false
  }
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
</script>

<template>
  <AnalysisLayout>
    <header class="resume-page-head">
      <div>
        <h1>简历中心</h1>
        <p>管理你的简历，并与已经完成分析的多个岗位同时匹配。</p>
      </div>
      <div class="resume-head-mark" aria-hidden="true"><BriefcaseBusiness :size="20" /></div>
    </header>

    <AnalysisErrorNotice v-if="error" class="mb-5" :message="error" :retryable="false" />

    <div class="resume-input-grid">
      <section class="resume-workbench">
        <div class="resume-section-head">
          <div><span>第一步</span><h2>选择简历</h2></div>
          <div class="resume-mode-switch" role="tablist" aria-label="简历来源">
            <button type="button" role="tab" :aria-selected="resumeMode === 'library'" :class="{ active: resumeMode === 'library' }" @click="resumeMode = 'library'">
              <FolderOpen :size="15" />简历库
            </button>
            <button type="button" role="tab" :aria-selected="resumeMode === 'upload'" :class="{ active: resumeMode === 'upload' }" @click="resumeMode = 'upload'">
              <Upload :size="15" />上传新简历
            </button>
          </div>
        </div>

        <ResumeLibrary
          v-if="resumeMode === 'library'"
          :items="resumes"
          :selected-id="selectedResumeId"
          :loading="loadingResumes"
          @select="selectedResumeId = $event"
          @legacy="openLegacy"
          @delete="deleteTarget = { kind: 'resume', item: $event }"
        />
        <div v-else class="resume-upload-mode">
          <FileUploadZone
            :file="uploadFile"
            label="上传简历文件"
            hint="PDF、PNG、JPG 或 JPEG，最大 10MB"
            :formats="['.pdf', '.png', '.jpg', '.jpeg']"
            accept=".pdf,.png,.jpg,.jpeg"
            @select="uploadFile = $event"
            @remove="uploadFile = null"
          />
          <button type="button" class="btn btn--secondary" :disabled="!uploadFile || uploading" @click="uploadResume">
            <FilePlus2 :size="16" />{{ uploading ? '正在上传...' : '上传并选中' }}
          </button>
        </div>

        <div class="resume-divider"></div>

        <div class="resume-section-head job-section-head">
          <div><span>第二步</span><h2>选择已分析岗位</h2></div>
          <small>已选择 {{ selectedJdIds.length }} 个</small>
        </div>
        <AnalyzedJobPicker
          :items="completedJds"
          :selected-ids="selectedJdIds"
          :loading="loadingJds"
          @toggle="toggleJd"
        />

        <div class="resume-submit-row">
          <span>每个岗位会生成独立报告，可在结果页横向比较。</span>
          <button type="button" class="btn btn--primary" :disabled="!canSubmit || submitting" @click="submitMatch">
            <Sparkles :size="16" />{{ submitting ? '正在创建任务...' : submitLabel }}
          </button>
        </div>
      </section>

      <aside class="resume-history-panel">
        <div class="resume-history-title">
          <div><History :size="17" /><h2>最近匹配</h2></div>
          <div class="history-actions">
            <button v-if="managingHistory" type="button" @click="toggleSelectAllHistory">{{ selectedHistoryIds.length === history.length ? '取消全选' : '全选' }}</button>
            <button type="button" :disabled="!history.length" @click="toggleManageHistory">{{ managingHistory ? '完成' : '管理' }}</button>
            <button v-if="!managingHistory" type="button" :disabled="loadingHistory" @click="loadHistory">刷新</button>
          </div>
        </div>
        <ResumeMatchHistory
          :items="history"
          :loading="loadingHistory"
          :managing="managingHistory"
          :selected-ids="selectedHistoryIds"
          @open="openHistory"
          @delete="deleteTarget = { kind: 'match', item: $event }"
          @toggle="toggleHistoryItem"
        />
        <button v-if="managingHistory" type="button" class="batch-delete-button" :disabled="!selectedHistoryIds.length || deleting" @click="deleteTarget = { kind: 'batch-match', ids: [...selectedHistoryIds] }"><Trash2 :size="14" />删除所选（{{ selectedHistoryIds.length }}）</button>
      </aside>
    </div>

    <ConfirmDialog
      :show="Boolean(deleteTarget)"
      :title="deleteTarget?.kind === 'resume' ? '删除简历' : deleteTarget?.kind === 'batch-match' ? '批量删除匹配报告' : '删除匹配报告'"
      :message="deleteTarget?.kind === 'resume'
        ? `删除“${deleteTarget?.item?.file_name || '这份简历'}”后，相关匹配记录也会删除且无法恢复。`
        : deleteTarget?.kind === 'batch-match'
        ? `确定删除选中的 ${deleteTarget?.ids?.length || 0} 条匹配报告吗？删除后无法恢复。`
        : `删除“${deleteTarget?.item?.result?.job?.title || '这份匹配报告'}”后无法恢复。`"
      confirm-text="删除"
      :loading="deleting"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />
  </AnalysisLayout>
</template>

<style scoped>
.resume-page-head { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; margin-bottom:1.5rem; }
.resume-page-head h1 { font-size:1.5rem; }
.resume-page-head p { margin-top:.4rem; color:var(--color-ink-muted); font-size:.9rem; }
.resume-head-mark { width:2.75rem; height:2.75rem; display:grid; place-items:center; flex:none; border-radius:var(--radius-md); color:var(--color-primary); background:var(--color-surface-alt); }
.resume-input-grid { display:grid; grid-template-columns:minmax(0,1fr) 18rem; gap:1.25rem; align-items:start; }
.resume-workbench { min-width:0; padding:1.5rem; border:1px solid var(--color-border); border-radius:var(--radius-lg); background:var(--color-white); box-shadow:var(--shadow-sm); }
.resume-section-head { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:1rem; }
.resume-section-head span { display:block; margin-bottom:.2rem; color:var(--color-primary); font-size:.68rem; font-weight:700; }
.resume-section-head h2 { font-size:.95rem; }
.resume-section-head small { color:var(--color-ink-muted); font-size:.72rem; }
.resume-mode-switch { display:inline-flex; gap:.2rem; padding:.22rem; border-radius:var(--radius-sm); background:var(--color-surface); }
.resume-mode-switch button { min-height:2rem; display:inline-flex; align-items:center; gap:.35rem; padding:0 .7rem; border-radius:6px; color:var(--color-ink-light); font-size:.75rem; font-weight:600; }
.resume-mode-switch button.active { color:white; background:var(--color-primary); }
.resume-upload-mode { display:grid; gap:.85rem; }
.resume-upload-mode .btn { justify-self:end; }
.resume-divider { height:1px; margin:1.4rem 0; background:var(--color-border-light); }
.job-section-head { margin-bottom:.7rem; }
.resume-submit-row { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-top:1.1rem; }
.resume-submit-row > span { color:var(--color-ink-muted); font-size:.75rem; }
.resume-history-panel { min-width:0; padding-left:1.25rem; border-left:1px solid var(--color-border-light); }
.resume-history-title { display:flex; align-items:center; justify-content:space-between; gap:.75rem; margin-bottom:.8rem; }
.resume-history-title > div:first-child { display:flex; align-items:center; gap:.5rem; color:var(--color-primary); }
.resume-history-title h2 { font-size:.9rem; }
.resume-history-title button { color:var(--color-ink-muted); font-size:.75rem; }
.resume-history-title button:hover { color:var(--color-primary); }
.history-actions { display:flex; align-items:center; gap:.45rem; }
.batch-delete-button { width:100%; min-height:2.35rem; display:flex; align-items:center; justify-content:center; gap:.4rem; margin-top:.75rem; border-radius:var(--radius-sm); color:white; background:var(--color-accent); font-size:.75rem; font-weight:700; }
.batch-delete-button:disabled { opacity:.45; cursor:not-allowed; }
@media (max-width:900px) { .resume-input-grid { grid-template-columns:1fr; } .resume-history-panel { padding:1.25rem 0 0; border-left:0; border-top:1px solid var(--color-border-light); } }
@media (max-width:620px) { .resume-workbench { padding:1rem; } .resume-section-head { align-items:flex-start; flex-direction:column; } .job-section-head { align-items:center; flex-direction:row; } .resume-mode-switch { width:100%; } .resume-mode-switch button { flex:1; justify-content:center; } .resume-submit-row { align-items:stretch; flex-direction:column; } .resume-submit-row .btn { justify-content:center; } }
</style>
