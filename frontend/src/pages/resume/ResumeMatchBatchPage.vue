<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowUpRight, CheckCircle2, CircleAlert, LoaderCircle, RefreshCw } from 'lucide-vue-next'
import AnalysisLayout from '@/layouts/AnalysisLayout.vue'
import AnalysisErrorNotice from '@/components/common/AnalysisErrorNotice.vue'
import { api } from '@/api/index.js'

const route = useRoute()
const router = useRouter()
const batchId = route.params.batchId
const batch = ref(null)
const loading = ref(true)
const error = ref(null)
let timer = null

const isRunning = computed(() => batch.value && !['completed', 'failed'].includes(batch.value.status))
const rankedMatches = computed(() => batch.value?.matches || [])

onMounted(loadBatch)
onBeforeUnmount(() => clearTimeout(timer))

function scheduleRefresh() {
  clearTimeout(timer)
  if (isRunning.value) timer = setTimeout(loadBatch, 1800)
}

async function loadBatch() {
  try {
    error.value = null
    const data = await api.getResumeMatchBatch(batchId)
    batch.value = data
    if (!['completed', 'failed'].includes(data.status)) {
      await Promise.allSettled(
        data.matches
          .filter((item) => !['completed', 'failed'].includes(item.status))
          .map((item) => api.resumeResumeMatch(item.id)),
      )
    }
  } catch (e) {
    error.value = e.message || '无法恢复这组匹配任务'
  } finally {
    loading.value = false
    scheduleRefresh()
  }
}

function scoreOf(item) {
  return item.result?.score?.value ?? '--'
}

function jobTitle(item) {
  return item.result?.job?.title || item.jd_analysis?.job?.title || '未命名岗位'
}

function openMatch(item) {
  router.push({
    name: item.status === 'completed' ? 'resume-match-report' : 'resume-match-task',
    params: { [item.status === 'completed' ? 'matchId' : 'taskId']: item.id },
  })
}

function handleRowKeydown(event, item) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    openMatch(item)
  }
}
</script>

<template>
  <AnalysisLayout>
    <nav class="batch-nav">
      <router-link :to="{ name: 'resume' }"><ArrowLeft :size="16" />返回简历匹配</router-link>
      <button type="button" :disabled="loading" aria-label="刷新批次状态" @click="loadBatch"><RefreshCw :size="15" /></button>
    </nav>

    <div v-if="loading" class="batch-loading">
      <LoaderCircle :size="26" />
      <strong>正在恢复岗位匹配进度</strong>
      <span>离开当前页面不会中断后台任务。</span>
    </div>

    <AnalysisErrorNotice v-else-if="error" :message="error" @retry="loadBatch" />

    <template v-else-if="batch">
      <header class="batch-head">
        <div>
          <span>{{ isRunning ? '批量匹配进行中' : '岗位匹配对比' }}</span>
          <h1>{{ batch.resume?.file_name || '当前简历' }}</h1>
          <p v-if="isRunning">已完成 {{ batch.completed_count }} / {{ batch.total_count }} 个岗位，可以继续浏览其他模块。</p>
          <p v-else>按综合匹配分从高到低排列，每个岗位保留独立完整报告。</p>
        </div>
        <strong>{{ Math.round(batch.progress * 100) }}%</strong>
      </header>

      <div class="batch-progress" aria-label="总匹配进度"><span :style="{ width: `${Math.max(3, batch.progress * 100)}%` }"></span></div>

      <section class="batch-results" aria-label="岗位匹配结果">
        <article v-for="(item, index) in rankedMatches" :key="item.id" class="batch-result" :data-status="item.status" role="link" tabindex="0" @click="openMatch(item)" @keydown="handleRowKeydown($event, item)">
          <span class="batch-rank">{{ item.status === 'completed' ? String(index + 1).padStart(2, '0') : '--' }}</span>
          <div class="batch-job">
            <strong>{{ jobTitle(item) }}</strong>
            <span>{{ item.result?.job?.company || item.jd_analysis?.job?.company || '公司未注明' }}</span>
          </div>

          <div v-if="item.status === 'completed'" class="batch-metrics">
            <span>硬性要求 <strong>{{ item.result?.metrics?.required_coverage ?? '--' }}%</strong></span>
            <span>技能覆盖 <strong>{{ item.result?.metrics?.skill_coverage ?? '--' }}%</strong></span>
            <span>证据质量 <strong>{{ item.result?.metrics?.evidence_quality ?? '--' }}%</strong></span>
          </div>
          <div v-else class="batch-state">
            <CircleAlert v-if="item.status === 'failed'" :size="15" />
            <LoaderCircle v-else :size="15" />
            <span>{{ item.status === 'failed' ? '匹配失败，可单独重试' : '正在匹配简历证据' }}</span>
          </div>

          <div class="batch-score">
            <CheckCircle2 v-if="item.status === 'completed'" :size="15" />
            <strong>{{ scoreOf(item) }}</strong><small>/100</small>
          </div>

          <router-link
            v-if="item.status === 'completed'"
            :to="{ name: 'resume-match-report', params: { matchId: item.id } }"
            class="batch-open"
            aria-label="查看完整匹配报告"
            @click.stop
          ><ArrowUpRight :size="17" /></router-link>
          <router-link
            v-else
            :to="{ name: 'resume-match-task', params: { taskId: item.id } }"
            class="batch-open"
            aria-label="查看岗位任务状态"
            @click.stop
          ><ArrowUpRight :size="17" /></router-link>
        </article>
      </section>
    </template>
  </AnalysisLayout>
