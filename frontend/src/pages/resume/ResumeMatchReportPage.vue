<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, FilePlus2, RefreshCw, Trash2 } from 'lucide-vue-next'
import AnalysisLayout from '@/layouts/AnalysisLayout.vue'
import AnalysisErrorNotice from '@/components/common/AnalysisErrorNotice.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import ResumeMatchDashboard from '@/components/resume/ResumeMatchDashboard.vue'
import { api } from '@/api/index.js'

const route = useRoute()
const router = useRouter()
const matchId = route.params.matchId
const match = ref(null)
const loading = ref(true)
const error = ref(null)
const showDelete = ref(false)
const deleting = ref(false)

onMounted(loadReport)

async function loadReport() {
  loading.value = true
  error.value = null
  try {
    const data = await api.getResumeMatch(matchId)
    if (['pending', 'running'].includes(data.status)) {
      await router.replace({ name: 'resume-match-task', params: { taskId: matchId } })
      return
    }
    if (data.status === 'failed') {
      match.value = data
      error.value = data.error || '这次匹配没有生成报告'
      return
    }
    if (!data.result) throw new Error('匹配报告内容暂时不可用')
    match.value = data
  } catch (e) {
    error.value = e.message || '无法加载简历匹配报告'
  } finally {
    loading.value = false
  }
}

async function deleteReport() {
  deleting.value = true
  try {
    await api.deleteResumeMatch(matchId)
    await router.replace({ name: 'resume' })
  } catch (e) {
    error.value = e.message || '删除失败，请稍后重试'
    showDelete.value = false
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <AnalysisLayout>
    <div class="match-report-actions">
      <router-link :to="{ name: 'resume' }"><ArrowLeft :size="16" />返回匹配历史</router-link>
      <div>
        <button v-if="match" type="button" class="match-delete-command" @click="showDelete = true"><Trash2 :size="15" />删除</button>
        <router-link :to="{ name: 'resume' }" class="match-new-command"><FilePlus2 :size="16" />开始新匹配</router-link>
      </div>
    </div>

    <div v-if="loading" class="match-report-loading"><RefreshCw :size="22" /><span>正在读取报告...</span></div>
    <AnalysisErrorNotice v-else-if="error" :message="error" @retry="loadReport" />
    <ResumeMatchDashboard v-else-if="match?.result" :report="match.result" :resume-name="match.resume?.file_name" />

    <ConfirmDialog
      :show="showDelete"
      title="删除简历匹配报告"
      :message="`删除“${match?.result?.job?.title || '这份匹配报告'}”后无法恢复。`"
      confirm-text="删除"
      :loading="deleting"
      @confirm="deleteReport"
      @cancel="showDelete = false"
    />
  </AnalysisLayout>
</template>

<style scoped>
.match-report-actions { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:1rem; }
.match-report-actions > a, .match-delete-command { display:inline-flex; align-items:center; gap:.4rem; color:var(--color-ink-muted); font-size:.8rem; }
.match-report-actions > a:hover, .match-delete-command:hover { color:var(--color-primary); }
.match-report-actions > div { display:flex; align-items:center; gap:.6rem; }
.match-delete-command { min-height:2.5rem; padding:0 .65rem; border-radius:var(--radius-sm); }
.match-delete-command:hover { color:var(--color-accent); background:color-mix(in srgb,var(--color-accent) 9%,transparent); }
.match-new-command { min-height:2.5rem; display:inline-flex; align-items:center; gap:.45rem; padding:0 .85rem; border:1px solid color-mix(in srgb,var(--color-primary) 25%,var(--color-border)); border-radius:var(--radius-sm); color:var(--color-primary); background:color-mix(in srgb,var(--color-primary) 7%,var(--color-white)); font-size:.8rem; font-weight:700; transition:background var(--duration-fast),border-color var(--duration-fast),transform var(--duration-fast); }
.match-new-command:hover { border-color:var(--color-primary); background:color-mix(in srgb,var(--color-primary) 12%,var(--color-white)); transform:translateY(-1px); }
.match-report-loading { min-height:18rem; display:flex; align-items:center; justify-content:center; gap:.6rem; color:var(--color-ink-muted); }
.match-report-loading svg { animation:spin 1s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }
@media (max-width:560px) { .match-report-actions { align-items:flex-start; } .match-report-actions > div { align-items:stretch; flex-direction:column-reverse; } .match-new-command { justify-content:center; } }
</style>
