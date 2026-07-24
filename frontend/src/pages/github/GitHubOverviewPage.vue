<script setup>
import { onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useGithubAnalysis } from '@/composables/useGithubAnalysis.js'
import ScoreRing from '@/components/common/ScoreRing.vue'
import TechStackTags from '@/components/github/TechStackTags.vue'
import DirectoryTree from '@/components/github/DirectoryTree.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'

const route = useRoute()
const { currentRepo: repo, loading, error, phase, progressMessage, activeTaskId, fetchRepo, reconnectTask, analyzeNewRepo } = useGithubAnalysis()

const isAnalyzing = computed(() => ['analyzing', 'submitting', 'fetching'].includes(phase.value))
const overlayText = computed(() => {
  if (phase.value === 'submitting') return '正在提交分析请求'
  if (phase.value === 'analyzing') return '正在分析代码仓库'
  if (phase.value === 'fetching') return '正在加载分析结果'
  return '正在加载仓库数据'
})

onMounted(async () => {
  await fetchRepo(route.params.id)
  const stillRunning = ['pending', 'running'].includes(repo.value?.status)
  if (stillRunning || activeTaskId.value === route.params.id) {
    await reconnectTask(route.params.id)
  }
})

async function handleRetry() {
  if (!repo.value?.url) return
  await analyzeNewRepo(repo.value.url)
}
</script>

<template>
  <div class="github-overview-page">
    <router-link to="/analysis/github" class="github-back inline-flex items-center gap-2 text-sm text-ink-muted hover:text-primary transition-colors no-underline">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      返回仓库列表
    </router-link>

    <div v-if="repo" class="animate-fade-in">
      <div v-if="repo.status === 'failed'" class="text-center py-12">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-red-50 dark:bg-red-900/20 flex items-center justify-center">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" class="text-red-500"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/><path d="M8 8l8 8M16 8l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        </div>
        <h3 class="text-lg font-bold text-ink mb-2">分析失败</h3>
        <p class="text-sm text-ink-muted mb-6 max-w-md mx-auto">{{ repo.error || '分析过程中出现错误，请重试。' }}</p>
        <div class="flex items-center justify-center gap-3">
          <button class="btn btn--primary text-sm" @click="handleRetry">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 8a6 6 0 1 1 12 0A6 6 0 0 1 2 8z" stroke="currentColor" stroke-width="1.5"/><path d="M8 5v3l2 1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
            重新分析
          </button>
          <router-link to="/analysis/github" class="btn text-sm text-ink-muted hover:text-ink">返回列表</router-link>
        </div>
      </div>

      <template v-else>
        <header class="github-repo-header">
          <div class="github-repo-copy">
            <p class="github-kicker">Repository overview</p>
            <h1>{{ repo.fullName }}</h1>
            <p>{{ repo.description || '暂无项目描述，以下内容来自仓库源码索引。' }}</p>
          </div>
          <a :href="repo.url" target="_blank" rel="noopener" class="github-source-link inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-border dark:border-border bg-white dark:bg-surface text-ink-light hover:border-primary hover:text-primary transition-theme no-underline">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M5.5 8.5l3-3M4.5 5.5h-2v6h6v-2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            GitHub
          </a>
        </header>

        <section class="github-signal-band" :class="{ 'github-signal-band--solo': !repo.score }">
          <ScoreRing v-if="repo.score" :score="repo.score" label="项目综合评分" :summary="`仓库 ${repo.fullName} 综合评估`" />
          <TechStackTags :tags="repo.techTags" />
        </section>

        <section class="github-report-grid">
          <section v-if="repo.directoryTree" class="github-report-section github-structure-section">
            <div class="github-section-heading">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" class="text-primary"><path d="M3 5c0-.6.4-1 1-1h2l1.5 2h6.5c.6 0 1 .4 1 1v6c0 .6-.4 1-1 1H4c-.6 0-1-.4-1-1V5z" stroke="currentColor" stroke-width="1.3"/></svg>
              <div><h2>项目结构</h2><span>快速浏览仓库目录与入口文件</span></div>
            </div>
            <div class="github-tree-wrap"><DirectoryTree :node="repo.directoryTree" /></div>
          </section>

          <section class="github-report-section github-insights-section">
            <div class="github-section-heading">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" class="text-primary"><path d="M9 2l2.1 4.3 4.7.7-3.4 3.3.8 4.7L9 12.8l-4.2 2.2.8-4.7L2.2 7l4.7-.7z" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <div><h2>项目亮点与改进</h2><span>从架构、可维护性和体验提炼重点</span></div>
            </div>
            <div class="github-insight-group">
              <h3>项目亮点</h3>
              <ul><li v-for="(highlight, index) in repo.highlights" :key="index">{{ highlight.text || highlight }}</li></ul>
            </div>
            <div class="github-insight-group github-suggestion-group">
              <h3>改进建议</h3>
              <ul><li v-for="(suggestion, index) in repo.suggestions" :key="index">{{ suggestion.text || suggestion }}</li></ul>
            </div>
          </section>
        </section>

        <section class="github-report-section github-questions-section">
          <div class="github-section-heading">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" class="text-primary"><circle cx="9" cy="9" r="7" stroke="currentColor" stroke-width="1.3"/><path d="M7 7.5a2 2 0 0 1 3.3 1.3c0 1-1.3 1.2-1.3 2.2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/><circle cx="9.2" cy="13" r="0.8" fill="currentColor"/></svg>
            <div><h2>面试问题</h2><span>围绕仓库真实实现准备追问</span></div>
          </div>
          <div class="github-question-grid">
            <article v-for="(qa, index) in repo.questions" :key="index" class="github-question-row">
              <span class="github-question-number">{{ String(index + 1).padStart(2, '0') }}</span>
              <div><h3>{{ qa.q }}</h3><p>{{ qa.a }}</p></div>
            </article>
          </div>
        </section>

        <div class="github-deep-action">
          <router-link :to="`/analysis/github/${repo.id}/deep`" class="btn btn--primary text-sm">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 3h12M2 8h8M2 13h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
            查看深度分析报告
          </router-link>
        </div>
      </template>
    </div>

    <div v-else-if="error && !loading && !isAnalyzing" class="text-center py-12 animate-fade-in">
      <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-red-50 dark:bg-red-900/20 flex items-center justify-center">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" class="text-red-500"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/><path d="M8 8l8 8M16 8l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
      </div>
      <h3 class="text-lg font-bold text-ink mb-2">分析失败</h3>
      <p class="text-sm text-ink-muted mb-6 max-w-md mx-auto">{{ error }}</p>
      <router-link to="/analysis/github" class="btn btn--primary text-sm">返回列表</router-link>
    </div>

    <LoadingOverlay :active="loading || isAnalyzing" :text="overlayText" :subtext="progressMessage || '猫头鹰助手正在整理分析结果…'" />
  </div>