</template>

<style scoped>
.batch-nav { display:flex; align-items:center; justify-content:space-between; margin-bottom:1.2rem; }
.batch-nav a { display:inline-flex; align-items:center; gap:.4rem; color:var(--color-ink-muted); font-size:.8rem; }
.batch-nav a:hover { color:var(--color-primary); }
.batch-nav button { width:2.25rem; height:2.25rem; display:grid; place-items:center; border-radius:6px; color:var(--color-ink-muted); }
.batch-nav button:hover { color:var(--color-primary); background:var(--color-surface); }
.batch-loading { min-height:22rem; display:flex; align-items:center; justify-content:center; flex-direction:column; gap:.6rem; color:var(--color-ink-muted); text-align:center; }
.batch-loading svg, .batch-state svg { animation:spin 1s linear infinite; }
.batch-loading strong { color:var(--color-ink); font-size:.95rem; }
.batch-loading span { font-size:.75rem; }
.batch-head { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; }
.batch-head span { color:var(--color-primary); font-size:.7rem; font-weight:700; }
.batch-head h1 { margin-top:.35rem; font-size:1.45rem; overflow-wrap:anywhere; }
.batch-head p { margin-top:.4rem; color:var(--color-ink-muted); font-size:.8rem; }
.batch-head > strong { color:var(--color-primary); font-size:1.15rem; }
.batch-progress { height:.42rem; overflow:hidden; margin:1.1rem 0 1.4rem; border-radius:999px; background:var(--color-surface-alt); }
.batch-progress span { display:block; height:100%; border-radius:inherit; background:var(--color-primary); transition:width .3s; }
.batch-results { border-top:1px solid var(--color-border); }
.batch-result { min-width:0; display:grid; grid-template-columns:2rem minmax(11rem,1.1fr) minmax(16rem,1.6fr) 5rem 2.25rem; align-items:center; gap:1rem; padding:1rem .25rem; border-bottom:1px solid var(--color-border-light); cursor:pointer; transition:background .18s, border-color .18s, transform .18s; }
.batch-result:hover { background:color-mix(in srgb,var(--color-primary) 5%,var(--color-base)); border-bottom-color:color-mix(in srgb,var(--color-primary) 28%,var(--color-border-light)); }
.batch-result:focus-visible { outline:2px solid var(--color-primary); outline-offset:-2px; background:color-mix(in srgb,var(--color-primary) 7%,var(--color-base)); }
.batch-rank { color:var(--color-secondary); font-size:.72rem; font-weight:800; }
.batch-job { min-width:0; }
.batch-job strong, .batch-job span { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.batch-job strong { color:var(--color-ink); font-size:.86rem; }
.batch-job span { margin-top:.25rem; color:var(--color-ink-muted); font-size:.7rem; }
.batch-metrics { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.6rem; }
.batch-metrics span { color:var(--color-ink-muted); font-size:.65rem; }
.batch-metrics strong { display:block; margin-top:.2rem; color:var(--color-ink); font-size:.75rem; }
.batch-state { display:flex; align-items:center; gap:.4rem; color:var(--color-ink-muted); font-size:.72rem; }
.batch-result[data-status="failed"] .batch-state { color:var(--color-accent); }
.batch-result[data-status="failed"] .batch-state svg { animation:none; }
.batch-score { display:flex; align-items:baseline; justify-content:flex-end; color:var(--color-primary); }
.batch-score svg { align-self:center; margin-right:.3rem; }
.batch-score strong { font-size:1.25rem; }
.batch-score small { margin-left:.15rem; color:var(--color-ink-muted); font-size:.6rem; }
.batch-open { width:2.2rem; height:2.2rem; display:grid; place-items:center; border-radius:6px; color:var(--color-ink-muted); }
.batch-open:hover { color:white; background:var(--color-primary); }
@keyframes spin { to { transform:rotate(360deg); } }
@media (max-width:850px) { .batch-result { grid-template-columns:1.5rem minmax(0,1fr) 4.5rem 2.25rem; gap:.65rem; } .batch-metrics, .batch-state { grid-column:2 / -1; grid-row:2; } }
@media (max-width:560px) { .batch-result { grid-template-columns:1.3rem minmax(0,1fr) 2.2rem; } .batch-score { grid-column:2; justify-content:flex-start; } .batch-open { grid-column:3; grid-row:1 / 3; } .batch-metrics, .batch-state { grid-column:2; grid-row:auto; } .batch-metrics { grid-template-columns:1fr 1fr; } }
</style>
