<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Check, FileScan, LayoutGrid, ListChecks, LoaderCircle, RefreshCw, Save, Scale, ShieldAlert } from 'lucide-vue-next'
import AnalysisLayout from '@/layouts/AnalysisLayout.vue'
import { api } from '@/api/index.js'
import { useResumeMatchTask } from '@/composables/useResumeMatchTask.js'

const route = useRoute()
const router = useRouter()
const taskId = route.params.taskId
const task = useResumeMatchTask()

const steps = [
  { key: 'extracting', title: '读取简历证据', detail: '识别经历、项目、技能与量化成果', icon: FileScan },
  { key: 'parsing_jd', title: '拆解岗位要求', detail: '区分硬性要求、优先条件与加分项', icon: ListChecks },
  { key: 'matching', title: '逐条匹配与评分', detail: '只使用简历中可验证的内容作为证据', icon: Scale },
  { key: 'saving', title: '整理匹配报告', detail: '保存后自动进入结构化报告页', icon: Save },
]

const stageIndex = computed(() => {
  if (task.status.value === 'completed') return steps.length
  const index = steps.findIndex((item) => item.key === task.stage.value)
  return index < 0 ? 0 : index
})

const title = computed(() => task.match.value?.resume?.file_name || '正在读取简历')

onMounted(() => task.start(taskId))

watch(task.status, (status) => {
  if (status === 'completed') {
    router.replace({ name: 'resume-match-report', params: { matchId: taskId } })
  }
})

async function retry() {
  await api.resumeResumeMatch(taskId)
  await task.start(taskId)
}
</script>

<template>
  <AnalysisLayout>
    <nav class="match-task-nav">
      <router-link :to="{ name: 'resume' }"><ArrowLeft :size="16" />返回简历匹配</router-link>
      <router-link :to="{ name: 'jd' }"><LayoutGrid :size="16" />前往其他模块</router-link>
    </nav>

    <section v-if="task.status.value === 'failed'" class="match-task-error">
      <ShieldAlert :size="30" />
      <h1>这次匹配没有完成</h1>
      <p>{{ task.error.value || '模型暂时没有生成有效报告，请稍后重试。' }}</p>
      <button type="button" class="btn btn--primary" @click="retry"><RefreshCw :size="16" />重新匹配</button>
    </section>

    <section v-else class="match-task-card">
      <div class="match-task-head">
        <div><span>简历匹配任务</span><h1>{{ title }}</h1></div>
        <strong>{{ Math.round(task.progress.value * 100) }}%</strong>
      </div>
      <div class="match-progress-track" aria-label="匹配进度">
        <span :style="{ width: `${Math.max(4, task.progress.value * 100)}%` }"></span>
      </div>
      <div class="match-task-steps">
        <div v-for="(step, index) in steps" :key="step.key" class="match-task-step" :class="{ done: index < stageIndex, active: index === stageIndex }">
          <div class="match-step-icon">
            <Check v-if="index < stageIndex" :size="16" />
            <LoaderCircle v-else-if="index === stageIndex" :size="16" class="spin" />
            <component :is="step.icon" v-else :size="16" />
          </div>
          <div><strong>{{ step.title }}</strong><span>{{ step.detail }}</span></div>
          <small>{{ index < stageIndex ? '完成' : index === stageIndex ? '进行中' : '等待' }}</small>
        </div>
      </div>
    </section>
  </AnalysisLayout>
</template>

<style scoped>
.match-task-nav { display:flex; justify-content:space-between; gap:1rem; margin-bottom:1.25rem; }
.match-task-nav a { display:inline-flex; align-items:center; gap:.4rem; color:var(--color-ink-muted); font-size:.82rem; }
.match-task-nav a:hover { color:var(--color-primary); }
.match-task-card, .match-task-error { padding:1.75rem; border:1px solid var(--color-border); border-radius:var(--radius-lg); background:var(--color-white); box-shadow:var(--shadow-sm); }
.match-task-head { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; }
.match-task-head span { color:var(--color-ink-muted); font-size:.75rem; }
.match-task-head h1 { margin-top:.35rem; font-size:1.25rem; overflow-wrap:anywhere; }
.match-task-head > strong { color:var(--color-primary); font-size:1rem; }
.match-progress-track { height:.45rem; overflow:hidden; margin:1.25rem 0 1.5rem; border-radius:999px; background:var(--color-surface-alt); }
.match-progress-track span { display:block; height:100%; border-radius:inherit; background:var(--color-primary); transition:width .35s var(--ease-out); }
.match-task-steps { display:grid; }
.match-task-step { display:grid; grid-template-columns:2.25rem minmax(0,1fr) auto; align-items:center; gap:.8rem; padding:1rem 0; border-bottom:1px solid var(--color-border-light); }
.match-task-step:last-child { border-bottom:0; }
.match-step-icon { width:2.1rem; height:2.1rem; display:grid; place-items:center; border-radius:var(--radius-sm); color:var(--color-ink-muted); background:var(--color-surface); }
.match-task-step.done .match-step-icon { color:var(--color-primary); background:color-mix(in srgb,var(--color-primary) 13%,transparent); }
.match-task-step.active .match-step-icon { color:#8a6515; background:color-mix(in srgb,var(--color-secondary) 22%,transparent); }
.match-task-step strong, .match-task-step span { display:block; }
.match-task-step strong { color:var(--color-ink); font-size:.88rem; }
.match-task-step span { margin-top:.2rem; color:var(--color-ink-muted); font-size:.75rem; }
.match-task-step small { color:var(--color-ink-muted); font-size:.7rem; }
.match-task-step.done small { color:var(--color-primary); }
.match-task-step.active small { color:#8a6515; }
.spin { animation:spin 1s linear infinite; }
.match-task-error { display:grid; justify-items:center; gap:.8rem; text-align:center; color:var(--color-accent); }
.match-task-error h1 { font-size:1.2rem; }
.match-task-error p { max-width:30rem; color:var(--color-ink-muted); font-size:.86rem; }
@keyframes spin { to { transform:rotate(360deg); } }
@media (max-width:560px) { .match-task-card, .match-task-error { padding:1.15rem; } .match-task-step { grid-template-columns:2.25rem minmax(0,1fr); } .match-task-step small { grid-column:2; } }
</style>