</template>

<style scoped>
.github-overview-page { --github-gap: 1.25rem; width: 100%; padding-bottom: 2rem; }
.github-back { margin-bottom: 1.35rem; }
.github-repo-header { display:flex; align-items:flex-end; justify-content:space-between; gap:2rem; padding-bottom:1.4rem; border-bottom:1px solid var(--color-border); }
.github-repo-copy { min-width:0; }
.github-kicker { color:var(--color-primary); font-size:.68rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }
.github-repo-copy h1 { margin-top:.35rem; font-size:1.65rem; overflow-wrap:anywhere; }
.github-repo-copy > p:last-child { max-width:52rem; margin-top:.45rem; color:var(--color-ink-muted); font-size:.8rem; line-height:1.55; overflow-wrap:anywhere; }
.github-source-link { flex:none; }
.github-signal-band { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); align-items:stretch; gap:var(--github-gap); margin-top:var(--github-gap); }
.github-signal-band--solo { grid-template-columns:1fr; }
.github-signal-band :deep(.flex.items-center) { height:100%; padding:1rem 1.25rem !important; border-radius:var(--radius-md) !important; box-shadow:none; }
.github-signal-band :deep(.w-20) { width:4.5rem; height:4.5rem; }
.github-signal-band :deep(.text-4xl) { font-size:1.8rem; }
.github-signal-band :deep(.text-lg) { font-size:.92rem; }
.github-signal-band :deep(.text-sm) { font-size:.7rem; }
.github-report-grid { display:grid; grid-template-columns:minmax(0, 1fr) minmax(0, 1fr); gap:var(--github-gap); margin-top:var(--github-gap); align-items:start; }
.github-report-section { min-width:0; padding:1.25rem; border:1px solid var(--color-border-light); border-radius:var(--radius-md); background:var(--color-white); }
.github-section-heading { display:flex; align-items:flex-start; gap:.6rem; padding-bottom:.85rem; border-bottom:1px solid var(--color-border-light); color:var(--color-primary); }
.github-section-heading svg { flex:none; margin-top:.1rem; }
.github-section-heading h2 { font-size:.92rem; }
.github-section-heading span { display:block; margin-top:.2rem; color:var(--color-ink-muted); font-size:.68rem; font-weight:400; }
.github-tree-wrap { max-height:32rem; overflow:auto; padding-top:.75rem; }
.github-tree-wrap :deep(.font-mono) { font-size:.72rem; }
.github-insights-section { display:grid; gap:1.15rem; }
.github-insight-group h3 { color:var(--color-primary); font-size:.74rem; }
.github-insight-group ul { display:grid; gap:.6rem; margin-top:.6rem; padding:0; list-style:none; }
.github-insight-group li { position:relative; padding-left:1rem; color:var(--color-ink-light); font-size:.75rem; line-height:1.6; overflow-wrap:anywhere; }
.github-insight-group li::before { content:''; position:absolute; top:.65em; left:0; width:.35rem; height:.35rem; border-radius:50%; background:var(--color-primary); }
.github-suggestion-group { padding-top:1rem; border-top:1px solid var(--color-border-light); }
.github-suggestion-group li::before { background:var(--color-secondary); }
.github-questions-section { margin-top:var(--github-gap); }
.github-question-grid { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); column-gap:2rem; }
.github-question-row { display:grid; grid-template-columns:2rem minmax(0,1fr); gap:.7rem; padding:1rem 0; border-bottom:1px solid var(--color-border-light); }
.github-question-number { color:var(--color-primary); font-family:var(--font-mono); font-size:.72rem; font-weight:700; }
.github-question-row h3 { font-size:.78rem; line-height:1.45; overflow-wrap:anywhere; }
.github-question-row p { margin-top:.35rem; color:var(--color-ink-muted); font-size:.72rem; line-height:1.55; overflow-wrap:anywhere; }
.github-deep-action { display:flex; justify-content:center; margin-top:1.5rem; }
:global(.dark) .github-report-section { background:var(--color-surface); }
:global(.dark) .github-signal-band :deep(.flex.items-center) { background:var(--color-surface) !important; }
@media (max-width:900px) { .github-repo-header { align-items:flex-start; flex-direction:column; gap:1rem; } .github-signal-band, .github-report-grid { grid-template-columns:1fr; } .github-question-grid { grid-template-columns:1fr; } }
@media (max-width:560px) { .github-overview-page { padding-bottom:1rem; } .github-repo-copy h1 { font-size:1.35rem; } .github-report-section { padding:1rem; } .github-signal-band :deep(.flex.items-center) { padding:1rem !important; } }
</style>
