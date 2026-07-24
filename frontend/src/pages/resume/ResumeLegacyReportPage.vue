<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, CheckCircle2, FileSearch, Lightbulb, RefreshCw, TriangleAlert } from 'lucide-vue-next'
import AnalysisLayout from '@/layouts/AnalysisLayout.vue'
import AnalysisErrorNotice from '@/components/common/AnalysisErrorNotice.vue'
import { api } from '@/api/index.js'

const route = useRoute()
const resume = ref(null)
const loading = ref(true)
const error = ref(null)

onMounted(loadLegacy)

async function loadLegacy() {
  loading.value = true
  error.value = null
  try {
    const data = await api.getResume(route.params.resumeId)
    if (!data.analysis_result) throw new Error('这份简历没有旧版分析报告')
    resume.value = data
  } catch (e) {
    error.value = e.message || '无法读取旧版简历报告'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AnalysisLayout>
    <div class="legacy-actions">
      <router-link :to="{ name: 'resume' }"><ArrowLeft :size="16" />返回简历匹配</router-link>
      <router-link :to="{ name: 'resume' }" class="btn btn--primary"><FileSearch :size="16" />用于岗位匹配</router-link>
    </div>

    <div v-if="loading" class="legacy-loading"><RefreshCw :size="20" />正在读取旧版报告...</div>
    <AnalysisErrorNotice v-else-if="error" :message="error" @retry="loadLegacy" />
    <div v-else class="legacy-report">
      <header><span>旧版单简历分析</span><h1>{{ resume.file_name }}</h1><p>这份历史报告只评价简历本身，不包含岗位匹配分数。</p></header>
      <section>
        <div class="legacy-title"><CheckCircle2 :size="18" /><h2>简历优势</h2></div>
        <article v-for="(item, index) in resume.analysis_result.strengths" :key="index"><strong>{{ item.text }}</strong><p>{{ item.detail }}</p></article>
      </section>
      <section>
        <div class="legacy-title risk"><TriangleAlert :size="18" /><h2>待改进项</h2></div>
        <article v-for="(item, index) in resume.analysis_result.weaknesses" :key="index"><strong>{{ item.text }}</strong><p>{{ item.suggestion }}</p></article>
      </section>
      <section>
        <div class="legacy-title"><Lightbulb :size="18" /><h2>整体建议</h2></div>
        <ol><li v-for="(item, index) in resume.analysis_result.suggestions" :key="index">{{ item }}</li></ol>
      </section>
    </div>
  </AnalysisLayout>
</template>

<style scoped>
.legacy-actions { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:1.25rem; }
.legacy-actions > a:first-child { display:inline-flex; align-items:center; gap:.4rem; color:var(--color-ink-muted); font-size:.8rem; }
.legacy-loading { min-height:18rem; display:flex; align-items:center; justify-content:center; gap:.5rem; color:var(--color-ink-muted); }
.legacy-loading svg { animation:spin 1s linear infinite; }
.legacy-report { display:grid; gap:1.4rem; }
.legacy-report > header { padding-bottom:1.25rem; border-bottom:1px solid var(--color-border); }
.legacy-report header span { color:var(--color-primary); font-size:.72rem; }
.legacy-report h1 { margin-top:.4rem; font-size:1.45rem; overflow-wrap:anywhere; }
.legacy-report header p { margin-top:.45rem; color:var(--color-ink-muted); font-size:.8rem; }
.legacy-report section { padding-top:1rem; border-top:1px solid var(--color-border-light); }
.legacy-title { display:flex; align-items:center; gap:.55rem; margin-bottom:.65rem; color:var(--color-primary); }
.legacy-title.risk { color:var(--color-accent); }
.legacy-title h2 { color:var(--color-ink); font-size:.95rem; }
.legacy-report article { padding:.8rem 0; border-bottom:1px solid var(--color-border-light); }
.legacy-report article strong { color:var(--color-ink); font-size:.82rem; }
.legacy-report article p { margin-top:.35rem; color:var(--color-ink-light); font-size:.75rem; line-height:1.6; }
.legacy-report ol { display:grid; gap:.6rem; padding-left:1.2rem; color:var(--color-ink-light); font-size:.78rem; line-height:1.6; }
@keyframes spin { to { transform:rotate(360deg); } }
@media (max-width:560px) { .legacy-actions { align-items:flex-start; flex-direction:column; } }
</style>
