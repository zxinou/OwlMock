<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, FilePlus2, RefreshCw, Trash2 } from 'lucide-vue-next'
import AnalysisLayout from '@/layouts/AnalysisLayout.vue'
import AnalysisErrorNotice from '@/components/common/AnalysisErrorNotice.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import JdReportDashboard from '@/components/jd/JdReportDashboard.vue'
import { api } from '@/api/index.js'

const route = useRoute()
const router = useRouter()
const analysisId = route.params.analysisId
const analysis = ref(null)
const loading = ref(true)
const error = ref(null)
const showDelete = ref(false)
const deleting = ref(false)

onMounted(loadReport)

async function loadReport() {
  loading.value = true
  error.value = null
  try {
    const data = await api.getJdAnalysis(analysisId)
    if (['pending', 'running'].includes(data.status)) {
      await router.replace({ name: 'jd-task', params: { taskId: analysisId } })
      return
    }
    if (data.status === 'failed') {
      error.value = data.error || '这次分析没有生成报告'
      analysis.value = data
      return
    }
    if (!data.result) throw new Error('报告内容暂时不可用')
    analysis.value = data
  } catch (e) {
    error.value = e.message || '无法加载 JD 分析报告'
  } finally {
    loading.value = false
  }
}

async function deleteReport() {
  deleting.value = true
  try {
    await api.deleteJdAnalysis(analysisId)
    await router.replace({ name: 'jd' })
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
    <div class="jd-report-actions">
      <router-link :to="{ name: 'jd' }"><ArrowLeft :size="16" />返回历史</router-link>
      <div>
        <button v-if="analysis" type="button" class="jd-delete-command" @click="showDelete = true"><Trash2 :size="15" />删除</button>
        <router-link :to="{ name: 'jd' }" class="jd-new-command"><FilePlus2 :size="16" />分析新 JD</router-link>
      </div>
    </div>

    <div v-if="loading" class="jd-report-loading">
      <RefreshCw :size="22" />
      <span>正在读取报告...</span>
    </div>

    <AnalysisErrorNotice
      v-else-if="error"
      :message="error"
      @retry="loadReport"
    />

    <JdReportDashboard v-else-if="analysis?.result" :report="analysis.result" />

    <ConfirmDialog
      :show="showDelete"
      title="删除 JD 分析报告"
      :message="`删除“${analysis?.result?.job?.title || '这份报告'}”后无法恢复。`"
      confirm-text="删除"
      :loading="deleting"
      @confirm="deleteReport"
      @cancel="showDelete = false"
    />
  </AnalysisLayout>
</template>

<style scoped>
.jd-report-actions { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:1rem; }
.jd-report-actions > a, .jd-delete-command { display:inline-flex; align-items:center; gap:.4rem; color:var(--color-ink-muted); font-size:.8rem; }
.jd-report-actions > a:hover, .jd-delete-command:hover { color:var(--color-primary); }
.jd-report-actions > div { display:flex; align-items:center; gap:.6rem; }
.jd-delete-command { min-height:2.5rem; padding:0 .65rem; border-radius:var(--radius-sm); }
.jd-delete-command:hover { color:var(--color-accent); background:color-mix(in srgb,var(--color-accent) 9%,transparent); }
.jd-new-command { min-height:2.5rem; display:inline-flex; align-items:center; gap:.45rem; padding:0 .85rem; border:1px solid color-mix(in srgb,var(--color-primary) 25%,var(--color-border)); border-radius:var(--radius-sm); color:var(--color-primary); background:color-mix(in srgb,var(--color-primary) 7%,var(--color-white)); font-size:.8rem; font-weight:700; transition:background var(--duration-fast),border-color var(--duration-fast),transform var(--duration-fast); }
.jd-new-command:hover { border-color:var(--color-primary); background:color-mix(in srgb,var(--color-primary) 12%,var(--color-white)); transform:translateY(-1px); }
.jd-report-loading { min-height:18rem; display:flex; align-items:center; justify-content:center; gap:.6rem; color:var(--color-ink-muted); }
.jd-report-loading svg { animation:spin 1s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }
@media (max-width:560px) { .jd-report-actions { align-items:flex-start; } .jd-report-actions > div { align-items:stretch; flex-direction:column-reverse; } .jd-new-command { justify-content:center; } }
</style>
